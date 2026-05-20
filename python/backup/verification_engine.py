#!/usr/bin/env python3
"""
Verification Engine for Backup Integrity

This module provides cryptographic hash-based integrity checking and corruption
detection for backup snapshots and files.
"""

import os
import sys
import json
import hashlib
import hmac
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
import concurrent.futures
import logging

class VerificationEngine:
    """
    Handles integrity verification through cryptographic hashing and corruption detection.
    """

    def __init__(self, workspace_root: Path, max_workers: int = 4):
        self.workspace_root = workspace_root
        self.max_workers = max_workers
        self.logger = logging.getLogger("VerificationEngine")
        self.logger.setLevel(logging.INFO)

        # Hash algorithms in order of preference
        self.hash_algorithms = ['sha256', 'md5']  # sha256 primary, md5 fallback

        # Verification thresholds
        self.corruption_threshold_percent = 5.0  # Alert if >5% files corrupted
        self.missing_threshold_percent = 1.0     # Alert if >1% files missing

    def calculate_file_hash(self, file_path: Path, algorithm: str = 'sha256') -> Optional[str]:
        """
        Calculate cryptographic hash of file content.

        Args:
            file_path: Path to file to hash
            algorithm: Hash algorithm ('sha256', 'md5')

        Returns:
            Hexadecimal hash string or None if error
        """
        if algorithm not in self.hash_algorithms:
            algorithm = 'sha256'

        hash_func = getattr(hashlib, algorithm, None)
        if not hash_func:
            return None

        try:
            hasher = hash_func()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):  # 64KB chunks
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, IOError, PermissionError) as e:
            self.logger.error(f"Failed to hash file {file_path}: {e}")
            return None

    def calculate_directory_hash(self, dir_path: Path, algorithm: str = 'sha256') -> Dict:
        """
        Calculate hash of all files in directory with metadata.

        Returns directory manifest with file hashes and statistics.
        """
        manifest = {
            "directory": str(dir_path),
            "algorithm": algorithm,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files": {},
            "statistics": {
                "total_files": 0,
                "total_size_bytes": 0,
                "errors": 0
            }
        }

        def process_file(file_path: Path) -> Tuple[str, Dict]:
            relative_path = file_path.relative_to(dir_path)
            file_info = {
                "size_bytes": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat()
            }

            file_hash = self.calculate_file_hash(file_path, algorithm)
            if file_hash:
                file_info["hash"] = file_hash
            else:
                file_info["error"] = "hash_calculation_failed"
                manifest["statistics"]["errors"] += 1

            return str(relative_path), file_info

        # Collect all files
        all_files = []
        try:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    all_files.append(file_path)
        except PermissionError as e:
            manifest["error"] = f"Permission denied accessing directory: {e}"
            return manifest

        # Process files in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(process_file, fp): fp for fp in all_files}

            for future in concurrent.futures.as_completed(future_to_file):
                relative_path, file_info = future.result()
                manifest["files"][relative_path] = file_info
                manifest["statistics"]["total_files"] += 1
                manifest["statistics"]["total_size_bytes"] += file_info.get("size_bytes", 0)

        # Calculate directory hash (hash of all file hashes concatenated)
        if manifest["files"]:
            combined_hash = hashlib.sha256()
            for file_path in sorted(manifest["files"].keys()):
                file_hash = manifest["files"][file_path].get("hash")
                if file_hash:
                    combined_hash.update(file_hash.encode('utf-8'))
            manifest["directory_hash"] = combined_hash.hexdigest()

        return manifest

    def verify_file_integrity(self, file_path: Path, expected_hash: str,
                            algorithm: str = 'sha256') -> Dict:
        """
        Verify single file integrity against expected hash.

        Returns verification result with details.
        """
        result = {
            "file_path": str(file_path),
            "expected_hash": expected_hash,
            "algorithm": algorithm,
            "verified": False,
            "error": None
        }

        if not file_path.exists():
            result["error"] = "file_not_found"
            return result

        actual_hash = self.calculate_file_hash(file_path, algorithm)
        if actual_hash is None:
            result["error"] = "hash_calculation_failed"
            return result

        result["actual_hash"] = actual_hash
        result["verified"] = (actual_hash == expected_hash)

        if not result["verified"]:
            result["error"] = "hash_mismatch"

        return result

    def verify_directory_integrity(self, dir_path: Path, manifest: Dict) -> Dict:
        """
        Verify directory integrity against manifest.

        Returns comprehensive verification report.
        """
        verification = {
            "directory": str(dir_path),
            "manifest_timestamp": manifest.get("timestamp"),
            "verification_timestamp": datetime.now(timezone.utc).isoformat(),
            "algorithm": manifest.get("algorithm", "sha256"),
            "files_verified": 0,
            "files_ok": 0,
            "files_corrupted": 0,
            "files_missing": 0,
            "files_extra": 0,
            "errors": [],
            "file_results": {}
        }

        manifest_files = set(manifest.get("files", {}).keys())

        # Check all files in manifest
        for relative_path in manifest_files:
            file_path = dir_path / relative_path
            expected_info = manifest["files"][relative_path]

            verification["files_verified"] += 1

            if not file_path.exists():
                verification["files_missing"] += 1
                verification["file_results"][relative_path] = {
                    "status": "missing",
                    "expected_size": expected_info.get("size_bytes")
                }
                continue

            # Check file size first (quick check)
            actual_size = file_path.stat().st_size
            expected_size = expected_info.get("size_bytes", 0)

            if actual_size != expected_size:
                verification["files_corrupted"] += 1
                verification["file_results"][relative_path] = {
                    "status": "size_mismatch",
                    "expected_size": expected_size,
                    "actual_size": actual_size
                }
                continue

            # Check hash
            expected_hash = expected_info.get("hash")
            if expected_hash:
                result = self.verify_file_integrity(file_path, expected_hash, verification["algorithm"])
                if result["verified"]:
                    verification["files_ok"] += 1
                    verification["file_results"][relative_path] = {"status": "ok"}
                else:
                    verification["files_corrupted"] += 1
                    verification["file_results"][relative_path] = {
                        "status": "corrupted",
                        "error": result.get("error"),
                        "expected_hash": expected_hash,
                        "actual_hash": result.get("actual_hash")
                    }
            else:
                # No hash to check, assume OK if size matches
                verification["files_ok"] += 1
                verification["file_results"][relative_path] = {"status": "ok_no_hash"}

        # Check for extra files not in manifest
        try:
            actual_files = set()
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(dir_path)
                    actual_files.add(str(relative_path))

            extra_files = actual_files - manifest_files
            verification["files_extra"] = len(extra_files)
            for extra_file in extra_files:
                verification["file_results"][extra_file] = {"status": "extra"}

        except PermissionError as e:
            verification["errors"].append(f"Permission denied scanning directory: {e}")

        # Calculate percentages
        if verification["files_verified"] > 0:
            verification["corruption_rate_percent"] = (
                verification["files_corrupted"] / verification["files_verified"] * 100
            )
            verification["missing_rate_percent"] = (
                verification["files_missing"] / verification["files_verified"] * 100
            )

        # Overall status
        verification["overall_status"] = "ok"
        if verification["files_corrupted"] > 0:
            verification["overall_status"] = "corrupted"
        if verification["files_missing"] > 0:
            verification["overall_status"] = "incomplete"
        if verification["files_corrupted"] > 0 and verification["files_missing"] > 0:
            verification["overall_status"] = "compromised"

        # Check against thresholds
        corruption_rate = verification.get("corruption_rate_percent", 0)
        missing_rate = verification.get("missing_rate_percent", 0)

        verification["thresholds_exceeded"] = {
            "corruption": corruption_rate > self.corruption_threshold_percent,
            "missing": missing_rate > self.missing_threshold_percent
        }

        return verification

    def verify_backup_snapshot(self, snapshot_dir: Path) -> Dict:
        """
        Verify integrity of a backup snapshot.

        Expects snapshot directory with metadata.json and backup files.
        """
        metadata_path = snapshot_dir / "metadata.json"

        if not metadata_path.exists():
            return {
                "snapshot": str(snapshot_dir),
                "verified": False,
                "error": "metadata_not_found"
            }

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return {
                "snapshot": str(snapshot_dir),
                "verified": False,
                "error": f"metadata_corrupted: {e}"
            }

        # Verify the snapshot directory itself
        verification = self.verify_directory_integrity(snapshot_dir, metadata)

        # Add snapshot-specific information
        verification["snapshot_name"] = metadata.get("snapshot_name")
        verification["snapshot_type"] = metadata.get("snapshot_type", "unknown")
        verification["created_at"] = metadata.get("created_at")

        return verification

    def generate_integrity_report(self, verifications: List[Dict]) -> Dict:
        """
        Generate comprehensive integrity report from multiple verifications.
        """
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_verifications": len(verifications),
            "summary": {
                "ok": 0,
                "corrupted": 0,
                "incomplete": 0,
                "compromised": 0,
                "errors": 0
            },
            "threshold_alerts": {
                "corruption_threshold_exceeded": [],
                "missing_threshold_exceeded": []
            },
            "details": verifications
        }

        for verification in verifications:
            status = verification.get("overall_status", "unknown")
            if status in report["summary"]:
                report["summary"][status] += 1
            else:
                report["summary"]["errors"] += 1

            # Check thresholds
            thresholds = verification.get("thresholds_exceeded", {})
            if thresholds.get("corruption"):
                report["threshold_alerts"]["corruption_threshold_exceeded"].append(
                    verification.get("directory", verification.get("snapshot", "unknown"))
                )
            if thresholds.get("missing"):
                report["threshold_alerts"]["missing_threshold_exceeded"].append(
                    verification.get("directory", verification.get("snapshot", "unknown"))
                )

        # Overall assessment
        if report["summary"]["compromised"] > 0 or report["summary"]["corrupted"] > 0:
            report["overall_assessment"] = "CRITICAL"
        elif report["summary"]["incomplete"] > 0:
            report["overall_assessment"] = "WARNING"
        else:
            report["overall_assessment"] = "HEALTHY"

        return report

    def create_hmac_signature(self, data: str, key: str) -> str:
        """
        Create HMAC signature for data integrity verification.
        """
        return hmac.new(key.encode(), data.encode(), hashlib.sha256).hexdigest()

    def verify_hmac_signature(self, data: str, signature: str, key: str) -> bool:
        """
        Verify HMAC signature for data integrity.
        """
        expected_signature = self.create_hmac_signature(data, key)
        return hmac.compare_digest(expected_signature, signature)


def main():
    """CLI interface for integrity verification."""
    import argparse

    parser = argparse.ArgumentParser(description="Backup Integrity Verification Engine")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace root directory")
    parser.add_argument("--verify-file", nargs=2, help="Verify single file: <file_path> <expected_hash>")
    parser.add_argument("--verify-dir", type=str, help="Verify directory against manifest file")
    parser.add_argument("--manifest", type=str, help="Manifest file for directory verification")
    parser.add_argument("--verify-snapshot", type=str, help="Verify backup snapshot directory")
    parser.add_argument("--create-manifest", type=str, help="Create integrity manifest for directory")
    parser.add_argument("--output", type=str, help="Output file for results")

    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    engine = VerificationEngine(workspace_root)

    if args.verify_file:
        file_path, expected_hash = args.verify_file
        result = engine.verify_file_integrity(Path(file_path), expected_hash)
        output = json.dumps(result, indent=2)
        print(output)

    elif args.verify_dir and args.manifest:
        dir_path = Path(args.verify_dir)
        with open(args.manifest, 'r') as f:
            manifest = json.load(f)

        result = engine.verify_directory_integrity(dir_path, manifest)
        output = json.dumps(result, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
        else:
            print(output)

    elif args.verify_snapshot:
        snapshot_dir = Path(args.verify_snapshot)
        result = engine.verify_backup_snapshot(snapshot_dir)
        output = json.dumps(result, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
        else:
            print(output)

    elif args.create_manifest:
        dir_path = Path(args.create_manifest)
        manifest = engine.calculate_directory_hash(dir_path)
        output = json.dumps(manifest, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
        else:
            print(output)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
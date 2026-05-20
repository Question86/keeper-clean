#!/usr/bin/env python3
"""
Snapshot Engine for Automated Backup System

This module handles compressed workspace imaging with metadata preservation,
providing efficient snapshot creation and management.
"""

import os
import sys
import json
import hashlib
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
import logging

class SnapshotEngine:
    """
    Handles compressed workspace imaging with intelligent file prioritization
    and metadata preservation for backup snapshots.
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.logger = logging.getLogger("SnapshotEngine")
        self.logger.setLevel(logging.INFO)

        # Compression settings
        self.compression_level = 6  # Balanced speed/compression
        self.max_file_size_mb = 100  # Skip files larger than 100MB

        # File type priorities for compression
        self.priority_extensions = {
            '.md', '.json', '.py', '.txt', '.csv', '.log',  # Text files
            '.html', '.css', '.js', '.xml', '.yaml', '.yml'  # Config files
        }

        self.binary_extensions = {
            '.zip', '.tar', '.gz', '.bz2', '.7z',  # Archives
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',  # Images
            '.mp4', '.avi', '.mkv', '.mov',  # Videos
            '.mp3', '.wav', '.flac',  # Audio
            '.pdf', '.doc', '.docx', '.xls', '.xlsx'  # Documents
        }

    def should_compress_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be included in compression based on size and type.
        """
        # Check file size
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                self.logger.warning(f"Skipping large file: {file_path} ({file_size_mb:.1f}MB)")
                return False
        except OSError:
            return False

        # Check file extension
        extension = file_path.suffix.lower()

        # Always include priority files
        if extension in self.priority_extensions:
            return True

        # Include binary files only if they're not too large
        if extension in self.binary_extensions:
            return file_size_mb < 10  # 10MB limit for binary files

        # Include other small files
        return file_size_mb < 1  # 1MB limit for unknown types

    def create_incremental_snapshot(self, previous_snapshot_path: Optional[Path] = None) -> Dict:
        """
        Create an incremental snapshot based on a previous full snapshot.

        This saves space by only storing changed files.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"incremental_{timestamp}"

        metadata = {
            "snapshot_type": "incremental",
            "snapshot_name": snapshot_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "base_snapshot": str(previous_snapshot_path) if previous_snapshot_path else None,
            "files": {},
            "statistics": {
                "total_files": 0,
                "changed_files": 0,
                "new_files": 0,
                "deleted_files": 0,
                "total_size_bytes": 0
            }
        }

        # For incremental snapshots, we'd need to compare against base
        # For now, fall back to full snapshot logic
        self.logger.info("Incremental snapshot not yet implemented, creating full snapshot")
        return self.create_full_snapshot(snapshot_name)

    def create_full_snapshot(self, snapshot_name: str) -> Dict:
        """
        Create a full compressed snapshot of the workspace.
        """
        metadata = {
            "snapshot_type": "full",
            "snapshot_name": snapshot_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workspace_root": str(self.workspace_root),
            "files": {},
            "statistics": {
                "total_files": 0,
                "compressed_files": 0,
                "skipped_files": 0,
                "total_size_bytes": 0,
                "compressed_size_bytes": 0
            }
        }

        # Create temporary zip file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            temp_zip_path = Path(temp_zip.name)

        try:
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=self.compression_level) as zipf:
                # Walk through workspace
                for file_path in self.workspace_root.rglob('*'):
                    if not file_path.is_file():
                        continue

                    # Skip backup directory and other excluded paths
                    if any(part.startswith('.') or part == 'backup' or part == '__pycache__'
                           for part in file_path.parts):
                        continue

                    relative_path = file_path.relative_to(self.workspace_root)
                    metadata["statistics"]["total_files"] += 1

                    try:
                        file_size = file_path.stat().st_size
                        file_hash = self._calculate_file_hash(file_path)

                        if self.should_compress_file(file_path):
                            # Add to zip
                            zipf.write(file_path, relative_path)
                            metadata["statistics"]["compressed_files"] += 1
                            metadata["statistics"]["total_size_bytes"] += file_size

                            metadata["files"][str(relative_path)] = {
                                "size_bytes": file_size,
                                "hash": file_hash,
                                "compressed": True,
                                "included": True
                            }
                        else:
                            # Track but don't compress
                            metadata["statistics"]["skipped_files"] += 1
                            metadata["files"][str(relative_path)] = {
                                "size_bytes": file_size,
                                "hash": file_hash,
                                "compressed": False,
                                "included": False,
                                "reason": "size_or_type_excluded"
                            }

                    except (OSError, IOError) as e:
                        self.logger.error(f"Failed to process file {file_path}: {e}")
                        metadata["files"][str(relative_path)] = {
                            "error": str(e),
                            "included": False
                        }

            # Get compressed size
            metadata["statistics"]["compressed_size_bytes"] = temp_zip_path.stat().st_size

            # Calculate compression ratio
            if metadata["statistics"]["total_size_bytes"] > 0:
                ratio = (1 - metadata["statistics"]["compressed_size_bytes"] /
                        metadata["statistics"]["total_size_bytes"]) * 100
                metadata["statistics"]["compression_ratio_percent"] = round(ratio, 1)

            self.logger.info(f"Created full snapshot: {snapshot_name} "
                           f"({metadata['statistics']['compressed_files']} files compressed, "
                           f"{metadata['statistics']['compression_ratio_percent']}% ratio)")

            return metadata, temp_zip_path

        except Exception as e:
            # Clean up temp file on error
            if temp_zip_path.exists():
                temp_zip_path.unlink()
            raise e

    def extract_snapshot(self, snapshot_zip_path: Path, extract_to: Path,
                        files_to_extract: Optional[List[str]] = None) -> Dict:
        """
        Extract files from a snapshot zip.

        Args:
            snapshot_zip_path: Path to the snapshot zip file
            extract_to: Directory to extract to
            files_to_extract: List of specific files to extract (None for all)

        Returns:
            Extraction metadata
        """
        extract_to.mkdir(parents=True, exist_ok=True)

        metadata = {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "source_zip": str(snapshot_zip_path),
            "extract_to": str(extract_to),
            "files_extracted": 0,
            "total_size_bytes": 0,
            "errors": []
        }

        try:
            with zipfile.ZipFile(snapshot_zip_path, 'r') as zipf:
                # Get list of files to extract
                if files_to_extract:
                    members = [name for name in zipf.namelist()
                             if any(name.endswith(file) or file in name for file in files_to_extract)]
                else:
                    members = zipf.namelist()

                # Extract files
                for member in members:
                    try:
                        zipf.extract(member, extract_to)
                        file_info = zipf.getinfo(member)
                        metadata["files_extracted"] += 1
                        metadata["total_size_bytes"] += file_info.file_size
                    except Exception as e:
                        metadata["errors"].append(f"Failed to extract {member}: {e}")

        except (zipfile.BadZipFile, IOError) as e:
            metadata["errors"].append(f"Failed to open zip file: {e}")

        self.logger.info(f"Extracted {metadata['files_extracted']} files from snapshot")

        return metadata

    def compare_snapshots(self, snapshot1_metadata: Dict, snapshot2_metadata: Dict) -> Dict:
        """
        Compare two snapshots to identify changes.

        Returns analysis of added, modified, and deleted files.
        """
        comparison = {
            "snapshot1": snapshot1_metadata["snapshot_name"],
            "snapshot2": snapshot2_metadata["snapshot_name"],
            "comparison": {
                "added": [],
                "modified": [],
                "deleted": [],
                "unchanged": []
            },
            "statistics": {
                "total_files_snapshot1": len(snapshot1_metadata.get("files", {})),
                "total_files_snapshot2": len(snapshot2_metadata.get("files", {})),
                "files_added": 0,
                "files_modified": 0,
                "files_deleted": 0,
                "files_unchanged": 0
            }
        }

        files1 = snapshot1_metadata.get("files", {})
        files2 = snapshot2_metadata.get("files", {})

        # Find added and modified files
        for file_path, file_info2 in files2.items():
            if file_path not in files1:
                comparison["comparison"]["added"].append(file_path)
                comparison["statistics"]["files_added"] += 1
            elif files1[file_path].get("hash") != file_info2.get("hash"):
                comparison["comparison"]["modified"].append(file_path)
                comparison["statistics"]["files_modified"] += 1
            else:
                comparison["comparison"]["unchanged"].append(file_path)
                comparison["statistics"]["files_unchanged"] += 1

        # Find deleted files
        for file_path in files1:
            if file_path not in files2:
                comparison["comparison"]["deleted"].append(file_path)
                comparison["statistics"]["files_deleted"] += 1

        return comparison

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except (OSError, IOError):
            return ""

    def get_snapshot_info(self, snapshot_zip_path: Path) -> Dict:
        """Get information about a snapshot without extracting it."""
        info = {
            "zip_path": str(snapshot_zip_path),
            "file_count": 0,
            "total_size_bytes": 0,
            "compressed_size_bytes": snapshot_zip_path.stat().st_size,
            "files": [],
            "errors": []
        }

        try:
            with zipfile.ZipFile(snapshot_zip_path, 'r') as zipf:
                for file_info in zipf.filelist:
                    info["file_count"] += 1
                    info["total_size_bytes"] += file_info.file_size
                    info["files"].append({
                        "name": file_info.filename,
                        "size_bytes": file_info.file_size,
                        "compressed_size": file_info.compress_size,
                        "compression_ratio": (1 - file_info.compress_size / file_info.file_size) * 100
                        if file_info.file_size > 0 else 0
                    })

        except (zipfile.BadZipFile, IOError) as e:
            info["errors"].append(str(e))

        if info["total_size_bytes"] > 0:
            info["overall_compression_ratio"] = (
                (1 - info["compressed_size_bytes"] / info["total_size_bytes"]) * 100
            )

        return info


def main():
    """CLI interface for snapshot operations."""
    import argparse

    parser = argparse.ArgumentParser(description="Snapshot Engine for Backup System")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace root directory")
    parser.add_argument("--create-full", type=str, help="Create full snapshot with given name")
    parser.add_argument("--extract", type=str, help="Extract snapshot zip file")
    parser.add_argument("--extract-to", type=str, default="./extracted", help="Directory to extract to")
    parser.add_argument("--info", type=str, help="Get info about snapshot zip")
    parser.add_argument("--compare", nargs=2, help="Compare two snapshot metadata files")

    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    engine = SnapshotEngine(workspace_root)

    if args.create_full:
        try:
            metadata, zip_path = engine.create_full_snapshot(args.create_full)
            print(f"Created full snapshot: {args.create_full}")
            print(f"Files compressed: {metadata['statistics']['compressed_files']}")
            print(f"Compression ratio: {metadata['statistics'].get('compression_ratio_percent', 0)}%")
            print(f"Zip saved to: {zip_path}")
        except Exception as e:
            print(f"Error creating snapshot: {e}")
            sys.exit(1)

    elif args.extract:
        zip_path = Path(args.extract)
        extract_to = Path(args.extract_to)

        if not zip_path.exists():
            print(f"Snapshot file not found: {zip_path}")
            sys.exit(1)

        try:
            result = engine.extract_snapshot(zip_path, extract_to)
            print(f"Extracted {result['files_extracted']} files to {extract_to}")
            if result['errors']:
                print("Errors during extraction:")
                for error in result['errors']:
                    print(f"  {error}")
        except Exception as e:
            print(f"Error extracting snapshot: {e}")
            sys.exit(1)

    elif args.info:
        zip_path = Path(args.info)
        if not zip_path.exists():
            print(f"Snapshot file not found: {zip_path}")
            sys.exit(1)

        try:
            info = engine.get_snapshot_info(zip_path)
            print(f"Snapshot Info: {zip_path.name}")
            print(f"Files: {info['file_count']}")
            print(f"Original size: {info['total_size_bytes']} bytes")
            print(f"Compressed size: {info['compressed_size_bytes']} bytes")
            if 'overall_compression_ratio' in info:
                print(f"Compression ratio: {info['overall_compression_ratio']:.1f}%")
            if info['errors']:
                print("Errors:")
                for error in info['errors']:
                    print(f"  {error}")
        except Exception as e:
            print(f"Error getting snapshot info: {e}")
            sys.exit(1)

    elif args.compare:
        meta1_path, meta2_path = args.compare

        try:
            with open(meta1_path, 'r') as f:
                meta1 = json.load(f)
            with open(meta2_path, 'r') as f:
                meta2 = json.load(f)

            comparison = engine.compare_snapshots(meta1, meta2)
            print(f"Comparing {comparison['snapshot1']} vs {comparison['snapshot2']}")
            print(f"Files added: {comparison['statistics']['files_added']}")
            print(f"Files modified: {comparison['statistics']['files_modified']}")
            print(f"Files deleted: {comparison['statistics']['files_deleted']}")
            print(f"Files unchanged: {comparison['statistics']['files_unchanged']}")

        except Exception as e:
            print(f"Error comparing snapshots: {e}")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
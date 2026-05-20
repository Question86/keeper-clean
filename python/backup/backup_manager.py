#!/usr/bin/env python3
"""
Automated Backup Infrastructure Implementation

This module implements the core backup orchestration engine for the Keeper project,
providing automated workspace snapshots with 30-minute intervals, critical file
prioritization, and integrity verification.
"""

import os
import sys
import json
import hashlib
import shutil
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Tuple
import threading
import schedule
import logging

class BackupManager:
    """
    Core backup orchestration engine with automated snapshots and integrity verification.
    """

    def __init__(self, workspace_root: Path, backup_interval_minutes: int = 30):
        self.workspace_root = workspace_root
        self.backup_interval = backup_interval_minutes
        self.backup_root = workspace_root / "backup" / "snapshots"
        self.backup_root.mkdir(parents=True, exist_ok=True)

        # Critical files that get priority backup
        self.critical_files = {
            "current.json",
            "NEU.md",
            "Alt.md",
            "_LOOP_GATE.md",
            "PROJECT_TECH_BASELINE.md",
            "NEURAL_CORTEX.md"
        }

        # Task files pattern
        self.task_pattern = "task_TASK_*.md"

        # Setup logging
        self.logger = logging.getLogger("BackupManager")
        self.logger.setLevel(logging.INFO)

        # Background scheduler
        self.scheduler = schedule.Scheduler()
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None

    def get_critical_files(self) -> Set[Path]:
        """Get all critical files that exist in workspace."""
        critical_paths = set()

        # Add explicitly critical files
        for filename in self.critical_files:
            path = self.workspace_root / filename
            if path.exists():
                critical_paths.add(path)

        # Add all task files
        for pattern in [self.task_pattern]:
            for path in self.workspace_root.glob(pattern):
                if path.is_file():
                    critical_paths.add(path)

        return critical_paths

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except (OSError, IOError) as e:
            self.logger.error(f"Failed to hash file {file_path}: {e}")
            return ""

    def create_snapshot(self, snapshot_name: Optional[str] = None) -> Dict:
        """
        Create a compressed snapshot of the workspace.

        Returns metadata about the snapshot including file hashes and statistics.
        """
        if snapshot_name is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            snapshot_name = f"snapshot_{timestamp}"

        snapshot_dir = self.backup_root / snapshot_name
        snapshot_dir.mkdir(exist_ok=True)

        metadata = {
            "snapshot_name": snapshot_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workspace_root": str(self.workspace_root),
            "files": {},
            "statistics": {
                "total_files": 0,
                "critical_files": 0,
                "total_size_bytes": 0,
                "compressed_size_bytes": 0
            }
        }

        critical_files = self.get_critical_files()
        total_size = 0

        # Copy critical files first
        for file_path in critical_files:
            if file_path.exists():
                relative_path = file_path.relative_to(self.workspace_root)
                backup_path = snapshot_dir / relative_path

                # Create subdirectories if needed
                backup_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    # Copy file
                    shutil.copy2(file_path, backup_path)

                    # Calculate hash
                    file_hash = self.calculate_file_hash(file_path)
                    file_size = file_path.stat().st_size
                    total_size += file_size

                    metadata["files"][str(relative_path)] = {
                        "hash": file_hash,
                        "size_bytes": file_size,
                        "is_critical": True,
                        "backed_up": True
                    }

                    metadata["statistics"]["critical_files"] += 1

                except (OSError, IOError) as e:
                    self.logger.error(f"Failed to backup critical file {file_path}: {e}")
                    metadata["files"][str(relative_path)] = {
                        "error": str(e),
                        "is_critical": True,
                        "backed_up": False
                    }

        # Copy entire workspace for full backup (compressed)
        try:
            import zipfile

            zip_path = snapshot_dir / "workspace_full.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self.workspace_root.rglob('*'):
                    if file_path.is_file() and not str(file_path).startswith(str(snapshot_dir)):
                        relative_path = file_path.relative_to(self.workspace_root)
                        zipf.write(file_path, relative_path)
                        metadata["statistics"]["total_files"] += 1

            metadata["statistics"]["compressed_size_bytes"] = zip_path.stat().st_size
            metadata["statistics"]["total_size_bytes"] = total_size

        except ImportError:
            self.logger.warning("zipfile not available, skipping full workspace compression")
        except Exception as e:
            self.logger.error(f"Failed to create full workspace backup: {e}")

        # Save metadata
        metadata_path = snapshot_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Created snapshot: {snapshot_name} ({metadata['statistics']['critical_files']} critical files)")

        return metadata

    def verify_snapshot_integrity(self, snapshot_name: str) -> Dict:
        """
        Verify integrity of a snapshot by comparing file hashes.

        Returns verification results.
        """
        snapshot_dir = self.backup_root / snapshot_name
        metadata_path = snapshot_dir / "metadata.json"

        if not metadata_path.exists():
            return {"valid": False, "error": "Metadata file not found"}

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return {"valid": False, "error": f"Failed to read metadata: {e}"}

        verification_results = {
            "snapshot_name": snapshot_name,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "files_checked": 0,
            "files_valid": 0,
            "files_invalid": 0,
            "files_missing": 0,
            "details": {}
        }

        for file_path_str, file_info in metadata.get("files", {}).items():
            if not file_info.get("backed_up", False):
                continue

            file_path = Path(file_path_str)
            backup_path = snapshot_dir / file_path

            verification_results["files_checked"] += 1

            if not backup_path.exists():
                verification_results["files_missing"] += 1
                verification_results["details"][file_path_str] = "missing"
                continue

            current_hash = self.calculate_file_hash(backup_path)
            original_hash = file_info.get("hash", "")

            if current_hash == original_hash:
                verification_results["files_valid"] += 1
                verification_results["details"][file_path_str] = "valid"
            else:
                verification_results["files_invalid"] += 1
                verification_results["details"][file_path_str] = "corrupted"

        verification_results["valid"] = (
            verification_results["files_invalid"] == 0 and
            verification_results["files_missing"] == 0
        )

        return verification_results

    def list_snapshots(self) -> List[Dict]:
        """List all available snapshots with metadata."""
        snapshots = []

        if not self.backup_root.exists():
            return snapshots

        for snapshot_dir in sorted(self.backup_root.iterdir()):
            if snapshot_dir.is_dir():
                metadata_path = snapshot_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        snapshots.append(metadata)
                    except (json.JSONDecodeError, IOError):
                        # Skip corrupted metadata
                        continue

        return snapshots

    def cleanup_old_snapshots(self, keep_hours: int = 24, keep_days: int = 7) -> Dict:
        """
        Clean up old snapshots based on retention policy.

        - Keep all snapshots from last 24 hours
        - Keep one daily snapshot for last 7 days
        - Remove older snapshots
        """
        cleanup_results = {
            "snapshots_before": 0,
            "snapshots_removed": 0,
            "space_freed_bytes": 0,
            "errors": []
        }

        snapshots = self.list_snapshots()
        cleanup_results["snapshots_before"] = len(snapshots)

        if not snapshots:
            return cleanup_results

        now = datetime.now(timezone.utc)
        snapshots_to_keep = set()

        # Keep all from last 24 hours
        for snapshot in snapshots:
            created_at = datetime.fromisoformat(snapshot["created_at"])
            if (now - created_at).total_seconds() < (keep_hours * 3600):
                snapshots_to_keep.add(snapshot["snapshot_name"])

        # Keep one per day for last 7 days
        daily_snapshots = {}
        for snapshot in snapshots:
            created_at = datetime.fromisoformat(snapshot["created_at"])
            days_ago = (now - created_at).days
            if days_ago <= keep_days:
                date_key = created_at.strftime("%Y-%m-%d")
                if date_key not in daily_snapshots or created_at > datetime.fromisoformat(daily_snapshots[date_key]["created_at"]):
                    daily_snapshots[date_key] = snapshot

        for snapshot in daily_snapshots.values():
            snapshots_to_keep.add(snapshot["snapshot_name"])

        # Remove snapshots not in keep set
        for snapshot in snapshots:
            if snapshot["snapshot_name"] not in snapshots_to_keep:
                snapshot_dir = self.backup_root / snapshot["snapshot_name"]
                try:
                    size_before = sum(f.stat().st_size for f in snapshot_dir.rglob('*') if f.is_file())
                    shutil.rmtree(snapshot_dir)
                    cleanup_results["snapshots_removed"] += 1
                    cleanup_results["space_freed_bytes"] += size_before
                    self.logger.info(f"Removed old snapshot: {snapshot['snapshot_name']}")
                except Exception as e:
                    cleanup_results["errors"].append(f"Failed to remove {snapshot['snapshot_name']}: {e}")

        return cleanup_results

    def start_automated_backup(self):
        """Start automated backup scheduling in background thread."""
        if self.running:
            self.logger.warning("Automated backup already running")
            return

        def backup_job():
            try:
                self.create_snapshot()
                self.cleanup_old_snapshots()
            except Exception as e:
                self.logger.error(f"Automated backup failed: {e}")

        # Schedule backup every N minutes
        self.scheduler.every(self.backup_interval).minutes.do(backup_job)

        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()

        self.logger.info(f"Started automated backup (every {self.backup_interval} minutes)")

    def stop_automated_backup(self):
        """Stop automated backup scheduling."""
        if not self.running:
            return

        self.running = False
        self.scheduler.clear()

        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.logger.info("Stopped automated backup")

    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.running:
            self.scheduler.run_pending()
            time.sleep(60)  # Check every minute

    def get_backup_status(self) -> Dict:
        """Get current backup system status."""
        snapshots = self.list_snapshots()
        critical_files = self.get_critical_files()

        latest_snapshot = None
        if snapshots:
            latest_snapshot = max(snapshots, key=lambda s: s["created_at"])

        return {
            "automated_backup_running": self.running,
            "backup_interval_minutes": self.backup_interval,
            "total_snapshots": len(snapshots),
            "critical_files_count": len(critical_files),
            "latest_snapshot": latest_snapshot,
            "backup_directory": str(self.backup_root)
        }


def main():
    """CLI interface for backup management."""
    import argparse

    parser = argparse.ArgumentParser(description="Automated Backup Infrastructure")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace root directory")
    parser.add_argument("--create-snapshot", action="store_true", help="Create immediate snapshot")
    parser.add_argument("--verify", type=str, help="Verify snapshot integrity")
    parser.add_argument("--list", action="store_true", help="List all snapshots")
    parser.add_argument("--status", action="store_true", help="Show backup system status")
    parser.add_argument("--cleanup", action="store_true", help="Run cleanup of old snapshots")
    parser.add_argument("--start-auto", action="store_true", help="Start automated backup")
    parser.add_argument("--stop-auto", action="store_true", help="Stop automated backup")

    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    backup_manager = BackupManager(workspace_root)

    if args.create_snapshot:
        result = backup_manager.create_snapshot()
        print(f"Created snapshot: {result['snapshot_name']}")
        print(f"Critical files backed up: {result['statistics']['critical_files']}")

    elif args.verify:
        result = backup_manager.verify_snapshot_integrity(args.verify)
        print(f"Snapshot '{args.verify}' verification:")
        print(f"  Valid: {result['valid']}")
        print(f"  Files checked: {result['files_checked']}")
        print(f"  Files valid: {result['files_valid']}")
        print(f"  Files invalid: {result['files_invalid']}")
        print(f"  Files missing: {result['files_missing']}")

    elif args.list:
        snapshots = backup_manager.list_snapshots()
        if snapshots:
            print("Available snapshots:")
            for snap in snapshots:
                created = datetime.fromisoformat(snap["created_at"])
                print(f"  {snap['snapshot_name']} - {created.strftime('%Y-%m-%d %H:%M:%S')} ({snap['statistics']['critical_files']} critical files)")
        else:
            print("No snapshots found")

    elif args.status:
        status = backup_manager.get_backup_status()
        print("Backup System Status:")
        print(f"  Automated backup: {'Running' if status['automated_backup_running'] else 'Stopped'}")
        print(f"  Interval: {status['backup_interval_minutes']} minutes")
        print(f"  Total snapshots: {status['total_snapshots']}")
        print(f"  Critical files: {status['critical_files_count']}")
        if status['latest_snapshot']:
            created = datetime.fromisoformat(status['latest_snapshot']['created_at'])
            print(f"  Latest snapshot: {status['latest_snapshot']['snapshot_name']} ({created.strftime('%Y-%m-%d %H:%M:%S')})")

    elif args.cleanup:
        result = backup_manager.cleanup_old_snapshots()
        print("Cleanup completed:")
        print(f"  Snapshots before: {result['snapshots_before']}")
        print(f"  Snapshots removed: {result['snapshots_removed']}")
        print(f"  Space freed: {result['space_freed_bytes']} bytes")

    elif args.start_auto:
        backup_manager.start_automated_backup()
        print(f"Started automated backup (every {backup_manager.backup_interval} minutes)")

    elif args.stop_auto:
        backup_manager.stop_automated_backup()
        print("Stopped automated backup")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
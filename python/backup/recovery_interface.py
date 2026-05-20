#!/usr/bin/env python3
"""
Recovery Interface for Backup System

This module provides streamlined restoration workflow with conflict resolution
and recovery management for backup snapshots.
"""

import os
import sys
import json
import shutil
import difflib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
import logging

class RecoveryInterface:
    """
    Handles backup restoration with conflict resolution and recovery management.
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.logger = logging.getLogger("RecoveryInterface")
        self.logger.setLevel(logging.INFO)

        # Recovery settings
        self.backup_before_restore = True  # Create backup before restoration
        self.conflict_resolution = "interactive"  # interactive, overwrite, skip

    def list_available_snapshots(self, backup_root: Path) -> List[Dict]:
        """
        List all available snapshots for recovery.

        Returns list of snapshot metadata sorted by creation time (newest first).
        """
        snapshots = []

        if not backup_root.exists():
            return snapshots

        for snapshot_dir in backup_root.iterdir():
            if snapshot_dir.is_dir():
                metadata_path = snapshot_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        snapshots.append(metadata)
                    except (json.JSONDecodeError, IOError):
                        continue

        # Sort by creation time (newest first)
        snapshots.sort(key=lambda s: s.get("created_at", ""), reverse=True)

        return snapshots

    def analyze_recovery_options(self, snapshot_metadata: Dict) -> Dict:
        """
        Analyze what would happen if we recover from this snapshot.

        Returns analysis of changes, conflicts, and recovery impact.
        """
        analysis = {
            "snapshot_name": snapshot_metadata.get("snapshot_name"),
            "created_at": snapshot_metadata.get("created_at"),
            "recovery_analysis": {
                "files_to_restore": [],
                "files_with_conflicts": [],
                "files_missing_in_snapshot": [],
                "files_newer_locally": [],
                "total_files_in_snapshot": 0,
                "estimated_restore_time_seconds": 0
            }
        }

        snapshot_files = snapshot_metadata.get("files", {})

        for file_path_str, file_info in snapshot_files.items():
            if not file_info.get("backed_up", True):
                continue

            analysis["recovery_analysis"]["total_files_in_snapshot"] += 1

            file_path = self.workspace_root / file_path_str

            if file_path.exists():
                # File exists - check for conflicts
                local_modified = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)
                snapshot_modified = datetime.fromisoformat(file_info.get("modified", snapshot_metadata.get("created_at", datetime.now(timezone.utc).isoformat())))

                if local_modified > snapshot_modified:
                    analysis["recovery_analysis"]["files_newer_locally"].append({
                        "path": file_path_str,
                        "local_modified": local_modified.isoformat(),
                        "snapshot_modified": snapshot_modified.isoformat()
                    })
                elif local_modified < snapshot_modified:
                    analysis["recovery_analysis"]["files_to_restore"].append(file_path_str)
                # else: files are in sync
            else:
                # File doesn't exist locally
                analysis["recovery_analysis"]["files_to_restore"].append(file_path_str)

        # Check for files that exist locally but not in snapshot
        local_files = set()
        for file_path in self.workspace_root.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.workspace_root)
                local_files.add(str(relative_path))

        snapshot_file_set = set(snapshot_files.keys())
        missing_in_snapshot = local_files - snapshot_file_set

        analysis["recovery_analysis"]["files_missing_in_snapshot"] = list(missing_in_snapshot)

        # Estimate restore time (rough calculation: 100 files per second)
        files_to_restore = len(analysis["recovery_analysis"]["files_to_restore"])
        analysis["recovery_analysis"]["estimated_restore_time_seconds"] = files_to_restore / 100

        return analysis

    def create_pre_recovery_backup(self) -> Optional[Path]:
        """
        Create a backup of current state before performing recovery.

        Returns path to pre-recovery backup or None if failed.
        """
        if not self.backup_before_restore:
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"pre_recovery_{timestamp}"

        backup_dir = self.workspace_root / "backup" / "pre_recovery" / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy critical files
            critical_files = [
                "current.json", "NEU.md", "Alt.md", "_LOOP_GATE.md",
                "PROJECT_TECH_BASELINE.md", "NEURAL_CORTEX.md"
            ]

            for filename in critical_files:
                src = self.workspace_root / filename
                if src.exists():
                    shutil.copy2(src, backup_dir / filename)

            # Create metadata
            metadata = {
                "backup_type": "pre_recovery",
                "backup_name": backup_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "workspace_root": str(self.workspace_root),
                "reason": "Pre-recovery safety backup"
            }

            with open(backup_dir / "metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            self.logger.info(f"Created pre-recovery backup: {backup_name}")
            return backup_dir

        except Exception as e:
            self.logger.error(f"Failed to create pre-recovery backup: {e}")
            return None

    def resolve_conflicts_interactive(self, conflicts: List[Dict]) -> Dict:
        """
        Interactive conflict resolution for files that exist in both places.

        Returns resolution decisions.
        """
        resolutions = {}

        print("\n=== CONFLICT RESOLUTION ===")
        print("The following files exist in both the snapshot and current workspace:")
        print("Choose how to handle each conflict:")
        print("  (o)verwrite - Replace with snapshot version")
        print("  (s)kip - Keep current version")
        print("  (d)iff - Show differences then choose")
        print("  (b)ackup - Backup current and restore")

        for i, conflict in enumerate(conflicts, 1):
            file_path = conflict["path"]
            print(f"\n{i}. {file_path}")
            print(f"   Local: {conflict.get('local_modified', 'unknown')}")
            print(f"   Snapshot: {conflict.get('snapshot_modified', 'unknown')}")

            while True:
                choice = input("   Choice (o/s/d/b): ").lower().strip()

                if choice in ['o', 'overwrite']:
                    resolutions[file_path] = "overwrite"
                    break
                elif choice in ['s', 'skip']:
                    resolutions[file_path] = "skip"
                    break
                elif choice in ['d', 'diff']:
                    # Show diff (simplified)
                    try:
                        snapshot_content = conflict.get("snapshot_content", "")
                        local_content = conflict.get("local_content", "")

                        if snapshot_content and local_content:
                            diff = list(difflib.unified_diff(
                                local_content.splitlines(keepends=True),
                                snapshot_content.splitlines(keepends=True),
                                fromfile="current",
                                tofile="snapshot",
                                lineterm=''
                            ))
                            print("   Differences:")
                            for line in diff[:20]:  # Show first 20 lines
                                print(f"   {line.rstrip()}")
                            if len(diff) > 20:
                                print(f"   ... ({len(diff) - 20} more lines)")
                        else:
                            print("   Cannot show diff: content not available")
                    except Exception as e:
                        print(f"   Error showing diff: {e}")

                    # Ask again after showing diff
                    continue
                elif choice in ['b', 'backup']:
                    resolutions[file_path] = "backup"
                    break
                else:
                    print("   Invalid choice. Please enter o, s, d, or b.")

        return resolutions

    def perform_recovery(self, snapshot_metadata: Dict, backup_root: Path,
                        conflict_resolution: str = "interactive",
                        files_to_restore: Optional[List[str]] = None) -> Dict:
        """
        Perform recovery from snapshot.

        Args:
            snapshot_metadata: Metadata of snapshot to recover from
            backup_root: Root directory containing snapshots
            conflict_resolution: How to handle conflicts ('interactive', 'overwrite', 'skip')
            files_to_restore: Specific files to restore (None for all)

        Returns:
            Recovery report
        """
        recovery_report = {
            "snapshot_name": snapshot_metadata.get("snapshot_name"),
            "recovery_started": datetime.now(timezone.utc).isoformat(),
            "recovery_completed": None,
            "pre_recovery_backup": None,
            "files_restored": 0,
            "files_skipped": 0,
            "conflicts_resolved": 0,
            "errors": [],
            "statistics": {
                "total_files_processed": 0,
                "bytes_restored": 0
            }
        }

        try:
            # Create pre-recovery backup
            pre_backup = self.create_pre_recovery_backup()
            if pre_backup:
                recovery_report["pre_recovery_backup"] = str(pre_backup)

            # Find snapshot directory
            snapshot_dir = backup_root / snapshot_metadata["snapshot_name"]
            if not snapshot_dir.exists():
                raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")

            # Get files to restore
            snapshot_files = snapshot_metadata.get("files", {})
            if files_to_restore:
                files_to_process = {fp: snapshot_files[fp] for fp in files_to_restore if fp in snapshot_files}
            else:
                files_to_process = {fp: info for fp, info in snapshot_files.items() if info.get("backed_up", True)}

            # Identify conflicts
            conflicts = []
            for file_path_str in files_to_process:
                file_path = self.workspace_root / file_path_str
                if file_path.exists():
                    local_modified = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)
                    snapshot_modified = datetime.fromisoformat(snapshot_files[file_path_str].get("modified", snapshot_metadata.get("created_at")))

                    if local_modified > snapshot_modified:
                        conflicts.append({
                            "path": file_path_str,
                            "local_modified": local_modified.isoformat(),
                            "snapshot_modified": snapshot_modified.isoformat()
                        })

            # Resolve conflicts
            conflict_resolutions = {}
            if conflicts and conflict_resolution == "interactive":
                conflict_resolutions = self.resolve_conflicts_interactive(conflicts)
            elif conflict_resolution == "overwrite":
                conflict_resolutions = {c["path"]: "overwrite" for c in conflicts}
            elif conflict_resolution == "skip":
                conflict_resolutions = {c["path"]: "skip" for c in conflicts}

            # Perform restoration
            for file_path_str, file_info in files_to_process.items():
                recovery_report["statistics"]["total_files_processed"] += 1

                local_path = self.workspace_root / file_path_str
                snapshot_path = snapshot_dir / file_path_str

                if not snapshot_path.exists():
                    recovery_report["errors"].append(f"Snapshot file missing: {file_path_str}")
                    recovery_report["files_skipped"] += 1
                    continue

                # Check conflict resolution
                resolution = conflict_resolutions.get(file_path_str, "overwrite")

                if resolution == "skip":
                    recovery_report["files_skipped"] += 1
                    continue

                try:
                    # Create backup of current file if requested
                    if resolution == "backup" and local_path.exists():
                        backup_path = local_path.with_suffix(local_path.suffix + ".backup")
                        shutil.copy2(local_path, backup_path)
                        self.logger.info(f"Backed up current file: {backup_path}")

                    # Ensure destination directory exists
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    # Restore file
                    shutil.copy2(snapshot_path, local_path)
                    file_size = local_path.stat().st_size

                    recovery_report["files_restored"] += 1
                    recovery_report["statistics"]["bytes_restored"] += file_size

                    if file_path_str in conflict_resolutions:
                        recovery_report["conflicts_resolved"] += 1

                    self.logger.info(f"Restored: {file_path_str} ({file_size} bytes)")

                except Exception as e:
                    recovery_report["errors"].append(f"Failed to restore {file_path_str}: {e}")
                    recovery_report["files_skipped"] += 1

            recovery_report["recovery_completed"] = datetime.now(timezone.utc).isoformat()

            # Calculate duration
            if recovery_report["recovery_completed"] and recovery_report["recovery_started"]:
                start_time = datetime.fromisoformat(recovery_report["recovery_started"])
                end_time = datetime.fromisoformat(recovery_report["recovery_completed"])
                recovery_report["duration_seconds"] = (end_time - start_time).total_seconds()

            self.logger.info(f"Recovery completed: {recovery_report['files_restored']} files restored")

        except Exception as e:
            recovery_report["errors"].append(f"Recovery failed: {e}")
            self.logger.error(f"Recovery failed: {e}")

        return recovery_report

    def validate_recovery(self, recovery_report: Dict) -> Dict:
        """
        Validate that recovery was successful by checking restored files.
        """
        validation = {
            "recovery_snapshot": recovery_report.get("snapshot_name"),
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "files_validated": 0,
            "files_ok": 0,
            "files_corrupted": 0,
            "validation_errors": []
        }

        # This would integrate with VerificationEngine for comprehensive validation
        # For now, just check that files exist and have expected sizes

        # Placeholder - would need snapshot metadata to do proper validation
        validation["validation_note"] = "Full validation requires VerificationEngine integration"

        return validation

    def get_recovery_history(self) -> List[Dict]:
        """
        Get history of recovery operations.
        """
        history_file = self.workspace_root / "backup" / "recovery_history.jsonl"

        if not history_file.exists():
            return []

        history = []
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        history.append(json.loads(line))
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Failed to read recovery history: {e}")

        return history

    def log_recovery_operation(self, recovery_report: Dict):
        """
        Log recovery operation to history.
        """
        history_file = self.workspace_root / "backup" / "recovery_history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(recovery_report, ensure_ascii=False) + '\n')
        except IOError as e:
            self.logger.error(f"Failed to log recovery operation: {e}")


def main():
    """CLI interface for recovery operations."""
    import argparse

    parser = argparse.ArgumentParser(description="Backup Recovery Interface")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace root directory")
    parser.add_argument("--backup-root", type=str, help="Backup root directory")
    parser.add_argument("--list-snapshots", action="store_true", help="List available snapshots")
    parser.add_argument("--analyze", type=str, help="Analyze recovery options for snapshot")
    parser.add_argument("--recover", type=str, help="Recover from snapshot")
    parser.add_argument("--files", nargs="*", help="Specific files to recover")
    parser.add_argument("--conflict-resolution", choices=["interactive", "overwrite", "skip"],
                       default="interactive", help="How to handle conflicts")

    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    backup_root = Path(args.backup_root) if args.backup_root else workspace_root / "backup" / "snapshots"

    interface = RecoveryInterface(workspace_root)

    if args.list_snapshots:
        snapshots = interface.list_available_snapshots(backup_root)
        if snapshots:
            print("Available snapshots (newest first):")
            for snap in snapshots:
                created = datetime.fromisoformat(snap["created_at"])
                print(f"  {snap['snapshot_name']} - {created.strftime('%Y-%m-%d %H:%M:%S')} "
                      f"({snap['statistics']['critical_files']} critical files)")
        else:
            print("No snapshots found")

    elif args.analyze:
        # Find snapshot metadata
        snapshots = interface.list_available_snapshots(backup_root)
        snapshot_meta = None
        for snap in snapshots:
            if snap["snapshot_name"] == args.analyze:
                snapshot_meta = snap
                break

        if not snapshot_meta:
            print(f"Snapshot not found: {args.analyze}")
            sys.exit(1)

        analysis = interface.analyze_recovery_options(snapshot_meta)
        print(f"Recovery Analysis for {args.analyze}:")
        print(f"  Files to restore: {len(analysis['recovery_analysis']['files_to_restore'])}")
        print(f"  Files with conflicts: {len(analysis['recovery_analysis']['files_newer_locally'])}")
        print(f"  Estimated time: {analysis['recovery_analysis']['estimated_restore_time_seconds']:.1f}s")

    elif args.recover:
        # Find snapshot metadata
        snapshots = interface.list_available_snapshots(backup_root)
        snapshot_meta = None
        for snap in snapshots:
            if snap["snapshot_name"] == args.recover:
                snapshot_meta = snap
                break

        if not snapshot_meta:
            print(f"Snapshot not found: {args.recover}")
            sys.exit(1)

        # Perform recovery
        print(f"Starting recovery from snapshot: {args.recover}")
        report = interface.perform_recovery(
            snapshot_meta, backup_root,
            conflict_resolution=args.conflict_resolution,
            files_to_restore=args.files
        )

        # Log recovery
        interface.log_recovery_operation(report)

        # Print results
        print("\nRecovery completed:")
        print(f"  Files restored: {report['files_restored']}")
        print(f"  Files skipped: {report['files_skipped']}")
        print(f"  Conflicts resolved: {report['conflicts_resolved']}")
        if report['errors']:
            print("  Errors:")
            for error in report['errors']:
                print(f"    {error}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
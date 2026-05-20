#!/usr/bin/env python3
"""
Simple Backup Recovery CLI Tool

This script provides a simple command-line interface for restoring from automated backups.
Usage: python recovery_cli.py [snapshot_name] [--overwrite|--interactive|--skip]

If no snapshot_name is provided, lists available snapshots.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from backup.recovery_interface import RecoveryInterface

def list_snapshots(backup_root: Path):
    """List available snapshots."""
    snapshots = []
    if backup_root.exists():
        for item in backup_root.iterdir():
            if item.is_dir() and item.name.startswith("snapshot_"):
                metadata_file = item / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        snapshots.append(metadata)
                    except Exception as e:
                        print(f"Warning: Could not read metadata for {item.name}: {e}")
                        # Create basic metadata from directory name
                        timestamp_str = item.name.replace("snapshot_", "")
                        try:
                            created_at = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc).isoformat()
                            snapshots.append({
                                "snapshot_name": item.name,
                                "created_at": created_at,
                                "files": {}
                            })
                        except:
                            pass

    # Sort by creation time (newest first)
    snapshots.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    if not snapshots:
        print("No snapshots found.")
        return None

    print("Available snapshots:")
    print("-" * 50)
    for i, snap in enumerate(snapshots, 1):
        created = snap.get("created_at", "Unknown")
        if created != "Unknown":
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except:
                pass
        file_count = len(snap.get("files", {}))
        print(f"{i}. {snap['snapshot_name']} - {created} ({file_count} files)")

    return snapshots

    # Sort by creation time (newest first)
    snapshots.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    if not snapshots:
        print("No snapshots found.")
        return None

    print("Available snapshots:")
    print("-" * 50)
    for i, snap in enumerate(snapshots, 1):
        created = snap.get("created_at", "Unknown")
        if created != "Unknown":
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except:
                pass
        file_count = len(snap.get("files", {}))
        print(f"{i}. {snap['snapshot_name']} - {created} ({file_count} files)")

    return snapshots

def main():
    if len(sys.argv) < 2:
        # List snapshots
        workspace_root = Path.cwd()
        backup_root = workspace_root / "backup" / "snapshots"
        snapshots = list_snapshots(backup_root)
        if snapshots:
            print("\nTo restore, run: python recovery_cli.py <snapshot_name> [options]")
            print("Options:")
            print("  --overwrite    Overwrite conflicting files without asking")
            print("  --interactive  Ask for each conflicting file (default)")
            print("  --skip         Skip conflicting files")
        return

    snapshot_name = sys.argv[1]

    # Parse options
    conflict_resolution = "interactive"
    if "--overwrite" in sys.argv:
        conflict_resolution = "overwrite"
    elif "--skip" in sys.argv:
        conflict_resolution = "skip"

    # Setup recovery
    workspace_root = Path.cwd()
    backup_root = workspace_root / "backup" / "snapshots"

    # Load snapshot metadata
    metadata_file = backup_root / snapshot_name / "metadata.json"
    if not metadata_file.exists():
        print(f"Error: Snapshot metadata not found: {metadata_file}")
        return

    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            snapshot_metadata = json.load(f)
    except Exception as e:
        print(f"Error reading snapshot metadata: {e}")
        return

    # Perform recovery
    print(f"Starting recovery from snapshot: {snapshot_name}")
    print(f"Conflict resolution mode: {conflict_resolution}")
    print("-" * 50)

    recovery = RecoveryInterface(workspace_root)
    try:
        report = recovery.perform_recovery(
            snapshot_metadata,
            backup_root,
            conflict_resolution=conflict_resolution
        )

        # Print results
        print("\nRecovery completed!")
        print(f"Files restored: {report['files_restored']}")
        print(f"Files skipped: {report['files_skipped']}")
        print(f"Conflicts resolved: {report['conflicts_resolved']}")
        print(f"Bytes restored: {report['statistics']['bytes_restored']:,}")

        if report['pre_recovery_backup']:
            print(f"Pre-recovery backup created: {report['pre_recovery_backup']}")

        if report['errors']:
            print(f"\nErrors encountered ({len(report['errors'])}):")
            for error in report['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(report['errors']) > 5:
                print(f"  ... and {len(report['errors']) - 5} more")

    except Exception as e:
        print(f"Recovery failed: {e}")
        return

if __name__ == "__main__":
    main()
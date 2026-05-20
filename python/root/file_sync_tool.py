#!/usr/bin/env python3
"""
Secure File Comparison and Synchronization Tool
Safely compares files on disk with potential cache/memory state
and provides options for secure synchronization.
"""

import os
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    if not os.path.exists(filepath):
        return None

    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def get_file_info(filepath):
    """Get comprehensive file information."""
    if not os.path.exists(filepath):
        return None

    stat = os.stat(filepath)
    return {
        'exists': True,
        'size': stat.st_size,
        'mtime': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'hash': calculate_file_hash(filepath)
    }

def safe_backup_file(filepath, backup_dir="file_backup_safe"):
    """Create a safe backup of a file before any operations."""
    if not os.path.exists(filepath):
        return False

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = Path(filepath).name
    backup_path = os.path.join(backup_dir, f"{filename}.backup_{timestamp}")

    shutil.copy2(filepath, backup_path)
    return backup_path

def compare_files_on_disk(file1, file2):
    """Compare two files on disk."""
    info1 = get_file_info(file1)
    info2 = get_file_info(file2)

    if not info1 or not info2:
        return {
            'comparison_possible': False,
            'reason': f"One or both files don't exist: {file1} exists={info1 is not None}, {file2} exists={info2 is not None}"
        }

    return {
        'comparison_possible': True,
        'files_identical': info1['hash'] == info2['hash'],
        'size_difference': info1['size'] - info2['size'],
        'file1_info': info1,
        'file2_info': info2,
        'newer_file': file1 if info1['mtime'] > info2['mtime'] else file2
    }

def create_sync_plan(source_file, target_file):
    """Create a safe synchronization plan."""
    comparison = compare_files_on_disk(source_file, target_file)

    if not comparison['comparison_possible']:
        return {
            'action': 'error',
            'message': comparison['reason']
        }

    if comparison['files_identical']:
        return {
            'action': 'no_action_needed',
            'message': 'Files are identical'
        }

    # Determine sync direction based on modification time
    if comparison['newer_file'] == source_file:
        return {
            'action': 'sync_source_to_target',
            'source': source_file,
            'target': target_file,
            'backup_recommended': True,
            'message': f'Copy {source_file} (newer) to {target_file}'
        }
    else:
        return {
            'action': 'sync_target_to_source',
            'source': target_file,
            'target': source_file,
            'backup_recommended': True,
            'message': f'Copy {target_file} (newer) to {source_file}'
        }

def execute_safe_sync(sync_plan):
    """Execute synchronization with safety measures."""
    if sync_plan['action'] == 'no_action_needed':
        print("✅ No synchronization needed - files are identical")
        return True

    if sync_plan['action'] == 'error':
        print(f"❌ Error: {sync_plan['message']}")
        return False

    # Create backup if recommended
    if sync_plan.get('backup_recommended'):
        backup_path = safe_backup_file(sync_plan['target'])
        if backup_path:
            print(f"📦 Backup created: {backup_path}")
        else:
            print("⚠️  Warning: Could not create backup")

    # Perform sync
    try:
        shutil.copy2(sync_plan['source'], sync_plan['target'])
        print(f"✅ Successfully synced {sync_plan['source']} → {sync_plan['target']}")
        return True
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False

def main():
    """Main function for file comparison and sync."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python file_sync_tool.py <file1> <file2> [--sync]")
        print("  --sync: Actually perform synchronization (default is compare only)")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]
    do_sync = '--sync' in sys.argv

    print(f"🔍 Comparing: {file1} ↔ {file2}")
    print("-" * 60)

    # Get file information
    info1 = get_file_info(file1)
    info2 = get_file_info(file2)

    if info1:
        print(f"📄 {file1}:")
        print(f"   Size: {info1['size']} bytes")
        print(f"   Modified: {info1['mtime']}")
        print(f"   Hash: {info1['hash'][:16]}...")
    else:
        print(f"❌ {file1}: File does not exist")

    if info2:
        print(f"📄 {file2}:")
        print(f"   Size: {info2['size']} bytes")
        print(f"   Modified: {info2['mtime']}")
        print(f"   Hash: {info2['hash'][:16]}...")
    else:
        print(f"❌ {file2}: File does not exist")

    print("-" * 60)

    # Compare files
    comparison = compare_files_on_disk(file1, file2)

    if not comparison['comparison_possible']:
        print(f"❌ {comparison['reason']}")
        return

    if comparison['files_identical']:
        print("✅ Files are IDENTICAL")
    else:
        print("⚠️  Files are DIFFERENT")
        print(f"   Size difference: {comparison['size_difference']} bytes")
        print(f"   Newer file: {comparison['newer_file']}")

    # Create sync plan
    if not do_sync:
        sync_plan = create_sync_plan(file1, file2)
        print(f"💡 Recommended action: {sync_plan['message']}")
        print("   Use --sync flag to execute this synchronization")
    else:
        print("🔄 Executing synchronization...")
        sync_plan = create_sync_plan(file1, file2)
        success = execute_safe_sync(sync_plan)
        if success:
            print("✅ Synchronization completed successfully")
        else:
            print("❌ Synchronization failed")

if __name__ == "__main__":
    main()
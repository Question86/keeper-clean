#!/usr/bin/env python3
"""
File Location Correction and Recovery Tool
Corrects breadcrumb tracking errors where files exist in subdirectories
but were tracked as root files.
"""

import os
import shutil
from pathlib import Path

def find_file_in_workspace(filename):
    """Find a file anywhere in the workspace."""
    for root, dirs, files in os.walk('.'):
        if filename in files:
            return os.path.join(root, filename)
    return None

def correct_file_locations():
    """Correct file locations based on actual vs tracked paths."""
    print("🔍 FILE LOCATION CORRECTION AND RECOVERY")
    print("=" * 60)

    # Files that were tracked as root but exist elsewhere
    corrections = {
        # Files that exist in reports/
        'documentation_framework_analysis.md': 'reports/documentation_framework_analysis.md',
        'mega.md': 'reports/mega.md',
        'skl_demo_document.md': 'reports/skl_demo_document.md',
        'skl_implementation_roadmap.md': 'reports/skl_implementation_roadmap.md',

        # Files that exist in archive/
        'ARCHIV_0085.md': 'archive/ARCHIV_0085.md',
        'ARCHIV_0086.md': 'archive/ARCHIV_0086.md',

        # Files that exist in tasks/
        'task_TASK_0001.md': 'tasks/task_TASK_0001.md',
        'task_TASK_0181.md': 'tasks/task_TASK_0181.md',

        # Files that exist in workspace_backup (most recent)
        'consistency_auditor.py': 'workspace_backup/20260128_020201/consistency_auditor.py',
        'skl_framework.py': 'workspace_backup/20260128_020201/skl_framework.py',
        'skl_publisher.py': 'workspace_backup/20260128_020201/skl_publisher.py',
        'skl_simple.py': 'workspace_backup/20260128_020201/skl_simple.py',
    }

    corrected = []
    failed = []

    for tracked_name, actual_path in corrections.items():
        print(f"\n📁 Processing: {tracked_name}")
        print(f"   Tracked as: {tracked_name} (root)")
        print(f"   Actually at: {actual_path}")

        # Check if source exists
        if os.path.exists(actual_path):
            print(f"   ✅ Source file exists")
            # Check if already in root (no need to copy)
            root_path = tracked_name
            if os.path.exists(root_path):
                print(f"   ℹ️  Already exists in root - skipping")
                continue

            # Copy to root
            try:
                # For root files, no need to create directories
                root_dir = os.path.dirname(root_path)
                if root_dir and root_dir != '.':
                    os.makedirs(root_dir, exist_ok=True)
                shutil.copy2(actual_path, root_path)
                print(f"   ✅ Copied to root: {root_path}")
                corrected.append(tracked_name)
            except Exception as e:
                print(f"   ❌ Copy failed: {e}")
                failed.append(tracked_name)
        else:
            print(f"   ❌ Source file not found")
            failed.append(tracked_name)

    print("\n" + "=" * 60)
    print("📊 CORRECTION RESULTS:")
    print(f"   Files corrected: {len(corrected)}")
    print(f"   Files failed: {len(failed)}")

    if corrected:
        print("\n✅ Successfully corrected:")
        for f in corrected:
            print(f"   • {f}")

    if failed:
        print("\n❌ Failed to correct:")
        for f in failed:
            print(f"   • {f}")

    return corrected, failed

def verify_corrections():
    """Verify that corrections worked."""
    print("\n🔍 VERIFICATION:")
    print("-" * 30)

    # Check the files that should now be in root
    to_verify = [
        'documentation_framework_analysis.md',
        'mega.md',
        'skl_demo_document.md',
        'skl_implementation_roadmap.md',
        'ARCHIV_0085.md',
        'ARCHIV_0086.md',
        'task_TASK_0001.md',
        'task_TASK_0181.md',
        'consistency_auditor.py',
        'skl_framework.py',
        'skl_publisher.py',
        'skl_simple.py'
    ]

    verified = []
    still_missing = []

    for filename in to_verify:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"   ✅ {filename} ({size} bytes)")
            verified.append(filename)
        else:
            print(f"   ❌ {filename} (still missing)")
            still_missing.append(filename)

    print(f"\nVerification: {len(verified)}/{len(to_verify)} files now in root")
    return verified, still_missing

def main():
    """Main correction process."""
    print("🚀 STARTING FILE LOCATION CORRECTION")
    print("This will copy files from their actual locations to root directory")
    print("to match breadcrumb tracking expectations.\n")

    # Perform corrections
    corrected, failed = correct_file_locations()

    # Verify results
    verified, still_missing = verify_corrections()

    print("\n" + "=" * 60)
    print("🎯 FINAL STATUS:")

    if verified:
        print(f"✅ {len(verified)} files successfully restored to root")
        print("   These files are now where the breadcrumb system expects them")

    if still_missing:
        print(f"⚠️  {len(still_missing)} files still missing")
        print("   These may need to be recreated or recovered from other sources")

    if failed:
        print(f"❌ {len(failed)} corrections failed")
        print("   Check file permissions or paths")

    print("\n💡 NEXT STEPS:")
    print("   1. Run breadcrumb validation to confirm tracking is now accurate")
    print("   2. Consider updating breadcrumb system to handle subdirectories correctly")
    print("   3. Review file organization strategy")

if __name__ == "__main__":
    main()
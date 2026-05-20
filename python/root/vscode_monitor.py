#!/usr/bin/env python3
"""
VS Code Unsaved Changes Detector
Monitors files for potential unsaved changes in VS Code.
"""

import os
import time
from datetime import datetime
from pathlib import Path

def monitor_file_changes(filepath, duration_seconds=30):
    """Monitor a file for changes that might indicate unsaved content being saved."""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    print(f"👀 Monitoring {filepath} for {duration_seconds} seconds...")
    print("💡 In VS Code: Make your changes and save (Ctrl+S) to see detection in action")
    print("-" * 60)

    initial_stat = os.stat(filepath)
    initial_mtime = initial_stat.st_mtime
    initial_size = initial_stat.st_size

    start_time = time.time()
    changes_detected = []

    try:
        while time.time() - start_time < duration_seconds:
            if os.path.exists(filepath):
                current_stat = os.stat(filepath)
                current_mtime = current_stat.st_mtime
                current_size = current_stat.st_size

                if current_mtime != initial_mtime or current_size != initial_size:
                    change_time = datetime.now().isoformat()
                    changes_detected.append({
                        'timestamp': change_time,
                        'old_size': initial_size,
                        'new_size': current_size,
                        'size_diff': current_size - initial_size
                    })

                    print(f"✅ CHANGE DETECTED at {change_time}")
                    print(f"   Size: {initial_size} → {current_size} bytes ({current_size - initial_size:+d})")
                    print(f"   File: {filepath}")
                    print()

                    # Update baseline
                    initial_mtime = current_mtime
                    initial_size = current_size

            time.sleep(0.5)  # Check every 500ms

    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")

    print("-" * 60)
    if changes_detected:
        print(f"📊 Summary: {len(changes_detected)} change(s) detected")
        for i, change in enumerate(changes_detected, 1):
            print(f"   {i}. {change['timestamp']}: {change['size_diff']:+d} bytes")
    else:
        print("📊 Summary: No changes detected during monitoring period")
        print("💡 This could mean:")
        print("   - No unsaved changes exist")
        print("   - Changes were already saved")
        print("   - VS Code auto-save is enabled")

def check_vscode_unsaved_indicators():
    """Check for indicators of unsaved changes in VS Code."""
    print("🔍 Checking for VS Code unsaved change indicators...")
    print()

    # Check for common unsaved file patterns
    workspace_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith(('.md', '.py', '.txt', '.json')):  # Common editable files
                filepath = os.path.join(root, file)
                workspace_files.append(filepath)

    print(f"📁 Found {len(workspace_files)} editable files in workspace")

    # Check modification times (recent modifications might indicate active editing)
    recent_modifications = []
    now = time.time()
    recent_threshold = 300  # 5 minutes

    for filepath in workspace_files:
        try:
            mtime = os.path.getmtime(filepath)
            age = now - mtime
            if age < recent_threshold:
                recent_modifications.append((filepath, age))
        except:
            continue

    if recent_modifications:
        print(f"🕐 {len(recent_modifications)} files modified in last 5 minutes:")
        for filepath, age in sorted(recent_modifications, key=lambda x: x[1]):
            print(".1f")
    else:
        print("🕐 No files modified in last 5 minutes")

    print()
    print("💡 VS Code Unsaved Changes Detection:")
    print("   • Look for dot (•) next to filename in tabs")
    print("   • Check if 'Save' button is enabled")
    print("   • Use Ctrl+Shift+P → 'View: Toggle Editor Group Sizes' to see unsaved indicators")
    print("   • Run: monitor_file_changes('Alt.md') to watch for saves")

def main():
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if os.path.exists(filepath):
            monitor_file_changes(filepath)
        else:
            print(f"❌ File not found: {filepath}")
    else:
        check_vscode_unsaved_indicators()

if __name__ == "__main__":
    main()
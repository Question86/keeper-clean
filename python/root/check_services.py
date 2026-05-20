#!/usr/bin/env python3
"""
Simple Service Status Checker

Checks the status of background services without interfering with the daemon.
"""

import subprocess
import sys
from pathlib import Path

def check_service_status():
    """Check status of services."""

    workspace_root = Path.cwd()

    print("Service Status Check")
    print("=" * 50)

    # Check backup manager
    try:
        result = subprocess.run([
            sys.executable, 'backup/backup_manager.py', '--status'
        ], capture_output=True, text=True, cwd=str(workspace_root))

        if result.returncode == 0:
            print("✅ Automated Backup: Running")
            # Parse the status output
            for line in result.stdout.split('\n'):
                if 'Automated backup:' in line:
                    print(f"   {line.strip()}")
                elif 'Latest snapshot:' in line:
                    print(f"   {line.strip()}")
        else:
            print("❌ Automated Backup: Error")
            print(f"   {result.stderr.strip()}")

    except Exception as e:
        print(f"❌ Automated Backup: Exception - {e}")

    # Check if orchestrator daemon is running
    try:
        result = subprocess.run([
            'tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'
        ], capture_output=True, text=True)

        daemon_running = 'service_orchestrator' in result.stdout and '--daemon' in result.stdout
        if daemon_running:
            print("✅ Service Orchestrator: Running (daemon mode)")
        else:
            print("❌ Service Orchestrator: Not running")

    except Exception as e:
        print(f"⚠️  Service Orchestrator: Unable to check - {e}")

    # Check behavioral telemetry data
    breadcrumb_file = workspace_root / "breadcrumb_trail.jsonl"
    if breadcrumb_file.exists():
        try:
            with open(breadcrumb_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"✅ Behavioral Telemetry: Active ({len(lines)} breadcrumbs)")
        except Exception as e:
            print(f"⚠️  Behavioral Telemetry: File exists but error reading - {e}")
    else:
        print("❌ Behavioral Telemetry: No breadcrumb data")

    # Check transaction log
    transaction_file = workspace_root / "_transaction_log.jsonl"
    if transaction_file.exists():
        try:
            with open(transaction_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"✅ AI Integrity Protection: Active ({len(lines)} transactions logged)")
        except Exception as e:
            print(f"⚠️  AI Integrity Protection: Log exists but error reading - {e}")
    else:
        print("❌ AI Integrity Protection: No transaction log")

    print("\nService orchestrator provides continuous monitoring:")
    print("- Behavioral telemetry analysis every 15 minutes")
    print("- AI integrity checks every 5 minutes")
    print("- Token budget monitoring every 10 minutes")
    print("- Automated backups every 30 minutes")

if __name__ == "__main__":
    check_service_status()
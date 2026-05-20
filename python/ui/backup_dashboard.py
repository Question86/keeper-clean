#!/usr/bin/env python3
"""
Backup Dashboard for Cockpit Integration

This module provides monitoring and control interface for the backup system
integrated with the loop cockpit dashboard.
"""

import os
import sys
import json
import psutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging

class BackupDashboard:
    """
    Dashboard interface for backup system monitoring and control.
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.backup_root = workspace_root / "backup"
        self.snapshots_root = self.backup_root / "snapshots"
        self.logger = logging.getLogger("BackupDashboard")
        self.logger.setLevel(logging.INFO)

    def get_backup_status(self) -> Dict:
        """
        Get comprehensive backup system status for dashboard display.
        """
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_status": "unknown",
            "automated_backup": {
                "running": False,
                "interval_minutes": 30,
                "last_backup": None,
                "next_backup": None
            },
            "storage": {
                "total_snapshots": 0,
                "total_size_bytes": 0,
                "oldest_snapshot": None,
                "newest_snapshot": None,
                "retention_days": 7
            },
            "last_operations": {
                "last_full_backup": None,
                "last_verification": None,
                "last_recovery": None
            },
            "health_indicators": {
                "backup_success_rate": 0.0,
                "average_backup_time_seconds": 0,
                "storage_utilization_percent": 0.0,
                "data_loss_risk": "unknown"
            },
            "alerts": []
        }

        try:
            # Check if backup system exists
            if not self.snapshots_root.exists():
                status["system_status"] = "not_initialized"
                status["alerts"].append({
                    "level": "warning",
                    "message": "Backup system not initialized",
                    "action": "Initialize backup system"
                })
                return status

            # Get snapshots
            snapshots = self._list_snapshots()
            status["storage"]["total_snapshots"] = len(snapshots)

            if snapshots:
                # Calculate storage size
                total_size = sum(snap["statistics"].get("compressed_size_bytes", 0) for snap in snapshots)
                status["storage"]["total_size_bytes"] = total_size

                # Get oldest and newest
                sorted_snaps = sorted(snapshots, key=lambda s: s.get("created_at", ""))
                status["storage"]["oldest_snapshot"] = sorted_snaps[0].get("created_at")
                status["storage"]["newest_snapshot"] = sorted_snaps[-1].get("created_at")

                # Last backup info
                latest_snapshot = sorted_snaps[-1]
                status["automated_backup"]["last_backup"] = latest_snapshot.get("created_at")

                # Estimate next backup (assuming 30-minute intervals)
                if status["automated_backup"]["last_backup"]:
                    last_backup_time = datetime.fromisoformat(status["automated_backup"]["last_backup"])
                    next_backup = last_backup_time + timedelta(minutes=30)
                    status["automated_backup"]["next_backup"] = next_backup.isoformat()

            # Check for automated backup process (simplified check)
            # In real implementation, this would check if backup_manager.py is running
            status["automated_backup"]["running"] = self._check_automated_backup_running()

            # Get last operations from logs
            last_ops = self._get_last_operations()
            status["last_operations"].update(last_ops)

            # Calculate health indicators
            health = self._calculate_health_indicators(snapshots)
            status["health_indicators"].update(health)

            # Determine overall status
            if status["automated_backup"]["running"] and status["storage"]["total_snapshots"] > 0:
                status["system_status"] = "healthy"
            elif status["storage"]["total_snapshots"] > 0:
                status["system_status"] = "manual_only"
            else:
                status["system_status"] = "unhealthy"

            # Generate alerts
            alerts = self._generate_alerts(status)
            status["alerts"].extend(alerts)

        except Exception as e:
            self.logger.error(f"Failed to get backup status: {e}")
            status["system_status"] = "error"
            status["alerts"].append({
                "level": "error",
                "message": f"Status check failed: {e}",
                "action": "Check system logs"
            })

        return status

    def get_backup_history(self, limit: int = 20) -> List[Dict]:
        """
        Get backup operation history for dashboard display.
        """
        history = []

        try:
            # Read snapshot metadata
            snapshots = self._list_snapshots()
            for snap in snapshots[:limit]:
                history.append({
                    "type": "snapshot_created",
                    "timestamp": snap.get("created_at"),
                    "snapshot_name": snap.get("snapshot_name"),
                    "details": {
                        "critical_files": snap.get("statistics", {}).get("critical_files", 0),
                        "total_size_bytes": snap.get("statistics", {}).get("compressed_size_bytes", 0)
                    }
                })

            # Read recovery history
            recovery_history = self._get_recovery_history()
            for recovery in recovery_history[:limit]:
                history.append({
                    "type": "recovery_performed",
                    "timestamp": recovery.get("recovery_started"),
                    "snapshot_name": recovery.get("snapshot_name"),
                    "details": {
                        "files_restored": recovery.get("files_restored", 0),
                        "duration_seconds": recovery.get("duration_seconds", 0)
                    }
                })

            # Sort by timestamp (newest first)
            history.sort(key=lambda h: h.get("timestamp", ""), reverse=True)

        except Exception as e:
            self.logger.error(f"Failed to get backup history: {e}")

        return history[:limit]

    def trigger_manual_backup(self) -> Dict:
        """
        Trigger immediate manual backup.
        """
        result = {
            "success": False,
            "message": "",
            "snapshot_name": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            # Import and use backup manager
            from .backup_manager import BackupManager

            backup_manager = BackupManager(self.workspace_root)
            metadata = backup_manager.create_snapshot()

            result["success"] = True
            result["message"] = f"Manual backup created: {metadata['snapshot_name']}"
            result["snapshot_name"] = metadata["snapshot_name"]

            self.logger.info(f"Manual backup triggered: {result['snapshot_name']}")

        except ImportError:
            result["message"] = "Backup system not available"
        except Exception as e:
            result["message"] = f"Manual backup failed: {e}"
            self.logger.error(f"Manual backup failed: {e}")

        return result

    def get_storage_analysis(self) -> Dict:
        """
        Analyze backup storage usage and provide recommendations.
        """
        analysis = {
            "total_size_bytes": 0,
            "snapshots_by_age": {
                "last_24h": {"count": 0, "size_bytes": 0},
                "last_7d": {"count": 0, "size_bytes": 0},
                "older": {"count": 0, "size_bytes": 0}
            },
            "average_snapshot_size_bytes": 0,
            "storage_efficiency_percent": 0.0,
            "recommendations": []
        }

        try:
            snapshots = self._list_snapshots()
            if not snapshots:
                analysis["recommendations"].append("No snapshots found - initialize backup system")
                return analysis

            now = datetime.now(timezone.utc)

            for snap in snapshots:
                size = snap.get("statistics", {}).get("compressed_size_bytes", 0)
                analysis["total_size_bytes"] += size

                created_at = datetime.fromisoformat(snap.get("created_at", now.isoformat()))
                age_days = (now - created_at).days

                if age_days <= 1:
                    analysis["snapshots_by_age"]["last_24h"]["count"] += 1
                    analysis["snapshots_by_age"]["last_24h"]["size_bytes"] += size
                elif age_days <= 7:
                    analysis["snapshots_by_age"]["last_7d"]["count"] += 1
                    analysis["snapshots_by_age"]["last_7d"]["size_bytes"] += size
                else:
                    analysis["snapshots_by_age"]["older"]["count"] += 1
                    analysis["snapshots_by_age"]["older"]["size_bytes"] += size

            # Calculate averages
            if snapshots:
                analysis["average_snapshot_size_bytes"] = analysis["total_size_bytes"] / len(snapshots)

            # Calculate efficiency (assuming 50% compression)
            original_size = analysis["total_size_bytes"] * 2  # Estimate
            if original_size > 0:
                analysis["storage_efficiency_percent"] = (1 - analysis["total_size_bytes"] / original_size) * 100

            # Generate recommendations
            if analysis["snapshots_by_age"]["older"]["count"] > 10:
                analysis["recommendations"].append("Consider cleaning up old snapshots (>7 days)")

            if analysis["total_size_bytes"] > 1024 * 1024 * 1024:  # 1GB
                analysis["recommendations"].append("Backup storage is getting large - consider cleanup")

            if analysis["snapshots_by_age"]["last_24h"]["count"] == 0:
                analysis["recommendations"].append("No recent backups - check automated backup status")

        except Exception as e:
            self.logger.error(f"Failed to analyze storage: {e}")
            analysis["recommendations"].append(f"Storage analysis failed: {e}")

        return analysis

    def _list_snapshots(self) -> List[Dict]:
        """Internal method to list snapshots."""
        snapshots = []

        if not self.snapshots_root.exists():
            return snapshots

        for snapshot_dir in self.snapshots_root.iterdir():
            if snapshot_dir.is_dir():
                metadata_path = snapshot_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        snapshots.append(metadata)
                    except (json.JSONDecodeError, IOError):
                        continue

        return snapshots

    def _check_automated_backup_running(self) -> bool:
        """Check if automated backup is currently running."""
        # Simplified check - look for backup manager processes
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'backup_manager.py' in ' '.join(proc.info['cmdline'] or []):
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        return False

    def _get_last_operations(self) -> Dict:
        """Get information about last backup operations."""
        last_ops = {
            "last_full_backup": None,
            "last_verification": None,
            "last_recovery": None
        }

        try:
            # Get last snapshot
            snapshots = self._list_snapshots()
            if snapshots:
                sorted_snaps = sorted(snapshots, key=lambda s: s.get("created_at", ""), reverse=True)
                last_ops["last_full_backup"] = sorted_snaps[0].get("created_at")

            # Get last recovery
            recovery_file = self.backup_root / "recovery_history.jsonl"
            if recovery_file.exists():
                with open(recovery_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        last_recovery = json.loads(lines[-1])
                        last_ops["last_recovery"] = last_recovery.get("recovery_started")

        except Exception as e:
            self.logger.error(f"Failed to get last operations: {e}")

        return last_ops

    def _calculate_health_indicators(self, snapshots: List[Dict]) -> Dict:
        """Calculate health indicators from snapshot data."""
        health = {
            "backup_success_rate": 0.0,
            "average_backup_time_seconds": 0,
            "storage_utilization_percent": 0.0,
            "data_loss_risk": "unknown"
        }

        if not snapshots:
            health["data_loss_risk"] = "high"
            return health

        # Calculate success rate (assume all listed snapshots are successful)
        total_snapshots = len(snapshots)
        successful_snapshots = total_snapshots  # In real implementation, check for failed backups
        health["backup_success_rate"] = (successful_snapshots / max(total_snapshots, 1)) * 100

        # Calculate average backup time (placeholder - would need timing data)
        health["average_backup_time_seconds"] = 30  # Assume 30 seconds average

        # Calculate storage utilization (placeholder)
        total_size = sum(s["statistics"].get("compressed_size_bytes", 0) for s in snapshots)
        # Assume 10GB available storage
        available_storage = 10 * 1024 * 1024 * 1024  # 10GB
        health["storage_utilization_percent"] = (total_size / available_storage) * 100

        # Determine data loss risk
        latest_snapshot = max(snapshots, key=lambda s: s.get("created_at", ""))
        latest_time = datetime.fromisoformat(latest_snapshot.get("created_at", datetime.now(timezone.utc).isoformat()))
        hours_since_last_backup = (datetime.now(timezone.utc) - latest_time).total_seconds() / 3600

        if hours_since_last_backup < 1:
            health["data_loss_risk"] = "low"
        elif hours_since_last_backup < 24:
            health["data_loss_risk"] = "medium"
        else:
            health["data_loss_risk"] = "high"

        return health

    def _generate_alerts(self, status: Dict) -> List[Dict]:
        """Generate alerts based on status information."""
        alerts = []

        # Check backup age
        if status["automated_backup"]["last_backup"]:
            last_backup = datetime.fromisoformat(status["automated_backup"]["last_backup"])
            hours_ago = (datetime.now(timezone.utc) - last_backup).total_seconds() / 3600

            if hours_ago > 24:
                alerts.append({
                    "level": "error",
                    "message": f"Last backup is {hours_ago:.1f} hours old",
                    "action": "Check automated backup status"
                })
            elif hours_ago > 6:
                alerts.append({
                    "level": "warning",
                    "message": f"Last backup is {hours_ago:.1f} hours old",
                    "action": "Verify backup system"
                })

        # Check storage utilization
        storage_percent = status["health_indicators"]["storage_utilization_percent"]
        if storage_percent > 80:
            alerts.append({
                "level": "warning",
                "message": f"Backup storage {storage_percent:.1f}% full",
                "action": "Clean up old snapshots"
            })

        # Check success rate
        success_rate = status["health_indicators"]["backup_success_rate"]
        if success_rate < 95:
            alerts.append({
                "level": "warning",
                "message": f"Backup success rate: {success_rate:.1f}%",
                "action": "Check backup logs"
            })

        # Check automated backup status
        if not status["automated_backup"]["running"]:
            alerts.append({
                "level": "warning",
                "message": "Automated backup not running",
                "action": "Start automated backup"
            })

        return alerts

    def _get_recovery_history(self) -> List[Dict]:
        """Get recovery operation history."""
        recovery_file = self.backup_root / "recovery_history.jsonl"
        history = []

        if recovery_file.exists():
            try:
                with open(recovery_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            history.append(json.loads(line))
            except (json.JSONDecodeError, IOError):
                pass

        return history


# Flask route integration for cockpit
def register_backup_routes(app, workspace_root: Path):
    """
    Register backup dashboard routes with Flask app.
    """

    dashboard = BackupDashboard(workspace_root)

    @app.route('/api/backup/status')
    def get_backup_status():
        """Get backup system status."""
        try:
            status = dashboard.get_backup_status()
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/backup/history')
    def get_backup_history():
        """Get backup operation history."""
        try:
            limit = int(request.args.get('limit', 20))
            history = dashboard.get_backup_history(limit)
            return jsonify({"history": history})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/backup/trigger', methods=['POST'])
    def trigger_manual_backup():
        """Trigger manual backup."""
        try:
            result = dashboard.trigger_manual_backup()
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/backup/storage')
    def get_storage_analysis():
        """Get storage analysis and recommendations."""
        try:
            analysis = dashboard.get_storage_analysis()
            return jsonify(analysis)
        except Exception as e:
            return jsonify({"error": str(e)}), 500


def main():
    """CLI interface for backup dashboard."""
    import argparse

    parser = argparse.ArgumentParser(description="Backup Dashboard")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace root directory")
    parser.add_argument("--status", action="store_true", help="Show backup status")
    parser.add_argument("--history", action="store_true", help="Show backup history")
    parser.add_argument("--storage", action="store_true", help="Show storage analysis")
    parser.add_argument("--trigger", action="store_true", help="Trigger manual backup")

    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    dashboard = BackupDashboard(workspace_root)

    if args.status:
        status = dashboard.get_backup_status()
        print("Backup System Status:")
        print(f"  Status: {status['system_status']}")
        print(f"  Automated: {status['automated_backup']['running']}")
        print(f"  Total snapshots: {status['storage']['total_snapshots']}")
        print(f"  Last backup: {status['automated_backup']['last_backup']}")
        if status['alerts']:
            print("  Alerts:")
            for alert in status['alerts']:
                print(f"    [{alert['level']}] {alert['message']}")

    elif args.history:
        history = dashboard.get_backup_history()
        if history:
            print("Backup History:")
            for item in history[:10]:  # Show last 10
                print(f"  {item['timestamp'][:19]} - {item['type']} - {item.get('snapshot_name', 'N/A')}")
        else:
            print("No backup history found")

    elif args.storage:
        analysis = dashboard.get_storage_analysis()
        print("Storage Analysis:")
        print(f"  Total size: {analysis['total_size_bytes']} bytes")
        print(f"  Snapshots: {analysis['snapshots_by_age']['last_24h']['count']} (24h), {analysis['snapshots_by_age']['last_7d']['count']} (7d), {analysis['snapshots_by_age']['older']['count']} (older)")
        if analysis['recommendations']:
            print("  Recommendations:")
            for rec in analysis['recommendations']:
                print(f"    - {rec}")

    elif args.trigger:
        result = dashboard.trigger_manual_backup()
        if result["success"]:
            print(f"Manual backup created: {result['snapshot_name']}")
        else:
            print(f"Manual backup failed: {result['message']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
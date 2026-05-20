#!/usr/bin/env python3
"""
Service Orchestrator - Background Service Management System

This script provides autostart infrastructure for monitoring and automation services.
It manages background processes for AI integrity protection, behavioral telemetry,
automated backups, and other critical services.

Usage:
    python service_orchestrator.py --start-all    # Start all services
    python service_orchestrator.py --start <service>  # Start specific service
    python service_orchestrator.py --stop-all     # Stop all services
    python service_orchestrator.py --status       # Show service status
    python service_orchestrator.py --daemon       # Run as daemon (persistent)
"""

import argparse
import json
import logging
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServiceOrchestrator:
    """Manages background services for the Keeper system."""

    def __init__(self, workspace_root: Path, daemon_mode: bool = False):
        self.workspace_root = workspace_root
        self.services = {}
        self.running_services = {}
        self.threads = {}
        self.running = True
        self.daemon_mode = daemon_mode

        # Define available services
        self._define_services()

        # Setup signal handlers only in daemon mode
        if daemon_mode:
            try:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            except ValueError:
                # Signal handling not available in this context
                pass

    def _define_services(self):
        """Define the available services and their configurations."""

        # Backup Manager - automated snapshots
        self.services['backup_manager'] = {
            'name': 'Automated Backup',
            'command': [sys.executable, 'backup/backup_manager.py', '--start-auto'],
            'working_dir': str(self.workspace_root),
            'description': 'Automated workspace backups every 30 minutes',
            'type': 'subprocess',  # Runs as separate process
            'health_check': self._check_backup_status
        }

        # Behavioral Telemetry Analyzer - periodic analysis
        self.services['behavioral_telemetry'] = {
            'name': 'Behavioral Telemetry',
            'function': self._run_behavioral_telemetry,
            'description': 'Continuous behavioral pattern analysis',
            'type': 'thread',  # Runs in thread
            'interval_minutes': 15,
            'health_check': self._check_telemetry_status
        }

        # AI Integrity Protector - continuous monitoring
        self.services['ai_integrity'] = {
            'name': 'AI Integrity Protection',
            'function': self._run_integrity_monitoring,
            'description': 'Continuous AI safety and integrity monitoring',
            'type': 'thread',
            'interval_minutes': 5,
            'health_check': self._check_integrity_status
        }

        # Token Governor Monitor - budget monitoring
        self.services['token_monitor'] = {
            'name': 'Token Budget Monitor',
            'function': self._run_token_monitoring,
            'description': 'Continuous token usage monitoring and alerts',
            'type': 'thread',
            'interval_minutes': 10,
            'health_check': self._check_token_status
        }

        # Quality Manager - DEACTIVATED due to terminal interference
        # self.services['quality_manager'] = {
        #     'name': 'Quality Manager',
        #     'function': self._run_quality_monitoring,
        #     'description': 'Continuous code quality monitoring and alerts',
        #     'type': 'thread',
        #     'interval_minutes': 30,
        #     'health_check': self._check_quality_status
        # }

        # Chaosbox - seed idea quality control pipeline
        self.services['chaosbox'] = {
            'name': 'Chaosbox Quality Control',
            'function': self._run_chaosbox_processing,
            'description': 'Continuous processing of seed ideas through quality control pipeline',
            'type': 'thread',
            'continuous': True,  # Runs continuously, not on interval
            'health_check': self._check_chaosbox_status
        }

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        if self.daemon_mode:
            logger.info(f"Received signal {signum}, shutting down services...")
            self.running = False
            self.stop_all_services()

    def start_service(self, service_name: str) -> bool:
        """Start a specific service."""
        if service_name not in self.services:
            logger.error(f"Unknown service: {service_name}")
            return False

        service_config = self.services[service_name]

        try:
            if service_config['type'] == 'subprocess':
                # Start as subprocess
                process = subprocess.Popen(
                    service_config['command'],
                    cwd=service_config.get('working_dir', str(self.workspace_root)),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.running_services[service_name] = {
                    'process': process,
                    'config': service_config,
                    'start_time': time.time()
                }
                logger.info(f"Started subprocess service: {service_config['name']}")

            elif service_config['type'] == 'thread':
                # Start as thread
                thread = threading.Thread(
                    target=self._run_service_thread,
                    args=(service_name, service_config),
                    daemon=True
                )
                thread.start()
                self.threads[service_name] = thread
                self.running_services[service_name] = {
                    'thread': thread,
                    'config': service_config,
                    'start_time': time.time()
                }
                logger.info(f"Started thread service: {service_config['name']}")

            return True

        except Exception as e:
            logger.error(f"Failed to start service {service_name}: {e}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """Stop a specific service."""
        if service_name not in self.running_services:
            logger.warning(f"Service {service_name} is not running")
            return False

        service_info = self.running_services[service_name]

        try:
            if 'process' in service_info:
                # Stop subprocess
                process = service_info['process']
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                logger.info(f"Stopped subprocess service: {service_info['config']['name']}")

            elif 'thread' in service_info:
                # Threads are daemon threads, they will stop when main process exits
                logger.info(f"Thread service {service_info['config']['name']} will stop on shutdown")

            del self.running_services[service_name]
            return True

        except Exception as e:
            logger.error(f"Failed to stop service {service_name}: {e}")
            return False

    def start_all_services(self) -> Dict[str, bool]:
        """Start all defined services."""
        results = {}
        for service_name in self.services:
            results[service_name] = self.start_service(service_name)
        return results

    def stop_all_services(self):
        """Stop all running services."""
        for service_name in list(self.running_services.keys()):
            self.stop_service(service_name)

    def get_service_status(self) -> Dict:
        """Get status of all services."""
        status = {}

        for service_name, service_config in self.services.items():
            service_status = {
                'name': service_config['name'],
                'description': service_config['description'],
                'running': service_name in self.running_services,
                'type': service_config['type']
            }

            if service_name in self.running_services:
                service_info = self.running_services[service_name]
                service_status['start_time'] = service_info['start_time']
                service_status['uptime_seconds'] = time.time() - service_info['start_time']

                # Run health check if available
                if 'health_check' in service_config:
                    try:
                        health_status = service_config['health_check']()
                        service_status['health'] = health_status
                    except Exception as e:
                        service_status['health'] = {'status': 'error', 'error': str(e)}

            status[service_name] = service_status

        return status

    def _run_service_thread(self, service_name: str, service_config: Dict):
        """Run a service function in a thread with periodic execution or continuously."""
        if service_config.get('continuous', False):
            # Continuous service - run once and keep alive
            try:
                service_config['function']()
            except Exception as e:
                logger.error(f"Error in continuous service {service_name}: {e}")
        else:
            # Periodic service - run on intervals
            interval_seconds = service_config.get('interval_minutes', 15) * 60

            while self.running:
                try:
                    service_config['function']()
                except Exception as e:
                    logger.error(f"Error in service {service_name}: {e}")

                # Wait for next interval or until shutdown
                time.sleep(min(interval_seconds, 60))  # Check every minute for shutdown

    # Service implementation functions

    def _run_behavioral_telemetry(self):
        """Run behavioral telemetry analysis."""
        try:
            from behavioral_telemetry_analyzer import BehavioralTelemetryAnalyzer

            breadcrumb_file = self.workspace_root / "breadcrumb_trail.jsonl"
            analyzer = BehavioralTelemetryAnalyzer(str(breadcrumb_file))
            state = analyzer.get_enhanced_behavioral_state()

            # Log significant findings
            if state['confidence_score'] < 30:
                logger.warning(f"Low confidence detected: {state['confidence_score']:.1f}%")
            elif state['arousal_level'] > 0.8:
                logger.info(f"High activity detected: arousal {state['arousal_level']:.2f}")

        except ImportError:
            logger.error("Behavioral telemetry module not available")
        except Exception as e:
            logger.error(f"Behavioral telemetry error: {e}")

    def _run_integrity_monitoring(self):
        """Run AI integrity monitoring."""
        try:
            from ai_integrity_protector import AIIntegrityProtector

            protector = AIIntegrityProtector(self.workspace_root)
            # Run multiple integrity checks
            file_checks = protector.validate_file_integrity()
            bypass_checks = protector.check_for_bypass_attempts()
            breadcrumb_checks = protector.validate_breadcrumb_drift_protection()

            all_results = file_checks + bypass_checks + breadcrumb_checks

            # Log any failures
            failures = [r for r in all_results if r.status == 'FAIL']
            if failures:
                for failure in failures:
                    logger.warning(f"Integrity check failed: {failure.check_type} - {failure.message}")

        except ImportError:
            logger.error("AI integrity protector module not available")
        except Exception as e:
            logger.error(f"Integrity monitoring error: {e}")

    def _run_token_monitoring(self):
        """Run token budget monitoring."""
        try:
            from token_governor import TokenGovernor

            governor = TokenGovernor(workspace_root=self.workspace_root)
            metrics = governor.get_current_metrics()

            # Log warnings for concerning token levels
            if metrics.zone.value in ['EMERGENCY', 'ABORT']:
                logger.warning(f"Token budget critical: {metrics.used:,} used ({metrics.percentage:.1f}%), zone: {metrics.zone.value}")

        except ImportError:
            logger.error("Token governor module not available")
        except Exception as e:
            logger.error(f"Token monitoring error: {e}")

    def _run_quality_monitoring(self):
        """Run quality monitoring scan."""
        try:
            # Import quality manager
            sys.path.insert(0, str(self.workspace_root / "quality_manager"))
            from quality_integration import QualityManagerIntegration

            integration = QualityManagerIntegration()
            
            # Run quality scan
            results = integration.run_quality_scan(save_report=True)
            
            score = results["project_score"]["overall_score"]
            issues_count = len(results["issues"])
            
            # Log quality status
            if score < 70:
                logger.warning(f"Quality score critical: {score:.1f}/100, {issues_count} issues detected")
            elif score < 80:
                logger.info(f"Quality score acceptable: {score:.1f}/100, {issues_count} issues detected")
            else:
                logger.info(f"Quality score good: {score:.1f}/100, {issues_count} issues detected")

        except ImportError:
            logger.error("Quality manager module not available")
        except Exception as e:
            logger.error(f"Quality monitoring error: {e}")

    def _run_chaosbox_processing(self):
        """Run chaosbox idea processing pipeline."""
        try:
            # Import chaosbox manager
            sys.path.insert(0, str(self.workspace_root / "chaosbox"))
            from chaosbox_manager import get_chaosbox_manager

            manager = get_chaosbox_manager()
            
            # Start processing if not already running
            if not hasattr(manager, 'is_running') or not manager.is_running:
                manager.start_processing()
                logger.info("Chaosbox processing started")
            
            # Keep the thread alive while processing
            while self.running:
                time.sleep(30)  # Check every 30 seconds
                # The chaosbox manager handles its own threading internally
                
        except ImportError:
            logger.error("Chaosbox manager module not available")
        except Exception as e:
            logger.error(f"Chaosbox processing error: {e}")

    def _check_chaosbox_status(self) -> Dict:
        """Check chaosbox processing health."""
        try:
            sys.path.insert(0, str(self.workspace_root / "chaosbox"))
            from chaosbox_manager import get_chaosbox_status
            
            status = get_chaosbox_status()
            return {
                'status': 'healthy',
                'queue_size': status.get('queue_size', 0),
                'processing_count': status.get('processing_count', 0),
                'completed_count': status.get('completed_count', 0)
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    # Health check functions

    def _check_backup_status(self) -> Dict:
        """Check backup system health."""
        try:
            from backup.backup_manager import BackupManager
            manager = BackupManager(self.workspace_root)
            status = manager.get_backup_status()
            return {
                'status': 'healthy' if status['total_snapshots'] > 0 else 'warning',
                'snapshots': status['total_snapshots'],
                'last_backup': status.get('latest_snapshot', {}).get('created_at', 'never')
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_telemetry_status(self) -> Dict:
        """Check telemetry system health."""
        try:
            telemetry_file = self.workspace_root / "breadcrumb_trail.jsonl"
            if telemetry_file.exists():
                return {'status': 'healthy', 'file_exists': True}
            else:
                return {'status': 'warning', 'file_exists': False}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_integrity_status(self) -> Dict:
        """Check integrity system health."""
        try:
            transaction_file = self.workspace_root / "_transaction_log.jsonl"
            if transaction_file.exists():
                return {'status': 'healthy', 'log_exists': True}
            else:
                return {'status': 'warning', 'log_exists': False}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_token_status(self) -> Dict:
        """Check token monitoring health."""
        try:
            from token_governor import TokenGovernor
            governor = TokenGovernor(workspace_root=self.workspace_root)
            metrics = governor.get_current_metrics()
            return {
                'status': 'healthy',
                'used_tokens': metrics.used,
                'budget_zone': metrics.zone.value
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_quality_status(self) -> Dict:
        """Check quality monitoring health."""
        try:
            sys.path.insert(0, str(self.workspace_root / "quality_manager"))
            from quality_integration import QualityManagerIntegration
            
            integration = QualityManagerIntegration()
            status = integration.get_quality_status()
            return {
                'status': 'healthy',
                'overall_score': status['overall_score'],
                'issues_count': status['issues_count'],
                'last_update': status['last_update']
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_service_health(self, service_name: str) -> Dict:
        """Get health status for a specific service."""
        if service_name not in self.services:
            return {'status': 'unknown', 'error': 'Service not defined'}

        service_config = self.services[service_name]

        # Call the service's health check function if available
        if 'health_check' in service_config:
            try:
                health_check_func = service_config['health_check']
                return health_check_func()
            except Exception as e:
                return {'status': 'error', 'error': str(e)}

        # Default health check based on running status
        if service_name in self.running_services:
            uptime = time.time() - self.running_services[service_name]['start_time']
            return {
                'status': 'healthy',
                'uptime_seconds': uptime
            }
        else:
            return {'status': 'stopped'}

    def run_daemon(self):
        """Run the orchestrator as a daemon."""
        logger.info("Starting Service Orchestrator daemon...")

        # Start all services
        self.start_all_services()

        # Main daemon loop
        while self.running:
            time.sleep(60)  # Check every minute

            # Log status periodically
            status = self.get_service_status()
            running_count = sum(1 for s in status.values() if s['running'])
            logger.info(f"Service status: {running_count}/{len(status)} services running")

        logger.info("Service Orchestrator daemon stopped")


def main():
    """CLI interface for the service orchestrator."""
    parser = argparse.ArgumentParser(description="Service Orchestrator - Background Service Management")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace root directory")
    parser.add_argument("--start-all", action="store_true", help="Start all services")
    parser.add_argument("--start", type=str, help="Start specific service")
    parser.add_argument("--stop-all", action="store_true", help="Stop all services")
    parser.add_argument("--status", action="store_true", help="Show service status")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (persistent)")

    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    orchestrator = ServiceOrchestrator(workspace_root, daemon_mode=args.daemon)

    if args.start_all:
        results = orchestrator.start_all_services()
        print("Service startup results:")
        for service, success in results.items():
            status = "✅ Started" if success else "❌ Failed"
            print(f"  {service}: {status}")

    elif args.start:
        success = orchestrator.start_service(args.start)
        print(f"Service {args.start}: {'✅ Started' if success else '❌ Failed to start'}")

    elif args.stop_all:
        orchestrator.stop_all_services()
        print("All services stopped")

    elif args.status:
        status = orchestrator.get_service_status()
        print("Service Status:")
        print("=" * 50)
        for service_name, service_info in status.items():
            running = "🟢 Running" if service_info['running'] else "🔴 Stopped"
            print(f"{service_info['name']} ({service_name}): {running}")
            print(f"  Description: {service_info['description']}")
            if service_info['running']:
                uptime = service_info.get('uptime_seconds', 0)
                print(f"  Uptime: {uptime:.0f} seconds")
                if 'health' in service_info:
                    health = service_info['health']
                    health_status = health.get('status', 'unknown')
                    health_icon = "✅" if health_status == 'healthy' else "⚠️" if health_status == 'warning' else "❌"
                    print(f"  Health: {health_icon} {health_status}")
            print()

    elif args.daemon:
        orchestrator.run_daemon()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
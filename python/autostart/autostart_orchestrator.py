"""
Autostart Orchestrator
Main engine for starting, monitoring, and managing autostart services
"""

import time
import subprocess
import threading
import signal
import os
import psutil
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from service_registry import ServiceRegistry, ServiceStatus, ServiceDefinition
from health_monitor import HealthMonitor


class AutostartOrchestrator:
    def __init__(self, registry: ServiceRegistry, health_monitor: HealthMonitor):
        self.registry = registry
        self.health_monitor = health_monitor
        self.executor = ThreadPoolExecutor(max_workers=3)  # Limited concurrent starts
        self.running = False
        self.startup_complete = False
        self.startup_lock = threading.Lock()

        # Register health callbacks
        for service_name in self.registry.services:
            self.health_monitor.register_health_callback(service_name, self._handle_service_restart)

    def start_all_services(self) -> Dict[str, bool]:
        """Start all enabled services in dependency order"""
        with self.startup_lock:
            if self.startup_complete:
                return {"error": "Startup already completed"}

            print("Starting autostart services...")
            self.running = True

            startup_order = self.registry.get_startup_order()
            results = {}

            # Validate dependencies first
            dep_errors = self.registry.validate_dependencies()
            if dep_errors:
                return {"error": "Dependency validation failed", "details": dep_errors}

            # Start services in parallel respecting dependencies
            futures = {}
            for service in startup_order:
                if not service.enabled:
                    continue

                future = self.executor.submit(self._start_service, service.name)
                futures[future] = service.name

            # Wait for all startups to complete
            for future in as_completed(futures):
                service_name = futures[future]
                try:
                    success = future.result(timeout=60)  # 60 second timeout per service
                    results[service_name] = success
                except Exception as e:
                    print(f"Service {service_name} startup failed: {e}")
                    results[service_name] = False

            self.startup_complete = True
            self.health_monitor.start_monitoring()

            successful_starts = sum(1 for success in results.values() if success)
            print(f"Autostart complete: {successful_starts}/{len(results)} services started")

            return results

    def _start_service(self, service_name: str) -> bool:
        """Start a single service"""
        service = self.registry.services.get(service_name)
        if not service:
            return False

        try:
            print(f"Starting service: {service_name}")

            # Check if dependencies are running
            for dep in service.dependencies:
                dep_service = self.registry.services.get(dep)
                if dep_service and dep_service.enabled and dep_service.status != ServiceStatus.RUNNING:
                    print(f"Service {service_name}: waiting for dependency {dep}")
                    # Wait up to 30 seconds for dependency
                    timeout = 30
                    while timeout > 0 and dep_service.status != ServiceStatus.RUNNING:
                        time.sleep(1)
                        timeout -= 1

                    if dep_service.status != ServiceStatus.RUNNING:
                        print(f"Service {service_name}: dependency {dep} failed to start")
                        return False

            # Update status to starting
            self.registry.update_service_status(service_name, ServiceStatus.STARTING)

            # Launch the process
            cmd = ["python", service.script_path] + service.args
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path.cwd(),
                env=os.environ.copy()
            )

            # Wait a bit for process to start
            time.sleep(2)

            if process.poll() is None:  # Process is still running
                pid = process.pid
                self.registry.update_service_status(service_name, ServiceStatus.RUNNING, pid)
                print(f"Service {service_name} started successfully (PID: {pid})")
                return True
            else:
                # Process exited immediately
                stdout, stderr = process.communicate()
                print(f"Service {service_name} failed to start:")
                if stdout:
                    print(f"STDOUT: {stdout.decode()}")
                if stderr:
                    print(f"STDERR: {stderr.decode()}")
                self.registry.update_service_status(service_name, ServiceStatus.FAILED)
                return False

        except Exception as e:
            print(f"Error starting service {service_name}: {e}")
            self.registry.update_service_status(service_name, ServiceStatus.FAILED)
            return False

    def _handle_service_restart(self, service_name: str, action: str):
        """Handle service restart requests from health monitor"""
        if action == "restart":
            threading.Thread(target=self._restart_service, args=(service_name,), daemon=True).start()

    def _restart_service(self, service_name: str):
        """Restart a failed service"""
        service = self.registry.services.get(service_name)
        if not service:
            return

        print(f"Restarting service: {service_name}")

        # Stop existing process if any
        if service.pid:
            try:
                os.kill(service.pid, signal.SIGTERM)
                time.sleep(2)  # Give it time to terminate gracefully
                if psutil.pid_exists(service.pid):
                    os.kill(service.pid, signal.SIGKILL)
            except:
                pass

        # Reset status and restart
        service.pid = None
        service.start_time = None
        service.health_check_failures = 0

        success = self._start_service(service_name)
        if not success:
            print(f"Failed to restart service {service_name}")

    def stop_all_services(self):
        """Stop all running services"""
        print("Stopping all autostart services...")

        for service_name, service in self.registry.services.items():
            if service.status == ServiceStatus.RUNNING and service.pid:
                try:
                    print(f"Stopping service: {service_name} (PID: {service.pid})")
                    os.kill(service.pid, signal.SIGTERM)
                    time.sleep(1)
                    if psutil.pid_exists(service.pid):
                        os.kill(service.pid, signal.SIGKILL)
                    self.registry.update_service_status(service_name, ServiceStatus.STOPPED)
                except Exception as e:
                    print(f"Error stopping service {service_name}: {e}")

        self.health_monitor.stop_monitoring()
        self.running = False
        self.executor.shutdown(wait=True)
        print("All services stopped")

    def get_status_summary(self) -> Dict:
        """Get comprehensive status summary"""
        registry_summary = self.registry.get_service_status_summary()

        summary = {
            "orchestrator_status": "running" if self.running else "stopped",
            "startup_complete": self.startup_complete,
            "health_monitoring": self.health_monitor.monitoring,
            **registry_summary
        }

        return summary

    def reload_configuration(self):
        """Reload service configuration"""
        try:
            self.registry.load_config()
            print("Service configuration reloaded")
            return True
        except Exception as e:
            print(f"Failed to reload configuration: {e}")
            return False


# Global orchestrator instance
orchestrator = AutostartOrchestrator(ServiceRegistry(), HealthMonitor(ServiceRegistry()))
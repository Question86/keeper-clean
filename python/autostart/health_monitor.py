"""
Health Monitor for Autostart Services
Monitors service health, detects failures, and triggers restarts
"""

import time
import psutil
import subprocess
import threading
from pathlib import Path
from typing import Dict, Optional, Callable
from service_registry import ServiceRegistry, ServiceStatus, ServiceDefinition


class HealthMonitor:
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.health_callbacks: Dict[str, Callable] = {}

    def start_monitoring(self):
        """Start the health monitoring thread"""
        if self.monitoring:
            return

        self.monitoring = True
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("Health monitoring started")

    def stop_monitoring(self):
        """Stop the health monitoring thread"""
        if not self.monitoring:
            return

        self.monitoring = False
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("Health monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self.stop_event.is_set():
            try:
                self._check_all_services()
            except Exception as e:
                print(f"Health monitor error: {e}")

            # Sleep for 10 seconds between checks
            self.stop_event.wait(10)

    def _check_all_services(self):
        """Check health of all running services"""
        current_time = time.time()

        for service_name, service in self.registry.services.items():
            if not service.enabled or service.status != ServiceStatus.RUNNING:
                continue

            # Check if it's time for health check
            if (service.last_health_check and
                current_time - service.last_health_check < service.health_check_interval):
                continue

            self._check_service_health(service_name)

    def _check_service_health(self, service_name: str):
        """Check health of a specific service"""
        service = self.registry.services.get(service_name)
        if not service or not service.pid:
            return

        try:
            # Check if process is still running
            process = psutil.Process(service.pid)

            # Check CPU and memory usage
            cpu_percent = process.cpu_percent(interval=1)
            memory_mb = process.memory_info().rss / 1024 / 1024

            # Check resource limits
            if cpu_percent > service.resource_limits.get('cpu_percent', 100):
                print(f"Service {service_name}: CPU usage {cpu_percent:.1f}% exceeds limit")
                self._handle_service_failure(service_name, "CPU limit exceeded")
                return

            if memory_mb > service.resource_limits.get('memory_mb', 1000):
                print(f"Service {service_name}: Memory usage {memory_mb:.1f}MB exceeds limit")
                self._handle_service_failure(service_name, "Memory limit exceeded")
                return

            # Service-specific health checks
            if self._perform_service_health_check(service):
                # Health check passed
                service.last_health_check = time.time()
                service.health_check_failures = 0
            else:
                # Health check failed
                service.health_check_failures += 1
                print(f"Service {service_name}: Health check failed ({service.health_check_failures}/{service.max_restart_attempts})")

                if service.health_check_failures >= service.max_restart_attempts:
                    self._handle_service_failure(service_name, "Health check failures exceeded")

        except psutil.NoSuchProcess:
            # Process died
            self._handle_service_failure(service_name, "Process terminated unexpectedly")
        except Exception as e:
            print(f"Error checking service {service_name}: {e}")

    def _perform_service_health_check(self, service: ServiceDefinition) -> bool:
        """Perform service-specific health check"""
        # For now, just check if process exists and is responsive
        # In future, could add service-specific checks (e.g., HTTP endpoints, log analysis)
        try:
            if service.pid:
                process = psutil.Process(service.pid)
                # Check if process is not zombie
                return process.status() != psutil.STATUS_ZOMBIE
        except:
            pass
        return False

    def _handle_service_failure(self, service_name: str, reason: str):
        """Handle service failure - attempt restart or mark as failed"""
        service = self.registry.services.get(service_name)
        if not service:
            return

        print(f"Service {service_name} failed: {reason}")

        if service.restart_count < service.max_restart_attempts:
            print(f"Attempting to restart service {service_name} (attempt {service.restart_count + 1})")
            self.registry.update_service_status(service_name, ServiceStatus.RESTARTING)
            service.restart_count += 1

            # Trigger restart via callback
            if service_name in self.health_callbacks:
                self.health_callbacks[service_name](service_name, "restart")
        else:
            print(f"Service {service_name} exceeded max restart attempts, marking as failed")
            self.registry.update_service_status(service_name, ServiceStatus.FAILED)

    def register_health_callback(self, service_name: str, callback: Callable):
        """Register callback for service health events"""
        self.health_callbacks[service_name] = callback

    def get_service_health_status(self, service_name: str) -> Dict:
        """Get detailed health status for a service"""
        service = self.registry.services.get(service_name)
        if not service:
            return {"error": "Service not found"}

        status = {
            "name": service.name,
            "status": service.status.value,
            "pid": service.pid,
            "restart_count": service.restart_count,
            "health_check_failures": service.health_check_failures,
            "last_health_check": service.last_health_check
        }

        if service.pid:
            try:
                process = psutil.Process(service.pid)
                status.update({
                    "cpu_percent": process.cpu_percent(),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "create_time": process.create_time()
                })
            except psutil.NoSuchProcess:
                status["process_status"] = "not_found"

        return status


# Global health monitor instance
health_monitor = HealthMonitor(ServiceRegistry())
"""
Service Registry for Autostart System
Manages service definitions, dependencies, and startup priorities
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ServicePriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class ServiceStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    RESTARTING = "restarting"


@dataclass
class ServiceDefinition:
    name: str
    enabled: bool
    priority: ServicePriority
    script_path: str
    args: List[str]
    dependencies: List[str]
    health_check_interval: int
    max_restart_attempts: int
    resource_limits: Dict[str, float]
    status: ServiceStatus = ServiceStatus.STOPPED
    pid: Optional[int] = None
    start_time: Optional[float] = None
    restart_count: int = 0
    last_health_check: Optional[float] = None
    health_check_failures: int = 0


class ServiceRegistry:
    def __init__(self, config_path: str = "autostart/service_config.json"):
        self.config_path = Path(config_path)
        self.services: Dict[str, ServiceDefinition] = {}
        self.load_config()

    def load_config(self):
        """Load service configuration from JSON file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Service config not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = json.load(f)

        for service_name, service_config in config['services'].items():
            priority = ServicePriority(service_config['priority'])
            script_path = service_config['script']

            # Ensure script exists
            if not Path(script_path).exists():
                print(f"Warning: Script {script_path} for service {service_name} not found")
                continue

            service_def = ServiceDefinition(
                name=service_name,
                enabled=service_config['enabled'],
                priority=priority,
                script_path=script_path,
                args=service_config.get('args', []),
                dependencies=service_config.get('dependencies', []),
                health_check_interval=service_config['health_check_interval'],
                max_restart_attempts=service_config['max_restart_attempts'],
                resource_limits=service_config['resource_limit']
            )

            self.services[service_name] = service_def

    def get_enabled_services(self) -> List[ServiceDefinition]:
        """Get all enabled services sorted by priority"""
        enabled = [s for s in self.services.values() if s.enabled]
        return sorted(enabled, key=lambda s: s.priority.value)

    def get_service_dependencies(self, service_name: str) -> List[str]:
        """Get dependency chain for a service"""
        if service_name not in self.services:
            return []

        service = self.services[service_name]
        deps = []

        for dep in service.dependencies:
            if dep in self.services:
                deps.extend(self.get_service_dependencies(dep))
                deps.append(dep)

        # Remove duplicates while preserving order
        seen = set()
        unique_deps = []
        for dep in deps:
            if dep not in seen:
                seen.add(dep)
                unique_deps.append(dep)

        return unique_deps

    def validate_dependencies(self) -> List[str]:
        """Validate that all dependencies exist and are enabled"""
        errors = []

        for service_name, service in self.services.items():
            if not service.enabled:
                continue

            for dep in service.dependencies:
                if dep not in self.services:
                    errors.append(f"Service {service_name}: dependency {dep} not found")
                elif not self.services[dep].enabled:
                    errors.append(f"Service {service_name}: dependency {dep} is disabled")

        return errors

    def get_startup_order(self) -> List[ServiceDefinition]:
        """Get services in startup order considering dependencies"""
        enabled_services = self.get_enabled_services()
        ordered = []
        processed = set()

        def add_service(service: ServiceDefinition):
            if service.name in processed:
                return

            # Add dependencies first
            for dep_name in service.dependencies:
                if dep_name in self.services:
                    dep_service = self.services[dep_name]
                    if dep_service.enabled:
                        add_service(dep_service)

            ordered.append(service)
            processed.add(service.name)

        for service in enabled_services:
            add_service(service)

        return ordered

    def update_service_status(self, service_name: str, status: ServiceStatus, pid: Optional[int] = None):
        """Update service status"""
        if service_name in self.services:
            self.services[service_name].status = status
            if pid is not None:
                self.services[service_name].pid = pid
            if status == ServiceStatus.RUNNING:
                import time
                self.services[service_name].start_time = time.time()

    def get_service_status_summary(self) -> Dict[str, Any]:
        """Get summary of all service statuses"""
        summary = {
            'total_services': len(self.services),
            'enabled_services': len([s for s in self.services.values() if s.enabled]),
            'running_services': len([s for s in self.services.values() if s.status == ServiceStatus.RUNNING]),
            'failed_services': len([s for s in self.services.values() if s.status == ServiceStatus.FAILED]),
            'services': {}
        }

        for name, service in self.services.items():
            summary['services'][name] = {
                'enabled': service.enabled,
                'status': service.status.value,
                'pid': service.pid,
                'restart_count': service.restart_count
            }

        return summary


# Global registry instance
registry = ServiceRegistry()
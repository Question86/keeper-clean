#!/usr/bin/env python3
"""
Environment Manager - Handles test environment setup and teardown

This module manages the setup and teardown of test environments across different
platforms and configurations, ensuring consistent test execution.
"""

import os
import sys
import json
import shutil
import tempfile
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

class EnvironmentManager:
    """Manages test environment setup and teardown."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.temp_dirs: List[Path] = []
        self.environments: Dict[str, Dict] = self._load_environments()

    def _load_environments(self) -> Dict[str, Dict]:
        """Load environment configurations."""
        return {
            'local': {
                'name': 'Local Development',
                'python_version': '>=3.8',
                'requirements': ['pytest', 'pytest-cov', 'coverage'],
                'env_vars': {},
                'cleanup_temp': True
            },
            'ci': {
                'name': 'CI/CD Pipeline',
                'python_version': '>=3.8',
                'requirements': ['pytest', 'pytest-cov', 'coverage', 'pytest-xdist'],
                'env_vars': {
                    'CI': 'true',
                    'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'
                },
                'cleanup_temp': True
            },
            'staging': {
                'name': 'Staging Environment',
                'python_version': '>=3.8',
                'requirements': ['pytest', 'pytest-cov', 'coverage', 'allure-pytest'],
                'env_vars': {
                    'TEST_ENV': 'staging'
                },
                'cleanup_temp': False
            }
        }

    def setup_environment(self, environment: str = 'local') -> bool:
        """
        Setup test environment.

        Args:
            environment: Environment type ('local', 'ci', 'staging')

        Returns:
            bool: True if setup successful
        """
        if environment not in self.environments:
            print(f"Unknown environment: {environment}")
            return False

        env_config = self.environments[environment]
        print(f"Setting up {env_config['name']} environment...")

        try:
            # Check Python version
            if not self._check_python_version(env_config['python_version']):
                return False

            # Create temporary directories if needed
            if env_config.get('cleanup_temp', True):
                self._create_temp_dirs()

            # Install requirements
            if not self._install_requirements(env_config['requirements']):
                return False

            # Set environment variables
            self._set_environment_variables(env_config['env_vars'])

            # Platform-specific setup
            if not self._platform_setup():
                return False

            print(f"Environment {environment} setup complete")
            return True

        except Exception as e:
            print(f"Environment setup failed: {e}")
            self.teardown_environment(environment)
            return False

    def teardown_environment(self, environment: str = 'local') -> bool:
        """
        Teardown test environment.

        Args:
            environment: Environment type

        Returns:
            bool: True if teardown successful
        """
        print(f"Tearing down {environment} environment...")

        try:
            # Clean up temporary directories
            self._cleanup_temp_dirs()

            # Reset environment variables
            env_config = self.environments.get(environment, {})
            self._reset_environment_variables(env_config.get('env_vars', {}))

            # Platform-specific cleanup
            self._platform_teardown()

            print(f"Environment {environment} teardown complete")
            return True

        except Exception as e:
            print(f"Environment teardown failed: {e}")
            return False

    def _check_python_version(self, required_version: str) -> bool:
        """Check if Python version meets requirements."""
        current_version = sys.version_info
        required = required_version.lstrip('>=')

        try:
            major, minor = map(int, required.split('.')[:2])
            if current_version.major > major or \
               (current_version.major == major and current_version.minor >= minor):
                print(f"Python version {current_version.major}.{current_version.minor} OK")
                return True
            else:
                print(f"Python version {current_version.major}.{current_version.minor} "
                      f"does not meet requirement {required_version}")
                return False
        except ValueError:
            print(f"Invalid version requirement: {required_version}")
            return False

    def _create_temp_dirs(self) -> None:
        """Create temporary directories for testing."""
        # Create temp directory for test artifacts
        temp_dir = Path(tempfile.mkdtemp(prefix='keeper_test_'))
        self.temp_dirs.append(temp_dir)

        # Set environment variable for tests to use
        os.environ['TEST_TEMP_DIR'] = str(temp_dir)
        print(f"Created temp directory: {temp_dir}")

    def _cleanup_temp_dirs(self) -> None:
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                print(f"Failed to cleanup {temp_dir}: {e}")

        self.temp_dirs.clear()

    def _install_requirements(self, requirements: List[str]) -> bool:
        """Install required packages."""
        try:
            # Check if packages are already installed
            missing = []
            for req in requirements:
                if not self._is_package_installed(req):
                    missing.append(req)

            if not missing:
                print("All required packages already installed")
                return True

            print(f"Installing missing packages: {', '.join(missing)}")

            # Use pip to install
            cmd = [sys.executable, '-m', 'pip', 'install'] + missing
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print("Package installation successful")
                return True
            else:
                print(f"Package installation failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"Requirement installation failed: {e}")
            return False

    def _is_package_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        try:
            # Handle version specifiers
            package_name = package.split('>=')[0].split('==')[0].split('<')[0].strip()

            result = subprocess.run(
                [sys.executable, '-c', f'import {package_name}'],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False

    def _set_environment_variables(self, env_vars: Dict[str, str]) -> None:
        """Set environment variables for testing."""
        for key, value in env_vars.items():
            os.environ[key] = value
            print(f"Set {key}={value}")

    def _reset_environment_variables(self, env_vars: Dict[str, str]) -> None:
        """Reset environment variables."""
        for key in env_vars.keys():
            if key in os.environ:
                del os.environ[key]
                print(f"Reset {key}")

    def _platform_setup(self) -> bool:
        """Platform-specific setup."""
        system = platform.system().lower()

        if system == 'windows':
            return self._windows_setup()
        elif system == 'linux':
            return self._linux_setup()
        elif system == 'darwin':
            return self._macos_setup()
        else:
            print(f"Unsupported platform: {system}")
            return False

    def _platform_teardown(self) -> bool:
        """Platform-specific teardown."""
        system = platform.system().lower()

        if system == 'windows':
            return self._windows_teardown()
        elif system == 'linux':
            return self._linux_teardown()
        elif system == 'darwin':
            return self._macos_teardown()
        else:
            return True  # No-op for unsupported platforms

    def _windows_setup(self) -> bool:
        """Windows-specific setup."""
        # Ensure long path support
        os.environ['PYTHONPATH'] = str(self.project_root)
        return True

    def _windows_teardown(self) -> bool:
        """Windows-specific teardown."""
        return True

    def _linux_setup(self) -> bool:
        """Linux-specific setup."""
        os.environ['PYTHONPATH'] = str(self.project_root)
        return True

    def _linux_teardown(self) -> bool:
        """Linux-specific teardown."""
        return True

    def _macos_setup(self) -> bool:
        """macOS-specific setup."""
        os.environ['PYTHONPATH'] = str(self.project_root)
        return True

    def _macos_teardown(self) -> bool:
        """macOS-specific teardown."""
        return True

    def get_environment_info(self, environment: str) -> Optional[Dict]:
        """Get information about an environment configuration."""
        return self.environments.get(environment)

    def list_environments(self) -> List[str]:
        """List available environments."""
        return list(self.environments.keys())
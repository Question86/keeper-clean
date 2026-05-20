#!/usr/bin/env python3
"""
Universal Test Runner - Orchestrates testing across all project components

This module provides a unified interface for running tests across all components
in the Keeper project, with automated environment management and result aggregation.

Usage:
    python test_framework/universal_test_runner.py [options]

Options:
    --component COMPONENT    Run tests for specific component only
    --type TYPE             Test type: unit, integration, performance, all
    --environment ENV       Test environment: local, ci, staging
    --verbose               Enable verbose output
    --report                Generate detailed report
    --parallel              Run tests in parallel where possible
"""

import os
import sys
import time
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import platform

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.environment_manager import EnvironmentManager
from test_framework.result_aggregator import ResultAggregator

@dataclass
class TestResult:
    """Represents the result of a test run."""
    component: str
    test_type: str
    status: str  # 'PASS', 'FAIL', 'SKIP', 'ERROR'
    duration: float
    output: str
    error_output: str = ""
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class TestSuite:
    """Represents a collection of tests for a component."""
    name: str
    component: str
    test_types: List[str]
    requirements: List[str]
    setup_commands: List[str]
    test_commands: List[str]
    teardown_commands: List[str]

class UniversalTestRunner:
    """Main test orchestration class."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.environment_manager = EnvironmentManager(project_root)
        self.result_aggregator = ResultAggregator(project_root)
        self.test_suites = self._load_test_suites()

    def _load_test_suites(self) -> Dict[str, TestSuite]:
        """Load test suite configurations."""
        suites = {}

        # Core Python components
        suites['loop_cockpit'] = TestSuite(
            name='Loop Cockpit',
            component='loop_cockpit',
            test_types=['unit', 'integration'],
            requirements=['flask', 'python>=3.8'],
            setup_commands=[
                'cd /d %PROJECT_ROOT%',
                'python -m pip install -r requirements_cockpit.txt'
            ],
            test_commands=[
                'python -m pytest tests/ -v --tb=short'
            ],
            teardown_commands=[]
        )

        suites['ai_integrity'] = TestSuite(
            name='AI Integrity Framework',
            component='ai_integrity',
            test_types=['unit', 'integration'],
            requirements=['pytest', 'pytest-cov'],
            setup_commands=[
                'cd /d %PROJECT_ROOT%'
            ],
            test_commands=[
                'python -m pytest ai_integrity_protector.py -v',
                'python -m pytest ai_false_positive_suppressor.py -v'
            ],
            teardown_commands=[]
        )

        suites['breadcrumb_tracker'] = TestSuite(
            name='Breadcrumb Tracker',
            component='breadcrumb_tracker',
            test_types=['unit'],
            requirements=['pytest'],
            setup_commands=[
                'cd /d %PROJECT_ROOT%'
            ],
            test_commands=[
                'python -c "from ai_breadcrumb_tracker import BreadcrumbTracker; print(\'Import test passed\')"'
            ],
            teardown_commands=[]
        )

        # Add more test suites as components are identified
        return suites

    def run_tests(self, component: Optional[str] = None,
                  test_type: str = 'all',
                  environment: str = 'local',
                  verbose: bool = False,
                  parallel: bool = False) -> Dict:
        """
        Run tests for specified components.

        Args:
            component: Specific component to test, or None for all
            test_type: Type of tests to run ('unit', 'integration', 'performance', 'all')
            environment: Test environment ('local', 'ci', 'staging')
            verbose: Enable verbose output
            parallel: Run tests in parallel

        Returns:
            Dict containing test results and summary
        """
        start_time = time.time()

        # Setup test environment
        if not self.environment_manager.setup_environment(environment):
            return {
                'status': 'ERROR',
                'error': 'Failed to setup test environment',
                'results': []
            }

        try:
            # Determine which test suites to run
            suites_to_run = []
            if component:
                if component in self.test_suites:
                    suites_to_run = [self.test_suites[component]]
                else:
                    return {
                        'status': 'ERROR',
                        'error': f'Unknown component: {component}',
                        'results': []
                    }
            else:
                suites_to_run = list(self.test_suites.values())

            # Filter by test type
            if test_type != 'all':
                suites_to_run = [
                    suite for suite in suites_to_run
                    if test_type in suite.test_types
                ]

            if verbose:
                print(f"Running tests for {len(suites_to_run)} component(s)")

            # Run test suites
            all_results = []
            for suite in suites_to_run:
                if verbose:
                    print(f"Testing {suite.name}...")

                results = self._run_test_suite(suite, environment, verbose)
                all_results.extend(results)

            # Aggregate results
            summary = self.result_aggregator.aggregate_results(all_results)

            # Generate report
            report_path = self.result_aggregator.generate_report(
                all_results, summary, start_time
            )

            return {
                'status': 'SUCCESS',
                'summary': summary,
                'results': [asdict(result) for result in all_results],
                'report_path': str(report_path),
                'duration': time.time() - start_time
            }

        finally:
            # Cleanup environment
            self.environment_manager.teardown_environment(environment)

    def _run_test_suite(self, suite: TestSuite, environment: str,
                       verbose: bool = False) -> List[TestResult]:
        """Run a single test suite."""
        results = []

        try:
            # Setup component environment
            if not self._execute_commands(suite.setup_commands, suite.component, verbose):
                return [TestResult(
                    component=suite.component,
                    test_type='setup',
                    status='ERROR',
                    duration=0.0,
                    output='',
                    error_output='Setup failed'
                )]

            # Run test commands
            for test_type in suite.test_types:
                start_time = time.time()

                success, output, error_output = self._execute_commands(
                    suite.test_commands, suite.component, verbose
                )

                duration = time.time() - start_time
                status = 'PASS' if success else 'FAIL'

                results.append(TestResult(
                    component=suite.component,
                    test_type=test_type,
                    status=status,
                    duration=duration,
                    output=output,
                    error_output=error_output,
                    metadata={'environment': environment}
                ))

        except Exception as e:
            results.append(TestResult(
                component=suite.component,
                test_type='execution',
                status='ERROR',
                duration=0.0,
                output='',
                error_output=str(e)
            ))

        finally:
            # Always attempt teardown
            self._execute_commands(suite.teardown_commands, suite.component, verbose)

        return results

    def _execute_commands(self, commands: List[str], component: str,
                         verbose: bool = False) -> Tuple[bool, str, str]:
        """Execute a list of shell commands."""
        output = ""
        error_output = ""

        for cmd in commands:
            try:
                # Replace placeholders
                cmd = cmd.replace('%PROJECT_ROOT%', str(self.project_root))

                if verbose:
                    print(f"Executing: {cmd}")

                # Run command
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                output += result.stdout
                error_output += result.stderr

                if result.returncode != 0:
                    return False, output, error_output

            except subprocess.TimeoutExpired:
                error_output += f"Command timed out: {cmd}\n"
                return False, output, error_output
            except Exception as e:
                error_output += f"Command failed: {cmd} - {str(e)}\n"
                return False, output, error_output

        return True, output, error_output

    def list_components(self) -> List[str]:
        """List all available test components."""
        return list(self.test_suites.keys())

    def get_component_info(self, component: str) -> Optional[Dict]:
        """Get information about a specific component."""
        if component not in self.test_suites:
            return None

        suite = self.test_suites[component]
        return {
            'name': suite.name,
            'test_types': suite.test_types,
            'requirements': suite.requirements
        }

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Universal Test Runner')
    parser.add_argument('--component', help='Specific component to test')
    parser.add_argument('--type', choices=['unit', 'integration', 'performance', 'all'],
                       default='all', help='Type of tests to run')
    parser.add_argument('--environment', choices=['local', 'ci', 'staging'],
                       default='local', help='Test environment')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--list', action='store_true', help='List available components')

    args = parser.parse_args()

    runner = UniversalTestRunner(PROJECT_ROOT)

    if args.list:
        print("Available test components:")
        for component in runner.list_components():
            info = runner.get_component_info(component)
            print(f"  {component}: {info['name']} ({', '.join(info['test_types'])})")
        return

    # Run tests
    result = runner.run_tests(
        component=args.component,
        test_type=args.type,
        environment=args.environment,
        verbose=args.verbose,
        parallel=args.parallel
    )

    # Print results
    if result['status'] == 'SUCCESS':
        summary = result['summary']
        print(f"\nTest Results Summary:")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"Duration: {result['duration']:.2f}s")

        if result.get('report_path'):
            print(f"Report: {result['report_path']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)
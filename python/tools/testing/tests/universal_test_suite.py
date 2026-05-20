#!/usr/bin/env python3
"""
Universal Test Suite - Comprehensive test suite for all project components

This module provides a comprehensive test suite that exercises all components
of the Keeper project using the Universal Test Framework.

Usage:
    python tests/universal_test_suite.py [options]

Options:
    --quick          Run quick subset of tests
    --full          Run complete test suite (default)
    --performance   Include performance tests
    --integration   Include integration tests
    --verbose       Enable verbose output
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.universal_test_runner import UniversalTestRunner
from test_framework.result_aggregator import ResultAggregator

class UniversalTestSuite:
    """Comprehensive test suite for all project components."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.runner = UniversalTestRunner(project_root)
        self.aggregator = ResultAggregator(project_root / 'test_reports')

    def run_quick_tests(self) -> dict:
        """Run quick subset of tests for CI/CD."""
        print("Running Quick Test Suite...")

        results = self.runner.run_tests(
            component=None,  # All components
            test_type='unit',
            environment='ci',
            parallel=True,
            verbose=False
        )

        return self.aggregator.aggregate_results(results)

    def run_full_tests(self) -> dict:
        """Run complete test suite."""
        print("Running Full Test Suite...")

        # Unit tests
        unit_results = self.runner.run_tests(
            component=None,
            test_type='unit',
            environment='local',
            parallel=True,
            verbose=True
        )

        # Integration tests
        integration_results = self.runner.run_tests(
            component=None,
            test_type='integration',
            environment='staging',
            parallel=False,
            verbose=True
        )

        # Combine results
        all_results = unit_results + integration_results

        return self.aggregator.aggregate_results(all_results)

    def run_performance_tests(self) -> dict:
        """Run performance regression tests."""
        print("Running Performance Tests...")

        results = self.runner.run_tests(
            component=None,
            test_type='performance',
            environment='local',
            parallel=False,
            verbose=True
        )

        return self.aggregator.aggregate_results(results)

    def run_integration_tests(self) -> dict:
        """Run integration tests."""
        print("Running Integration Tests...")

        results = self.runner.run_tests(
            component=None,
            test_type='integration',
            environment='staging',
            parallel=False,
            verbose=True
        )

        return self.aggregator.aggregate_results(results)

def main():
    parser = argparse.ArgumentParser(description='Universal Test Suite')
    parser.add_argument('--quick', action='store_true', help='Run quick test subset')
    parser.add_argument('--full', action='store_true', help='Run complete test suite')
    parser.add_argument('--performance', action='store_true', help='Include performance tests')
    parser.add_argument('--integration', action='store_true', help='Include integration tests')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Default to full if no specific test type requested
    if not any([args.quick, args.full, args.performance, args.integration]):
        args.full = True

    project_root = Path(__file__).parent.parent
    suite = UniversalTestSuite(project_root)

    start_time = time.time()
    all_results = []

    try:
        if args.quick:
            results = suite.run_quick_tests()
            all_results.append(('quick', results))

        if args.full:
            results = suite.run_full_tests()
            all_results.append(('full', results))

        if args.performance:
            results = suite.run_performance_tests()
            all_results.append(('performance', results))

        if args.integration:
            results = suite.run_integration_tests()
            all_results.append(('integration', results))

        # Generate final report
        final_report = suite.aggregator.generate_final_report(all_results)

        # Print summary
        print("\n" + "="*60)
        print("TEST SUITE COMPLETED")
        print("="*60)
        print(f"Total execution time: {time.time() - start_time:.2f} seconds")
        print(f"Test suites run: {len(all_results)}")

        for suite_name, results in all_results:
            print(f"\n{suite_name.upper()} SUITE:")
            print(f"  Total tests: {results.get('total_tests', 0)}")
            print(f"  Passed: {results.get('passed', 0)}")
            print(f"  Failed: {results.get('failed', 0)}")
            print(f"  Skipped: {results.get('skipped', 0)}")
            print(f"  Success rate: {results.get('success_rate', 0):.1f}%")

        # Save final report
        report_path = project_root / 'test_reports' / f'universal_test_report_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump(final_report, f, indent=2, default=str)

        print(f"\nDetailed report saved to: {report_path}")

        # Exit with appropriate code
        total_failed = sum(results.get('failed', 0) for _, results in all_results)
        sys.exit(0 if total_failed == 0 else 1)

    except Exception as e:
        print(f"Test suite failed with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
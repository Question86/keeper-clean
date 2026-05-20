#!/usr/bin/env python3
"""
Universal Testing Framework

This package provides a unified testing framework for the Keeper project,
enabling comprehensive testing across all components with consistent
reporting and environment management.
"""

from .universal_test_runner import UniversalTestRunner
from .environment_manager import EnvironmentManager
from .result_aggregator import ResultAggregator, TestResult

__version__ = "1.0.0"
__all__ = [
    'UniversalTestRunner',
    'EnvironmentManager',
    'ResultAggregator',
    'TestResult'
]
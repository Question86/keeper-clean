#!/usr/bin/env python3
"""
Test Runner for Mathematical Testing Framework (Task 199)

This script prepares and runs the mathematical testing framework
for deep field piercing exploration.
"""

import sys
import os
from pathlib import Path

def prepare_environment():
    """Prepare the test environment."""
    # Add the axiom scripts to path
    axiom_path = Path("docs/First_research_mega.md/first_scripts")
    if axiom_path.exists():
        sys.path.append(str(axiom_path))
        print(f"✓ Added axiom path: {axiom_path}")
    else:
        print(f"✗ Axiom path not found: {axiom_path}")
        return False

    # Check for required dependencies
    try:
        import torch
        print(f"✓ PyTorch available: {torch.__version__}")
    except ImportError:
        print("✗ PyTorch not available")
        return False

    try:
        import numpy
        print(f"✓ NumPy available: {numpy.__version__}")
    except ImportError:
        print("✗ NumPy not available")
        return False

    # Check for framework
    try:
        from mathematical_testing_framework import MathematicalTestingFramework
        print("✓ Mathematical Testing Framework imported successfully")
    except ImportError as e:
        print(f"✗ Framework import failed: {e}")
        return False

    return True

def run_quick_tests():
    """Run quick validation tests."""
    from mathematical_testing_framework import MathematicalTestingFramework

    framework = MathematicalTestingFramework()
    print("\nRunning quick validation tests...")

    # Test timescale separation
    print("Testing Timescale Separation:")
    result = framework.test_timescale_separation(1e-3, 1e-5)
    print(f"  Ratio 0.01: {'PASS' if result['passed'] else 'FAIL'}")

    result = framework.test_timescale_separation(1e-3, 1e-4)
    print(f"  Ratio 0.1: {'PASS' if result['passed'] else 'FAIL'} (expected FAIL)")

    # Test contraction stability
    print("Testing Contraction Stability:")
    result = framework.test_contraction_stability(0.5, 0.99)
    print(f"  Rho 0.5, c_max 0.99: {'PASS' if result['passed'] else 'FAIL'}")

    result = framework.test_contraction_stability(1.1, 0.99)
    print(f"  Rho 1.1, c_max 0.99: {'PASS' if result['passed'] else 'FAIL'} (expected FAIL)")

    # Test MI finiteness
    print("Testing MI Finiteness:")
    result = framework.test_mi_finiteness(10.0, 0.1)
    print(f"  SNR 100.0: {'PASS' if result['passed'] else 'FAIL'}")

    result = framework.test_mi_finiteness(100.0, 1e-10)
    print(f"  SNR 1e12: {'PASS' if result['passed'] else 'FAIL'} (expected FAIL)")

    print("✓ Quick tests completed")

def run_full_framework():
    """Run the full mathematical testing framework."""
    from mathematical_testing_framework import main
    print("\nRunning full Mathematical Testing Framework...")
    main()

if __name__ == "__main__":
    print("Preparing test environment for Task 199: Mathematical Testing Framework")
    print("=" * 70)

    if not prepare_environment():
        print("Environment preparation failed. Please check dependencies.")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        run_full_framework()
    else:
        run_quick_tests()
        print("\nTo run the full framework, use: python test_runner_task199.py --full")
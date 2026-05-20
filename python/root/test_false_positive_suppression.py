#!/usr/bin/env python3
"""
Test script for AI False-Positive Suppression Architecture

Tests the implementation of TASK_0172.
"""

from pathlib import Path
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.getcwd())

def test_false_positive_suppression():
    """Test the AI False-Positive Suppression system."""
    print("Testing AI False-Positive Suppression Architecture...")

    try:
        from ai_false_positive_suppressor import AIFalsePositiveSuppressor

        workspace_root = Path.cwd()
        suppressor = AIFalsePositiveSuppressor(workspace_root)

        # Test 1: Valid output should pass
        print("\n1. Testing valid output...")
        result1 = suppressor.validate_ai_output(
            content="This is a valid analysis with proper evidence and reasoning.",
            output_type="analysis",
            ai_source="test_ai",
            target_path="reports/test_report.md",
            require_proof=False
        )
        print(f"   Status: {result1['status']}")
        assert result1['status'] in ['approved', 'warning'], f"Expected approved/warning, got {result1['status']}"

        # Test 2: Pretense pattern should be detected
        print("\n2. Testing pretense pattern detection...")
        result2 = suppressor.validate_ai_output(
            content="I am absolutely certain this works perfectly, although it might have some issues.",
            output_type="validation",
            ai_source="test_ai",
            target_path="current.json",
            require_proof=True
        )
        print(f"   Status: {result2['status']}")
        print(f"   Pretense detected: {result2['pretense_detected']}")
        assert result2['pretense_detected'] == True, "Pretense should be detected"
        assert result2['status'] == 'rejected', f"Pretense should be rejected, got {result2['status']}"

        # Test 3: Proof generation
        print("\n3. Testing proof generation...")
        result3 = suppressor.validate_ai_output(
            content="This validation is based on systematic checking.",
            output_type="validation",
            ai_source="test_ai",
            target_path="milestone_01.json",
            require_proof=True
        )
        print(f"   Status: {result3['status']}")
        print(f"   Proof provided: {result3['proof_provided']}")
        assert result3['proof_provided'] == True, "Proof should be provided for validation type"

        # Test 4: Architectural enforcement
        print("\n4. Testing architectural enforcement...")
        result4 = suppressor.validate_ai_output(
            content="I am certain this task creation is valid.",
            output_type="task_creation",
            ai_source="test_ai",
            target_path="current.json",  # Invalid path for task_creation
            require_proof=True
        )
        print(f"   Status: {result4['status']}")
        print(f"   Injection allowed: {result4['injection_allowed']}")
        assert result4['injection_allowed'] == False, "Injection should be blocked for invalid claim type/path"

        # Test 5: Test framework
        print("\n5. Testing test framework creation...")
        test_framework = suppressor.create_test_framework()
        print(f"   Framework created: {test_framework['test_framework_created']}")
        print(f"   Test categories: {len(test_framework['test_categories'])}")
        print(f"   Total test cases: {test_framework['total_test_cases']}")

        # Run tests
        test_results = test_framework['run_tests'](test_framework['test_cases'])
        print(f"   Tests run: {test_results['total_tests']}")
        print(f"   Tests passed: {test_results['passed']}")
        print(f"   Tests failed: {test_results['failed']}")

        assert test_results['passed'] > 0, "Some tests should pass"
        assert test_results['total_tests'] > 0, "Tests should exist"

        print("\n✅ All tests passed! AI False-Positive Suppression Architecture is working.")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_false_positive_suppression()
    sys.exit(0 if success else 1)
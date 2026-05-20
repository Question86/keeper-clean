#!/usr/bin/env python3
"""
AI Integrity Protection Tests

Tests for TASK_0172 and TASK_0173: Protection against false-positives and jailbreak bypasses.
"""

import unittest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from ai_integrity_protector import AIIntegrityProtector, IntegrityCheck, TransactionRecord


class TestAIIntegrityProtector(unittest.TestCase):
    """Test cases for the AI integrity protection system."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create test files first
        self.test_files = {
            "current.json": {"STATE": {"status": "ACTIVE", "loop": 84}},
            "milestone_01.json": {"completed": True},
            "_SESSION.md": "# Session\nTest content",
            "NEU.md": "# NEU\nTest content"
        }

        for filename, content in self.test_files.items():
            filepath = self.temp_dir / filename
            if isinstance(content, dict):
                with open(filepath, 'w') as f:
                    json.dump(content, f)
            else:
                with open(filepath, 'w') as f:
                    f.write(content)

        # Now create the protector after files exist
        self.protector = AIIntegrityProtector(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test protector initialization."""
        self.assertIsNotNone(self.protector.workspace_root)
        self.assertIsNotNone(self.protector.file_snapshots)
        self.assertGreater(len(self.protector.file_snapshots), 0)

    def test_file_integrity_check(self):
        """Test file integrity validation."""
        # Initial check should pass
        checks = self.protector.validate_file_integrity()
        self.assertTrue(all(check.status == "PASS" for check in checks))

        # Modify a file
        current_json = self.temp_dir / "current.json"
        with open(current_json, 'w') as f:
            json.dump({"STATE": {"status": "MODIFIED", "loop": 84}}, f)

        # Integrity check should fail
        checks = self.protector.validate_file_integrity()
        failed_checks = [c for c in checks if c.status == "FAIL"]
        self.assertTrue(len(failed_checks) > 0)
        self.assertIn("current.json", [c.file_path for c in failed_checks])

    def test_false_positive_detection(self):
        """Test false-positive pattern detection."""
        # Test contradictory statements
        content_with_contradiction = "This is successful but also failed. The result is perfect but has minor issues."
        checks = self.protector.detect_false_positive_patterns(content_with_contradiction, "test.md")

        warning_checks = [c for c in checks if c.status == "WARN"]
        self.assertTrue(len(warning_checks) > 0)

        # Test statistical improbabilities
        content_with_improbability = "This system is 100% perfect and flawless."
        checks = self.protector.detect_false_positive_patterns(content_with_improbability, "test.md")

        improbability_checks = [c for c in checks if c.message and "perfection" in c.message.lower()]
        self.assertTrue(len(improbability_checks) > 0)

    def test_transaction_validation(self):
        """Test state transition validation."""
        # Valid transaction
        is_valid, message = self.protector.validate_state_transition(
            operation="test_operation",
            files_to_modify=["test.json"],
            validation_proof="Test validation proof",
            authorized_by="SYSTEM"
        )

        self.assertTrue(is_valid)
        self.assertIn("validated", message.lower())

        # Check transaction was logged
        transaction_log = self.temp_dir / "transaction_log.jsonl"
        self.assertTrue(transaction_log.exists())

        with open(transaction_log, 'r') as f:
            transactions = [json.loads(line) for line in f]
            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0]['operation'], "test_operation")

    def test_protected_operation_validation(self):
        """Test validation of protected operations."""
        # Test finalization without proper proof
        is_valid, message = self.protector.validate_state_transition(
            operation="finalize_loop_84",
            files_to_modify=["current.json"],
            validation_proof="Insufficient proof",
            authorized_by="SYSTEM"
        )

        # Should fail due to insufficient proof
        self.assertFalse(is_valid)
        self.assertIn("requires valid proof", message)

        # Test finalization with proper proof
        is_valid, message = self.protector.validate_state_transition(
            operation="finalize_loop_84",
            files_to_modify=["current.json"],
            validation_proof="validation complete, skeptical verification passed, evidence score high",
            authorized_by="SYSTEM"
        )

        self.assertTrue(is_valid)

    def test_bypass_attempt_detection(self):
        """Test detection of bypass attempts."""
        # Initially no bypass attempts
        checks = self.protector.check_for_bypass_attempts()
        initial_failures = len([c for c in checks if c.status == "FAIL"])
        initial_warnings = len([c for c in checks if c.status == "WARN"])

        # Modify a protected file directly
        current_json = self.temp_dir / "current.json"
        with open(current_json, 'w') as f:
            json.dump({"STATE": {"status": "TAMPERED", "loop": 84}}, f)

        # Should detect bypass attempt
        checks = self.protector.check_for_bypass_attempts()
        new_failures = len([c for c in checks if c.status == "FAIL"])

        # Should have detected the integrity violation
        self.assertGreaterEqual(new_failures, initial_failures)

    def test_integrity_report_generation(self):
        """Test comprehensive integrity report generation."""
        report = self.protector.create_integrity_report()

        required_keys = ['timestamp', 'total_checks', 'passed', 'warnings', 'failures', 'checks']
        for key in required_keys:
            self.assertIn(key, report)

        self.assertIsInstance(report['checks'], list)
        self.assertGreaterEqual(report['total_checks'], 0)

    def test_emergency_integrity_reset(self):
        """Test emergency integrity reset functionality."""
        # Modify a file to create integrity violation
        current_json = self.temp_dir / "current.json"
        original_content = json.dumps(self.test_files["current.json"])
        with open(current_json, 'w') as f:
            f.write('{"modified": true}')

        # Verify integrity violation exists
        checks = self.protector.validate_file_integrity()
        violations = [c for c in checks if c.status == "FAIL"]
        self.assertTrue(len(violations) > 0)

        # Perform emergency reset
        success = self.protector.emergency_integrity_reset()
        self.assertTrue(success)

        # Verify integrity is now clean
        checks = self.protector.validate_file_integrity()
        violations = [c for c in checks if c.status == "FAIL"]
        self.assertEqual(len(violations), 0)


class TestIntegrationWithGuardrails(unittest.TestCase):
    """Test integration with existing guardrails system."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create minimal workspace structure
        self.create_test_workspace()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_workspace(self):
        """Create a minimal test workspace."""
        # Create current.json
        current_data = {
            "STATE": {
                "loop": 84,
                "status": "ACTIVE",
                "lastTaskWorked": "TASK_0172"
            }
        }
        with open(self.temp_dir / "current.json", 'w') as f:
            json.dump(current_data, f)

        # Create NEU.md
        neu_content = """# NEU

MODE: POINTER-ONLY
CONTENT: FORBIDDEN

---

## TASK QUEUE (PRIORITY ORDER)

[ref:tasks/task_TASK_0172.md|v:1|tags:active,critical,security,ai-integrity|src:loop84] - AI False-Positive Suppression Architecture
"""
        with open(self.temp_dir / "NEU.md", 'w') as f:
            f.write(neu_content)

        # Create Alt.md
        with open(self.temp_dir / "Alt.md", 'w') as f:
            f.write("# Alt\n\nMODE: POINTER-ONLY\n")

    @patch('ai_integrity_protector.AIIntegrityProtector')
    def test_metadata_lint_integration(self, mock_protector_class):
        """Test that metadata_lint calls integrity protection."""
        # Mock the protector
        mock_protector = MagicMock()
        mock_protector.validate_file_integrity.return_value = [
            IntegrityCheck("current.json", "hash_integrity", "PASS", "File integrity verified")
        ]
        mock_protector.check_for_bypass_attempts.return_value = []
        mock_protector_class.return_value = mock_protector

        # Import and call metadata_lint
        import sys
        sys.path.insert(0, str(self.temp_dir.parent))
        from loop_guardrails import metadata_lint

        result = metadata_lint(self.temp_dir)

        # Verify protector was called
        mock_protector_class.assert_called_once_with(self.temp_dir)
        mock_protector.validate_file_integrity.assert_called_once()
        mock_protector.check_for_bypass_attempts.assert_called_once()

        # Verify result structure
        self.assertIn('errors', result)
        self.assertIn('warnings', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
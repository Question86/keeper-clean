#!/usr/bin/env python3
"""
Demonstration of AI Integrity Protection System

This script demonstrates TASK_0172 and TASK_0173: Protection against false-positives and jailbreak bypasses.
"""

import json
import tempfile
from pathlib import Path
from ai_integrity_protector import AIIntegrityProtector


def demonstrate_protection():
    """Demonstrate the AI integrity protection system in action."""

    print("🔒 AI Integrity Protection System Demonstration")
    print("=" * 50)

    # Create a temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)

        # Create protected files
        protected_files = {
            "current.json": {
                "STATE": {
                    "status": "ACTIVE",
                    "loop": 84,
                    "lastTaskWorked": "TASK_0172"
                }
            },
            "milestone_01.json": {"completed": True, "timestamp": "2026-01-27T12:00:00Z"},
            "_SESSION.md": "# Session\n\nCurrent work on AI integrity protection.",
            "NEU.md": "# NEU\n\nMODE: POINTER-ONLY\nCONTENT: FORBIDDEN\n\n---\n\n## TASK QUEUE\n\n[ref:tasks/task_TASK_0172.md|v:1|tags:active,critical,security|src:loop84] - AI False-Positive Suppression Architecture"
        }

        print("📁 Creating protected workspace files...")
        for filename, content in protected_files.items():
            filepath = workspace / filename
            if isinstance(content, dict):
                with open(filepath, 'w') as f:
                    json.dump(content, f, indent=2)
            else:
                with open(filepath, 'w') as f:
                    f.write(content)

        # Initialize protection system
        print("🛡️  Initializing AI Integrity Protector...")
        protector = AIIntegrityProtector(workspace)

        # Test 1: Clean integrity check
        print("\n✅ Test 1: Clean integrity validation")
        checks = protector.validate_file_integrity()
        passed = sum(1 for c in checks if c.status == "PASS")
        total = len(checks)
        print(f"   Integrity checks: {passed}/{total} passed")

        # Test 2: False positive detection
        print("\n🔍 Test 2: False positive pattern detection")
        suspicious_content = """
        This AI system is perfect and flawless. It never makes mistakes.
        The implementation is 100% complete and successful.
        All tests pass perfectly with no issues whatsoever.
        """

        fp_checks = protector.detect_false_positive_patterns(suspicious_content, "test.md")
        warnings = [c for c in fp_checks if c.status == "WARN"]
        print(f"   False positive warnings detected: {len(warnings)}")
        for warning in warnings[:2]:  # Show first 2
            print(f"   - {warning.message}")

        # Test 3: Transaction validation
        print("\n🔐 Test 3: Transaction validation")
        is_valid, message = protector.validate_state_transition(
            operation="finalize_loop_84",
            files_to_modify=["current.json"],
            validation_proof="validation complete, skeptical verification passed, evidence score high",
            authorized_by="SYSTEM"
        )
        print(f"   Transaction validation: {'✅ PASS' if is_valid else '❌ FAIL'}")
        print(f"   Message: {message}")

        # Test 4: Attempt bypass (modify protected file)
        print("\n🚨 Test 4: Bypass attempt detection")
        current_json = workspace / "current.json"
        with open(current_json, 'w') as f:
            json.dump({"STATE": {"status": "TAMPERED", "loop": 84}}, f)

        bypass_checks = protector.check_for_bypass_attempts()
        violations = [c for c in bypass_checks if c.status == "FAIL"]
        print(f"   Bypass attempts detected: {len(violations)}")
        for violation in violations[:1]:  # Show first violation
            print(f"   - {violation.message}")

        # Test 5: Emergency reset
        print("\n🔄 Test 5: Emergency integrity reset")
        success = protector.emergency_integrity_reset()
        print(f"   Emergency reset: {'✅ SUCCESS' if success else '❌ FAILED'}")

        # Verify reset worked
        post_reset_checks = protector.validate_file_integrity()
        post_reset_passed = sum(1 for c in post_reset_checks if c.status == "PASS")
        print(f"   Post-reset integrity: {post_reset_passed}/{len(post_reset_checks)} passed")

        # Test 6: Comprehensive report
        print("\n📊 Test 6: Integrity report generation")
        report = protector.create_integrity_report()
        print(f"   Report generated with {report['total_checks']} checks")
        print(f"   Status: {report['passed']} passed, {report['warnings']} warnings, {report['failures']} failures")

    print("\n🎉 AI Integrity Protection System demonstration complete!")
    print("\nKey protections implemented:")
    print("• File integrity monitoring with SHA256 hashing")
    print("• False-positive pattern detection")
    print("• Transaction validation for critical operations")
    print("• Bypass attempt detection and logging")
    print("• Emergency integrity reset capability")
    print("• Integration with existing guardrails system")


if __name__ == "__main__":
    demonstrate_protection()
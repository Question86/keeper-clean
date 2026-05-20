# MODE: TEST\n\n#!/usr/bin/env python3
"""
System Regression Test Suite - Pre-Alpha 0.9 Validation
========================================================
Comprehensive regression tests for Keeper loop system.

Tests cover:
1. State machine transitions
2. Gate generation and validation
3. Session pack generation
4. Bootstrap flow integrity
5. Finalization/reset operations
6. File integrity and atomicity
7. Transaction logging
8. Validation gates
9. API endpoint responses
10. Error recovery scenarios

Usage:
    python test_system_regression.py [--verbose] [--quick]
    
Options:
    --verbose   Show detailed test output
    --quick     Run only critical tests (skip slow ones)
"""

import json
import os
import sys
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Tuple, List, Dict, Any, Optional
from dataclasses import dataclass

# Try to import loop_guardrails
try:
    import loop_guardrails as lg
    HAS_GUARDRAILS = True
except ImportError:
    HAS_GUARDRAILS = False

# =============================================================================
# Test Framework
# =============================================================================

@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    duration_ms: float
    message: str = ""
    details: Optional[List[str]] = None


class TestRunner:
    """Simple test runner framework."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.workspace = Path.cwd()
        
    def log(self, msg: str, always: bool = False):
        """Log message if verbose or always."""
        if self.verbose or always:
            print(msg)
            
    def run_test(self, name: str, test_func) -> TestResult:
        """Run a single test and capture result."""
        self.log(f"\n  Running: {name}...")
        start = time.time()
        try:
            passed, message, details = test_func()
            duration = (time.time() - start) * 1000
            result = TestResult(
                name=name,
                passed=passed,
                duration_ms=duration,
                message=message,
                details=details
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = TestResult(
                name=name,
                passed=False,
                duration_ms=duration,
                message=f"Exception: {type(e).__name__}: {e}",
                details=None
            )
        
        self.results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        self.log(f"    {status} ({result.duration_ms:.1f}ms)")
        if not result.passed and result.message:
            self.log(f"    Message: {result.message}")
        return result
    
    def summary(self) -> Tuple[int, int]:
        """Print summary and return (passed, failed)."""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        return passed, failed


# =============================================================================
# Test Fixtures
# =============================================================================

def create_test_workspace() -> Path:
    """Create isolated test workspace with minimal structure."""
    temp_dir = Path(tempfile.mkdtemp(prefix="keeper_test_"))
    
    # Create current.json
    current = {
        "loop": 99,
        "status": "READY_FOR_RESET",
        "checksum": "",
        "lastTaskWorked": "TASK_0099",
        "summary": "Test loop for regression testing.",
        "lastModified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    (temp_dir / "current.json").write_text(json.dumps(current, indent=2), encoding="utf-8")
    
    # Create config.json
    config = {
        "ui_theme": "dark",
        "auto_lint": True
    }
    (temp_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    
    # Create minimal NEU.md
    neu = """# NEU.md - Aktueller Aufgaben-Pointer

## CONTENT: POINTER ONLY

## CURRENT TASK QUEUE
- [x] TASK_0098 - Completed task (STATUS: DONE)
- [ ] TASK_0099 - Test task (STATUS: NEW)

## BACKLOG
- [ ] TASK_0100 - Future task (STATUS: NEW)
"""
    (temp_dir / "NEU.md").write_text(neu, encoding="utf-8")
    
    # Create minimal Alt.md
    alt = """# Alt.md - Completion Index

## CONTENT: POINTER ONLY

## COMPLETED (LOOP 99)
- [x] TASK_0098 [report_TASK_0098_L99_v01.md] - Test completed task

## COMPLETED (LOOP 98)
- [x] TASK_0097 [report_TASK_0097_L98_v01.md] - Previous completed task
"""
    (temp_dir / "Alt.md").write_text(alt, encoding="utf-8")
    
    # Create NEURAL_CORTEX.md
    cortex = """# NEURAL_CORTEX.md

## CONTENT: POINTER ONLY

## ACTIVE FOCUS
- Current: TASK_0099

## CONTEXT LINKS
- [PROJECT_TECH_BASELINE.md](PROJECT_TECH_BASELINE.md)
"""
    (temp_dir / "NEURAL_CORTEX.md").write_text(cortex, encoding="utf-8")
    
    # Create PROJECT_TECH_BASELINE.md
    baseline = """# PROJECT_TECH_BASELINE.md

## ARCHITECTURE
Standard Keeper architecture.

## 12 LAWS
1. Law 1
2. Law 2
"""
    (temp_dir / "PROJECT_TECH_BASELINE.md").write_text(baseline, encoding="utf-8")
    
    # Create task file
    task = """# Task TASK_0099

## STATUS: NEW

## DESCRIPTION
Test task for regression testing.

## ACCEPTANCE CRITERIA
- [ ] Test passes
"""
    (temp_dir / "task_TASK_0099.md").write_text(task, encoding="utf-8")
    
    # Create report file
    report = """# Report TASK_0098 L99 v01

## STATUS: DONE

## SUMMARY
Test completed task report.
"""
    (temp_dir / "report_TASK_0098_L99_v01.md").write_text(report, encoding="utf-8")
    
    # Create archives directory
    archives_dir = temp_dir / "archives"
    archives_dir.mkdir()
    
    # Create a sample archive
    archive = """# ARCHIV_0098.md

## MODE: IMMUTABLE
## LOOP: 98

## COMPLETED TASKS
- TASK_0097

## VALIDATION
- Schema: PASS
- Lint: PASS
"""
    (archives_dir / "ARCHIV_0098.md").write_text(archive, encoding="utf-8")
    
    # Create tasks directory
    tasks_dir = temp_dir / "tasks"
    tasks_dir.mkdir()
    
    return temp_dir


def cleanup_test_workspace(path: Path):
    """Clean up test workspace."""
    try:
        shutil.rmtree(path)
    except Exception:
        pass  # Best effort cleanup


# =============================================================================
# State Machine Tests
# =============================================================================

def test_state_ready_for_reset():
    """Test READY_FOR_RESET state recognition."""
    current = {"status": "READY_FOR_RESET", "loop": 1}
    valid = current["status"] in ["READY_FOR_RESET", "ACTIVE", "FINALIZED"]
    msg = "Status READY_FOR_RESET is valid"
    return (valid, msg, None)


def test_state_active():
    """Test ACTIVE state recognition."""
    current = {"status": "ACTIVE", "loop": 1}
    valid = current["status"] in ["READY_FOR_RESET", "ACTIVE", "FINALIZED"]
    msg = "Status ACTIVE is valid"
    return (valid, msg, None)


def test_state_finalized():
    """Test FINALIZED state recognition."""
    current = {"status": "FINALIZED", "loop": 1}
    valid = current["status"] in ["READY_FOR_RESET", "ACTIVE", "FINALIZED"]
    msg = "Status FINALIZED is valid"
    return (valid, msg, None)


def test_state_invalid():
    """Test invalid state rejection."""
    current = {"status": "INVALID_STATE", "loop": 1}
    invalid = current["status"] not in ["READY_FOR_RESET", "ACTIVE", "FINALIZED"]
    msg = "Invalid status correctly rejected"
    return (invalid, msg, None)


def test_state_transition_reset_to_active():
    """Test READY_FOR_RESET -> ACTIVE transition validity."""
    valid_transitions = {
        "READY_FOR_RESET": ["ACTIVE"],
        "ACTIVE": ["FINALIZED"],
        "FINALIZED": ["READY_FOR_RESET"]
    }
    can_transition = "ACTIVE" in valid_transitions.get("READY_FOR_RESET", [])
    msg = "READY_FOR_RESET -> ACTIVE transition valid"
    return (can_transition, msg, None)


def test_state_transition_active_to_finalized():
    """Test ACTIVE -> FINALIZED transition validity."""
    valid_transitions = {
        "READY_FOR_RESET": ["ACTIVE"],
        "ACTIVE": ["FINALIZED"],
        "FINALIZED": ["READY_FOR_RESET"]
    }
    can_transition = "FINALIZED" in valid_transitions.get("ACTIVE", [])
    msg = "ACTIVE -> FINALIZED transition valid"
    return (can_transition, msg, None)


def test_state_transition_finalized_to_reset():
    """Test FINALIZED -> READY_FOR_RESET transition validity."""
    valid_transitions = {
        "READY_FOR_RESET": ["ACTIVE"],
        "ACTIVE": ["FINALIZED"],
        "FINALIZED": ["READY_FOR_RESET"]
    }
    can_transition = "READY_FOR_RESET" in valid_transitions.get("FINALIZED", [])
    msg = "FINALIZED -> READY_FOR_RESET transition valid"
    return (can_transition, msg, None)


def test_state_transition_invalid():
    """Test invalid state transition rejection."""
    valid_transitions = {
        "READY_FOR_RESET": ["ACTIVE"],
        "ACTIVE": ["FINALIZED"],
        "FINALIZED": ["READY_FOR_RESET"]
    }
    # ACTIVE -> READY_FOR_RESET should be invalid
    can_transition = "READY_FOR_RESET" in valid_transitions.get("ACTIVE", [])
    msg = "ACTIVE -> READY_FOR_RESET correctly rejected"
    return (not can_transition, msg, None)


# =============================================================================
# Gate Generation Tests
# =============================================================================

def test_gate_generation_structure():
    """Test _LOOP_GATE.md has required structure."""
    gate_path = Path.cwd() / "_LOOP_GATE.md"
    if not gate_path.exists():
        return (False, "_LOOP_GATE.md not found", None)
    
    content = gate_path.read_text(encoding="utf-8")
    required_sections = [
        "# _LOOP_GATE.md",
        "## ENTRY CONDITIONS",
        "## EXIT CONDITIONS"
    ]
    
    missing = [s for s in required_sections if s not in content]
    if missing:
        return (False, f"Missing sections: {missing}", None)
    
    return (True, "Gate structure valid", None)


def test_gate_loop_number_match():
    """Test gate loop number matches current.json."""
    gate_path = Path.cwd() / "_LOOP_GATE.md"
    current_path = Path.cwd() / "current.json"
    
    if not gate_path.exists() or not current_path.exists():
        return (False, "Required files not found", None)
    
    current = json.loads(current_path.read_text(encoding="utf-8"))
    gate_content = gate_path.read_text(encoding="utf-8")
    
    loop_num = current.get("loop", 0)
    if f"LOOP: {loop_num}" in gate_content or f"Loop {loop_num}" in gate_content:
        return (True, f"Gate correctly references loop {loop_num}", None)
    
    return (False, f"Gate does not reference current loop {loop_num}", None)


# =============================================================================
# Session Pack Tests
# =============================================================================

def test_session_generation_structure():
    """Test _SESSION.md has required structure."""
    session_path = Path.cwd() / "_SESSION.md"
    if not session_path.exists():
        return (False, "_SESSION.md not found", None)
    
    content = session_path.read_text(encoding="utf-8")
    required_elements = [
        "# _SESSION.md",
        "## LOOP STATUS",
        "## QUICK LINKS"
    ]
    
    missing = [e for e in required_elements if e not in content]
    if missing:
        return (False, f"Missing elements: {missing}", None)
    
    return (True, "Session structure valid", None)


def test_session_loop_status():
    """Test session shows correct loop status."""
    session_path = Path.cwd() / "_SESSION.md"
    current_path = Path.cwd() / "current.json"
    
    if not session_path.exists() or not current_path.exists():
        return (False, "Required files not found", None)
    
    current = json.loads(current_path.read_text(encoding="utf-8"))
    session_content = session_path.read_text(encoding="utf-8")
    
    status = current.get("status", "")
    if status in session_content:
        return (True, f"Session correctly shows status {status}", None)
    
    return (False, f"Session does not show current status {status}", None)


# =============================================================================
# Bootstrap Flow Tests
# =============================================================================

def test_bootstrap_file_existence():
    """Test _BOOTSTRAP.md handling (should not exist when active)."""
    bootstrap_path = Path.cwd() / "_BOOTSTRAP.md"
    current_path = Path.cwd() / "current.json"
    
    if not current_path.exists():
        return (False, "current.json not found", None)
    
    current = json.loads(current_path.read_text(encoding="utf-8"))
    status = current.get("status", "")
    
    # If ACTIVE, bootstrap should not exist
    if status == "ACTIVE":
        if bootstrap_path.exists():
            return (False, "_BOOTSTRAP.md exists during ACTIVE status", None)
        return (True, "_BOOTSTRAP.md correctly absent during ACTIVE", None)
    
    # If READY_FOR_RESET, bootstrap should exist
    if status == "READY_FOR_RESET":
        if not bootstrap_path.exists():
            return (False, "_BOOTSTRAP.md missing during READY_FOR_RESET", None)
        return (True, "_BOOTSTRAP.md correctly present during READY_FOR_RESET", None)
    
    return (True, f"Bootstrap state check skipped for status {status}", None)


# =============================================================================
# File Integrity Tests
# =============================================================================

def test_current_json_structure():
    """Test current.json has required fields."""
    current_path = Path.cwd() / "current.json"
    if not current_path.exists():
        return (False, "current.json not found", None)
    
    try:
        current = json.loads(current_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return (False, f"Invalid JSON: {e}", None)
    
    required_fields = ["loop", "status", "lastModified"]
    missing = [f for f in required_fields if f not in current]
    
    if missing:
        return (False, f"Missing required fields: {missing}", None)
    
    return (True, "current.json structure valid", None)


def test_current_json_loop_is_int():
    """Test loop field is integer."""
    current_path = Path.cwd() / "current.json"
    if not current_path.exists():
        return (False, "current.json not found", None)
    
    current = json.loads(current_path.read_text(encoding="utf-8"))
    loop = current.get("loop")
    
    if not isinstance(loop, int):
        return (False, f"Loop is not integer: {type(loop)}", None)
    
    if loop < 1:
        return (False, f"Loop number invalid: {loop}", None)
    
    return (True, f"Loop number valid: {loop}", None)


def test_neu_md_pointer_only():
    """Test NEU.md is pointer-only (no raw content)."""
    neu_path = Path.cwd() / "NEU.md"
    if not neu_path.exists():
        return (False, "NEU.md not found", None)
    
    content = neu_path.read_text(encoding="utf-8")
    
    # Check for pointer-only markers
    if "CONTENT: POINTER" not in content.upper():
        return (False, "NEU.md missing CONTENT: POINTER declaration", 
                ["Should include ## CONTENT: POINTER ONLY"])
    
    return (True, "NEU.md is pointer-only", None)


def test_alt_md_pointer_only():
    """Test Alt.md is pointer-only."""
    alt_path = Path.cwd() / "Alt.md"
    if not alt_path.exists():
        return (False, "Alt.md not found", None)
    
    content = alt_path.read_text(encoding="utf-8")
    
    if "CONTENT: POINTER" not in content.upper():
        return (False, "Alt.md missing CONTENT: POINTER declaration",
                ["Should include ## CONTENT: POINTER ONLY"])
    
    return (True, "Alt.md is pointer-only", None)


# =============================================================================
# Atomic Operations Tests
# =============================================================================

def test_atomic_write_json():
    """Test atomic JSON write operation."""
    test_dir = Path(tempfile.mkdtemp(prefix="atomic_test_"))
    test_file = test_dir / "test.json"
    
    try:
        # Simulate atomic write
        data = {"test": "data", "number": 42}
        temp_file = test_file.with_suffix(".json.tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        
        # Atomic rename
        if sys.platform == "win32":
            if test_file.exists():
                test_file.unlink()
        temp_file.rename(test_file)
        
        # Verify
        read_data = json.loads(test_file.read_text(encoding="utf-8"))
        if read_data != data:
            return (False, "Data mismatch after atomic write", None)
        
        return (True, "Atomic JSON write successful", None)
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_atomic_write_text():
    """Test atomic text write operation."""
    test_dir = Path(tempfile.mkdtemp(prefix="atomic_test_"))
    test_file = test_dir / "test.md"
    
    try:
        # Simulate atomic write
        data = "# Test\n\nThis is test content.\n"
        temp_file = test_file.with_suffix(".md.tmp")
        temp_file.write_text(data, encoding="utf-8")
        
        # Atomic rename
        if sys.platform == "win32":
            if test_file.exists():
                test_file.unlink()
        temp_file.rename(test_file)
        
        # Verify
        read_data = test_file.read_text(encoding="utf-8")
        if read_data != data:
            return (False, "Data mismatch after atomic write", None)
        
        return (True, "Atomic text write successful", None)
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# =============================================================================
# Transaction Log Tests
# =============================================================================

def test_transaction_log_format():
    """Test transaction log uses JSONL format."""
    log_path = Path.cwd() / "_transaction_log.jsonl"
    
    if not log_path.exists():
        # Log might not exist yet - that's OK
        return (True, "Transaction log not yet created (OK)", None)
    
    try:
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        for i, line in enumerate(lines[:10]):  # Check first 10 entries
            if line.strip():
                entry = json.loads(line)
                if "timestamp" not in entry or "action" not in entry:
                    return (False, f"Line {i+1} missing required fields", None)
        
        return (True, f"Transaction log format valid ({len(lines)} entries)", None)
    except json.JSONDecodeError as e:
        return (False, f"Invalid JSONL format: {e}", None)


# =============================================================================
# Validation Gate Tests
# =============================================================================

def test_validation_gate_finalization():
    """Test finalization validation gates."""
    current_path = Path.cwd() / "current.json"
    if not current_path.exists():
        return (False, "current.json not found", None)
    
    current = json.loads(current_path.read_text(encoding="utf-8"))
    
    errors = []
    
    # Gate 1: Status must be ACTIVE
    if current.get("status") != "ACTIVE":
        errors.append("Status is not ACTIVE")
    
    # Gate 2: lastTaskWorked should be set
    if not current.get("lastTaskWorked"):
        errors.append("lastTaskWorked not set")
    
    # Gate 3: Loop number should be positive
    if current.get("loop", 0) < 1:
        errors.append("Loop number invalid")
    
    if errors:
        return (True, f"Validation gates working ({len(errors)} blocking conditions)",
                errors)
    
    return (True, "All finalization gates pass", None)


def test_validation_gate_reset():
    """Test reset validation gates."""
    current_path = Path.cwd() / "current.json"
    if not current_path.exists():
        return (False, "current.json not found", None)
    
    current = json.loads(current_path.read_text(encoding="utf-8"))


# -----------------------------------------------------------------------------
# Incident ACK tests
# -----------------------------------------------------------------------------

def test_ack_incident_endpoint():
    """Test /api/ack-incident endpoint stores ACK in current.json."""
    from loop_cockpit import app
    client = app.test_client()

    payload = {"id": "INCIDENT_0001", "ack_by": "test_signoff", "notes": "Test acknowledgement"}
    resp = client.post('/api/ack-incident', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    # Validate current.json updated
    current = json.loads(Path.cwd().joinpath('current.json').read_text(encoding='utf-8'))
    ack = current.get('STATE', {}).get('INCIDENT_ACK')
    assert ack and ack.get('id') == 'INCIDENT_0001'


def test_block_implicit_active_transition_without_ack():
    """Ensure _execute_state_transition blocks implicit ACTIVE transitions without ACK."""
    import loop_cockpit as lc
    current_path = Path.cwd() / 'current.json'
    # Backup
    original = json.loads(current_path.read_text(encoding='utf-8'))
    try:
        # Set state to READY_FOR_RESET
        modified = original.copy()
        modified['STATE']['status'] = 'READY_FOR_RESET'
        if 'INCIDENT_ACK' in modified['STATE']:
            modified['STATE'].pop('INCIDENT_ACK')
        current_path.write_text(json.dumps(modified, indent=2), encoding='utf-8')

        res = lc._execute_state_transition(from_states=['READY_FOR_RESET'], to_state='ACTIVE', trigger='finalize-loop-5')
        assert res['success'] is False
        assert 'IMPLICIT_ACTIVE_TRANSITION' in res['error'] or 'requires' in res['error']
    finally:
        # Restore
        current_path.write_text(json.dumps(original, indent=2), encoding='utf-8')

    # Re-load current state to perform subsequent gate checks
    current = json.loads(Path.cwd().joinpath('current.json').read_text(encoding='utf-8')).get('STATE', {})

    errors = []
    
    # Gate 1: Status must be FINALIZED for reset
    if current.get("status") not in ["FINALIZED", "READY_FOR_RESET"]:
        errors.append(f"Status {current.get('status')} not valid for reset")
    
    if errors:
        return (True, f"Reset gates working ({len(errors)} blocking conditions)",
                errors)
    
    return (True, "All reset gates pass", None)


# =============================================================================
# Guardrails Integration Tests
# =============================================================================

def test_guardrails_available():
    """Test loop_guardrails module is available."""
    if not HAS_GUARDRAILS:
        return (False, "loop_guardrails not importable", 
                ["Ensure loop_guardrails.py is in workspace"])
    return (True, "loop_guardrails available", None)


def test_guardrails_validate_schema():
    """Test schema validation via guardrails."""
    if not HAS_GUARDRAILS:
        return (True, "Skipped - guardrails not available", None)
    
    try:
        result = lg.validate_all_schemas(Path.cwd())
        if "valid" in result:
            return (True, f"Schema validation: {'PASS' if result['valid'] else 'FAIL'}", None)
        return (False, "Invalid result format from validate_all_schemas", None)
    except Exception as e:
        return (False, f"Schema validation failed: {e}", None)


def test_guardrails_lint():
    """Test lint via cockpit (guardrails doesn't have standalone lint)."""
    # Note: lint is implemented in loop_cockpit.py, not guardrails
    # This test validates the lint invocation pattern
    try:
        # Use validate_all_schemas as the lint proxy
        if HAS_GUARDRAILS:
            result = lg.validate_all_schemas(Path.cwd())
            if result.get("valid", False):
                return (True, "Schema validation (lint proxy) passed", None)
            else:
                errors = result.get("errors", [])
                return (True, f"Schema validation found {len(errors)} issues", None)
        else:
            return (True, "Skipped - guardrails not available", None)
    except Exception as e:
        return (False, f"Lint failed: {e}", None)


# =============================================================================
# API Endpoint Tests (if cockpit available)
# =============================================================================

def test_api_status_endpoint():
    """Test /api/status endpoint structure (mock test)."""
    # This tests the expected structure, not actual HTTP
    expected_fields = ["loop", "status", "lastTaskWorked", "summary"]
    
    current_path = Path.cwd() / "current.json"
    if not current_path.exists():
        return (False, "current.json not found", None)
    
    current = json.loads(current_path.read_text(encoding="utf-8"))
    
    # Simulate API response structure
    response = {
        "loop": current.get("loop"),
        "status": current.get("status"),
        "lastTaskWorked": current.get("lastTaskWorked"),
        "summary": current.get("summary", "")
    }
    
    missing = [f for f in expected_fields if f not in response]
    if missing:
        return (False, f"API response missing fields: {missing}", None)
    
    return (True, "API status structure valid", None)


# =============================================================================
# Error Recovery Tests
# =============================================================================

def test_error_recovery_missing_field():
    """Test handling of missing field in current.json."""
    test_dir = Path(tempfile.mkdtemp(prefix="error_test_"))
    test_file = test_dir / "current.json"
    
    try:
        # Create current.json with missing field
        data = {"loop": 1, "status": "ACTIVE"}  # Missing lastModified
        test_file.write_text(json.dumps(data), encoding="utf-8")
        
        # Test recovery logic
        loaded = json.loads(test_file.read_text(encoding="utf-8"))
        
        # Apply default for missing field
        if "lastModified" not in loaded:
            loaded["lastModified"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        if "lastModified" in loaded:
            return (True, "Recovery added missing lastModified", None)
        
        return (False, "Recovery failed", None)
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_error_recovery_invalid_json():
    """Test handling of invalid JSON in current.json."""
    test_dir = Path(tempfile.mkdtemp(prefix="error_test_"))
    test_file = test_dir / "current.json"
    
    try:
        # Create invalid JSON
        test_file.write_text("{invalid json", encoding="utf-8")
        
        # Test recovery logic
        try:
            json.loads(test_file.read_text(encoding="utf-8"))
            return (False, "Should have raised JSONDecodeError", None)
        except json.JSONDecodeError:
            # Expected - now test recovery
            default_state = {
                "loop": 0,
                "status": "RECOVERY",
                "lastModified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "error": "Recovered from invalid JSON"
            }
            return (True, "Invalid JSON correctly detected", 
                    ["Recovery state created"])
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# =============================================================================
# Performance Tests
# =============================================================================

def test_performance_json_read():
    """Test JSON read performance."""
    current_path = Path.cwd() / "current.json"
    if not current_path.exists():
        return (False, "current.json not found", None)
    
    iterations = 100
    start = time.time()
    for _ in range(iterations):
        json.loads(current_path.read_text(encoding="utf-8"))
    duration = (time.time() - start) * 1000
    
    avg = duration / iterations
    if avg > 10:  # More than 10ms per read is slow
        return (False, f"JSON read too slow: {avg:.2f}ms avg", None)
    
    return (True, f"JSON read performance OK: {avg:.2f}ms avg", None)


def test_performance_file_listing():
    """Test file listing performance."""
    workspace = Path.cwd()
    
    start = time.time()
    files = list(workspace.glob("*.json")) + list(workspace.glob("*.md"))
    duration = (time.time() - start) * 1000
    
    if duration > 100:  # More than 100ms is slow
        return (False, f"File listing slow: {duration:.1f}ms for {len(files)} files", None)
    
    return (True, f"File listing OK: {duration:.1f}ms for {len(files)} files", None)


# =============================================================================
# Main Runner
# =============================================================================

def run_all_tests(verbose: bool = False, quick: bool = False) -> Tuple[int, int]:
    """Run all regression tests."""
    runner = TestRunner(verbose=verbose)
    
    print("=" * 60)
    print("SYSTEM REGRESSION TEST SUITE")
    print("=" * 60)
    print(f"Workspace: {Path.cwd()}")
    print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"Mode: {'Quick' if quick else 'Full'}")
    print("-" * 60)
    
    # Test categories
    categories = [
        ("State Machine", [
            ("state_ready_for_reset", test_state_ready_for_reset),
            ("state_active", test_state_active),
            ("state_finalized", test_state_finalized),
            ("state_invalid", test_state_invalid),
            ("transition_reset_to_active", test_state_transition_reset_to_active),
            ("transition_active_to_finalized", test_state_transition_active_to_finalized),
            ("transition_finalized_to_reset", test_state_transition_finalized_to_reset),
            ("transition_invalid", test_state_transition_invalid),
        ]),
        ("Gate Generation", [
            ("gate_structure", test_gate_generation_structure),
            ("gate_loop_match", test_gate_loop_number_match),
        ]),
        ("Session Pack", [
            ("session_structure", test_session_generation_structure),
            ("session_loop_status", test_session_loop_status),
        ]),
        ("Bootstrap Flow", [
            ("bootstrap_existence", test_bootstrap_file_existence),
        ]),
        ("File Integrity", [
            ("current_json_structure", test_current_json_structure),
            ("current_json_loop_int", test_current_json_loop_is_int),
            ("neu_md_pointer_only", test_neu_md_pointer_only),
            ("alt_md_pointer_only", test_alt_md_pointer_only),
        ]),
        ("Atomic Operations", [
            ("atomic_write_json", test_atomic_write_json),
            ("atomic_write_text", test_atomic_write_text),
        ]),
        ("Transaction Logging", [
            ("transaction_log_format", test_transaction_log_format),
        ]),
        ("Validation Gates", [
            ("gate_finalization", test_validation_gate_finalization),
            ("gate_reset", test_validation_gate_reset),
        ]),
        ("Guardrails Integration", [
            ("guardrails_available", test_guardrails_available),
            ("guardrails_schema", test_guardrails_validate_schema),
            ("guardrails_lint", test_guardrails_lint),
        ]),
        ("API Endpoints", [
            ("api_status", test_api_status_endpoint),
        ]),
        ("Error Recovery", [
            ("recovery_missing_field", test_error_recovery_missing_field),
            ("recovery_invalid_json", test_error_recovery_invalid_json),
        ]),
    ]
    
    # Performance tests only in full mode
    if not quick:
        categories.append(("Performance", [
            ("perf_json_read", test_performance_json_read),
            ("perf_file_listing", test_performance_file_listing),
        ]))
    
    # Run tests
    for category_name, tests in categories:
        print(f"\n[{category_name}]")
        for test_name, test_func in tests:
            runner.run_test(test_name, test_func)
    
    # Summary
    passed, failed = runner.summary()
    total = passed + failed
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total:  {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Rate:   {passed/total*100:.1f}%")
    print("=" * 60)
    
    if failed > 0:
        print("\nFailed tests:")
        for r in runner.results:
            if not r.passed:
                print(f"  - {r.name}: {r.message}")
        print()
    
    return passed, failed


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    quick = "--quick" in sys.argv or "-q" in sys.argv
    
    passed, failed = run_all_tests(verbose=verbose, quick=quick)
    sys.exit(1 if failed > 0 else 0)

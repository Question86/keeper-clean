#!/usr/bin/env python3
"""
AI Integrity Protection System

Implements TASK_0172 and TASK_0173: Protection against AI false-positives and jailbreak bypasses.
Provides architectural controls to prevent AI from pretending false results or manipulating canonical state.

This module is intentionally dependency-free (stdlib only) for maximum security and reliability.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class IntegrityCheck:
    """Represents an integrity check result."""
    file_path: str
    check_type: str
    status: str  # 'PASS', 'FAIL', 'WARN'
    message: str
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionRecord:
    """Records a validated state transition."""
    transaction_id: str
    timestamp: float
    operation: str
    files_modified: List[str]
    validation_proof: str
    authorized_by: str = "SYSTEM"


class AIIntegrityProtector:
    """
    Protects the loop system against AI false-positives and jailbreak bypasses.

    TASK_0172: AI False-Positive Suppression Architecture
    TASK_0173: Jailbreak Bypass Prevention System
    """

    def __init__(self, workspace_root: Path):
        """Initialize the AI Integrity Protector with workspace configuration."""
        self.workspace_root = workspace_root
        self.integrity_log = workspace_root / "integrity_log.jsonl"
        self.transaction_log = workspace_root / "transaction_log.jsonl"

        # Critical files that require protection
        self.protected_files = {
            "current.json",
            "milestone_01.json",
            "milestone_02.json",
            "milestone_03.json",
            "milestone_04.json",
            "knownissues.json",
            "_SESSION.md",
            "_LOOP_GATE.md",
            "NEU.md",
            "Alt.md"
        }

        # File integrity snapshots
        self.file_snapshots: Dict[str, str] = {}

        # Initialize integrity monitoring
        self._initialize_integrity_monitoring()

    def _initialize_integrity_monitoring(self) -> None:
        """Initialize integrity monitoring for protected files."""
        for filename in self.protected_files:
            filepath = self.workspace_root / filename
            if filepath.exists():
                self.file_snapshots[filename] = self._calculate_file_hash(filepath)

    def _calculate_file_hash(self, filepath: Path) -> str:
        """Calculate SHA256 hash of file content."""
        if not filepath.exists():
            return ""

        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def _log_integrity_check(self, check: IntegrityCheck) -> None:
        """Log an integrity check result."""
        try:
            with open(self.integrity_log, 'a', encoding='utf-8') as f:
                json.dump({
                    'timestamp': check.timestamp,
                    'file_path': check.file_path,
                    'check_type': check.check_type,
                    'status': check.status,
                    'message': check.message,
                    'details': check.details
                }, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            print(f"Warning: Failed to log integrity check: {e}")

    def _log_transaction(self, transaction: TransactionRecord) -> None:
        """Log a validated transaction."""
        try:
            with open(self.transaction_log, 'a', encoding='utf-8') as f:
                json.dump({
                    'transaction_id': transaction.transaction_id,
                    'timestamp': transaction.timestamp,
                    'operation': transaction.operation,
                    'files_modified': transaction.files_modified,
                    'validation_proof': transaction.validation_proof,
                    'authorized_by': transaction.authorized_by
                }, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            print(f"Warning: Failed to log transaction: {e}")

    def validate_file_integrity(self) -> List[IntegrityCheck]:
        """
        Validate integrity of all protected files.
        Returns list of integrity check results.
        """
        results = []

        for filename in self.protected_files:
            filepath = self.workspace_root / filename
            check = self._validate_single_file_integrity(filename, filepath)
            results.append(check)
            self._log_integrity_check(check)

        return results

    def _validate_single_file_integrity(self, filename: str, filepath: Path) -> IntegrityCheck:
        """Validate integrity of a single file."""
        if not filepath.exists():
            return IntegrityCheck(
                file_path=filename,
                check_type="existence",
                status="PASS",
                message="File does not exist (expected for some files)"
            )

        current_hash = self._calculate_file_hash(filepath)
        expected_hash = self.file_snapshots.get(filename, "")

        if not expected_hash:
            # First time seeing this file
            self.file_snapshots[filename] = current_hash
            return IntegrityCheck(
                file_path=filename,
                check_type="initial_snapshot",
                status="PASS",
                message="Initial integrity snapshot created"
            )

        if current_hash == expected_hash:
            return IntegrityCheck(
                file_path=filename,
                check_type="hash_integrity",
                status="PASS",
                message="File integrity verified"
            )
        else:
            return IntegrityCheck(
                file_path=filename,
                check_type="hash_integrity",
                status="FAIL",
                message="File has been modified unexpectedly - possible bypass attempt",
                details={
                    'expected_hash': expected_hash,
                    'current_hash': current_hash
                }
            )

    def detect_false_positive_patterns(self, content: str, source: str = "unknown") -> List[IntegrityCheck]:
        """
        Detect patterns that indicate AI might be pretending false results.

        TASK_0172: Architectural false-positive detection
        """
        results = []

        # Pattern 1: Overly confident language without evidence
        false_positive_indicators = [
            r'\b(certainly|definitely|absolutely)\b.*\b(but|however|although)\b',
            r'\b(proven|confirmed|verified)\b.*\b(speculation|guess|assume)\b',
            r'\b(impossible|never|always)\b.*\b(sometimes|occasionally|rarely)\b',
            r'\b(perfect|flawless|ideal)\b.*\b(minor|slight|small)\b',
        ]

        for pattern in false_positive_indicators:
            if re.search(pattern, content, re.IGNORECASE):
                results.append(IntegrityCheck(
                    file_path=source,
                    check_type="false_positive_pattern",
                    status="WARN",
                    message=f"Detected potential false-positive language pattern: {pattern}",
                    details={'pattern': pattern}
                ))

        # Pattern 2: Contradictory statements
        contradiction_patterns = [
            (r'\b(successful|completed|finished)\b', r'\b(failed|error|problem)\b'),
            (r'\b(valid|correct|accurate)\b', r'\b(invalid|wrong|incorrect)\b'),
            (r'\b(verified|confirmed|proven)\b', r'\b(unverified|unconfirmed|speculative)\b'),
        ]

        for pos_pattern, neg_pattern in contradiction_patterns:
            if re.search(pos_pattern, content, re.IGNORECASE) and re.search(neg_pattern, content, re.IGNORECASE):
                results.append(IntegrityCheck(
                    file_path=source,
                    check_type="contradiction_pattern",
                    status="WARN",
                    message="Detected contradictory statements that may indicate pretense",
                    details={
                        'positive_pattern': pos_pattern,
                        'negative_pattern': neg_pattern
                    }
                ))

        # Pattern 3: Statistical improbabilities
        if re.search(r'\b(100%|\bperfect\b|\bflawless\b)', content, re.IGNORECASE):
            results.append(IntegrityCheck(
                file_path=source,
                check_type="statistical_improbability",
                status="WARN",
                message="Detected claims of perfection that may be false-positive pretense"
            ))

        return results

    def validate_state_transition(self, operation: str, files_to_modify: List[str],
                                validation_proof: str, authorized_by: str = "SYSTEM") -> Tuple[bool, str]:
        """
        Validate a state transition request.

        TASK_0173: Ensure all state changes go through validated transaction paths
        """
        transaction_id = f"{operation}_{int(time.time())}_{hash(validation_proof) % 10000}"

        # ENFORCEMENT: Forbid code and task file changes before ACTIVE state
        current_json = self.workspace_root / "current.json"
        if current_json.exists():
            try:
                with open(current_json, 'r', encoding='utf-8') as f:
                    current_data = json.load(f)
                current_state = current_data.get('STATE', {}).get('status', 'UNKNOWN')
                if current_state != 'ACTIVE':
                    protected_pre_active = ['NEU.md', 'Alt.md'] + [f for f in files_to_modify if f.endswith('.py')]
                    blocked_files = [f for f in files_to_modify if f in protected_pre_active or f.endswith('.py')]
                    if blocked_files:
                        return False, f"Modifications forbidden before ACTIVE state: {blocked_files}"
            except Exception:
                # If can't read, allow (fail-safe)
                pass

        # Check if this is a protected operation
        protected_files_affected = [f for f in files_to_modify if f in self.protected_files]

        if protected_files_affected:
            # For protected files, require strong validation
            if not self._validate_protected_operation(operation, protected_files_affected, validation_proof):
                return False, f"Protected operation '{operation}' requires valid proof for files: {protected_files_affected}"

        # Log the validated transaction
        transaction = TransactionRecord(
            transaction_id=transaction_id,
            timestamp=time.time(),
            operation=operation,
            files_modified=files_to_modify,
            validation_proof=validation_proof,
            authorized_by=authorized_by
        )
        self._log_transaction(transaction)

        return True, f"Transaction {transaction_id} validated and logged"

    def _validate_protected_operation(self, operation: str, files: List[str],
                                    validation_proof: str) -> bool:
        """Validate operations on protected files."""
        # Critical operations require specific validation patterns
        critical_operations = {
            'finalize_loop': ['current.json'],
            'update_milestone': ['milestone_*.json'],
            'modify_session': ['_SESSION.md'],
            'update_gate': ['_LOOP_GATE.md']
        }

        for op, required_files in critical_operations.items():
            if operation.startswith(op):
                # Check if validation proof contains required evidence
                if not self._validate_operation_proof(operation, validation_proof):
                    return False

        return True

    def _validate_operation_proof(self, operation: str, proof: str) -> bool:
        """Validate that the operation has sufficient proof."""
        # Require specific evidence patterns for critical operations
        if operation.startswith('finalize_loop'):
            # Must have evidence of validation completion
            required_patterns = [
                r'validation.*complete',
                r'skeptical.*verification',
                r'evidence.*score',
                r'finalization.*assessment'
            ]
            return any(re.search(pattern, proof, re.IGNORECASE) for pattern in required_patterns)

        elif operation.startswith('update_milestone'):
            # Must have evidence of milestone criteria met
            required_patterns = [
                r'milestone.*criteria',
                r'completion.*requirements',
                r'validation.*passed'
            ]
            return any(re.search(pattern, proof, re.IGNORECASE) for pattern in required_patterns)

        return True  # Allow other operations with basic validation

    def check_for_bypass_attempts(self) -> List[IntegrityCheck]:
        """
        Check for signs of bypass attempts.

        TASK_0173: Detect unauthorized direct file manipulation
        """
        results = []

        # Check for recent unauthorized modifications
        integrity_results = self.validate_file_integrity()
        for check in integrity_results:
            if check.status == "FAIL":
                results.append(IntegrityCheck(
                    file_path=check.file_path,
                    check_type="bypass_attempt",
                    status="FAIL",
                    message=f"Detected possible bypass attempt: {check.message}",
                    details=check.details
                ))

        # Check transaction log for suspicious patterns
        suspicious_patterns = self._analyze_transaction_patterns()
        results.extend(suspicious_patterns)

        return results

    def _analyze_transaction_patterns(self) -> List[IntegrityCheck]:
        """Analyze transaction patterns for suspicious activity."""
        results = []

        try:
            if not self.transaction_log.exists():
                return results

            # Read recent transactions (last 100)
            transactions = []
            with open(self.transaction_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        transactions.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue

            recent_transactions = transactions[-100:] if len(transactions) > 100 else transactions

            # Check for rapid successive modifications (potential automation bypass)
            if len(recent_transactions) >= 3:
                timestamps = [t['timestamp'] for t in recent_transactions[-3:]]
                if max(timestamps) - min(timestamps) < 1.0:  # Within 1 second
                    results.append(IntegrityCheck(
                        file_path="transaction_log",
                        check_type="rapid_modifications",
                        status="WARN",
                        message="Detected rapid successive modifications - possible automated bypass attempt",
                        details={'timestamps': timestamps}
                    ))

            # Check for unauthorized operations
            for transaction in recent_transactions:
                if transaction.get('authorized_by') not in ['SYSTEM', 'USER_VERIFIED']:
                    results.append(IntegrityCheck(
                        file_path="transaction_log",
                        check_type="unauthorized_operation",
                        status="FAIL",
                        message=f"Detected unauthorized operation: {transaction.get('operation')}",
                        details=transaction
                    ))

        except Exception as e:
            results.append(IntegrityCheck(
                file_path="transaction_log",
                check_type="analysis_error",
                status="WARN",
                message=f"Failed to analyze transaction patterns: {e}"
            ))

        return results

    def create_integrity_report(self) -> Dict[str, Any]:
        """Create a comprehensive integrity report."""
        integrity_checks = self.validate_file_integrity()
        bypass_checks = self.check_for_bypass_attempts()
        breadcrumb_drift_checks = self.validate_breadcrumb_drift_protection()

        all_checks = integrity_checks + bypass_checks + breadcrumb_drift_checks

        report = {
            'timestamp': time.time(),
            'total_checks': len(all_checks),
            'passed': len([c for c in all_checks if c.status == 'PASS']),
            'warnings': len([c for c in all_checks if c.status == 'WARN']),
            'failures': len([c for c in all_checks if c.status == 'FAIL']),
            'checks': [
                {
                    'file_path': c.file_path,
                    'check_type': c.check_type,
                    'status': c.status,
                    'message': c.message,
                    'details': c.details
                }
                for c in all_checks
            ]
        }

        return report

    def emergency_integrity_reset(self) -> bool:
        """
        Emergency procedure to reset integrity monitoring.
        Use only when system integrity is confirmed manually.
        """
        try:
            # Clear existing snapshots
            self.file_snapshots.clear()

            # Re-initialize from current state
            self._initialize_integrity_monitoring()

            # Log the emergency reset
            emergency_check = IntegrityCheck(
                file_path="system",
                check_type="emergency_reset",
                status="WARN",
                message="Emergency integrity reset performed - manual verification required",
                details={'action': 'integrity_monitoring_reset'}
            )
            self._log_integrity_check(emergency_check)

            return True
        except Exception as e:
            print(f"Emergency integrity reset failed: {e}")
            return False

    def validate_breadcrumb_drift_protection(self) -> List[IntegrityCheck]:
        """
        Validate and refresh AI breadcrumb tracking awareness.

        TASK_0174: Regular drift protection for breadcrumb methodology
        Ensures breadcrumb tracking remains active and refreshes awareness.
        """
        results = []

        try:
            # Import breadcrumb tracker
            from ai_breadcrumb_tracker import get_breadcrumb_tracker

            tracker = get_breadcrumb_tracker(self.workspace_root)

            # Check if breadcrumb system is initialized
            if tracker is None:
                results.append(IntegrityCheck(
                    file_path="breadcrumb_system",
                    check_type="breadcrumb_drift",
                    status="FAIL",
                    message="AI Breadcrumb Tracking system not initialized - drift detected",
                    details={'action': 'needs_reinitialization'}
                ))
                return results

            # Check recent breadcrumb activity (last 24 hours)
            trail = tracker.get_breadcrumb_trail(limit=100)
            if trail:
                # Get most recent breadcrumb timestamp
                most_recent = max(bc.timestamp for bc in trail)
                
                # Parse timestamp, handling both formats (with and without milliseconds)
                try:
                    if '.' in most_recent:
                        # Format with milliseconds: 2026-01-28T01:07:03.271Z
                        parsed_time = time.strptime(most_recent, "%Y-%m-%dT%H:%M:%S.%fZ")
                    else:
                        # Format without milliseconds: 2026-01-27T19:43:00Z
                        parsed_time = time.strptime(most_recent, "%Y-%m-%dT%H:%M:%SZ")
                    hours_since_last = (time.time() - time.mktime(parsed_time)) / 3600
                except ValueError as e:
                    # If parsing fails, skip the time check
                    results.append(IntegrityCheck(
                        file_path="breadcrumb_system",
                        check_type="breadcrumb_drift",
                        status="WARN",
                        message=f"Timestamp parsing failed for {most_recent}: {e}",
                        details={'action': 'timestamp_format_issue'}
                    ))
                    return results

                if hours_since_last > 24:
                    results.append(IntegrityCheck(
                        file_path="breadcrumb_system",
                        check_type="breadcrumb_drift",
                        status="WARN",
                        message=".1f",
                        details={
                            'hours_since_last': hours_since_last,
                            'most_recent': most_recent,
                            'action': 'awareness_refresh_needed'
                        }
                    ))

                    # Refresh breadcrumb awareness by setting current context
                    tracker.set_current_context("drift_protection_refresh")
                else:
                    results.append(IntegrityCheck(
                        file_path="breadcrumb_system",
                        check_type="breadcrumb_drift",
                        status="PASS",
                        message="AI Breadcrumb Tracking active and current",
                        details={'hours_since_last': hours_since_last}
                    ))
            else:
                results.append(IntegrityCheck(
                    file_path="breadcrumb_system",
                    check_type="breadcrumb_drift",
                    status="WARN",
                    message="No breadcrumb trail found - initializing fresh tracking",
                    details={'action': 'initialization_needed'}
                ))

                # Initialize fresh breadcrumb context
                tracker.set_current_context("drift_protection_initialization")

        except ImportError:
            results.append(IntegrityCheck(
                file_path="breadcrumb_system",
                check_type="breadcrumb_drift",
                status="FAIL",
                message="AI Breadcrumb Tracking module not available",
                details={'error': 'module_not_found'}
            ))
        except Exception as e:
            results.append(IntegrityCheck(
                file_path="breadcrumb_system",
                check_type="breadcrumb_drift",
                status="FAIL",
                message=f"Breadcrumb drift protection check failed: {e}",
                details={'error': str(e)}
            ))

        return results
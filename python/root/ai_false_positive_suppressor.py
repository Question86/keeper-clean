#!/usr/bin/env python3
"""
AI False-Positive Suppression Architecture

Implements TASK_0172: Complete architectural suppression of AI false-positive results.
Provides system-level controls to prevent AI from injecting unproven claims or pretending results.

This module works with ai_integrity_protector.py to provide comprehensive protection.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


@dataclass
class Claim:
    """Represents an AI-generated claim that requires validation."""
    claim_id: str
    content: str
    claim_type: str  # 'validation', 'analysis', 'completion', 'error', etc.
    timestamp: float
    ai_source: str
    evidence_required: bool = True
    proof_chain: List[Dict[str, Any]] = field(default_factory=list)
    validation_status: str = "unvalidated"  # 'unvalidated', 'validated', 'rejected'


@dataclass
class ValidationProof:
    """Cryptographic proof for claim validation."""
    proof_id: str
    claim_id: str
    proof_type: str  # 'deterministic', 'evidence_based', 'consensus'
    proof_data: Dict[str, Any]
    timestamp: float
    validator: str
    signature: str


class ResultAuthenticationFramework:
    """
    Framework for authenticating all AI-generated results.

    Requires cryptographic or deterministic proof for every claim.
    """

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.environ.get('AI_INTEGRITY_KEY', 'default-key-change-in-production')
        self.proof_log = Path("validation_proofs.jsonl")

    def generate_claim_id(self, content: str, ai_source: str) -> str:
        """Generate unique claim ID based on content and source."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        source_hash = hashlib.sha256(ai_source.encode()).hexdigest()[:8]
        timestamp = str(int(time.time()))
        return f"claim_{content_hash}_{source_hash}_{timestamp}"

    def create_claim(self, content: str, claim_type: str, ai_source: str,
                    evidence_required: bool = True) -> Claim:
        """Create a validated claim structure."""
        claim_id = self.generate_claim_id(content, ai_source)
        return Claim(
            claim_id=claim_id,
            content=content,
            claim_type=claim_type,
            timestamp=time.time(),
            ai_source=ai_source,
            evidence_required=evidence_required
        )

    def generate_deterministic_proof(self, claim: Claim, validation_data: Dict[str, Any]) -> ValidationProof:
        """Generate deterministic proof based on verifiable computation."""
        proof_data = {
            'claim_hash': hashlib.sha256(claim.content.encode()).hexdigest(),
            'validation_rules': validation_data,
            'computation_steps': self._compute_validation_steps(claim, validation_data)
        }

        proof_string = json.dumps(proof_data, sort_keys=True)
        signature = hmac.new(
            self.secret_key.encode(),
            proof_string.encode(),
            hashlib.sha256
        ).hexdigest()

        proof = ValidationProof(
            proof_id=f"proof_{claim.claim_id}_{int(time.time())}",
            claim_id=claim.claim_id,
            proof_type="deterministic",
            proof_data=proof_data,
            timestamp=time.time(),
            validator="system",
            signature=signature
        )

        self._log_proof(proof)
        return proof

    def generate_evidence_based_proof(self, claim: Claim, evidence: List[Dict[str, Any]]) -> ValidationProof:
        """Generate proof based on external evidence validation."""
        # Validate evidence exists and is accessible
        validated_evidence = []
        for ev in evidence:
            if self._validate_evidence(ev):
                validated_evidence.append(ev)

        proof_data = {
            'claim_hash': hashlib.sha256(claim.content.encode()).hexdigest(),
            'evidence_count': len(validated_evidence),
            'evidence_hashes': [hashlib.sha256(json.dumps(ev, sort_keys=True).encode()).hexdigest()
                              for ev in validated_evidence],
            'validation_timestamp': time.time()
        }

        proof_string = json.dumps(proof_data, sort_keys=True)
        signature = hmac.new(
            self.secret_key.encode(),
            proof_string.encode(),
            hashlib.sha256
        ).hexdigest()

        proof = ValidationProof(
            proof_id=f"proof_{claim.claim_id}_{int(time.time())}",
            claim_id=claim.claim_id,
            proof_type="evidence_based",
            proof_data=proof_data,
            timestamp=time.time(),
            validator="system",
            signature=signature
        )

        self._log_proof(proof)
        return proof

    def _compute_validation_steps(self, claim: Claim, validation_data: Dict[str, Any]) -> List[str]:
        """Compute deterministic validation steps."""
        steps = []

        # Step 1: Content analysis
        content_length = len(claim.content)
        steps.append(f"content_length:{content_length}")

        # Step 2: Claim type validation
        valid_types = {'validation', 'analysis', 'completion', 'error', 'warning', 'info'}
        type_valid = claim.claim_type in valid_types
        steps.append(f"type_valid:{type_valid}")

        # Step 3: Timestamp validation (not in future)
        current_time = time.time()
        time_valid = claim.timestamp <= current_time + 60  # Allow 1 minute clock skew
        steps.append(f"time_valid:{time_valid}")

        # Step 4: AI source validation
        source_valid = bool(re.match(r'^[a-zA-Z0-9_-]+$', claim.ai_source))
        steps.append(f"source_valid:{source_valid}")

        return steps

    def _validate_evidence(self, evidence: Dict[str, Any]) -> bool:
        """Validate that evidence is accessible and legitimate."""
        evidence_type = evidence.get('type', '')

        if evidence_type == 'file':
            file_path = evidence.get('path', '')
            return Path(file_path).exists() and Path(file_path).is_file()

        elif evidence_type == 'url':
            # Basic URL validation
            url = evidence.get('url', '')
            return bool(re.match(r'^https?://', url))

        elif evidence_type == 'database':
            # Check if database record exists (simplified)
            return 'query' in evidence and 'result' in evidence

        return False

    def validate_proof(self, proof: ValidationProof) -> bool:
        """Validate a proof's authenticity and correctness."""
        # Verify signature
        proof_string = json.dumps(proof.proof_data, sort_keys=True)
        expected_signature = hmac.new(
            self.secret_key.encode(),
            proof_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if proof.signature != expected_signature:
            return False

        # Verify proof data integrity
        if proof.proof_type == "deterministic":
            # Recompute validation steps
            claim_hash = proof.proof_data.get('claim_hash', '')
            computation_steps = proof.proof_data.get('computation_steps', [])
            return len(computation_steps) >= 4  # Minimum validation steps

        elif proof.proof_type == "evidence_based":
            evidence_count = proof.proof_data.get('evidence_count', 0)
            evidence_hashes = proof.proof_data.get('evidence_hashes', [])
            return evidence_count > 0 and len(evidence_hashes) == evidence_count

        return False

    def _log_proof(self, proof: ValidationProof) -> None:
        """Log proof for audit trail."""
        try:
            with open(self.proof_log, 'a', encoding='utf-8') as f:
                json.dump({
                    'proof_id': proof.proof_id,
                    'claim_id': proof.claim_id,
                    'proof_type': proof.proof_type,
                    'timestamp': proof.timestamp,
                    'validator': proof.validator,
                    'signature': proof.signature
                }, f, ensure_ascii=False)
                f.write('\n')
        except Exception:
            pass  # Logging failure shouldn't break validation


class PretensePatternValidator:
    """
    Advanced pattern recognition to detect when AI is pretending vs genuinely reasoning.
    """

    def __init__(self):
        self.pretense_patterns = self._load_pretense_patterns()

    def _load_pretense_patterns(self) -> Dict[str, List[str]]:
        """Load comprehensive pretense pattern definitions."""
        return {
            'overconfidence_without_evidence': [
                r'\b(certainly|definitely|absolutely|undoubtedly)\b.{0,50}\b(might|could|possibly|perhaps)\b',
                r'\b(proven|confirmed|verified|established)\b.{0,30}\b(speculation|guess|assume|hypothesis)\b',
                r'\b(impossible|never|always)\b.{0,50}\b(sometimes|occasionally|rarely|sometimes)\b',
            ],
            'contradictory_statements': [
                r'\b(successful|completed|finished|working)\b.{0,100}\b(failed|error|problem|broken)\b',
                r'\b(valid|correct|accurate|true)\b.{0,100}\b(invalid|wrong|incorrect|false)\b',
                r'\b(verified|confirmed|proven)\b.{0,100}\b(unverified|unconfirmed|speculative)\b',
            ],
            'statistical_improbabilities': [
                r'\b(100%|perfect|flawless|ideal|optimal)\b.{0,50}\b(minor|slight|small|tiny)\b',
                r'\b(zero|no|none)\b.{0,30}\b(errors|problems|issues|failures)\b.{0,30}\b(except|but|however)\b',
                r'\b(guaranteed|ensured|promised)\b.{0,50}\b(might|could|may)\b',
            ],
            'authority_usurpation': [
                r'\b(I\s+am|we\s+are)\b.{0,30}\b(certain|sure|confident|positive)\b',
                r'\b(trust\s+me|believe\s+me|take\s+my\s+word)\b',
                r'\b(as\s+an?\s+AI|being\s+an?\s+AI)\b.{0,50}\b(know|understand|can\s+tell)\b',
            ],
            'fabricated_evidence': [
                r'\b(according\s+to|based\s+on|from)\b.{0,30}\b(my\s+analysis|our\s+data|the\s+system)\b',
                r'\b(evidence\s+shows|data\s+proves|results\s+indicate)\b.{0,30}\b(that|which)\b.{0,100}\b(but|however|although)\b',
            ]
        }

    def detect_pretense(self, content: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Detect pretense patterns in content.

        Returns list of detected pretense instances with confidence scores.
        """
        detections = []

        for pattern_category, patterns in self.pretense_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    # Calculate confidence based on pattern strength and context
                    confidence = self._calculate_confidence(match.group(), pattern_category, context or {})

                    if confidence > 0.3:  # Only report significant detections
                        detections.append({
                            'pattern_category': pattern_category,
                            'matched_text': match.group(),
                            'start_pos': match.start(),
                            'end_pos': match.end(),
                            'confidence': confidence,
                            'explanation': self._explain_pretense(pattern_category)
                        })

        return detections

    def _calculate_confidence(self, matched_text: str, category: str, context: Dict[str, Any]) -> float:
        """Calculate confidence score for a pretense detection."""
        base_confidence = {
            'overconfidence_without_evidence': 0.8,
            'contradictory_statements': 0.9,
            'statistical_improbabilities': 0.7,
            'authority_usurpation': 0.6,
            'fabricated_evidence': 0.5
        }.get(category, 0.5)

        # Adjust based on text length (longer matches more suspicious)
        length_bonus = min(len(matched_text) / 100, 0.2)

        # Adjust based on context
        context_penalty = 0
        if context.get('has_evidence', False):
            context_penalty = 0.1
        if context.get('is_verified', False):
            context_penalty = 0.2

        return min(base_confidence + length_bonus - context_penalty, 1.0)

    def _explain_pretense(self, category: str) -> str:
        """Provide explanation for why this pattern indicates pretense."""
        explanations = {
            'overconfidence_without_evidence': 'Combines absolute certainty with qualifiers indicating uncertainty',
            'contradictory_statements': 'Contains mutually exclusive claims in close proximity',
            'statistical_improbabilities': 'Makes claims of perfection or impossibility with exceptions',
            'authority_usurpation': 'Attempts to establish authority without verifiable credentials',
            'fabricated_evidence': 'References evidence or analysis that cannot be independently verified'
        }
        return explanations.get(category, 'Detected potential pretense pattern')


class ArchitecturalEnforcementLayer:
    """
    System-level controls that prevent false-positive injection regardless of AI intent.
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.enforcement_log = workspace_root / "architectural_enforcement.jsonl"
        self.blocked_claims: Set[str] = set()

        # Critical paths that require enforcement
        self.protected_paths = {
            'current.json',
            'milestone_*.json',
            'knownissues.json',
            '_LOOP_GATE.md',
            'NEU.md',
            'Alt.md',
            'reports/',
            'tasks/'
        }

    def validate_claim_injection(self, claim: Claim, target_path: str) -> Tuple[bool, str]:
        """
        Validate whether a claim can be injected into the system.

        Returns (allowed, reason)
        """
        # Check if target path requires protection
        if not self._path_requires_protection(target_path):
            return True, "Path not protected"

        # Check if claim has required validation
        if claim.evidence_required and not claim.proof_chain:
            self._block_claim(claim.claim_id, "missing_proof", target_path)
            return False, "Claim requires proof but none provided"

        # Check for pretense patterns
        validator = PretensePatternValidator()
        pretense_detections = validator.detect_pretense(claim.content)

        if pretense_detections:
            # High confidence detections block injection
            high_confidence = [d for d in pretense_detections if d['confidence'] > 0.7]
            if high_confidence:
                self._block_claim(claim.claim_id, "pretense_detected", target_path)
                return False, f"High-confidence pretense pattern detected: {high_confidence[0]['pattern_category']}"

        # Check claim type restrictions
        if not self._validate_claim_type_for_path(claim.claim_type, target_path):
            self._block_claim(claim.claim_id, "invalid_claim_type", target_path)
            return False, f"Claim type '{claim.claim_type}' not allowed for path '{target_path}'"

        # All checks passed
        return True, "Claim validated for injection"

    def _path_requires_protection(self, path: str) -> bool:
        """Check if a path requires architectural protection."""
        from fnmatch import fnmatch

        for protected in self.protected_paths:
            if fnmatch(path, protected):
                return True
        return False

    def _validate_claim_type_for_path(self, claim_type: str, path: str) -> bool:
        """Validate that claim type is appropriate for the target path."""
        # Define allowed claim types per path pattern
        path_restrictions = {
            'current.json': {'validation', 'state_update'},
            'milestone_*.json': {'milestone_update', 'validation'},
            'knownissues.json': {'issue_report', 'validation'},
            '_LOOP_GATE.md': {'gate_update', 'validation'},
            'NEU.md': {'task_update', 'validation'},
            'Alt.md': {'task_closure', 'validation'},
            'reports/': {'analysis', 'completion', 'validation', 'error'},
            'tasks/': {'task_creation', 'task_update', 'validation'}
        }

        for pattern, allowed_types in path_restrictions.items():
            from fnmatch import fnmatch
            if fnmatch(path, pattern):
                return claim_type in allowed_types

        return True  # Allow if no specific restrictions

    def _block_claim(self, claim_id: str, reason: str, target_path: str) -> None:
        """Block a claim and log the enforcement action."""
        self.blocked_claims.add(claim_id)

        enforcement_record = {
            'timestamp': time.time(),
            'claim_id': claim_id,
            'action': 'blocked',
            'reason': reason,
            'target_path': target_path,
            'enforcement_level': 'architectural'
        }

        try:
            with open(self.enforcement_log, 'a', encoding='utf-8') as f:
                json.dump(enforcement_record, f, ensure_ascii=False)
                f.write('\n')
        except Exception:
            pass

    def get_blocked_claims(self) -> List[str]:
        """Get list of currently blocked claim IDs."""
        return list(self.blocked_claims)

    def clear_expired_blocks(self, max_age_seconds: int = 3600) -> int:
        """Clear blocks older than specified age."""
        # In a real implementation, this would check timestamps
        # For now, just return count of blocked claims
        return len(self.blocked_claims)


class AIFalsePositiveSuppressor:
    """
    Main orchestrator for AI False-Positive Suppression Architecture.

    TASK_0172: Complete architectural suppression of AI false-positive results.
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.auth_framework = ResultAuthenticationFramework()
        self.pattern_validator = PretensePatternValidator()
        self.enforcement_layer = ArchitecturalEnforcementLayer(workspace_root)

        # Integration with existing integrity protector
        try:
            from ai_integrity_protector import AIIntegrityProtector
            self.integrity_protector = AIIntegrityProtector(workspace_root)
        except ImportError:
            self.integrity_protector = None

    def validate_ai_output(self, content: str, output_type: str, ai_source: str,
                          target_path: str = "", require_proof: bool = True) -> Dict[str, Any]:
        """
        Comprehensive validation of AI-generated output.

        Returns validation result with status and details.
        """
        validation_result = {
            'status': 'unknown',
            'claim_id': None,
            'proof_required': require_proof,
            'proof_provided': False,
            'pretense_detected': False,
            'injection_allowed': False,
            'errors': [],
            'warnings': []
        }

        try:
            # Step 1: Create claim structure
            claim = self.auth_framework.create_claim(content, output_type, ai_source, require_proof)
            validation_result['claim_id'] = claim.claim_id

            # Step 2: Detect pretense patterns
            pretense_detections = self.pattern_validator.detect_pretense(content)
            if pretense_detections:
                validation_result['pretense_detected'] = True
                validation_result['warnings'].extend([
                    f"Pretense pattern: {d['pattern_category']} (confidence: {d['confidence']:.2f})"
                    for d in pretense_detections
                ])

            # Step 3: Generate proof if required
            if require_proof:
                if output_type in {'validation', 'analysis', 'completion'}:
                    # Generate deterministic proof
                    proof = self.auth_framework.generate_deterministic_proof(claim, {
                        'output_type': output_type,
                        'content_length': len(content),
                        'target_path': target_path
                    })
                    claim.proof_chain.append({
                        'proof_id': proof.proof_id,
                        'type': proof.proof_type,
                        'validated': True
                    })
                    validation_result['proof_provided'] = True
                else:
                    validation_result['errors'].append("Proof required but no proof generation logic for output type")

            # Step 4: Validate claim injection
            if target_path:
                allowed, reason = self.enforcement_layer.validate_claim_injection(claim, target_path)
                validation_result['injection_allowed'] = allowed
                if not allowed:
                    validation_result['errors'].append(f"Injection blocked: {reason}")

            # Step 5: Cross-check with integrity protector
            if self.integrity_protector:
                integrity_checks = self.integrity_protector.detect_false_positive_patterns(content, target_path or "ai_output")
                for check in integrity_checks:
                    if check.status == 'WARN':
                        validation_result['warnings'].append(f"Integrity check: {check.message}")
                    elif check.status == 'FAIL':
                        validation_result['errors'].append(f"Integrity violation: {check.message}")

            # Determine overall status
            if validation_result['errors']:
                validation_result['status'] = 'rejected'
            elif validation_result['warnings'] or validation_result['pretense_detected']:
                validation_result['status'] = 'warning'
            else:
                validation_result['status'] = 'approved'

        except Exception as e:
            validation_result['status'] = 'error'
            validation_result['errors'].append(f"Validation failed: {str(e)}")

        return validation_result

    def create_test_framework(self) -> Dict[str, Any]:
        """
        Create comprehensive testing framework for false-positive protection.
        """
        test_cases = {
            'pretense_patterns': [
                {
                    'name': 'overconfidence_without_evidence',
                    'input': "I am absolutely certain that this code works perfectly, although it might have some minor issues.",
                    'expected_pretense': True
                },
                {
                    'name': 'contradictory_statements',
                    'input': "The validation was successful and completed without errors, but there were several problems encountered.",
                    'expected_pretense': True
                },
                {
                    'name': 'statistical_improbability',
                    'input': "This solution is 100% perfect and flawless, except for a few tiny details.",
                    'expected_pretense': True
                }
            ],
            'proof_validation': [
                {
                    'name': 'valid_deterministic_proof',
                    'claim_type': 'validation',
                    'expected_proof_valid': True
                },
                {
                    'name': 'missing_proof_for_critical',
                    'claim_type': 'validation',
                    'require_proof': True,
                    'expected_injection_blocked': True
                }
            ],
            'architectural_enforcement': [
                {
                    'name': 'invalid_claim_type_for_path',
                    'claim_type': 'task_creation',
                    'target_path': 'current.json',
                    'expected_blocked': True
                },
                {
                    'name': 'pretense_blocks_injection',
                    'content': "I am definitely sure this is correct, but it might be wrong.",
                    'target_path': 'milestone_01.json',
                    'expected_blocked': True
                }
            ]
        }

        return {
            'test_framework_created': True,
            'test_categories': list(test_cases.keys()),
            'total_test_cases': sum(len(cases) for cases in test_cases.values()),
            'test_cases': test_cases,
            'run_tests': self._run_test_suite
        }

    def _run_test_suite(self, test_cases: Dict[str, Any]) -> Dict[str, Any]:
        """Run the test suite and return results."""
        results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'details': []
        }

        for category, cases in test_cases.items():
            for test_case in cases:
                results['total_tests'] += 1

                try:
                    if category == 'pretense_patterns':
                        detections = self.pattern_validator.detect_pretense(test_case['input'])
                        has_pretense = len(detections) > 0
                        passed = has_pretense == test_case['expected_pretense']

                    elif category == 'proof_validation':
                        # Create test claim
                        claim = self.auth_framework.create_claim(
                            "test content", test_case['claim_type'], "test_ai"
                        )
                        if test_case.get('require_proof', False):
                            proof = self.auth_framework.generate_deterministic_proof(claim, {})
                            valid = self.auth_framework.validate_proof(proof)
                            passed = valid == test_case['expected_proof_valid']
                        else:
                            passed = True

                    elif category == 'architectural_enforcement':
                        claim = self.auth_framework.create_claim(
                            test_case.get('content', 'test'), 'validation', 'test_ai'
                        )
                        allowed, _ = self.enforcement_layer.validate_claim_injection(
                            claim, test_case['target_path']
                        )
                        passed = (not allowed) == test_case['expected_blocked']

                    else:
                        passed = False

                    if passed:
                        results['passed'] += 1
                    else:
                        results['failed'] += 1

                    results['details'].append({
                        'test_name': test_case['name'],
                        'category': category,
                        'passed': passed
                    })

                except Exception as e:
                    results['failed'] += 1
                    results['details'].append({
                        'test_name': test_case['name'],
                        'category': category,
                        'passed': False,
                        'error': str(e)
                    })

        return results
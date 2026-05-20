#!/usr/bin/env python3
"""
Validation Engine - Multi-layer Assessment for Seed Ideas

Performs comprehensive validation of seed ideas including:
- Sanity checks (basic structure and completeness)
- Duplicate detection (similarity analysis)
- Feasibility assessment (technical and resource evaluation)
- Scope validation (alignment with project constraints)
"""

import re
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher
from chaosbox.chaosbox_manager import SeedIdea, RejectionReason

class ValidationEngine:
    """Multi-layer validation engine for seed ideas."""

    def __init__(self):
        # Duplicate detection parameters
        self.similarity_threshold = 0.8
        self.title_weight = 0.6
        self.description_weight = 0.4

        # Feasibility keywords
        self.technical_keywords = [
            'algorithm', 'api', 'automation', 'code', 'database', 'framework',
            'implementation', 'infrastructure', 'integration', 'library',
            'machine learning', 'optimization', 'pipeline', 'protocol',
            'refactor', 'security', 'testing', 'validation', 'file', 'storage',
            'cleanup', 'restructure', 'migration', 'orchestration', 'wiring', 'ui'
        ]

        self.resource_keywords = [
            'analysis', 'assessment', 'audit', 'benchmark', 'documentation',
            'evaluation', 'monitoring', 'reporting', 'research', 'review',
            'roadmap', 'milestone', 'workflow', 'methodical'
        ]

    def validate_idea(self, idea: SeedIdea) -> Dict[str, Any]:
        """
        Perform comprehensive validation of a seed idea.

        Args:
            idea: The seed idea to validate

        Returns:
            Validation result with pass/fail and reason
        """
        # Layer 1: Sanity Checks
        sanity_result = self._sanity_checks(idea)
        if not sanity_result["passed"]:
            return sanity_result

        # Layer 2: Duplicate Detection
        duplicate_result = self._duplicate_detection(idea)
        if not duplicate_result["passed"]:
            return duplicate_result

        # Layer 3: Feasibility Assessment
        feasibility_result = self._feasibility_assessment(idea)
        if not feasibility_result["passed"]:
            return feasibility_result

        # Layer 4: Scope Validation
        scope_result = self._scope_validation(idea)
        if not scope_result["passed"]:
            return scope_result

        return {
            "passed": True,
            "reason": "validation_passed",
            "details": {
                "sanity": sanity_result,
                "duplicate": duplicate_result,
                "feasibility": feasibility_result,
                "scope": scope_result
            }
        }

    def _sanity_checks(self, idea: SeedIdea) -> Dict[str, Any]:
        """Basic sanity checks for idea structure and completeness."""
        errors = []

        # Title checks
        if not idea.title or len(idea.title.strip()) < 5:
            errors.append("Title too short or empty (minimum 5 characters)")

        if len(idea.title.strip()) > 200:
            errors.append("Title too long (maximum 200 characters)")

        # Description checks
        if not idea.description or len(idea.description.strip()) < 20:
            errors.append("Description too short or empty (minimum 20 characters)")

        if len(idea.description.strip()) > 2000:
            errors.append("Description too long (maximum 2000 characters)")

        # Check for meaningful content
        if not self._has_meaningful_content(idea.description):
            errors.append("Description lacks meaningful technical or actionable content")

        # Tag validation
        if idea.tags:
            invalid_tags = [tag for tag in idea.tags if not self._is_valid_tag(tag)]
            if invalid_tags:
                errors.append(f"Invalid tags: {', '.join(invalid_tags)}")

        return {
            "passed": len(errors) == 0,
            "reason": RejectionReason.MALFORMED if errors else "sanity_passed",
            "errors": errors
        }

    def _duplicate_detection(self, idea: SeedIdea) -> Dict[str, Any]:
        """Check for duplicate or very similar ideas."""
        # Check against idea history
        for existing_idea in getattr(self, '_idea_history', []):
            title_similarity = self.check_similarity(idea.title, existing_idea.title)
            desc_similarity = self.check_similarity(idea.description, existing_idea.description)
            
            combined_similarity = (title_similarity * self.title_weight + 
                                 desc_similarity * self.description_weight)
            
            if combined_similarity > self.similarity_threshold:
                return {
                    "passed": False,
                    "reason": RejectionReason.DUPLICATE,
                    "similarity_score": combined_similarity,
                    "existing_idea_id": existing_idea.idea_id
                }

        return {
            "passed": True,
            "reason": "no_duplicates_found",
            "similarity_score": 0.0
        }

    def _feasibility_assessment(self, idea: SeedIdea) -> Dict[str, Any]:
        """Assess technical and resource feasibility."""
        text = f"{idea.title} {idea.description}".lower()

        # Check for technical indicators
        technical_score = sum(1 for keyword in self.technical_keywords if keyword in text)
        resource_score = sum(1 for keyword in self.resource_keywords if keyword in text)

        # Feasibility heuristics
        has_technical_elements = technical_score > 0
        has_resource_elements = resource_score > 0
        has_actionable_language = self._has_actionable_language(text)

        # Determine feasibility
        if not (has_technical_elements or has_resource_elements):
            return {
                "passed": False,
                "reason": RejectionReason.INFEASIBLE,
                "details": "Idea lacks technical or resource management elements"
            }

        if not has_actionable_language:
            return {
                "passed": False,
                "reason": RejectionReason.INFEASIBLE,
                "details": "Idea does not contain actionable implementation concepts"
            }

        return {
            "passed": True,
            "reason": "feasible",
            "technical_score": technical_score,
            "resource_score": resource_score
        }

    def _scope_validation(self, idea: SeedIdea) -> Dict[str, Any]:
        """Validate that the idea is within project scope."""
        text = f"{idea.title} {idea.description}".lower()

        # Project scope keywords (would be configurable)
        in_scope_keywords = [
            'ai', 'automation', 'code', 'development', 'infrastructure',
            'integration', 'optimization', 'quality', 'security', 'testing',
            'llm', 'context', 'token', 'file', 'storage', 'cleanup', 'refactor'
        ]

        out_of_scope_keywords = [
            'hardware', 'physical', 'manufacturing', 'sales', 'marketing',
            'legal', 'finance', 'hr', 'office', 'administrative'
        ]

        in_scope_matches = sum(1 for keyword in in_scope_keywords if keyword in text)
        out_of_scope_matches = sum(1 for keyword in out_of_scope_keywords if keyword in text)

        if out_of_scope_matches > in_scope_matches:
            return {
                "passed": False,
                "reason": RejectionReason.OUT_OF_SCOPE,
                "details": f"Contains {out_of_scope_matches} out-of-scope keywords vs {in_scope_matches} in-scope"
            }

        if in_scope_matches == 0:
            return {
                "passed": False,
                "reason": RejectionReason.OUT_OF_SCOPE,
                "details": "No clear alignment with project scope"
            }

        return {
            "passed": True,
            "reason": "in_scope",
            "in_scope_matches": in_scope_matches,
            "out_of_scope_matches": out_of_scope_matches
        }

    def _has_meaningful_content(self, text: str) -> bool:
        """Check if text contains meaningful technical content."""
        # Remove common filler words
        filler_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}

        words = re.findall(r'\b\w+\b', text.lower())
        meaningful_words = [word for word in words if word not in filler_words]

        # Must have at least 10 meaningful words
        if len(meaningful_words) < 10:
            return False

        # Must contain some technical indicators
        technical_indicators = ['implement', 'create', 'build', 'develop', 'optimize', 'integrate', 'test', 'validate', 'analyze']
        has_technical = any(indicator in text.lower() for indicator in technical_indicators)

        return has_technical

    def _has_actionable_language(self, text: str) -> bool:
        """Check if text contains actionable implementation language."""
        actionable_verbs = [
            'implement', 'create', 'build', 'develop', 'add', 'integrate',
            'optimize', 'improve', 'fix', 'resolve', 'automate', 'generate',
            'validate', 'test', 'analyze', 'monitor', 'track', 'manage',
            'clean', 'organize', 'migrate', 'wire', 'orchestrate', 'structure'
        ]

        return any(verb in text for verb in actionable_verbs)

    def _is_valid_tag(self, tag: str) -> bool:
        """Validate a single tag."""
        if not tag or len(tag.strip()) == 0:
            return False

        # Tags should be lowercase, no spaces, alphanumeric + hyphens/underscores
        if not re.match(r'^[a-z0-9_-]+$', tag):
            return False

        # Reasonable length
        if len(tag) > 50:
            return False

        return True

    def check_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        from difflib import SequenceMatcher
        matcher = SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()

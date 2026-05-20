# MODE: LIBRARY

"""
Search Query Result Weighting Engine

Core algorithms for multi-factor result weighting and prioritization.
Implements configurable scoring system with performance optimization.

Features:
- Multi-factor scoring (relevance, recency, authority, etc.)
- Configurable weighting schemes
- Performance monitoring (<50ms latency target)
- Relevance improvement tracking (>30% improvement target)
"""

from __future__ import annotations

import time
import math
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class WeightingFactor(Enum):
    """Enumeration of available weighting factors."""
    RELEVANCE = "relevance"
    RECENCY = "recency"
    AUTHORITY = "authority"
    POPULARITY = "popularity"
    COMPLETENESS = "completeness"
    FRESHNESS = "freshness"
    CONTEXT_MATCH = "context_match"
    REFERENCE_DEPTH = "reference_depth"
    VALIDATION_STATUS = "validation_status"
    TASK_FOCUS = "task_focus"


@dataclass
class WeightingConfig:
    """Configuration for weighting factors and their relative importance."""
    factors: Dict[WeightingFactor, float] = field(default_factory=dict)
    normalization_method: str = "minmax"  # minmax, zscore, robust
    boost_multipliers: Dict[str, float] = field(default_factory=dict)
    decay_functions: Dict[WeightingFactor, Callable] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default weighting factors if not provided."""
        if not self.factors:
            self.factors = {
                WeightingFactor.RELEVANCE: 0.35,
                WeightingFactor.RECENCY: 0.20,
                WeightingFactor.AUTHORITY: 0.15,
                WeightingFactor.POPULARITY: 0.10,
                WeightingFactor.COMPLETENESS: 0.10,
                WeightingFactor.FRESHNESS: 0.05,
                WeightingFactor.CONTEXT_MATCH: 0.03,
                WeightingFactor.REFERENCE_DEPTH: 0.02,
            }

        if not self.boost_multipliers:
            self.boost_multipliers = {
                "validation_passed": 1.2,
                "high_authority": 1.15,
                "recent_access": 1.1,
                "task_focus": 1.25,
            }


@dataclass
class WeightedResult:
    """Container for a search result with computed weights."""
    result_id: str
    base_score: float
    factor_scores: Dict[WeightingFactor, float] = field(default_factory=dict)
    final_score: float = 0.0
    applied_boosts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0


class WeightingEngine:
    """
    Core weighting engine for search result prioritization.

    Implements multi-factor scoring with configurable weights and
    performance optimization for sub-50ms latency.
    """

    def __init__(self, config: Optional[WeightingConfig] = None):
        self.config = config or WeightingConfig()
        self.performance_log: List[Dict[str, Any]] = []
        self._factor_calculators = self._initialize_calculators()

    def _initialize_calculators(self) -> Dict[WeightingFactor, Callable]:
        """Initialize factor calculation functions."""
        return {
            WeightingFactor.RELEVANCE: self._calculate_relevance,
            WeightingFactor.RECENCY: self._calculate_recency,
            WeightingFactor.AUTHORITY: self._calculate_authority,
            WeightingFactor.POPULARITY: self._calculate_popularity,
            WeightingFactor.COMPLETENESS: self._calculate_completeness,
            WeightingFactor.FRESHNESS: self._calculate_freshness,
            WeightingFactor.CONTEXT_MATCH: self._calculate_context_match,
            WeightingFactor.REFERENCE_DEPTH: self._calculate_reference_depth,
            WeightingFactor.VALIDATION_STATUS: self._calculate_validation_status,
            WeightingFactor.TASK_FOCUS: self._calculate_task_focus,
        }

    def weight_results(
        self,
        results: List[Dict[str, Any]],
        query_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[WeightedResult], Dict[str, Any]]:
        """
        Apply weighting algorithm to search results.

        Args:
            results: Raw search results with metadata
            query_context: Context information about the query

        Returns:
            Tuple of (weighted_results, performance_metrics)
        """
        start_time = time.time()

        weighted_results = []
        total_base_score = 0.0

        for result in results:
            weighted = self._weight_single_result(result, query_context)
            weighted_results.append(weighted)
            total_base_score += weighted.base_score

        # Apply normalization across results
        self._normalize_scores(weighted_results)

        # Sort by final score (descending)
        weighted_results.sort(key=lambda x: x.final_score, reverse=True)

        # Calculate performance metrics
        processing_time = (time.time() - start_time) * 1000
        avg_base_score = total_base_score / len(weighted_results) if weighted_results else 0
        avg_final_score = sum(r.final_score for r in weighted_results) / len(weighted_results) if weighted_results else 0

        metrics = {
            "processing_time_ms": processing_time,
            "result_count": len(weighted_results),
            "avg_base_score": avg_base_score,
            "avg_final_score": avg_final_score,
            "improvement_ratio": avg_final_score / avg_base_score if avg_base_score > 0 else 0,
            "latency_target_met": processing_time < 50,
        }

        # Log performance
        self.performance_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "result_count": len(weighted_results)
        })

        return weighted_results, metrics

    def _weight_single_result(
        self,
        result: Dict[str, Any],
        query_context: Optional[Dict[str, Any]]
    ) -> WeightedResult:
        """Calculate weights for a single result."""
        result_id = result.get("id", str(hash(str(result))))
        base_score = result.get("relevance", 0.0)

        factor_scores = {}
        applied_boosts = []

        # Calculate each factor score
        for factor in WeightingFactor:
            if factor in self.config.factors:
                calculator = self._factor_calculators[factor]
                score = calculator(result, query_context)
                factor_scores[factor] = score

        # Calculate weighted sum
        final_score = sum(
            factor_scores.get(factor, 0.0) * weight
            for factor, weight in self.config.factors.items()
        )

        # Apply boost multipliers
        final_score = self._apply_boosts(final_score, result, applied_boosts)

        return WeightedResult(
            result_id=result_id,
            base_score=base_score,
            factor_scores=factor_scores,
            final_score=final_score,
            applied_boosts=applied_boosts,
            metadata=result,
        )

    def _apply_boosts(
        self,
        score: float,
        result: Dict[str, Any],
        applied_boosts: List[str]
    ) -> float:
        """Apply boost multipliers based on result characteristics."""
        boosted_score = score

        # Validation passed boost - check both top level and metadata
        validation_passed = result.get("validation_passed") or result.get("metadata", {}).get("validation_passed")
        if validation_passed:
            boosted_score *= self.config.boost_multipliers["validation_passed"]
            applied_boosts.append("validation_passed")

        # High authority boost (based on references or citations)
        references = result.get("references", []) or result.get("metadata", {}).get("references", [])
        if len(references) >= 5:
            boosted_score *= self.config.boost_multipliers["high_authority"]
            applied_boosts.append("high_authority")

        # Recent access boost
        recently_accessed = result.get("recently_accessed") or result.get("metadata", {}).get("recently_accessed")
        if recently_accessed:
            boosted_score *= self.config.boost_multipliers["recent_access"]
            applied_boosts.append("recent_access")

        # Task focus boost
        task_focus = result.get("task_focus") or result.get("metadata", {}).get("task_focus")
        if task_focus:
            boosted_score *= self.config.boost_multipliers["task_focus"]
            applied_boosts.append("task_focus")

        return boosted_score

    def _normalize_scores(self, results: List[WeightedResult]) -> None:
        """Apply normalization to factor scores across all results."""
        if not results:
            return

        method = self.config.normalization_method

        # Get all factors that have scores in any result
        all_factors = set()
        for result in results:
            all_factors.update(result.factor_scores.keys())

        if method == "minmax":
            self._minmax_normalize(results, all_factors)
        elif method == "zscore":
            self._zscore_normalize(results, all_factors)
        elif method == "robust":
            self._robust_normalize(results, all_factors)

    def _minmax_normalize(self, results: List[WeightedResult], factors: Set[WeightingFactor]) -> None:
        """Min-max normalization across results."""
        for factor in factors:
            scores = [r.factor_scores.get(factor, 0.0) for r in results]
            if not scores:
                continue

            min_score = min(scores)
            max_score = max(scores)
            score_range = max_score - min_score

            if score_range > 0:
                for result in results:
                    normalized = (result.factor_scores[factor] - min_score) / score_range
                    result.factor_scores[factor] = normalized

    def _zscore_normalize(self, results: List[WeightedResult], factors: Set[WeightingFactor]) -> None:
        """Z-score normalization across results."""
        for factor in factors:
            scores = [r.factor_scores.get(factor, 0.0) for r in results]
            if not scores:
                continue

            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            std_dev = math.sqrt(variance) if variance > 0 else 1.0

            for result in results:
                z_score = (result.factor_scores[factor] - mean_score) / std_dev
                # Convert to 0-1 scale
                result.factor_scores[factor] = 1 / (1 + math.exp(-z_score))

    def _robust_normalize(self, results: List[WeightedResult]) -> None:
        """Robust normalization using median and MAD."""
        for factor in factors:
            scores = [r.factor_scores.get(factor, 0.0) for r in results]
            if not scores:
                continue

            sorted_scores = sorted(scores)
            median = sorted_scores[len(scores) // 2]

            # Median Absolute Deviation
            mad = sum(abs(s - median) for s in scores) / len(scores)

            if mad > 0:
                for result in results:
                    robust_score = (result.factor_scores[factor] - median) / mad
                    # Convert to 0-1 scale using tanh
                    result.factor_scores[factor] = (math.tanh(robust_score) + 1) / 2

    # Factor calculation methods
    def _calculate_relevance(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate relevance score."""
        return result.get("relevance", 0.0)

    def _calculate_recency(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate recency score based on timestamp."""
        timestamp_str = result.get("timestamp") or result.get("created_at")
        if not timestamp_str:
            return 0.5  # Neutral score

        try:
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = timestamp_str

            current_time = datetime.now(timezone.utc)
            hours_since = (current_time - timestamp).total_seconds() / 3600

            # Exponential decay over 7 days
            return math.exp(-hours_since / (7 * 24))
        except (ValueError, TypeError):
            return 0.5

    def _calculate_authority(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate authority based on references and citations."""
        references = result.get("references", [])
        citations = result.get("citations", [])

        # Base authority from reference count
        ref_score = min(1.0, len(references) / 10)

        # Citation authority
        cit_score = min(1.0, len(citations) / 5)

        return (ref_score + cit_score) / 2

    def _calculate_popularity(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate popularity based on access patterns."""
        access_count = result.get("access_count", 0)
        view_count = result.get("view_count", 0)

        # Normalize to 0-1 scale
        return min(1.0, (access_count + view_count) / 100)

    def _calculate_completeness(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate completeness based on content metrics."""
        content_length = len(result.get("content", ""))
        has_summary = bool(result.get("summary"))
        has_metadata = bool(result.get("metadata"))

        # Length score (assuming good content is 1000-5000 chars)
        if content_length < 500:
            length_score = content_length / 500
        elif content_length <= 5000:
            length_score = 1.0
        else:
            length_score = max(0.5, 1.0 - (content_length - 5000) / 10000)

        # Structure score
        structure_score = (0.5 if has_summary else 0) + (0.5 if has_metadata else 0)

        return (length_score + structure_score) / 2

    def _calculate_freshness(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate freshness based on update frequency."""
        last_updated = result.get("last_updated")
        if not last_updated:
            return 0.5

        try:
            if isinstance(last_updated, str):
                update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            else:
                update_time = last_updated

            current_time = datetime.now(timezone.utc)
            days_since_update = (current_time - update_time).total_seconds() / (24 * 3600)

            # Higher score for recently updated content
            return math.exp(-days_since_update / 30)  # 30-day decay
        except (ValueError, TypeError):
            return 0.5

    def _calculate_context_match(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate context match score."""
        if not context:
            return 0.5

        query_terms = set(context.get("query_terms", []))
        result_terms = set(result.get("terms", []))

        if not query_terms:
            return 0.5

        intersection = query_terms & result_terms
        return len(intersection) / len(query_terms) if query_terms else 0.5

    def _calculate_reference_depth(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate reference chain depth."""
        references = result.get("references", [])
        return min(1.0, len(references) / 5)  # Cap at 5 references

    def _calculate_validation_status(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate validation status score."""
        if result.get("validation_passed"):
            return 1.0
        elif result.get("validation_failed"):
            return 0.0
        else:
            return 0.5  # Unknown status

    def _calculate_task_focus(self, result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate task focus score."""
        return 1.0 if result.get("task_focus") else 0.0

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.performance_log:
            return {}

        recent_logs = self.performance_log[-100:]

        processing_times = [log["metrics"]["processing_time_ms"] for log in recent_logs]
        improvement_ratios = [log["metrics"]["improvement_ratio"] for log in recent_logs]

        return {
            "total_operations": len(recent_logs),
            "avg_processing_time_ms": sum(processing_times) / len(processing_times),
            "p95_processing_time_ms": sorted(processing_times)[int(len(processing_times) * 0.95)],
            "avg_improvement_ratio": sum(improvement_ratios) / len(improvement_ratios),
            "latency_target_met_percent": sum(1 for log in recent_logs if log["metrics"]["latency_target_met"]) / len(recent_logs) * 100,
        }
# MODE: LIBRARY

"""
Search Result Hierarchy Manager

Organizes and tiers search results into hierarchical structures.
Implements configurable ranking systems and result categorization.

Features:
- Hierarchical result organization
- Tier-based ranking system
- Category-based grouping
- Performance-aware tiering
- Dynamic threshold adjustment
"""

from __future__ import annotations

import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

from .weighting_engine import WeightedResult, WeightingFactor


class HierarchyTier(Enum):
    """Enumeration of hierarchy tiers."""
    PREMIUM = "premium"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVAL = "archival"


@dataclass
class TierConfig:
    """Configuration for tier thresholds and limits."""
    tier: HierarchyTier
    min_score: float
    max_results: int
    priority_boost: float = 1.0
    quality_threshold: float = 0.0


@dataclass
class HierarchicalResult:
    """Result organized within hierarchy."""
    result: WeightedResult
    tier: HierarchyTier
    category: str
    rank_within_tier: int
    global_rank: int
    tier_score: float


@dataclass
class HierarchyConfig:
    """Configuration for result hierarchy."""
    tiers: List[TierConfig] = field(default_factory=list)
    category_weights: Dict[str, float] = field(default_factory=dict)
    max_total_results: int = 50
    tier_distribution: Dict[HierarchyTier, float] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default tier configuration."""
        if not self.tiers:
            self.tiers = [
                TierConfig(HierarchyTier.PREMIUM, 0.9, 5, 1.3, 0.95),
                TierConfig(HierarchyTier.HIGH, 0.7, 10, 1.1, 0.80),
                TierConfig(HierarchyTier.MEDIUM, 0.5, 15, 1.0, 0.60),
                TierConfig(HierarchyTier.LOW, 0.3, 20, 0.9, 0.40),
                TierConfig(HierarchyTier.ARCHIVAL, 0.0, 100, 0.7, 0.20),
            ]

        if not self.tier_distribution:
            self.tier_distribution = {
                HierarchyTier.PREMIUM: 0.10,  # 10% of results
                HierarchyTier.HIGH: 0.20,     # 20% of results
                HierarchyTier.MEDIUM: 0.30,   # 30% of results
                HierarchyTier.LOW: 0.30,      # 30% of results
                HierarchyTier.ARCHIVAL: 0.10, # 10% of results
            }


class HierarchyManager:
    """
    Manages hierarchical organization of search results.

    Implements tiered ranking system with configurable thresholds
    and category-based organization.
    """

    def __init__(self, config: Optional[HierarchyConfig] = None):
        self.config = config or HierarchyConfig()
        self.performance_log: List[Dict[str, Any]] = []

    def organize_results(
        self,
        weighted_results: List[WeightedResult],
        query_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[HierarchyTier, List[HierarchicalResult]], Dict[str, Any]]:
        """
        Organize weighted results into hierarchical tiers.

        Args:
            weighted_results: Results with computed weights
            query_context: Query context for categorization

        Returns:
            Tuple of (tiered_results, performance_metrics)
        """
        start_time = time.time()

        # Categorize results
        categorized_results = self._categorize_results(weighted_results, query_context)

        # Assign tiers based on scores and distribution
        tiered_results = self._assign_tiers(categorized_results)

        # Sort within each tier
        for tier_results in tiered_results.values():
            tier_results.sort(key=lambda x: x.tier_score, reverse=True)
            for i, result in enumerate(tier_results):
                result.rank_within_tier = i + 1

        # Assign global ranks
        self._assign_global_ranks(tiered_results)

        # Apply tier limits
        tiered_results = self._apply_tier_limits(tiered_results)

        # Calculate performance metrics
        processing_time = (time.time() - start_time) * 1000
        total_results = sum(len(results) for results in tiered_results.values())

        tier_distribution = {
            tier.value: len(results) for tier, results in tiered_results.items()
        }

        metrics = {
            "processing_time_ms": processing_time,
            "total_results": total_results,
            "tier_distribution": tier_distribution,
            "avg_results_per_tier": total_results / len(HierarchyTier),
            "hierarchy_depth": len([t for t in tiered_results.values() if t]),
        }

        # Log performance
        self.performance_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
        })

        return tiered_results, metrics

    def _categorize_results(
        self,
        results: List[WeightedResult],
        query_context: Optional[Dict[str, Any]]
    ) -> Dict[str, List[WeightedResult]]:
        """Categorize results by content type and relevance."""
        categories = {}

        for result in results:
            category = self._determine_category(result, query_context)

            if category not in categories:
                categories[category] = []

            categories[category].append(result)

        return categories

    def _determine_category(self, result: WeightedResult, query_context: Optional[Dict[str, Any]]) -> str:
        """Determine the category for a result."""
        metadata = result.metadata

        # Check for explicit category
        if "category" in metadata:
            return metadata["category"]

        # Determine based on content type
        content_type = metadata.get("type", "").lower()

        if "task" in content_type or "report" in content_type:
            return "tasks"
        elif "knowledge" in content_type or "doc" in content_type:
            return "documentation"
        elif "code" in content_type or "script" in content_type:
            return "code"
        elif "analysis" in content_type or "research" in content_type:
            return "analysis"
        else:
            return "general"

    def _assign_tiers(
        self,
        categorized_results: Dict[str, List[WeightedResult]]
    ) -> Dict[HierarchyTier, List[HierarchicalResult]]:
        """Assign results to hierarchy tiers."""
        tiered_results: Dict[HierarchyTier, List[HierarchicalResult]] = {
            tier: [] for tier in HierarchyTier
        }

        # Flatten categorized results with category weighting
        all_results = []
        for category, results in categorized_results.items():
            category_weight = self.config.category_weights.get(category, 1.0)

            for result in results:
                # Apply category weighting to final score
                adjusted_score = result.final_score * category_weight
                all_results.append((result, category, adjusted_score))

        # Sort by adjusted score
        all_results.sort(key=lambda x: x[2], reverse=True)

        # Assign to tiers based on score thresholds and distribution
        total_results = len(all_results)
        tier_counts = {
            tier: int(total_results * self.config.tier_distribution[tier])
            for tier in HierarchyTier
        }

        # Ensure minimum results per tier
        for tier_config in self.config.tiers:
            if tier_counts[tier_config.tier] < 1 and total_results > 0:
                tier_counts[tier_config.tier] = 1

        result_index = 0
        for tier_config in self.config.tiers:
            tier = tier_config.tier
            max_for_tier = min(tier_counts[tier], tier_config.max_results)

            for i in range(max_for_tier):
                if result_index >= len(all_results):
                    break

                result, category, adjusted_score = all_results[result_index]

                # Apply tier priority boost
                tier_score = adjusted_score * tier_config.priority_boost

                hierarchical_result = HierarchicalResult(
                    result=result,
                    tier=tier,
                    category=category,
                    rank_within_tier=0,  # Set later
                    global_rank=0,       # Set later
                    tier_score=tier_score
                )

                tiered_results[tier].append(hierarchical_result)
                result_index += 1

        return tiered_results

    def _assign_global_ranks(self, tiered_results: Dict[HierarchyTier, List[HierarchicalResult]]) -> None:
        """Assign global ranks across all tiers."""
        # Collect all results in tier order
        all_hierarchical = []

        # Premium first, then High, Medium, Low, Archival
        tier_order = [HierarchyTier.PREMIUM, HierarchyTier.HIGH, HierarchyTier.MEDIUM,
                     HierarchyTier.LOW, HierarchyTier.ARCHIVAL]

        for tier in tier_order:
            all_hierarchical.extend(tiered_results[tier])

        # Assign global ranks
        for i, hierarchical_result in enumerate(all_hierarchical):
            hierarchical_result.global_rank = i + 1

    def _apply_tier_limits(self, tiered_results: Dict[HierarchyTier, List[HierarchicalResult]]) -> Dict[HierarchyTier, List[HierarchicalResult]]:
        """Apply maximum limits to each tier."""
        limited_results = {}

        for tier, results in tiered_results.items():
            tier_config = next((t for t in self.config.tiers if t.tier == tier), None)
            if tier_config:
                limited_results[tier] = results[:tier_config.max_results]
            else:
                limited_results[tier] = results

        return limited_results

    def get_tier_stats(self, tiered_results: Dict[HierarchyTier, List[HierarchicalResult]]) -> Dict[str, Any]:
        """Get statistics about tier distribution."""
        stats = {}

        for tier, results in tiered_results.items():
            if results:
                scores = [r.tier_score for r in results]
                stats[tier.value] = {
                    "count": len(results),
                    "avg_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "categories": list(set(r.category for r in results))
                }
            else:
                stats[tier.value] = {
                    "count": 0,
                    "avg_score": 0.0,
                    "min_score": 0.0,
                    "max_score": 0.0,
                    "categories": []
                }

        return stats

    def optimize_tier_thresholds(
        self,
        historical_performance: List[Dict[str, Any]]
    ) -> HierarchyConfig:
        """
        Optimize tier thresholds based on historical performance.

        Args:
            historical_performance: List of past performance metrics

        Returns:
            Optimized hierarchy configuration
        """
        if not historical_performance:
            return self.config

        # Analyze click-through rates and user satisfaction
        # This is a simplified optimization - in practice would use ML

        avg_improvement = sum(h.get("improvement_ratio", 0) for h in historical_performance) / len(historical_performance)

        # Adjust thresholds based on performance
        optimized_config = HierarchyConfig()

        if avg_improvement > 1.3:  # Good performance
            # Tighten premium tier
            optimized_config.tiers[0].min_score = 0.85
        elif avg_improvement < 1.1:  # Poor performance
            # Loosen premium tier
            optimized_config.tiers[0].min_score = 0.75

        return optimized_config

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.performance_log:
            return {}

        recent_logs = self.performance_log[-100:]

        processing_times = [log["metrics"]["processing_time_ms"] for log in recent_logs]

        return {
            "total_operations": len(recent_logs),
            "avg_processing_time_ms": sum(processing_times) / len(processing_times),
            "p95_processing_time_ms": sorted(processing_times)[int(len(processing_times) * 0.95)],
            "avg_hierarchy_depth": sum(log["metrics"]["hierarchy_depth"] for log in recent_logs) / len(recent_logs),
        }
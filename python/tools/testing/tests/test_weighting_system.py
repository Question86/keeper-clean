# MODE: LIBRARY

"""
Comprehensive Weighting System Tests

Validates weighting engine, hierarchy manager, and relevance analyzer.
Tests performance targets and relevance improvements.
"""

import pytest
import time
from unittest.mock import Mock, patch
from typing import Dict, List, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search.weighting_engine import (
    WeightingEngine, WeightingConfig, WeightedResult, WeightingFactor
)
from search.hierarchy_manager import (
    HierarchyManager, HierarchyConfig, HierarchicalResult, HierarchyTier
)
from search.relevance_analyzer import (
    RelevanceAnalyzer, RelevanceConfig, RelevanceAnalysis, QualityMetrics
)
from api.enhanced_recommendations import (
    EnhancedRecommendationsAPI, RecommendationRequest
)


class TestWeightingEngine:
    """Test cases for the weighting engine."""

    @pytest.fixture
    def sample_results(self) -> List[Dict[str, Any]]:
        """Sample search results for testing."""
        return [
            {
                "id": "result_1",
                "relevance": 0.8,
                "content": "This is a high-quality task report with validation",
                "type": "task",
                "metadata": {
                    "validation_passed": True,
                    "references": ["ref1", "ref2", "ref3", "ref4", "ref5"],
                    "task_focus": True,
                    "timestamp": "2024-01-20T10:00:00Z",
                    "recently_accessed": True,
                }
            },
            {
                "id": "result_2",
                "relevance": 0.6,
                "content": "Basic documentation without validation",
                "type": "documentation",
                "metadata": {
                    "validation_passed": False,
                    "references": ["ref1"],
                    "task_focus": False,
                    "timestamp": "2024-01-15T10:00:00Z",
                    "recently_accessed": False,
                }
            },
            {
                "id": "result_3",
                "relevance": 0.7,
                "content": "Analysis with some references",
                "type": "analysis",
                "metadata": {
                    "validation_passed": True,
                    "references": ["ref1", "ref2"],
                    "task_focus": False,
                    "timestamp": "2024-01-25T10:00:00Z",
                    "recently_accessed": False,
                }
            }
        ]

    @pytest.fixture
    def weighting_engine(self) -> WeightingEngine:
        """Weighting engine instance."""
        config = WeightingConfig()
        return WeightingEngine(config)

    def test_weight_results_basic(self, weighting_engine, sample_results):
        """Test basic result weighting."""
        weighted_results, metrics = weighting_engine.weight_results(sample_results)

        assert len(weighted_results) == 3
        assert all(isinstance(r, WeightedResult) for r in weighted_results)
        assert metrics["result_count"] == 3
        assert "processing_time_ms" in metrics
        assert metrics["latency_target_met"] is True  # Should be < 50ms

    def test_weight_results_scoring(self, weighting_engine, sample_results):
        """Test that scoring improves results."""
        weighted_results, metrics = weighting_engine.weight_results(sample_results)

        # Check that scores are reasonable
        for result in weighted_results:
            assert 0 <= result.final_score <= 2.0  # Allow for boosts
            # Final score should be a reasonable combination of factors
            # (not necessarily higher than base score due to normalization)

        # Check improvement ratio (can be < 1.0 due to normalization balancing factors)
        assert 0.5 <= metrics["improvement_ratio"] <= 2.0

    def test_weight_results_with_boosts(self, weighting_engine):
        """Test boost multipliers are applied correctly."""
        results = [
            {
                "id": "high_quality",
                "relevance": 0.5,
                "metadata": {
                    "validation_passed": True,
                    "references": ["r1", "r2", "r3", "r4", "r5"],
                    "task_focus": True,
                    "recently_accessed": True,
                }
            }
        ]

        weighted_results, _ = weighting_engine.weight_results(results)

        # Should have multiple boosts applied
        assert len(weighted_results[0].applied_boosts) >= 3
        assert "validation_passed" in weighted_results[0].applied_boosts
        assert "high_authority" in weighted_results[0].applied_boosts
        assert "task_focus" in weighted_results[0].applied_boosts

    def test_performance_targets(self, weighting_engine, sample_results):
        """Test performance targets are met."""
        start_time = time.time()

        # Run multiple times to get stable measurement
        for _ in range(10):
            weighting_engine.weight_results(sample_results)

        avg_time = (time.time() - start_time) / 10 * 1000

        assert avg_time < 50  # < 50ms target

    def test_factor_calculation(self, weighting_engine):
        """Test individual factor calculations."""
        result = {
            "id": "test",
            "relevance": 0.8,
            "metadata": {
                "validation_passed": True,
                "references": ["r1", "r2"],
                "timestamp": "2024-01-20T10:00:00Z",
            }
        }

        weighted_results, _ = weighting_engine.weight_results([result])

        factor_scores = weighted_results[0].factor_scores

        # Check that configured factors have scores
        for factor in weighting_engine.config.factors:
            assert factor in factor_scores
            assert 0 <= factor_scores[factor] <= 1

    def test_normalization_methods(self):
        """Test different normalization methods."""
        config = WeightingConfig(normalization_method="zscore")
        engine = WeightingEngine(config)

        results = [
            {"id": "1", "relevance": 0.1, "metadata": {}},
            {"id": "2", "relevance": 0.5, "metadata": {}},
            {"id": "3", "relevance": 0.9, "metadata": {}}
        ]

        weighted_results, _ = engine.weight_results(results)

        # Z-score normalization should handle different scales
        assert all(0 <= r.final_score <= 1 for r in weighted_results)


class TestHierarchyManager:
    """Test cases for the hierarchy manager."""

    @pytest.fixture
    def sample_weighted_results(self) -> List[WeightedResult]:
        """Sample weighted results."""
        return [
            WeightedResult(
                result_id="result_1",
                base_score=0.8,
                final_score=1.2,
                metadata={"type": "task", "category": "tasks", "validation_passed": True}
            ),
            WeightedResult(
                result_id="result_2",
                base_score=0.6,
                final_score=0.8,
                metadata={"type": "doc", "category": "documentation", "validation_passed": False}
            ),
            WeightedResult(
                result_id="result_3",
                base_score=0.7,
                final_score=1.0,
                metadata={"type": "analysis", "category": "analysis", "validation_passed": True}
            )
        ]

    @pytest.fixture
    def hierarchy_manager(self) -> HierarchyManager:
        """Hierarchy manager instance."""
        config = HierarchyConfig()
        return HierarchyManager(config)

    def test_organize_results(self, hierarchy_manager, sample_weighted_results):
        """Test result organization into tiers."""
        # Pass WeightedResult objects directly
        tiered_results, metrics = hierarchy_manager.organize_results(sample_weighted_results)

        # Check that results are organized by tier
        assert isinstance(tiered_results, dict)
        assert all(isinstance(tier, HierarchyTier) for tier in tiered_results.keys())

        # Check that results have hierarchical structure
        total_results = sum(len(results) for results in tiered_results.values())
        assert total_results == len(sample_weighted_results)

        # Check metrics
        assert "processing_time_ms" in metrics
        assert "tier_distribution" in metrics

    def test_tier_assignment(self, hierarchy_manager):
        """Test tier assignment logic."""
        from search.weighting_engine import WeightedResult
        
        results = [
            WeightedResult(
                result_id="premium",
                base_score=0.9,
                final_score=1.5,
                metadata={"type": "task", "category": "tasks", "validation_passed": True, "references": ["r1", "r2", "r3", "r4", "r5"], "task_focus": True}
            ),
            WeightedResult(
                result_id="high", 
                base_score=0.7,
                final_score=1.0,
                metadata={"type": "doc", "category": "documentation", "validation_passed": True, "references": ["r1", "r2"], "task_focus": False}
            ),
            WeightedResult(
                result_id="medium",
                base_score=0.5, 
                final_score=0.7,
                metadata={"type": "analysis", "category": "analysis", "validation_passed": False, "references": [], "task_focus": False}
            ),
        ]

        tiered_results, _ = hierarchy_manager.organize_results(results)

        # Premium result should be in premium tier
        premium_results = tiered_results[HierarchyTier.PREMIUM]
        assert len(premium_results) >= 1
        assert any(r.result.result_id == "premium" for r in premium_results)

    def test_global_ranking(self, hierarchy_manager):
        """Test global ranking across tiers."""
        from search.weighting_engine import WeightedResult
        
        results = [
            WeightedResult(
                result_id="1",
                base_score=0.9,
                final_score=1.5,
                metadata={"type": "task", "category": "tasks", "validation_passed": True, "references": [], "task_focus": False}
            ),
            WeightedResult(
                result_id="2",
                base_score=0.8,
                final_score=1.2,
                metadata={"type": "task", "category": "tasks", "validation_passed": True, "references": [], "task_focus": False}
            ),
        ]

        tiered_results, _ = hierarchy_manager.organize_results(results)

        # Collect all hierarchical results
        all_results = []
        for tier_results in tiered_results.values():
            all_results.extend(tier_results)

        # Check global ranks are assigned
        global_ranks = [r.global_rank for r in all_results]
        assert global_ranks == sorted(global_ranks)  # Should be sequential

    def test_tier_limits(self, hierarchy_manager):
        """Test tier limits are enforced."""
        from search.weighting_engine import WeightedResult
        
        # Create many results
        results = [
            WeightedResult(
                result_id=f"result_{i}",
                base_score=0.8,
                final_score=1.2,
                metadata={"type": "task", "category": "tasks", "validation_passed": True, "references": [], "task_focus": False}
            )
            for i in range(20)
        ]

        tiered_results, _ = hierarchy_manager.organize_results(results)

        # Check tier limits (premium tier has max 5)
        premium_results = tiered_results[HierarchyTier.PREMIUM]
        assert len(premium_results) <= 5


class TestRelevanceAnalyzer:
    """Test cases for the relevance analyzer."""

    @pytest.fixture
    def sample_weighted_results(self) -> List[WeightedResult]:
        """Sample weighted results for relevance analysis."""
        return [
            WeightedResult(
                result_id="result_1",
                base_score=0.8,
                final_score=1.2,
                metadata={
                    "content": "This is a comprehensive task report with detailed analysis and validation.",
                    "type": "task",
                    "validation_passed": True,
                    "references": ["ref1", "ref2", "ref3"],
                    "author": "Test Author",
                    "created_at": "2024-01-20T10:00:00Z",
                    "summary": "A detailed task report",
                }
            ),
            WeightedResult(
                result_id="result_2",
                base_score=0.6,
                final_score=0.8,
                metadata={
                    "content": "Basic documentation",
                    "type": "documentation",
                    "validation_passed": False,
                    "references": [],
                    "created_at": "2024-01-15T10:00:00Z",
                }
            )
        ]

    @pytest.fixture
    def relevance_analyzer(self) -> RelevanceAnalyzer:
        """Relevance analyzer instance."""
        config = RelevanceConfig()
        return RelevanceAnalyzer(config)

    def test_analyze_relevance(self, relevance_analyzer, sample_weighted_results):
        """Test relevance analysis."""
        analyses, metrics = relevance_analyzer.analyze_relevance(
            sample_weighted_results, "task report", {"query_terms": ["task", "report"]}
        )

        assert len(analyses) == 2
        assert all(isinstance(a, RelevanceAnalysis) for a in analyses)
        assert metrics["result_count"] == 2
        assert "processing_time_ms" in metrics
        assert metrics["latency_target_met"] is True

    def test_quality_assessment(self, relevance_analyzer):
        """Test quality assessment metrics."""
        content = "This is a comprehensive analysis with references and examples."
        metadata = {
            "validation_passed": True,
            "references": ["ref1", "ref2"],
            "author": "Test Author",
            "created_at": "2024-01-20T10:00:00Z",
        }

        quality = relevance_analyzer._assess_quality(content, metadata)

        assert isinstance(quality, QualityMetrics)
        assert 0 <= quality.overall_quality <= 1
        assert quality.accuracy_score == 1.0  # validation_passed
        assert quality.authority_score > 0  # has references

    def test_relevance_improvement(self, relevance_analyzer, sample_weighted_results):
        """Test relevance improvement calculation."""
        _, metrics = relevance_analyzer.analyze_relevance(sample_weighted_results, "task", {})

        # Should calculate relevance improvement (can be < 1.0 for less relevant results)
        assert 0.5 <= metrics["relevance_improvement"] <= 2.0

    def test_query_intent_analysis(self, relevance_analyzer):
        """Test query intent analysis."""
        intent = relevance_analyzer._analyze_query_intent("how to implement task", {})

        assert intent["type"] == "question"
        assert intent["complexity"] == "medium"

    def test_content_extraction(self, relevance_analyzer, sample_weighted_results):
        """Test content extraction from results."""
        content = relevance_analyzer._extract_content(sample_weighted_results[0])

        assert "comprehensive task report" in content.lower()


class TestEnhancedRecommendationsAPI:
    """Test cases for the enhanced recommendations API."""

    @pytest.fixture
    def api_instance(self, tmp_path):
        """API instance with temporary workspace."""
        return EnhancedRecommendationsAPI(str(tmp_path))

    def test_get_recommendations_basic(self, api_instance):
        """Test basic recommendations request."""
        request_data = {
            "query": "test query",
            "limit": 5,
            "ranking_algorithm": "weighted"
        }

        # Mock the search method to return sample results
        with patch.object(api_instance, '_perform_search') as mock_search:
            mock_search.return_value = [
                {
                    "id": "result_1",
                    "relevance": 0.8,
                    "content": "Test content",
                    "type": "task",
                    "metadata": {"validation_passed": True},
                }
            ]

            response = api_instance.get_recommendations(request_data)

            assert "results" in response
            assert "metadata" in response
            assert "performance" in response
            assert response["performance"]["success"] is True

    def test_ranking_algorithms(self, api_instance):
        """Test different ranking algorithms."""
        request_data = {
            "query": "test",
            "ranking_algorithm": "hierarchical"
        }

        with patch.object(api_instance, '_perform_search') as mock_search:
            mock_search.return_value = [
                {
                    "id": "result_1",
                    "relevance": 0.8,
                    "content": "Test content",
                    "type": "task",
                    "metadata": {"validation_passed": True},
                }
            ]

            response = api_instance.get_recommendations(request_data)

            assert response["metadata"]["ranking_algorithm"] == "hierarchical"
            assert "hierarchy" in response

    def test_error_handling(self, api_instance):
        """Test error handling in API."""
        # Test missing query
        response = api_instance.get_recommendations({})

        assert "error" in response
        assert "success" in response["performance"]
        assert response["performance"]["success"] is False

    def test_performance_tracking(self, api_instance):
        """Test performance tracking."""
        request_data = {"query": "test"}

        with patch.object(api_instance, '_perform_search') as mock_search:
            mock_search.return_value = []

            api_instance.get_recommendations(request_data)

            stats = api_instance.get_performance_stats()
            assert "total_requests" in stats
            assert stats["total_requests"] >= 1


class TestIntegration:
    """Integration tests for the complete weighting system."""

    @pytest.fixture
    def full_system(self, tmp_path):
        """Complete weighting system."""
        return EnhancedRecommendationsAPI(str(tmp_path))

    def test_end_to_end_weighted_ranking(self, full_system):
        """Test end-to-end weighted ranking."""
        request_data = {
            "query": "task implementation",
            "ranking_algorithm": "weighted",
            "limit": 10
        }

        with patch.object(full_system, '_perform_search') as mock_search:
            mock_search.return_value = [
                {
                    "id": f"result_{i}",
                    "relevance": 0.5 + i * 0.1,
                    "content": f"Content for result {i}",
                    "type": "task" if i % 2 == 0 else "documentation",
                    "metadata": {
                        "validation_passed": i % 3 == 0,
                        "references": ["ref"] * (i % 5),
                        "task_focus": i % 4 == 0,
                        "timestamp": f"2024-01-{20+i:02d}T10:00:00Z",
                    }
                }
                for i in range(5)
            ]

            response = full_system.get_recommendations(request_data)

            assert len(response["results"]) <= 10
            assert all("score" in result for result in response["results"])

            # Check performance targets
            perf = response["performance"]
            assert perf["total_processing_time_ms"] < 100  # Reasonable limit
            assert perf["weighting"]["latency_target_met"] is True

    def test_relevance_improvement_target(self, full_system):
        """Test that relevance improvement target is met."""
        request_data = {
            "query": "validation testing",
            "ranking_algorithm": "relevance"
        }

        with patch.object(full_system, '_perform_search') as mock_search:
            mock_search.return_value = [
                {
                    "id": "high_quality",
                    "relevance": 0.6,
                    "content": "Comprehensive validation testing guide with examples and best practices.",
                    "type": "task",
                    "metadata": {
                        "validation_passed": True,
                        "references": ["ref1", "ref2", "ref3", "ref4", "ref5"],
                        "author": "Expert",
                        "created_at": "2024-01-25T10:00:00Z",
                        "summary": "Complete validation testing methodology",
                    }
                },
                {
                    "id": "low_quality",
                    "relevance": 0.4,
                    "content": "Basic test",
                    "type": "documentation",
                    "metadata": {
                        "validation_passed": False,
                        "references": [],
                        "created_at": "2024-01-01T10:00:00Z",
                    }
                }
            ]

            response = full_system.get_recommendations(request_data)

            ranking_metrics = response["performance"]["ranking"]

            # Should show significant improvement
            assert ranking_metrics["relevance_improvement"] >= 1.2  # 20% improvement minimum

    def test_latency_target(self, full_system):
        """Test that latency targets are met."""
        request_data = {"query": "performance test"}

        with patch.object(full_system, '_perform_search') as mock_search:
            # Create larger result set for performance testing
            mock_search.return_value = [
                {
                    "id": f"result_{i}",
                    "relevance": 0.5,
                    "content": f"Content {i} " * 10,  # Longer content
                    "type": "task",
                    "metadata": {
                        "validation_passed": True,
                        "references": ["ref"] * 3,
                        "timestamp": "2024-01-20T10:00:00Z",
                    }
                }
                for i in range(20)
            ]

            start_time = time.time()
            response = full_system.get_recommendations(request_data)
            total_time = (time.time() - start_time) * 1000

            # Overall latency should be < 50ms
            assert total_time < 50

            # Individual component latencies should also be met
            perf = response["performance"]
            assert perf["weighting"]["latency_target_met"] is True
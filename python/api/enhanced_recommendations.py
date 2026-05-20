# MODE: LIBRARY

"""
Enhanced Recommendations API

Updated route functionality with weighted ranking and hierarchical results.
Integrates search weighting system with recommendation endpoints.

Features:
- Weighted result ranking
- Hierarchical result organization
- Performance monitoring
- Enhanced recommendation algorithms
- API response optimization
"""

from __future__ import annotations

import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

# Import search components
from search.weighting_engine import WeightingEngine, WeightingConfig, WeightedResult
from search.hierarchy_manager import HierarchyManager, HierarchyConfig, HierarchicalResult, HierarchyTier
from search.relevance_analyzer import RelevanceAnalyzer, RelevanceConfig, RelevanceAnalysis
from knowledge_db import KnowledgeDB


@dataclass
class RecommendationRequest:
    """Request parameters for recommendations."""
    query: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    limit: int = 20
    include_metadata: bool = True
    ranking_algorithm: str = "weighted"  # weighted, hierarchical, relevance


@dataclass
class RecommendationResponse:
    """Response structure for recommendations."""
    results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, Any] = field(default_factory=dict)
    hierarchy: Optional[Dict[str, Any]] = None


class EnhancedRecommendationsAPI:
    """
    Enhanced recommendations API with weighted ranking.

    Integrates weighting engine, hierarchy manager, and relevance analyzer
    to provide high-quality, hierarchically organized recommendations.
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.knowledge_db = KnowledgeDB(workspace_path)

        # Initialize components with optimized configs
        weighting_config = WeightingConfig()
        self.weighting_engine = WeightingEngine(weighting_config)

        hierarchy_config = HierarchyConfig()
        self.hierarchy_manager = HierarchyManager(hierarchy_config)

        relevance_config = RelevanceConfig()
        self.relevance_analyzer = RelevanceAnalyzer(relevance_config)

        # Performance tracking
        self.request_log: List[Dict[str, Any]] = []

    def get_recommendations(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get enhanced recommendations with weighted ranking.

        Args:
            request_data: Request parameters

        Returns:
            JSON response with recommendations
        """
        start_time = time.time()

        try:
            # Parse request
            req = self._parse_request(request_data)

            # Get base search results
            base_results = self._perform_search(req)

            # Apply weighting
            weighted_results, weighting_metrics = self.weighting_engine.weight_results(
                base_results, req.context
            )

            # Apply ranking algorithm
            if req.ranking_algorithm == "hierarchical":
                ranked_results, ranking_metrics = self._apply_hierarchical_ranking(
                    weighted_results, req
                )
            elif req.ranking_algorithm == "relevance":
                ranked_results, ranking_metrics = self._apply_relevance_ranking(
                    weighted_results, req
                )
            else:  # weighted
                ranked_results, ranking_metrics = self._apply_weighted_ranking(
                    weighted_results, req
                )

            # Format response
            response = self._format_response(ranked_results, req, {
                "weighting": weighting_metrics,
                "ranking": ranking_metrics,
                "total_processing_time_ms": (time.time() - start_time) * 1000
            })

            # Log request
            self._log_request(req, response, start_time)

            return response

        except Exception as e:
            # Error handling
            error_response = {
                "error": str(e),
                "results": [],
                "metadata": {},
                "performance": {
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "success": False
                }
            }
            self._log_request_error(request_data, str(e), start_time)
            return error_response

    def _parse_request(self, data: Dict[str, Any]) -> RecommendationRequest:
        """Parse request data into RecommendationRequest object."""
        return RecommendationRequest(
            query=data.get("query", ""),
            user_id=data.get("user_id"),
            context=data.get("context", {}),
            limit=min(data.get("limit", 20), 50),  # Cap at 50
            include_metadata=data.get("include_metadata", True),
            ranking_algorithm=data.get("ranking_algorithm", "weighted")
        )

    def _perform_search(self, req: RecommendationRequest) -> List[Dict[str, Any]]:
        """Perform base search to get candidate results."""
        # Use KnowledgeDB search with expanded query
        search_results = self.knowledge_db.search(
            query=req.query,
            limit=req.limit * 3,  # Get more for re-ranking
            semantic=True,
            use_cache=True
        )

        # Convert to dict format for weighting engine
        return [
            {
                "id": result.id,
                "relevance": result.relevance,
                "content": getattr(result, 'content', ''),
                "type": getattr(result, 'type', 'unknown'),
                "metadata": getattr(result, 'context', {}),
                "timestamp": getattr(result, 'context', {}).get('timestamp'),
                "validation_passed": getattr(result, 'context', {}).get('validation_passed', False),
                "references": getattr(result, 'context', {}).get('references', []),
                "task_focus": getattr(result, 'context', {}).get('task_focus', False),
                "recently_accessed": False,  # Would be set based on user behavior
                "access_count": getattr(result, 'context', {}).get('access_count', 0),
                "view_count": getattr(result, 'context', {}).get('view_count', 0),
                "citations": getattr(result, 'context', {}).get('citations', []),
                "author": getattr(result, 'context', {}).get('author'),
                "created_at": getattr(result, 'context', {}).get('created_at'),
                "updated_at": getattr(result, 'context', {}).get('updated_at'),
                "summary": getattr(result, 'context', {}).get('summary'),
                "description": getattr(result, 'context', {}).get('description'),
                "title": getattr(result, 'context', {}).get('title'),
                "terms": getattr(result, 'context', {}).get('terms', []),
                "last_updated": getattr(result, 'context', {}).get('last_updated'),
                "verified": getattr(result, 'context', {}).get('verified', False),
            }
            for result in search_results
        ]

    def _apply_weighted_ranking(
        self,
        weighted_results: List[WeightedResult],
        req: RecommendationRequest
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Apply weighted ranking algorithm."""
        # Results are already weighted and sorted
        ranked_results = [
            self._format_weighted_result(result, req.include_metadata)
            for result in weighted_results[:req.limit]
        ]

        metrics = {
            "algorithm": "weighted",
            "result_count": len(ranked_results),
            "avg_final_score": sum(r.final_score for r in weighted_results[:req.limit]) / len(ranked_results) if ranked_results else 0,
        }

        return ranked_results, metrics

    def _apply_hierarchical_ranking(
        self,
        weighted_results: List[WeightedResult],
        req: RecommendationRequest
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Apply hierarchical ranking algorithm."""
        # Convert WeightedResult to dict format for hierarchy manager
        dict_results = [
            {
                "id": r.result_id,
                "relevance": r.base_score,
                "final_score": r.final_score,
                "type": r.metadata.get("type", "unknown"),
                "category": r.metadata.get("category", "general"),
                "validation_passed": r.metadata.get("validation_passed", False),
                "references": r.metadata.get("references", []),
                "task_focus": r.metadata.get("task_focus", False),
                "context": r.metadata,
            }
            for r in weighted_results
        ]

        # Apply hierarchy
        tiered_results, hierarchy_metrics = self.hierarchy_manager.organize_results(
            dict_results, req.context
        )

        # Flatten hierarchical results in tier order
        ranked_results = []
        tier_order = [HierarchyTier.PREMIUM, HierarchyTier.HIGH, HierarchyTier.MEDIUM,
                     HierarchyTier.LOW, HierarchyTier.ARCHIVAL]

        for tier in tier_order:
            for hierarchical_result in tiered_results[tier]:
                formatted = self._format_hierarchical_result(
                    hierarchical_result, req.include_metadata
                )
                ranked_results.append(formatted)

                if len(ranked_results) >= req.limit:
                    break
            if len(ranked_results) >= req.limit:
                break

        metrics = {
            "algorithm": "hierarchical",
            "result_count": len(ranked_results),
            "tier_distribution": self.hierarchy_manager.get_tier_stats(tiered_results),
            **hierarchy_metrics
        }

        return ranked_results, metrics

    def _apply_relevance_ranking(
        self,
        weighted_results: List[WeightedResult],
        req: RecommendationRequest
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Apply relevance-based ranking algorithm."""
        # Convert to dict format for relevance analyzer
        dict_results = [
            {
                "id": r.result_id,
                "relevance": r.base_score,
                "content": r.metadata.get("content", ""),
                "type": r.metadata.get("type", "unknown"),
                "metadata": r.metadata,
            }
            for r in weighted_results
        ]

        # Analyze relevance
        relevance_analyses, relevance_metrics = self.relevance_analyzer.analyze_relevance(
            dict_results, req.query, req.context
        )

        # Format results
        ranked_results = [
            self._format_relevance_result(analysis, req.include_metadata)
            for analysis in relevance_analyses[:req.limit]
        ]

        metrics = {
            "algorithm": "relevance",
            "result_count": len(ranked_results),
            **relevance_metrics
        }

        return ranked_results, metrics

    def _format_weighted_result(self, result: WeightedResult, include_metadata: bool) -> Dict[str, Any]:
        """Format a weighted result for API response."""
        formatted = {
            "id": result.result_id,
            "score": result.final_score,
            "base_score": result.base_score,
            "factor_scores": result.factor_scores,
            "applied_boosts": result.applied_boosts,
            "type": result.metadata.get("type", "unknown"),
        }

        if include_metadata:
            formatted["metadata"] = result.metadata

        return formatted

    def _format_hierarchical_result(
        self,
        result: HierarchicalResult,
        include_metadata: bool
    ) -> Dict[str, Any]:
        """Format a hierarchical result for API response."""
        formatted = {
            "id": result.result.result_id,
            "score": result.tier_score,
            "tier": result.tier.value,
            "category": result.category,
            "rank_within_tier": result.rank_within_tier,
            "global_rank": result.global_rank,
            "type": result.result.get("type", "unknown"),
        }

        if include_metadata:
            formatted["metadata"] = result.result

        return formatted

    def _format_relevance_result(
        self,
        analysis: RelevanceAnalysis,
        include_metadata: bool
    ) -> Dict[str, Any]:
        """Format a relevance analysis result for API response."""
        formatted = {
            "id": analysis.result_id,
            "relevance_score": analysis.final_relevance_score,
            "quality_metrics": {
                "readability": analysis.quality_metrics.readability_score,
                "informativeness": analysis.quality_metrics.informativeness_score,
                "accuracy": analysis.quality_metrics.accuracy_score,
                "completeness": analysis.quality_metrics.completeness_score,
                "authority": analysis.quality_metrics.authority_score,
                "freshness": analysis.quality_metrics.freshness_score,
                "overall_quality": analysis.quality_metrics.overall_quality,
            },
            "keyword_matches": list(analysis.keyword_matches),
            "semantic_matches": list(analysis.semantic_matches),
            "context_relevance": analysis.context_relevance,
            "user_intent_match": analysis.user_intent_match,
            "content_authority": analysis.content_authority,
            "temporal_relevance": analysis.temporal_relevance,
        }

        return formatted

    def _format_response(
        self,
        results: List[Dict[str, Any]],
        req: RecommendationRequest,
        performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format the complete API response."""
        response = {
            "results": results,
            "metadata": {
                "query": req.query,
                "result_count": len(results),
                "ranking_algorithm": req.ranking_algorithm,
                "limit_requested": req.limit,
            },
            "performance": performance,
        }

        # Add hierarchy info if hierarchical ranking was used
        if req.ranking_algorithm == "hierarchical" and "tier_distribution" in performance.get("ranking", {}):
            response["hierarchy"] = performance["ranking"]["tier_distribution"]

        return response

    def _log_request(
        self,
        req: RecommendationRequest,
        response: Dict[str, Any],
        start_time: float
    ) -> None:
        """Log successful request."""
        self.request_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": req.query,
            "user_id": req.user_id,
            "ranking_algorithm": req.ranking_algorithm,
            "result_count": len(response.get("results", [])),
            "processing_time_ms": response.get("performance", {}).get("total_processing_time_ms", 0),
            "success": True,
        })

    def _log_request_error(
        self,
        request_data: Dict[str, Any],
        error: str,
        start_time: float
    ) -> None:
        """Log failed request."""
        self.request_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": request_data.get("query", ""),
            "error": error,
            "processing_time_ms": (time.time() - start_time) * 1000,
            "success": False,
        })

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get API performance statistics."""
        if not self.request_log:
            return {}

        recent_logs = self.request_log[-100:]

        successful_requests = [log for log in recent_logs if log["success"]]
        processing_times = [log["processing_time_ms"] for log in successful_requests]

        return {
            "total_requests": len(recent_logs),
            "successful_requests": len(successful_requests),
            "success_rate": len(successful_requests) / len(recent_logs) * 100,
            "avg_processing_time_ms": sum(processing_times) / len(processing_times) if processing_times else 0,
            "p95_processing_time_ms": sorted(processing_times)[int(len(processing_times) * 0.95)] if processing_times else 0,
            "avg_results_per_request": sum(log["result_count"] for log in successful_requests) / len(successful_requests) if successful_requests else 0,
        }


# Flask Blueprint for API integration
enhanced_recommendations_bp = Blueprint('enhanced_recommendations', __name__)

# Global API instance (would be initialized in app factory)
_api_instance: Optional[EnhancedRecommendationsAPI] = None

def init_enhanced_recommendations_api(workspace_path: str):
    """Initialize the enhanced recommendations API."""
    global _api_instance
    _api_instance = EnhancedRecommendationsAPI(workspace_path)

@enhanced_recommendations_bp.route('/api/v2/recommendations', methods=['POST'])
def get_recommendations():
    """Enhanced recommendations endpoint with weighted ranking."""
    if not _api_instance:
        return jsonify({"error": "API not initialized"}), 500

    try:
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "Missing 'query' parameter"}), 400

        response = _api_instance.get_recommendations(data)
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enhanced_recommendations_bp.route('/api/v2/recommendations/performance', methods=['GET'])
def get_performance_stats():
    """Get performance statistics for recommendations API."""
    if not _api_instance:
        return jsonify({"error": "API not initialized"}), 500

    stats = _api_instance.get_performance_stats()
    return jsonify(stats)

@enhanced_recommendations_bp.route('/api/v2/recommendations/search', methods=['GET'])
def search_recommendations():
    """Legacy search endpoint with enhanced ranking."""
    if not _api_instance:
        return jsonify({"error": "API not initialized"}), 500

    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Missing 'q' query parameter"}), 400

    # Convert GET request to internal format
    data = {
        "query": query,
        "limit": int(request.args.get('limit', 20)),
        "ranking_algorithm": request.args.get('algorithm', 'weighted'),
        "include_metadata": request.args.get('metadata', 'true').lower() == 'true',
    }

    try:
        response = _api_instance.get_recommendations(data)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
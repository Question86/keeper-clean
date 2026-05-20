# MODE: LIBRARY

"""
Advanced Search Engine - Metadata-Driven Search with AI Optimization

Core search functionality that enhances the existing KnowledgeDB with:
- Metadata-based query optimization
- Intelligent result ranking using breadcrumb insights
- Performance monitoring (<500ms response times)
- Semantic expansion with context awareness
- Quality scoring integration

Integrates with:
- knowledge_db.py for base search capabilities
- breadcrumb_trail.jsonl for usage patterns
- mega.md methodology for reference chain analysis
"""

from __future__ import annotations

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
import re

from knowledge_db import KnowledgeDB, SearchResult


@dataclass
class SearchMetrics:
    """Performance and quality metrics for search operations."""
    query_time_ms: float
    result_count: int
    cache_hit: bool
    semantic_expansions: int
    quality_score: float
    breadcrumb_boost: float


@dataclass
class EnhancedSearchResult:
    """Extended search result with metadata insights."""
    base_result: SearchResult
    breadcrumb_relevance: float
    metadata_score: float
    temporal_freshness: float
    reference_chain_depth: int
    combined_score: float


class AdvancedSearchEngine:
    """
    Advanced search engine with metadata-driven optimization.

    Enhances base KnowledgeDB search with:
    - Breadcrumb-based relevance scoring
    - Metadata quality assessment
    - Temporal freshness weighting
    - Reference chain analysis
    - Performance monitoring
    """

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.knowledge_db = KnowledgeDB(workspace_path)
        self.breadcrumb_cache = {}
        self.performance_log = []

        # Load breadcrumb insights on initialization
        self._load_breadcrumb_insights()

    def _load_breadcrumb_insights(self) -> None:
        """Load and analyze breadcrumb trail for search optimization."""
        breadcrumb_file = self.workspace / "breadcrumb_trail.jsonl"

        if not breadcrumb_file.exists():
            return

        # Analyze recent file access patterns
        recent_access = {}
        context_weights = {}

        try:
            with open(breadcrumb_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    entry = json.loads(line)
                    file_path = entry.get('target_file', '')
                    context = entry.get('source_context', 'unknown')
                    timestamp = entry.get('timestamp', '')

                    # Track recent access frequency
                    if file_path not in recent_access:
                        recent_access[file_path] = []
                    recent_access[file_path].append(timestamp)

                    # Track context relevance
                    if context not in context_weights:
                        context_weights[context] = 0
                    context_weights[context] += 1

        except (json.JSONDecodeError, FileNotFoundError):
            pass

        # Calculate access frequency scores
        current_time = datetime.now(timezone.utc)
        self.breadcrumb_scores = {}

        for file_path, timestamps in recent_access.items():
            # Calculate recency score (newer = higher)
            if timestamps:
                latest_access = max(timestamps)
                try:
                    access_time = datetime.fromisoformat(latest_access.replace('Z', '+00:00'))
                    hours_since_access = (current_time - access_time).total_seconds() / 3600
                    recency_score = max(0, 1 - (hours_since_access / 168))  # 7 days decay
                except ValueError:
                    recency_score = 0.1
            else:
                recency_score = 0.1

            # Calculate frequency score
            access_count = len(timestamps)
            frequency_score = min(1.0, access_count / 10)  # Cap at 10 accesses

            self.breadcrumb_scores[file_path] = {
                'recency': recency_score,
                'frequency': frequency_score,
                'combined': (recency_score + frequency_score) / 2
            }

    def search(
        self,
        query: str,
        *,
        types: Optional[List[str]] = None,
        task_id: Optional[str] = None,
        loop_min: Optional[int] = None,
        loop_max: Optional[int] = None,
        validation_passed: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 20,
        use_metadata_boost: bool = True,
        use_breadcrumb_boost: bool = True,
        use_temporal_boost: bool = True,
    ) -> Tuple[List[EnhancedSearchResult], SearchMetrics]:
        """
        Perform advanced search with metadata optimization.

        Args:
            query: Search query string
            types: Result types to include
            task_id: Filter by task ID
            loop_min/max: Loop number range
            validation_passed: Validation filter
            category: Category filter for lessons
            limit: Maximum results
            use_metadata_boost: Enable metadata-based scoring
            use_breadcrumb_boost: Enable breadcrumb relevance
            use_temporal_boost: Enable temporal freshness

        Returns:
            Tuple of (enhanced_results, performance_metrics)
        """
        start_time = time.time()

        # Get base results from KnowledgeDB
        base_results = self.knowledge_db.search(
            query=query,
            types=types,
            task_id=task_id,
            loop_min=loop_min,
            loop_max=loop_max,
            validation_passed=validation_passed,
            category=category,
            limit=limit * 2,  # Get more for re-ranking
            semantic=True,
            use_cache=True
        )

        # Check if results came from cache
        cache_hit = len(base_results) > 0 and hasattr(base_results[0], '_from_cache')

        # Enhance results with metadata insights
        enhanced_results = []
        total_quality_score = 0

        for result in base_results:
            enhanced = self._enhance_result(
                result,
                use_metadata_boost,
                use_breadcrumb_boost,
                use_temporal_boost
            )
            enhanced_results.append(enhanced)
            total_quality_score += enhanced.combined_score

        # Sort by combined score
        enhanced_results.sort(key=lambda x: x.combined_score, reverse=True)

        # Limit results
        enhanced_results = enhanced_results[:limit]

        # Calculate metrics
        query_time = (time.time() - start_time) * 1000
        avg_quality = total_quality_score / len(enhanced_results) if enhanced_results else 0

        # Estimate breadcrumb boost impact
        breadcrumb_boost = sum(r.breadcrumb_relevance for r in enhanced_results) / len(enhanced_results) if enhanced_results else 0

        metrics = SearchMetrics(
            query_time_ms=query_time,
            result_count=len(enhanced_results),
            cache_hit=cache_hit,
            semantic_expansions=1,  # Base semantic expansion
            quality_score=avg_quality,
            breadcrumb_boost=breadcrumb_boost
        )

        # Log performance
        self.performance_log.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'query': query,
            'metrics': {
                'query_time_ms': metrics.query_time_ms,
                'result_count': metrics.result_count,
                'cache_hit': metrics.cache_hit,
                'quality_score': metrics.quality_score
            }
        })

        return enhanced_results, metrics

    def _enhance_result(
        self,
        result: SearchResult,
        use_metadata: bool,
        use_breadcrumb: bool,
        use_temporal: bool
    ) -> EnhancedSearchResult:
        """Enhance a search result with metadata insights."""

        # Base relevance from KnowledgeDB
        base_score = result.relevance

        # Breadcrumb relevance
        breadcrumb_score = 0.0
        if use_breadcrumb and hasattr(result, 'context'):
            # Check if result relates to recently accessed files
            file_path = self._extract_file_path(result)
            if file_path and file_path in self.breadcrumb_scores:
                breadcrumb_score = self.breadcrumb_scores[file_path]['combined']

        # Metadata quality score
        metadata_score = 0.0
        if use_metadata and result.context:
            metadata_score = self._calculate_metadata_score(result.context)

        # Temporal freshness
        temporal_score = 0.0
        if use_temporal and result.context:
            temporal_score = self._calculate_temporal_score(result.context)

        # Reference chain depth (from mega.md methodology)
        chain_depth = self._calculate_reference_depth(result)

        # Combine scores with weights
        combined_score = (
            base_score * 0.5 +           # Base relevance (50%)
            breadcrumb_score * 0.2 +     # Breadcrumb boost (20%)
            metadata_score * 0.15 +      # Metadata quality (15%)
            temporal_score * 0.1 +       # Temporal freshness (10%)
            chain_depth * 0.05           # Reference depth (5%)
        )

        return EnhancedSearchResult(
            base_result=result,
            breadcrumb_relevance=breadcrumb_score,
            metadata_score=metadata_score,
            temporal_freshness=temporal_score,
            reference_chain_depth=chain_depth,
            combined_score=combined_score
        )

    def _extract_file_path(self, result: SearchResult) -> Optional[str]:
        """Extract file path from search result context."""
        if not result.context:
            return None

        # Try different context keys for file path
        for key in ['file_path', 'path', 'id']:
            if key in result.context and result.context[key]:
                return str(result.context[key])

        return None

    def _calculate_metadata_score(self, context: Dict[str, Any]) -> float:
        """Calculate metadata quality score."""
        score = 0.0
        max_score = 1.0

        # Validation passed bonus
        if context.get('validation_passed'):
            score += 0.3

        # Task focus bonus
        if context.get('task_focus'):
            score += 0.2

        # References count (mega.md requirement: min 5)
        references = context.get('references', [])
        if isinstance(references, list):
            ref_score = min(1.0, len(references) / 5)  # Cap at 5 references
            score += ref_score * 0.3

        # Evidence quality
        evidence = context.get('evidence', [])
        if isinstance(evidence, list) and evidence:
            score += 0.2

        return min(score, max_score)

    def _calculate_temporal_score(self, context: Dict[str, Any]) -> float:
        """Calculate temporal freshness score."""
        # Prefer recent content (higher loop numbers)
        loop_num = context.get('loop_num')
        if loop_num and isinstance(loop_num, int):
            # Normalize to 0-1 scale (assuming current loop ~100)
            return min(1.0, loop_num / 100)
        return 0.5  # Neutral score for unknown

    def _calculate_reference_depth(self, result: SearchResult) -> int:
        """Calculate reference chain depth using mega.md methodology."""
        if not result.context:
            return 0

        references = result.context.get('references', [])
        if isinstance(references, list):
            return len(references)
        return 0

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring."""
        if not self.performance_log:
            return {}

        recent_logs = self.performance_log[-100:]  # Last 100 queries

        return {
            'total_queries': len(recent_logs),
            'avg_query_time_ms': sum(log['metrics']['query_time_ms'] for log in recent_logs) / len(recent_logs),
            'cache_hit_rate': sum(1 for log in recent_logs if log['metrics']['cache_hit']) / len(recent_logs),
            'avg_quality_score': sum(log['metrics']['quality_score'] for log in recent_logs) / len(recent_logs),
            'p95_query_time': sorted([log['metrics']['query_time_ms'] for log in recent_logs])[int(len(recent_logs) * 0.95)]
        }

    def optimize_query(self, query: str) -> List[str]:
        """Generate optimized query variations for better results."""
        variations = [query]

        # Add semantic expansions
        if len(query.split()) > 1:
            # Add individual terms
            variations.extend(query.split())

        # Add common synonyms/abbreviations
        synonyms = {
            'test': ['testing', 'tests'],
            'error': ['exception', 'failure', 'bug'],
            'fix': ['resolve', 'correction', 'patch'],
            'api': ['interface', 'endpoint'],
            'config': ['configuration', 'settings']
        }

        for term, syns in synonyms.items():
            if term in query.lower():
                for syn in syns:
                    variations.append(query.replace(term, syn))

        return list(set(variations))  # Remove duplicates
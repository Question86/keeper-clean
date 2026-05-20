# MODE: LIBRARY

"""
Search Relevance Analyzer

Assesses content quality and relevance for search results.
Implements multi-dimensional quality scoring and content analysis.

Features:
- Content quality assessment
- Relevance scoring algorithms
- Semantic analysis integration
- Quality threshold management
- Performance metrics tracking
"""

from __future__ import annotations

import re
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collectiofrom search.weighting_engine import WeightedResult, WeightingFactor


@dataclass
class QualityMetrics:
    """Quality assessment metrics for content."""
    readability_score: float = 0.0
    informativeness_score: float = 0.0
    accuracy_score: float = 0.0
    completeness_score: float = 0.0
    relevance_score: float = 0.0
    authority_score: float = 0.0
    freshness_score: float = 0.0
    overall_quality: float = 0.0


@dataclass
class RelevanceAnalysis:
    """Comprehensive relevance analysis for a result."""
    result_id: str
    quality_metrics: QualityMetrics
    keyword_matches: Set[str] = field(default_factory=set)
    semantic_matches: Set[str] = field(default_factory=set)
    context_relevance: float = 0.0
    user_intent_match: float = 0.0
    content_authority: float = 0.0
    temporal_relevance: float = 0.0
    final_relevance_score: float = 0.0


@dataclass
class RelevanceConfig:
    """Configuration for relevance analysis."""
    quality_weights: Dict[str, float] = field(default_factory=dict)
    keyword_boost: float = 1.2
    semantic_boost: float = 1.15
    context_boost: float = 1.1
    authority_boost: float = 1.25
    min_content_length: int = 100
    max_content_length: int = 10000
    quality_threshold: float = 0.6

    def __post_init__(self):
        """Initialize default quality weights."""
        if not self.quality_weights:
            self.quality_weights = {
                "readability": 0.15,
                "informativeness": 0.25,
                "accuracy": 0.20,
                "completeness": 0.15,
                "relevance": 0.15,
                "authority": 0.05,
                "freshness": 0.05,
            }


class RelevanceAnalyzer:
    """
    Analyzes content relevance and quality for search results.

    Implements comprehensive quality assessment with multiple
    scoring dimensions and performance optimization.
    """

    def __init__(self, config: Optional[RelevanceConfig] = None):
        self.config = config or RelevanceConfig()
        self.performance_log: List[Dict[str, Any]] = []
        self._stop_words = self._load_stop_words()

    def _load_stop_words(self) -> Set[str]:
        """Load common stop words for text analysis."""
        return {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through", "during",
            "before", "after", "above", "below", "between", "among", "this", "that",
            "these", "those", "i", "me", "my", "myself", "we", "our", "ours", "you",
            "your", "yours", "he", "him", "his", "she", "her", "hers", "it", "its",
            "they", "them", "their", "theirs", "what", "which", "who", "when",
            "where", "why", "how", "all", "any", "both", "each", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "can", "will", "just", "should"
        }

    def analyze_relevance(
        self,
        results: List[WeightedResult],
        query: str,
        query_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[RelevanceAnalysis], Dict[str, Any]]:
        """
        Perform comprehensive relevance analysis on search results.

        Args:
            results: Weighted search results
            query: Original search query
            query_context: Additional query context

        Returns:
            Tuple of (analyses, performance_metrics)
        """
        start_time = time.time()

        # Parse query for analysis
        query_terms = self._parse_query(query)
        query_intent = self._analyze_query_intent(query, query_context)

        analyses = []
        total_quality_score = 0.0

        for result in results:
            analysis = self._analyze_single_result(
                result, query_terms, query_intent, query_context
            )
            analyses.append(analysis)
            total_quality_score += analysis.quality_metrics.overall_quality

        # Sort by final relevance score
        analyses.sort(key=lambda x: x.final_relevance_score, reverse=True)

        # Calculate performance metrics
        processing_time = (time.time() - start_time) * 1000
        avg_quality = total_quality_score / len(analyses) if analyses else 0
        relevance_improvement = self._calculate_relevance_improvement(analyses)

        metrics = {
            "processing_time_ms": processing_time,
            "result_count": len(analyses),
            "avg_quality_score": avg_quality,
            "relevance_improvement": relevance_improvement,
            "quality_threshold_met": avg_quality >= self.config.quality_threshold,
            "latency_target_met": processing_time < 50,
        }

        # Log performance
        self.performance_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "metrics": metrics,
        })

        return analyses, metrics

    def _analyze_single_result(
        self,
        result: WeightedResult,
        query_terms: Set[str],
        query_intent: Dict[str, Any],
        query_context: Optional[Dict[str, Any]]
    ) -> RelevanceAnalysis:
        """Analyze relevance for a single result."""
        content = self._extract_content(result)
        quality_metrics = self._assess_quality(content, result.metadata)

        # Keyword matching
        keyword_matches = self._find_keyword_matches(content, query_terms)

        # Semantic matching (simplified - would use embeddings in production)
        semantic_matches = self._find_semantic_matches(content, query_terms)

        # Context relevance
        context_relevance = self._calculate_context_relevance(
            result, query_context, query_intent
        )

        # User intent matching
        user_intent_match = self._calculate_intent_match(
            content, query_intent, result.metadata
        )

        # Content authority
        content_authority = self._assess_content_authority(result.metadata)

        # Temporal relevance
        temporal_relevance = self._calculate_temporal_relevance(result.metadata)

        # Calculate final relevance score
        final_score = self._combine_relevance_scores(
            quality_metrics.overall_quality,
            len(keyword_matches),
            len(semantic_matches),
            context_relevance,
            user_intent_match,
            content_authority,
            temporal_relevance
        )

        return RelevanceAnalysis(
            result_id=result.result_id,
            quality_metrics=quality_metrics,
            keyword_matches=keyword_matches,
            semantic_matches=semantic_matches,
            context_relevance=context_relevance,
            user_intent_match=user_intent_match,
            content_authority=content_authority,
            temporal_relevance=temporal_relevance,
            final_relevance_score=final_score
        )

    def _extract_content(self, result: WeightedResult) -> str:
        """Extract analyzable content from result."""
        metadata = result.metadata

        # Try different content fields
        content_sources = [
            metadata.get("content", ""),
            metadata.get("summary", ""),
            metadata.get("description", ""),
            metadata.get("title", ""),
        ]

        # Combine available content
        content_parts = [part for part in content_sources if part]
        return " ".join(content_parts)

    def _assess_quality(self, content: str, metadata: Dict[str, Any]) -> QualityMetrics:
        """Assess overall content quality."""
        metrics = QualityMetrics()

        # Readability score
        metrics.readability_score = self._calculate_readability(content)

        # Informativeness score
        metrics.informativeness_score = self._calculate_informativeness(content, metadata)

        # Accuracy score (based on validation status)
        metrics.accuracy_score = self._calculate_accuracy(metadata)

        # Completeness score
        metrics.completeness_score = self._calculate_completeness(content, metadata)

        # Relevance score (will be updated with query-specific analysis)
        metrics.relevance_score = 0.5  # Placeholder

        # Authority score
        metrics.authority_score = self._calculate_authority(metadata)

        # Freshness score
        metrics.freshness_score = self._calculate_freshness(metadata)

        # Overall quality (weighted combination)
        metrics.overall_quality = sum(
            getattr(metrics, f"{key}_score") * weight
            for key, weight in self.config.quality_weights.items()
        )

        return metrics

    def _calculate_readability(self, content: str) -> float:
        """Calculate readability score based on text complexity."""
        if not content:
            return 0.0

        words = content.split()
        sentences = re.split(r'[.!?]+', content)

        if not words or not sentences:
            return 0.0

        avg_words_per_sentence = len(words) / len(sentences)
        avg_syllables_per_word = sum(self._count_syllables(word) for word in words) / len(words)

        # Simplified Flesch Reading Ease
        # Score = 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
        readability = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word

        # Normalize to 0-1 scale
        return max(0.0, min(1.0, readability / 100))

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified)."""
        word = word.lower()
        count = 0
        vowels = "aeiouy"

        if word[0] in vowels:
            count += 1

        for i in range(1, len(word)):
            if word[i] in vowels and word[i - 1] not in vowels:
                count += 1

        if word.endswith("e"):
            count -= 1

        return max(1, count)

    def _calculate_informativeness(self, content: str, metadata: Dict[str, Any]) -> float:
        """Calculate informativeness based on content density and structure."""
        if not content:
            return 0.0

        # Content length score
        length_score = min(1.0, len(content) / self.config.min_content_length)

        # Structure indicators
        has_sections = bool(re.search(r'^#+\s', content, re.MULTILINE))
        has_lists = bool(re.search(r'^[\s]*[-\*\+]\s', content, re.MULTILINE))
        has_code = bool(re.search(r'```', content))

        structure_score = (has_sections + has_lists + has_code) / 3

        # Keyword density (unique non-stop words)
        words = [w.lower() for w in re.findall(r'\b\w+\b', content)]
        filtered_words = [w for w in words if w not in self._stop_words]
        unique_ratio = len(set(filtered_words)) / len(filtered_words) if filtered_words else 0

        return (length_score + structure_score + unique_ratio) / 3

    def _calculate_accuracy(self, metadata: Dict[str, Any]) -> float:
        """Calculate accuracy based on validation and verification status."""
        if metadata.get("validation_passed"):
            return 1.0
        elif metadata.get("validation_failed"):
            return 0.0
        elif metadata.get("verified"):
            return 0.9
        elif metadata.get("citations") or metadata.get("references"):
            return 0.7
        else:
            return 0.5  # Unknown accuracy

    def _calculate_completeness(self, content: str, metadata: Dict[str, Any]) -> float:
        """Calculate completeness based on content coverage."""
        completeness_indicators = 0
        total_indicators = 5

        # Has introduction/conclusion
        if re.search(r'\b(introduction|overview|summary|conclusion)\b', content, re.IGNORECASE):
            completeness_indicators += 1

        # Has references
        if metadata.get("references") or re.search(r'\b(references?|citations?)\b', content, re.IGNORECASE):
            completeness_indicators += 1

        # Has examples
        if re.search(r'\b(example|sample|instance)\b', content, re.IGNORECASE):
            completeness_indicators += 1

        # Has metadata
        if metadata.get("author") or metadata.get("created_at"):
            completeness_indicators += 1

        # Appropriate length
        if self.config.min_content_length <= len(content) <= self.config.max_content_length:
            completeness_indicators += 1

        return completeness_indicators / total_indicators

    def _calculate_authority(self, metadata: Dict[str, Any]) -> float:
        """Calculate content authority."""
        authority_score = 0.0

        # Author reputation (simplified)
        if metadata.get("author"):
            authority_score += 0.3

        # References/citations
        references = metadata.get("references", [])
        citations = metadata.get("citations", [])
        ref_score = min(1.0, (len(references) + len(citations)) / 10)
        authority_score += ref_score * 0.4

        # Validation status
        if metadata.get("validation_passed"):
            authority_score += 0.3

        return min(1.0, authority_score)

    def _calculate_freshness(self, metadata: Dict[str, Any]) -> float:
        """Calculate content freshness."""
        timestamp = metadata.get("timestamp") or metadata.get("created_at") or metadata.get("updated_at")

        if not timestamp:
            return 0.5

        try:
            if isinstance(timestamp, str):
                content_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                content_date = timestamp

            current_time = datetime.now(timezone.utc)
            days_old = (current_time - content_date).total_seconds() / (24 * 3600)

            # Exponential decay over 365 days
            import math
            return math.exp(-days_old / 365)
        except (ValueError, TypeError):
            return 0.5

    def _parse_query(self, query: str) -> Set[str]:
        """Parse query into searchable terms."""
        # Remove punctuation and split
        words = re.findall(r'\b\w+\b', query.lower())

        # Remove stop words
        filtered_words = {word for word in words if word not in self._stop_words}

        return filtered_words

    def _analyze_query_intent(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the intent behind the query."""
        intent = {
            "type": "general",
            "focus": "content",
            "complexity": "simple",
            "domain": "general"
        }

        query_lower = query.lower()

        # Determine query type
        if any(word in query_lower for word in ["how", "what", "why", "when", "where", "who"]):
            intent["type"] = "question"
        elif "task" in query_lower or "report" in query_lower:
            intent["type"] = "task"
        elif "code" in query_lower or "script" in query_lower:
            intent["type"] = "code"
        elif "analyze" in query_lower or "analysis" in query_lower:
            intent["type"] = "analysis"

        # Determine complexity
        word_count = len(query.split())
        if word_count > 10:
            intent["complexity"] = "complex"
        elif word_count > 5:
            intent["complexity"] = "medium"

        return intent

    def _find_keyword_matches(self, content: str, query_terms: Set[str]) -> Set[str]:
        """Find exact keyword matches in content."""
        content_lower = content.lower()
        matches = set()

        for term in query_terms:
            if term in content_lower:
                matches.add(term)

        return matches

    def _find_semantic_matches(self, content: str, query_terms: Set[str]) -> Set[str]:
        """Find semantic matches (simplified - would use embeddings)."""
        # For now, just return keyword matches
        # In production, this would use word embeddings or semantic similarity
        return self._find_keyword_matches(content, query_terms)

    def _calculate_context_relevance(
        self,
        result: WeightedResult,
        query_context: Optional[Dict[str, Any]],
        query_intent: Dict[str, Any]
    ) -> float:
        """Calculate context relevance score."""
        if not query_context:
            return 0.5

        metadata = result.metadata
        relevance_score = 0.0

        # Match query intent with content type
        content_type = metadata.get("type", "").lower()
        intent_type = query_intent.get("type", "general")

        if intent_type == "task" and ("task" in content_type or "report" in content_type):
            relevance_score += 0.4
        elif intent_type == "code" and ("code" in content_type or "script" in content_type):
            relevance_score += 0.4
        elif intent_type == "analysis" and "analysis" in content_type:
            relevance_score += 0.4

        # Check for contextual keywords
        context_keywords = query_context.get("keywords", [])
        content_text = self._extract_content(result).lower()

        keyword_matches = sum(1 for keyword in context_keywords if keyword.lower() in content_text)
        relevance_score += min(0.6, keyword_matches / len(context_keywords)) if context_keywords else 0

        return min(1.0, relevance_score)

    def _calculate_intent_match(
        self,
        content: str,
        query_intent: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> float:
        """Calculate how well content matches user intent."""
        intent_type = query_intent.get("type", "general")
        content_lower = content.lower()

        # Simple intent matching
        if intent_type == "question":
            # Look for explanatory content
            if any(word in content_lower for word in ["because", "therefore", "however", "although"]):
                return 0.8
        elif intent_type == "task":
            # Look for task-related content
            if "task" in content_lower or metadata.get("task_id"):
                return 0.9
        elif intent_type == "code":
            # Look for code content
            if "```" in content or "def " in content:
                return 0.9

        return 0.5  # Neutral match

    def _assess_content_authority(self, metadata: Dict[str, Any]) -> float:
        """Assess content authority (alias for _calculate_authority)."""
        return self._calculate_authority(metadata)

    def _calculate_temporal_relevance(self, metadata: Dict[str, Any]) -> float:
        """Calculate temporal relevance (alias for _calculate_freshness)."""
        return self._calculate_freshness(metadata)

    def _combine_relevance_scores(
        self,
        quality_score: float,
        keyword_count: int,
        semantic_count: int,
        context_relevance: float,
        intent_match: float,
        authority: float,
        temporal: float
    ) -> float:
        """Combine all relevance scores into final score."""
        # Base quality score
        final_score = quality_score * 0.3

        # Keyword matching (boosted)
        keyword_score = min(1.0, keyword_count / 5) * self.config.keyword_boost
        final_score += keyword_score * 0.25

        # Semantic matching (boosted)
        semantic_score = min(1.0, semantic_count / 5) * self.config.semantic_boost
        final_score += semantic_score * 0.15

        # Context relevance (boosted)
        final_score += context_relevance * self.config.context_boost * 0.15

        # Intent matching
        final_score += intent_match * 0.1

        # Authority (boosted)
        final_score += authority * self.config.authority_boost * 0.05

        return min(1.0, final_score)

    def _calculate_relevance_improvement(self, analyses: List[RelevanceAnalysis]) -> float:
        """Calculate overall relevance improvement from analysis."""
        if not analyses:
            return 1.0

        # Compare quality scores to baseline (0.5)
        baseline_scores = [0.5] * len(analyses)
        actual_scores = [a.final_relevance_score for a in analyses]

        baseline_avg = sum(baseline_scores) / len(baseline_scores)
        actual_avg = sum(actual_scores) / len(actual_scores)

        return actual_avg / baseline_avg if baseline_avg > 0 else 1.0

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.performance_log:
            return {}

        recent_logs = self.performance_log[-100:]

        processing_times = [log["metrics"]["processing_time_ms"] for log in recent_logs]
        quality_scores = [log["metrics"]["avg_quality_score"] for log in recent_logs]
        improvements = [log["metrics"]["relevance_improvement"] for log in recent_logs]

        return {
            "total_operations": len(recent_logs),
            "avg_processing_time_ms": sum(processing_times) / len(processing_times),
            "p95_processing_time_ms": sorted(processing_times)[int(len(processing_times) * 0.95)],
            "avg_quality_score": sum(quality_scores) / len(quality_scores),
            "avg_relevance_improvement": sum(improvements) / len(improvements),
            "quality_threshold_met_percent": sum(1 for log in recent_logs if log["metrics"]["quality_threshold_met"]) / len(recent_logs) * 100,
            "latency_target_met_percent": sum(1 for log in recent_logs if log["metrics"]["latency_target_met"]) / len(recent_logs) * 100,
        }
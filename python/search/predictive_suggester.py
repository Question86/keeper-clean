# MODE: LIBRARY

"""
Predictive Suggester - AI-Powered Search Prediction System

Provides intelligent search suggestions based on:
- Query pattern analysis
- User behavior prediction
- Context-aware recommendations
- Collaborative filtering from breadcrumb trails
- Machine learning on search patterns

Integrates with Copilot LLM for enhanced suggestions.
"""

from __future__ import annotations

import json
import re
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
import math
import random

from advanced_search_engine import AdvancedSearchEngine
from intelligent_tagger import IntelligentTagger


@dataclass
class SearchSuggestion:
    """A search suggestion with confidence and metadata."""
    query: str
    confidence: float
    source: str  # 'pattern', 'context', 'collaborative', 'ai'
    category: str  # 'completion', 'related', 'popular', 'trending'
    metadata: Dict[str, Any]


@dataclass
class UserContext:
    """User context for personalized suggestions."""
    recent_queries: List[str]
    current_file: Optional[str]
    current_task: Optional[str]
    session_start: datetime
    preferences: Dict[str, Any]


class PredictiveSuggester:
    """
    AI-powered search prediction and suggestion system.

    Analyzes user behavior, query patterns, and context to provide
    intelligent search suggestions and query completions.
    """

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.search_engine = AdvancedSearchEngine(workspace_path)
        self.tagger = IntelligentTagger(workspace_path)

        # Pattern analysis data
        self.query_patterns = defaultdict(list)
        self.query_transitions = defaultdict(lambda: defaultdict(int))
        self.popular_queries = Counter()
        self.context_suggestions = defaultdict(list)

        # User session tracking
        self.current_context: Optional[UserContext] = None

        # Load historical data
        self._load_historical_patterns()

    def _load_historical_patterns(self) -> None:
        """Load historical search patterns from logs."""
        # Try to load from breadcrumb trail
        breadcrumb_file = self.workspace / "breadcrumb_trail.jsonl"

        if breadcrumb_file.exists():
            try:
                with open(breadcrumb_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue

                        entry = json.loads(line)
                        operation = entry.get('operation', '')
                        metadata = entry.get('metadata', {})

                        # Look for search operations
                        if operation == 'search' and 'query' in metadata:
                            query = metadata['query']
                            self.popular_queries[query] += 1

                            # Analyze query patterns
                            self._analyze_query_pattern(query)

            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # Load from any existing search logs
        search_log_file = self.workspace / "search_patterns.jsonl"
        if search_log_file.exists():
            try:
                with open(search_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue

                        entry = json.loads(line)
                        query = entry.get('query', '')
                        if query:
                            self.popular_queries[query] += 1
                            self._analyze_query_pattern(query)

            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def _analyze_query_pattern(self, query: str) -> None:
        """Analyze a query for patterns and transitions."""
        words = query.lower().split()

        if len(words) > 1:
            # Store word transitions
            for i in range(len(words) - 1):
                self.query_transitions[words[i]][words[i + 1]] += 1

        # Store query patterns by length
        query_length = len(words)
        self.query_patterns[query_length].append(query)

    def start_session(self, user_id: str = "default", current_file: Optional[str] = None) -> None:
        """Start a new user session for context tracking."""
        self.current_context = UserContext(
            recent_queries=[],
            current_file=current_file,
            current_task=self._infer_current_task(current_file),
            session_start=datetime.now(timezone.utc),
            preferences={}
        )

    def get_suggestions(
        self,
        partial_query: str,
        max_suggestions: int = 10,
        include_ai: bool = True
    ) -> List[SearchSuggestion]:
        """
        Get search suggestions based on partial query and context.

        Args:
            partial_query: Current partial search query
            max_suggestions: Maximum number of suggestions to return
            include_ai: Whether to include AI-powered suggestions

        Returns:
            List of search suggestions ordered by confidence
        """
        suggestions = []

        # Query completion suggestions
        suggestions.extend(self._get_completion_suggestions(partial_query))

        # Context-based suggestions
        suggestions.extend(self._get_context_suggestions(partial_query))

        # Popular query suggestions
        suggestions.extend(self._get_popular_suggestions(partial_query))

        # Related term suggestions
        suggestions.extend(self._get_related_suggestions(partial_query))

        if include_ai:
            # AI-powered suggestions
            suggestions.extend(self._get_ai_suggestions(partial_query))

        # Sort by confidence and limit
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:max_suggestions]

    def _get_completion_suggestions(self, partial: str) -> List[SearchSuggestion]:
        """Get query completion suggestions."""
        suggestions = []

        if not partial:
            return suggestions

        partial_lower = partial.lower()

        # Find queries that start with the partial query
        for query, count in self.popular_queries.items():
            if query.lower().startswith(partial_lower) and query.lower() != partial_lower:
                confidence = min(1.0, count / 10)  # Normalize by frequency
                suggestions.append(SearchSuggestion(
                    query=query,
                    confidence=confidence,
                    source='pattern',
                    category='completion',
                    metadata={'frequency': count}
                ))

        # Word-level completions using transition probabilities
        words = partial.split()
        if words:
            last_word = words[-1].lower()
            if last_word in self.query_transitions:
                transitions = self.query_transitions[last_word]
                total_transitions = sum(transitions.values())

                for next_word, count in transitions.items():
                    probability = count / total_transitions
                    completed_query = partial + " " + next_word

                    suggestions.append(SearchSuggestion(
                        query=completed_query,
                        confidence=probability * 0.8,  # Slightly lower confidence
                        source='pattern',
                        category='completion',
                        metadata={'transition_prob': probability}
                    ))

        return suggestions

    def _get_context_suggestions(self, partial: str) -> List[SearchSuggestion]:
        """Get context-aware suggestions based on current user context."""
        suggestions = []

        if not self.current_context:
            return suggestions

        # File-based context suggestions
        if self.current_context.current_file:
            file_suggestions = self._get_file_context_suggestions(
                self.current_context.current_file, partial
            )
            suggestions.extend(file_suggestions)

        # Task-based context suggestions
        if self.current_context.current_task:
            task_suggestions = self._get_task_context_suggestions(
                self.current_context.current_task, partial
            )
            suggestions.extend(task_suggestions)

        # Recent query-based suggestions
        if self.current_context.recent_queries:
            recent_suggestions = self._get_recent_query_suggestions(
                self.current_context.recent_queries, partial
            )
            suggestions.extend(recent_suggestions)

        return suggestions

    def _get_file_context_suggestions(self, file_path: str, partial: str) -> List[SearchSuggestion]:
        """Get suggestions based on current file context."""
        suggestions = []

        try:
            # Get tags for current file
            file_tags = self.tagger.generate_tags_for_file(file_path)

            # Suggest searches related to file tags
            for tag_metadata in file_tags.tags:
                if tag_metadata.confidence > 0.6:
                    tag_parts = tag_metadata.tag.split(':')
                    if len(tag_parts) > 1:
                        category, value = tag_parts
                        suggestion_query = f"{category}:{value}"

                        if partial.lower() in suggestion_query.lower():
                            suggestions.append(SearchSuggestion(
                                query=suggestion_query,
                                confidence=tag_metadata.confidence * 0.7,
                                source='context',
                                category='related',
                                metadata={'file': file_path, 'tag': tag_metadata.tag}
                            ))

        except Exception:
            pass  # Skip if file analysis fails

        return suggestions

    def _get_task_context_suggestions(self, task_id: str, partial: str) -> List[SearchSuggestion]:
        """Get suggestions based on current task context."""
        suggestions = []

        # Common task-related searches
        task_patterns = {
            'analysis': ['validation', 'metrics', 'performance', 'quality'],
            'implementation': ['code', 'function', 'class', 'api'],
            'testing': ['test', 'validation', 'error', 'debug'],
            'documentation': ['report', 'readme', 'guide', 'api']
        }

        for pattern, related_terms in task_patterns.items():
            if pattern in task_id.lower():
                for term in related_terms:
                    suggestion = f"{term} {task_id}"
                    if partial.lower() in suggestion.lower():
                        suggestions.append(SearchSuggestion(
                            query=suggestion,
                            confidence=0.6,
                            source='context',
                            category='related',
                            metadata={'task': task_id, 'pattern': pattern}
                        ))

        return suggestions

    def _get_recent_query_suggestions(self, recent_queries: List[str], partial: str) -> List[SearchSuggestion]:
        """Get suggestions based on recent query history."""
        suggestions = []

        for query in recent_queries[-5:]:  # Last 5 queries
            if partial.lower() in query.lower() and query.lower() != partial.lower():
                suggestions.append(SearchSuggestion(
                    query=query,
                    confidence=0.5,  # Lower confidence for history
                    source='context',
                    category='related',
                    metadata={'from_history': True}
                ))

        return suggestions

    def _get_popular_suggestions(self, partial: str) -> List[SearchSuggestion]:
        """Get suggestions from popular queries."""
        suggestions = []

        # Get top popular queries
        top_queries = self.popular_queries.most_common(20)

        for query, count in top_queries:
            if not partial or partial.lower() in query.lower():
                confidence = min(1.0, count / 20)  # Normalize
                suggestions.append(SearchSuggestion(
                    query=query,
                    confidence=confidence,
                    source='collaborative',
                    category='popular',
                    metadata={'frequency': count}
                ))

        return suggestions

    def _get_related_suggestions(self, partial: str) -> List[SearchSuggestion]:
        """Get suggestions for related terms and synonyms."""
        suggestions = []

        # Simple synonym expansion
        synonyms = {
            'test': ['testing', 'tests', 'validation'],
            'error': ['exception', 'failure', 'bug', 'issue'],
            'fix': ['resolve', 'correction', 'patch', 'solution'],
            'api': ['interface', 'endpoint', 'service'],
            'config': ['configuration', 'settings', 'setup'],
            'search': ['find', 'query', 'lookup'],
            'analysis': ['analyze', 'examine', 'review']
        }

        words = partial.lower().split()
        for word in words:
            if word in synonyms:
                for synonym in synonyms[word]:
                    # Replace the word with synonym
                    new_query = partial.replace(word, synonym)
                    if new_query != partial:
                        suggestions.append(SearchSuggestion(
                            query=new_query,
                            confidence=0.4,
                            source='pattern',
                            category='related',
                            metadata={'synonym_for': word, 'synonym': synonym}
                        ))

        return suggestions

    def _get_ai_suggestions(self, partial: str) -> List[SearchSuggestion]:
        """Get AI-powered suggestions (placeholder for Copilot integration)."""
        suggestions = []

        # For now, provide rule-based AI-like suggestions
        # In a real implementation, this would call Copilot LLM

        if len(partial.split()) == 1:
            # Single word - suggest combinations
            ai_combinations = [
                f"{partial} implementation",
                f"{partial} analysis",
                f"{partial} testing",
                f"how to {partial}",
                f"{partial} best practices"
            ]

            for combo in ai_combinations:
                suggestions.append(SearchSuggestion(
                    query=combo,
                    confidence=0.3,  # Lower confidence for AI suggestions
                    source='ai',
                    category='related',
                    metadata={'ai_generated': True}
                ))

        return suggestions

    def record_query(self, query: str) -> None:
        """Record a completed search query for learning."""
        if not query.strip():
            return

        # Update popular queries
        self.popular_queries[query] += 1

        # Update context if session active
        if self.current_context:
            self.current_context.recent_queries.append(query)
            # Keep only last 10 queries
            self.current_context.recent_queries = self.current_context.recent_queries[-10:]

        # Analyze pattern
        self._analyze_query_pattern(query)

        # Save to log file
        self._save_query_to_log(query)

    def _save_query_to_log(self, query: str) -> None:
        """Save query to persistent log."""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'query': query,
            'session_id': 'default',
            'context': {
                'file': self.current_context.current_file if self.current_context else None,
                'task': self.current_context.current_task if self.current_context else None
            }
        }

        try:
            with open(self.workspace / "search_patterns.jsonl", 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except IOError:
            pass  # Skip if can't write log

    def _infer_current_task(self, file_path: Optional[str]) -> Optional[str]:
        """Infer current task from file path."""
        if not file_path:
            return None

        # Extract task ID from file name
        if 'task_' in file_path:
            match = re.search(r'task_(\w+)', file_path)
            if match:
                return match.group(1)

        return None

    def get_trending_queries(self, hours: int = 24) -> List[Tuple[str, int]]:
        """Get trending queries from recent history."""
        # For now, return overall popular queries
        # In a real implementation, this would filter by time window
        return self.popular_queries.most_common(10)

    def get_query_suggestions_for_file(self, file_path: str) -> List[str]:
        """Get suggested queries specifically for a file."""
        try:
            file_tags = self.tagger.generate_tags_for_file(file_path)
            suggestions = []

            for tag in file_tags.tags:
                if tag.confidence > 0.5:
                    suggestions.append(f"tag:{tag.tag}")

            # Add file-specific suggestions
            if 'report' in file_path:
                suggestions.extend(['validation', 'references', 'evidence'])
            elif 'task' in file_path:
                suggestions.extend(['implementation', 'requirements', 'status'])
            elif '.py' in file_path:
                suggestions.extend(['function', 'class', 'import'])

            return suggestions[:5]  # Limit to 5

        except Exception:
            return []

    def optimize_suggestions(self, user_feedback: Dict[str, Any]) -> None:
        """Optimize suggestions based on user feedback."""
        # Placeholder for machine learning optimization
        # Would update confidence scores based on user selections
        pass
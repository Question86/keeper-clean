#!/usr/bin/env python3
"""
Breadcrumb Scanner - Copilot Activity Pattern Analysis

Analyzes breadcrumb trails to detect knowledge gaps and learning opportunities.
Part of TASK_0185: Autonomous Knowledge Gathering and Database Integration System.
"""

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass

from knowledge_db import KnowledgeDB

@dataclass
class ActivityPattern:
    """Represents a detected activity pattern."""
    pattern_type: str  # 'repeated_search', 'error_sequence', 'complex_task'
    frequency: int
    topics: List[str]
    confidence: float
    last_seen: str
    context: Dict[str, Any]

@dataclass
class KnowledgeGap:
    """Represents a detected knowledge gap."""
    topic: str
    confidence: float
    sources: List[str]
    priority: str  # 'high', 'medium', 'low'
    detected_at: str
    search_queries: List[str]

class BreadcrumbScanner:
    """
    Analyzes breadcrumb trails to detect knowledge gaps and learning patterns.

    Scans for:
    - Repeated searches for similar topics
    - Error sequences indicating missing knowledge
    - Complex tasks requiring external research
    - Time spent on unfamiliar domains
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.breadcrumb_file = workspace_root / 'breadcrumb_trail.jsonl'
        self.knowledge_db = KnowledgeDB(workspace_root)

        # Pattern detection thresholds
        self.min_repeated_searches = 3
        self.min_error_sequence = 2
        self.max_time_threshold = 3600  # 1 hour on similar topics
        self.confidence_threshold = 0.6

    def scan_for_gaps(self) -> List[KnowledgeGap]:
        """
        Scan breadcrumb trail for knowledge gaps.

        Returns list of detected knowledge gaps with confidence scores.
        """
        if not self.breadcrumb_file.exists():
            return []

        # Load recent breadcrumbs (last 24 hours)
        breadcrumbs = self._load_recent_breadcrumbs(hours=24)

        if not breadcrumbs:
            return []

        # Analyze patterns
        patterns = self._analyze_patterns(breadcrumbs)

        # Convert patterns to knowledge gaps
        gaps = []
        for pattern in patterns:
            gap = self._pattern_to_gap(pattern)
            if gap:
                gaps.append(gap)

        # Sort by priority and confidence
        gaps.sort(key=lambda g: (self._priority_score(g.priority), g.confidence), reverse=True)

        return gaps

    def _load_recent_breadcrumbs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Load breadcrumbs from the last N hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        breadcrumbs = []

        try:
            with open(self.breadcrumb_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line.strip())
                        timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                        if timestamp >= cutoff_time:
                            breadcrumbs.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception as e:
            print(f"Error loading breadcrumbs: {e}")

        return breadcrumbs

    def _analyze_patterns(self, breadcrumbs: List[Dict[str, Any]]) -> List[ActivityPattern]:
        """Analyze breadcrumbs for knowledge gap patterns."""
        patterns = []

        # Pattern 1: Repeated searches for similar topics
        search_patterns = self._detect_repeated_searches(breadcrumbs)
        patterns.extend(search_patterns)

        # Pattern 2: Error sequences
        error_patterns = self._detect_error_sequences(breadcrumbs)
        patterns.extend(error_patterns)

        # Pattern 3: Complex task indicators
        complex_patterns = self._detect_complex_tasks(breadcrumbs)
        patterns.extend(complex_patterns)

        # Pattern 4: Time-intensive unfamiliar topics
        time_patterns = self._detect_time_intensive_topics(breadcrumbs)
        patterns.extend(time_patterns)

        return patterns

    def _detect_repeated_searches(self, breadcrumbs: List[Dict[str, Any]]) -> List[ActivityPattern]:
        """Detect repeated searches indicating knowledge gaps."""
        patterns = []

        # Group by similar search terms
        search_terms = defaultdict(list)
        for crumb in breadcrumbs:
            if 'search' in crumb.get('operation', '').lower() or 'query' in crumb.get('metadata', {}):
                # Extract search terms from file names or metadata
                term = self._extract_search_term(crumb)
                if term:
                    search_terms[term].append(crumb)

        # Find repeated searches
        for term, crumbs in search_terms.items():
            if len(crumbs) >= self.min_repeated_searches:
                # Calculate time span
                timestamps = [datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00'))
                            for c in crumbs]
                time_span = max(timestamps) - min(timestamps)

                # High confidence if searches span significant time
                confidence = min(1.0, len(crumbs) / 10.0 + (time_span.total_seconds() / 86400))

                if confidence >= self.confidence_threshold:
                    pattern = ActivityPattern(
                        pattern_type='repeated_search',
                        frequency=len(crumbs),
                        topics=[term],
                        confidence=confidence,
                        last_seen=max(c['timestamp'] for c in crumbs),
                        context={
                            'time_span_hours': time_span.total_seconds() / 3600,
                            'search_term': term,
                            'file_count': len(set(c.get('target_file', '') for c in crumbs))
                        }
                    )
                    patterns.append(pattern)

        return patterns

    def _detect_error_sequences(self, breadcrumbs: List[Dict[str, Any]]) -> List[ActivityPattern]:
        """Detect sequences of errors indicating missing knowledge."""
        patterns = []

        # Look for error-related files and operations
        error_crumbs = [c for c in breadcrumbs if self._is_error_related(c)]

        if len(error_crumbs) >= self.min_error_sequence:
            # Group by topic/context
            error_topics = defaultdict(list)
            for crumb in error_crumbs:
                topic = self._extract_error_topic(crumb)
                if topic:
                    error_topics[topic].append(crumb)

            for topic, crumbs in error_topics.items():
                if len(crumbs) >= self.min_error_sequence:
                    confidence = min(1.0, len(crumbs) / 5.0)

                    pattern = ActivityPattern(
                        pattern_type='error_sequence',
                        frequency=len(crumbs),
                        topics=[topic],
                        confidence=confidence,
                        last_seen=max(c['timestamp'] for c in crumbs),
                        context={
                            'error_files': [c.get('target_file', '') for c in crumbs],
                            'error_types': list(set(self._extract_error_type(c) for c in crumbs))
                        }
                    )
                    patterns.append(pattern)

        return patterns

    def _detect_complex_tasks(self, breadcrumbs: List[Dict[str, Any]]) -> List[ActivityPattern]:
        """Detect complex tasks requiring external knowledge."""
        patterns = []

        # Look for indicators of complex work
        complex_indicators = [
            'research', 'analysis', 'design', 'architecture',
            'optimization', 'debugging', 'testing'
        ]

        complex_crumbs = []
        for crumb in breadcrumbs:
            file_name = crumb.get('target_file', '').lower()
            context = crumb.get('source_context', '').lower()

            if any(indicator in file_name or indicator in context for indicator in complex_indicators):
                complex_crumbs.append(crumb)

        # Group by topic
        topic_groups = defaultdict(list)
        for crumb in complex_crumbs:
            topic = self._extract_topic(crumb)
            if topic:
                topic_groups[topic].append(crumb)

        for topic, crumbs in topic_groups.items():
            if len(crumbs) >= 5:  # Significant activity
                confidence = min(1.0, len(crumbs) / 20.0)

                pattern = ActivityPattern(
                    pattern_type='complex_task',
                    frequency=len(crumbs),
                    topics=[topic],
                    confidence=confidence,
                    last_seen=max(c['timestamp'] for c in crumbs),
                    context={
                        'activity_count': len(crumbs),
                        'file_types': list(set(Path(c.get('target_file', '')).suffix for c in crumbs))
                    }
                )
                patterns.append(pattern)

        return patterns

    def _detect_time_intensive_topics(self, breadcrumbs: List[Dict[str, Any]]) -> List[ActivityPattern]:
        """Detect topics requiring significant time investment."""
        patterns = []

        # Group by time periods and topics
        time_windows = defaultdict(lambda: defaultdict(list))

        for crumb in breadcrumbs:
            timestamp = datetime.fromisoformat(crumb['timestamp'].replace('Z', '+00:00'))
            hour_window = timestamp.replace(minute=0, second=0, microsecond=0)
            topic = self._extract_topic(crumb)
            if topic:
                time_windows[hour_window][topic].append(crumb)

        # Find topics with high activity in time windows
        for window, topics in time_windows.items():
            for topic, crumbs in topics.items():
                if len(crumbs) >= 10:  # High activity in one hour
                    confidence = min(1.0, len(crumbs) / 30.0)

                    pattern = ActivityPattern(
                        pattern_type='time_intensive',
                        frequency=len(crumbs),
                        topics=[topic],
                        confidence=confidence,
                        last_seen=max(c['timestamp'] for c in crumbs),
                        context={
                            'time_window': window.isoformat(),
                            'activity_rate': len(crumbs) / 3600  # per second
                        }
                    )
                    patterns.append(pattern)

        return patterns

    def _pattern_to_gap(self, pattern: ActivityPattern) -> Optional[KnowledgeGap]:
        """Convert an activity pattern to a knowledge gap."""
        if pattern.confidence < self.confidence_threshold:
            return None

        # Determine priority based on pattern type and confidence
        if pattern.pattern_type == 'error_sequence' and pattern.confidence > 0.8:
            priority = 'high'
        elif pattern.confidence > 0.9:
            priority = 'high'
        elif pattern.confidence > 0.7:
            priority = 'medium'
        else:
            priority = 'low'

        # Generate search queries based on topics
        search_queries = []
        for topic in pattern.topics:
            # Clean and format topic for search
            clean_topic = re.sub(r'[^\w\s]', ' ', topic).strip()
            if clean_topic:
                search_queries.append(f"{clean_topic} tutorial")
                search_queries.append(f"{clean_topic} best practices")
                search_queries.append(f"{clean_topic} examples")

        if not search_queries:
            return None

        gap = KnowledgeGap(
            topic=pattern.topics[0],  # Primary topic
            confidence=pattern.confidence,
            sources=[f"breadcrumb_{pattern.pattern_type}"],
            priority=priority,
            detected_at=datetime.now(timezone.utc).isoformat(),
            search_queries=search_queries
        )

        return gap

    def _extract_search_term(self, crumb: Dict[str, Any]) -> Optional[str]:
        """Extract search term from breadcrumb."""
        # Check metadata
        metadata = crumb.get('metadata', {})
        if 'search_term' in metadata:
            return metadata['search_term']

        # Check file name for search indicators
        file_name = crumb.get('target_file', '')
        if 'search' in file_name.lower():
            return file_name

        # Check operation
        if 'search' in crumb.get('operation', '').lower():
            return crumb.get('source_context', '')

        return None

    def _is_error_related(self, crumb: Dict[str, Any]) -> bool:
        """Check if breadcrumb indicates an error."""
        file_name = crumb.get('target_file', '').lower()
        operation = crumb.get('operation', '').lower()

        error_indicators = ['error', 'fail', 'exception', 'debug', 'traceback']
        return any(indicator in file_name or indicator in operation
                  for indicator in error_indicators)

    def _extract_error_topic(self, crumb: Dict[str, Any]) -> Optional[str]:
        """Extract topic from error-related breadcrumb."""
        file_name = crumb.get('target_file', '')

        # Extract meaningful parts from file name
        if 'error' in file_name.lower():
            # Try to get context from path
            path_parts = Path(file_name).parts
            for part in reversed(path_parts):
                if len(part) > 3 and not part.startswith('.'):
                    return part

        return self._extract_topic(crumb)

    def _extract_error_type(self, crumb: Dict[str, Any]) -> str:
        """Extract error type from breadcrumb."""
        file_name = crumb.get('target_file', '').lower()

        if 'exception' in file_name:
            return 'exception'
        elif 'fail' in file_name:
            return 'failure'
        elif 'debug' in file_name:
            return 'debug'
        else:
            return 'unknown'

    def _extract_topic(self, crumb: Dict[str, Any]) -> Optional[str]:
        """Extract topic from breadcrumb."""
        # Try file name first
        file_name = crumb.get('target_file', '')
        if file_name:
            # Remove extension and common prefixes
            name = Path(file_name).stem
            name = re.sub(r'^(test|debug|analysis)_', '', name)
            if len(name) > 3:
                return name

        # Try source context
        context = crumb.get('source_context', '')
        if context and len(context) > 3:
            return context

        return None

    def _priority_score(self, priority: str) -> int:
        """Convert priority string to numeric score."""
        scores = {'high': 3, 'medium': 2, 'low': 1}
        return scores.get(priority, 0)


def main():
    """Test the breadcrumb scanner."""
    scanner = BreadcrumbScanner(Path('.'))
    gaps = scanner.scan_for_gaps()

    print(f"Found {len(gaps)} knowledge gaps:")
    for gap in gaps[:5]:  # Show first 5
        print(f"- {gap.topic} (confidence: {gap.confidence:.2f}, priority: {gap.priority})")


if __name__ == '__main__':
    main()
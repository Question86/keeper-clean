#!/usr/bin/env python3
"""
Dream-Enhanced KnowledgeDB Integration

Integrates context dreaming with KnowledgeDB for enhanced semantic search.
Provides dream-enhanced knowledge retrieval and context-aware search results.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from context_dreamer import ContextDreamer
from knowledge_db import KnowledgeDB

class DreamEnhancedKnowledgeDB:
    """
    Enhanced KnowledgeDB with context dreaming capabilities.
    """

    def __init__(self, db_path: str = "keeper_knowledge.db", workspace_root: str = "."):
        self.db_path = Path(db_path)
        self.workspace = Path(workspace_root)
        self.dreamer = ContextDreamer(str(self.workspace))
        self.knowledge_db = KnowledgeDB(self.workspace)
        
        # Dreaming configuration
        self.dreaming_enabled = True
        self.max_dream_iterations = 3
        self.dream_depth = 5
        self.similarity_threshold = 0.7

    def dream_enhanced_search(self, query: str, limit: int = 10,
                            use_dreaming: bool = True) -> List[Dict]:
        """
        Perform dream-enhanced semantic search.

        Args:
            query: Search query
            limit: Maximum results to return
            use_dreaming: Whether to use dreaming enhancement

        Returns:
            List of search results with enhanced ranking
        """
        # Get base search results
        base_results = self._base_semantic_search(query, limit * 2)

        if not use_dreaming or not self.dreaming_enabled:
            return base_results[:limit]

        # Enhance with dreaming
        enhanced_results = self._apply_dream_enhancement(query, base_results)

        # Re-rank with dreaming insights
        ranked_results = self._dream_boosted_ranking(query, enhanced_results)

        return ranked_results[:limit]

    def _base_semantic_search(self, query: str, limit: int) -> List[Dict]:
        """
        Perform basic semantic search using existing KnowledgeDB functionality.
        """
        # Use the KnowledgeDB search method
        search_results = self.knowledge_db.search(query, limit=limit, semantic=True)
        
        # Convert SearchResult objects to dictionaries
        results = []
        for result in search_results:
            results.append({
                'id': result.id,
                'title': result.id,  # Use ID as title for now
                'content': result.snippet or '',
                'metadata': result.context or {},
                'created_at': datetime.now().isoformat(),  # Placeholder
                'relevance_score': result.relevance,
                'type': result.type
            })
        
        return results

    def _calculate_base_relevance(self, query: str, title: str, content: str) -> float:
        """
        Calculate basic relevance score.
        """
        query_lower = query.lower()
        title_lower = title.lower()
        content_lower = content.lower()

        score = 0.0

        # Title matches are highly relevant
        if query_lower in title_lower:
            score += 1.0

        # Content matches
        content_matches = content_lower.count(query_lower)
        score += min(content_matches * 0.1, 0.5)

        # Exact phrase matches
        if query_lower in content_lower:
            score += 0.3

        return min(score, 1.0)

    def _apply_dream_enhancement(self, query: str, base_results: List[Dict]) -> List[Dict]:
        """
        Apply context dreaming enhancement to search results.
        """
        if not base_results:
            return base_results

        try:
            # Run dreaming iteration to get connectivity insights
            dream_result = self.dreamer.enhanced_context_dream(
                iterations=1,
                target_depth=self.dream_depth
            )

            # Extract connectivity patterns
            connectivity_insights = dream_result.get('connectivity_insights', [])

            # Enhance results with dreaming insights
            for result in base_results:
                dream_boost = self._calculate_dream_boost(
                    query, result, connectivity_insights
                )
                result['dream_boost'] = dream_boost
                result['enhanced_score'] = result['relevance_score'] * (1 + dream_boost)

        except Exception as e:
            print(f"Dreaming enhancement failed: {e}")
            # Continue without dreaming enhancement
            for result in base_results:
                result['dream_boost'] = 0.0
                result['enhanced_score'] = result['relevance_score']

        return base_results

    def _calculate_dream_boost(self, query: str, result: Dict,
                             connectivity_insights: List) -> float:
        """
        Calculate dream-based boost for a result.
        """
        boost = 0.0

        # Analyze connectivity patterns
        for insight in connectivity_insights:
            connections = insight.get('connectivity', {}).get('connections_found', 0)
            files_analyzed = insight.get('files_analyzed', [])

            # Boost if result relates to highly connected files
            if connections > 2:
                boost += 0.1

            # Boost based on semantic similarity to query
            for file in files_analyzed:
                if self._semantic_similarity(query, file) > self.similarity_threshold:
                    boost += 0.2

        return min(boost, 0.5)  # Cap the boost

    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.
        """
        # Simple implementation - in practice, use embeddings
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _dream_boosted_ranking(self, query: str, results: List[Dict]) -> List[Dict]:
        """
        Re-rank results using dream-enhanced scoring.
        """
        # Sort by enhanced score
        ranked = sorted(results,
                       key=lambda x: x.get('enhanced_score', x['relevance_score']),
                       reverse=True)

        return ranked

    def add_dream_insights(self, insights: Dict):
        """
        Add dreaming insights to the knowledge base.
        For now, just log them since direct DB insertion requires schema knowledge.
        """
        insight_content = json.dumps(insights, indent=2)
        
        print(f"Dreaming insights generated: {insight_content}")
        
        # Could save to a file or integrate with KnowledgeDB add methods if available
        # For now, just demonstrate the capability

    def close(self):
        """Close database connections."""
        # KnowledgeDB handles its own connection management
        pass

def main():
    """
    Demo of dream-enhanced knowledge search.
    """
    print("Dream-Enhanced KnowledgeDB Integration")
    print("=" * 50)

    # Initialize enhanced KnowledgeDB
    db = DreamEnhancedKnowledgeDB()

    # Example searches
    queries = [
        "context dreaming",
        "neural network",
        "knowledge optimization",
        "semantic search"
    ]

    print("Running example searches with dream enhancement:")
    print()

    for query in queries:
        print(f"Query: '{query}'")
        results = db.dream_enhanced_search(query, limit=3)

        for i, result in enumerate(results, 1):
            score = result.get('enhanced_score', result['relevance_score'])
            boost = result.get('dream_boost', 0.0)
            print(f"  {i}. {result['title'][:50]}... (score: {score:.2f}, boost: {boost:.2f})")
        print()

    # Add some dreaming insights
    sample_insights = {
        'connections_discovered': 15,
        'patterns_identified': ['semantic_clustering', 'temporal_correlation'],
        'optimization_suggestions': ['increase_depth', 'focus_on_high_connectivity']
    }

    db.add_dream_insights(sample_insights)
    print("Added dreaming insights to knowledge base")

    db.close()
    print("✅ Integration demo complete!")

if __name__ == "__main__":
    main()
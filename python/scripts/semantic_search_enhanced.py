#!/usr/bin/env python3
"""
Enhanced Semantic Search System
Provides semantic search with cross-referencing capabilities
"""

import json
import sqlite3
import sys
from typing import List, Dict, Any, Tuple

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge_redundancy_db import KnowledgeRedundancyDB
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None
import numpy as np

class SemanticSearchEnhanced:
    """Enhanced semantic search with vector similarity and cross-referencing"""

    def __init__(self, db_path: str = "keeper_knowledge_redundancy.db", model_name: str = "all-MiniLM-L6-v2"):
        self.db = KnowledgeRedundancyDB(db_path)
        try:
            if SentenceTransformer is None:
                raise ImportError("sentence_transformers unavailable")
            self.model = SentenceTransformer(model_name)
        except Exception:
            print("Warning: SentenceTransformer not available, using fallback")
            self.model = None

    def search(self, query: str, limit: int = 10, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Perform semantic search with vector similarity"""
        if not self.model:
            # Fallback to keyword search
            return self.db.semantic_search(query, limit)

        # Generate query embedding
        query_embedding = self.model.encode(query)

        # Get all knowledge items
        all_knowledge = self._get_all_knowledge_with_vectors()

        # Calculate similarities
        results = []
        for item in all_knowledge:
            if item['vector']:
                try:
                    item_embedding = np.array(json.loads(item['vector']))
                    similarity = self._cosine_similarity(query_embedding, item_embedding)
                    if similarity >= threshold:
                        results.append({
                            'key': item['key'],
                            'data': item['data'],
                            'similarity': float(similarity),
                            'source': item['source']
                        })
                except:
                    continue

        # Sort by similarity and limit
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]

    def add_cross_references(self, source_key: str, target_key: str, relationship: str, strength: float = 1.0):
        """Add cross-reference between knowledge items"""
        # Get IDs
        source_id = self._get_knowledge_id(source_key)
        target_id = self._get_knowledge_id(target_key)

        if source_id and target_id:
            import sqlite3
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()

            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cross_references
                    (source_id, target_id, relationship_type, strength, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (source_id, target_id, relationship, strength, now))

    def get_related_knowledge(self, key: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Get related knowledge through cross-references"""
        knowledge_id = self._get_knowledge_id(key)
        if not knowledge_id:
            return []

        related = []
        visited = set([knowledge_id])

        def traverse(current_id: int, depth: int):
            if depth >= max_depth:
                return

            with sqlite3.connect(self.db.db_path) as conn:
                # Get cross-references
                refs = conn.execute("""
                    SELECT kr.primary_key, kr.json_repr, cr.relationship_type, cr.strength
                    FROM cross_references cr
                    JOIN knowledge_redundancy kr ON cr.target_id = kr.id
                    WHERE cr.source_id = ?
                    UNION
                    SELECT kr.primary_key, kr.json_repr, cr.relationship_type, cr.strength
                    FROM cross_references cr
                    JOIN knowledge_redundancy kr ON cr.source_id = kr.id
                    WHERE cr.target_id = ?
                """, (current_id, current_id)).fetchall()

                for ref in refs:
                    ref_id = self._get_knowledge_id(ref[0])
                    if ref_id not in visited:
                        visited.add(ref_id)
                        related.append({
                            'key': ref[0],
                            'data': json.loads(ref[1]),
                            'relationship': ref[2],
                            'strength': ref[3]
                        })
                        traverse(ref_id, depth + 1)

        traverse(knowledge_id, 0)
        return related

    def update_search_index(self):
        """Update semantic search index with current vectors"""
        if not self.model:
            return

        all_knowledge = self._get_all_knowledge()

        for item in all_knowledge:
            # Generate embedding for text representation
            text = item['text_repr']
            if text:
                embedding = self.model.encode(text)
                vector_str = json.dumps(embedding.tolist())

                # Extract keywords (simple approach)
                keywords = self._extract_keywords(text)

                # Calculate relevance score (placeholder)
                relevance = 0.5

                # Update index
                self._update_search_index(item['id'], vector_str, keywords, relevance)

    def _get_all_knowledge(self) -> List[Dict[str, Any]]:
        """Get all knowledge items"""
        with sqlite3.connect(self.db.db_path) as conn:
            rows = conn.execute("""
                SELECT id, primary_key, json_repr, text_repr, source_file
                FROM knowledge_redundancy
            """).fetchall()

        return [{
            'id': row[0],
            'key': row[1],
            'data': json.loads(row[2]),
            'text_repr': row[3],
            'source': row[4]
        } for row in rows]

    def _get_all_knowledge_with_vectors(self) -> List[Dict[str, Any]]:
        """Get all knowledge with vectors"""
        knowledge = self._get_all_knowledge()

        for item in knowledge:
            # Get vector from search index
            with sqlite3.connect(self.db.db_path) as conn:
                row = conn.execute("""
                    SELECT search_vector FROM semantic_search_index
                    WHERE knowledge_id = ?
                """, (item['id'],)).fetchone()

            item['vector'] = row[0] if row else None

        return knowledge

    def _get_knowledge_id(self, key: str) -> int:
        """Get knowledge ID by key"""
        with sqlite3.connect(self.db.db_path) as conn:
            row = conn.execute("""
                SELECT id FROM knowledge_redundancy WHERE primary_key = ?
            """, (key,)).fetchone()

        return row[0] if row else None

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _extract_keywords(self, text: str) -> str:
        """Extract keywords from text (simple approach)"""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        return ','.join(set(keywords))

    def _update_search_index(self, knowledge_id: int, vector: str, keywords: str, relevance: float):
        """Update search index"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO semantic_search_index
                (knowledge_id, search_vector, keywords, relevance_score)
                VALUES (?, ?, ?, ?)
            """, (knowledge_id, vector, keywords, relevance))

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python semantic_search_enhanced.py <query>")
        return

    query = sys.argv[1]
    search = SemanticSearchEnhanced()

    # Update index first
    print("Updating search index...")
    search.update_search_index()

    # Perform search
    results = search.search(query)
    print(f"Found {len(results)} results for '{query}':")
    for i, result in enumerate(results[:5]):  # Show top 5
        print(f"{i+1}. {result['key']} (similarity: {result['similarity']:.3f})")
        print(f"   Source: {result['source']}")

if __name__ == "__main__":
    main()

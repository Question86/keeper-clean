"""
Semantic Database Searching and Knowledge Extraction
Implements automated knowledge extraction and prediction testing
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import numpy as np
from datetime import datetime, timezone
import hashlib
import math

class SemanticSearchEngine:
    """
    Semantic search engine for knowledge database with automated extraction
    """

    def __init__(self, workspace_root: Path, embedding_dim: int = 128):
        self.workspace_root = workspace_root
        self.embedding_dim = embedding_dim
        self.db_path = workspace_root / 'keeper_knowledge.db'
        self.semantic_db_path = workspace_root / 'semantic_knowledge.db'

        # Initialize semantic database
        self._init_semantic_db()

    def _init_semantic_db(self):
        """Initialize semantic database with enhanced schema"""
        conn = sqlite3.connect(str(self.semantic_db_path))
        cursor = conn.cursor()

        # Create tables for semantic search
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_documents (
                id INTEGER PRIMARY KEY,
                source_file TEXT,
                content_hash TEXT,
                content TEXT,
                metadata TEXT,
                embedding BLOB,
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_relationships (
                id INTEGER PRIMARY KEY,
                source_doc_id INTEGER,
                target_doc_id INTEGER,
                relationship_type TEXT,
                confidence REAL,
                metadata TEXT,
                created_at TEXT,
                FOREIGN KEY (source_doc_id) REFERENCES semantic_documents(id),
                FOREIGN KEY (target_doc_id) REFERENCES semantic_documents(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons_learned (
                id INTEGER PRIMARY KEY,
                document_id INTEGER,
                lesson_text TEXT,
                category TEXT,
                confidence REAL,
                extracted_at TEXT,
                metadata TEXT,
                FOREIGN KEY (document_id) REFERENCES semantic_documents(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_tests (
                id INTEGER PRIMARY KEY,
                test_name TEXT,
                description TEXT,
                test_data TEXT,
                expected_outcome TEXT,
                actual_outcome TEXT,
                confidence REAL,
                success BOOLEAN,
                created_at TEXT,
                completed_at TEXT
            )
        ''')

        # Create FTS table for semantic search
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fts USING fts5(
                content, metadata, content='semantic_documents', content_rowid='id'
            )
        ''')

        conn.commit()
        conn.close()

    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate simple hash-based embedding for text"""
        # Use content hash to create deterministic embedding
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_int = int(hash_obj.hexdigest(), 16)

        np.random.seed(hash_int % (2**32))
        embedding = np.random.normal(0, 1, self.embedding_dim)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize

        return embedding

    def index_document(self, source_file: str, content: str, metadata: Dict = None):
        """Index a document for semantic search"""
        if metadata is None:
            metadata = {}

        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        embedding = self._generate_embedding(content)

        conn = sqlite3.connect(str(self.semantic_db_path))
        cursor = conn.cursor()

        # Check if document already exists
        cursor.execute(
            'SELECT id FROM semantic_documents WHERE source_file = ? AND content_hash = ?',
            (source_file, content_hash)
        )

        existing = cursor.fetchone()

        if existing:
            # Update existing
            doc_id = existing[0]
            cursor.execute('''
                UPDATE semantic_documents
                SET content = ?, metadata = ?, embedding = ?, updated_at = ?
                WHERE id = ?
            ''', (
                content,
                json.dumps(metadata),
                embedding.tobytes(),
                datetime.now(timezone.utc).isoformat(),
                doc_id
            ))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO semantic_documents
                (source_file, content_hash, content, metadata, embedding, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                source_file,
                content_hash,
                content,
                json.dumps(metadata),
                embedding.tobytes(),
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat()
            ))

            doc_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return doc_id

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Perform semantic search using vector similarity and text matching

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of search results with relevance scores
        """
        query_embedding = self._generate_embedding(query)

        conn = sqlite3.connect(str(self.semantic_db_path))
        cursor = conn.cursor()

        # Get all documents with embeddings
        cursor.execute('SELECT id, source_file, content, metadata, embedding FROM semantic_documents')
        documents = cursor.fetchall()

        results = []
        for doc_id, source_file, content, metadata_str, embedding_bytes in documents:
            # Deserialize embedding
            embedding = np.frombuffer(embedding_bytes, dtype=np.float64)

            # Calculate cosine similarity
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )

            # Also check for text matches
            text_score = 0
            query_lower = query.lower()
            content_lower = content.lower()

            if query_lower in content_lower:
                text_score = 1.0
            else:
                # Count word matches
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                word_matches = len(query_words.intersection(content_words))
                text_score = word_matches / len(query_words) if query_words else 0

            # Combined score
            combined_score = 0.7 * similarity + 0.3 * text_score

            metadata = json.loads(metadata_str) if metadata_str else {}

            results.append({
                'doc_id': doc_id,
                'source_file': source_file,
                'content': content[:500] + '...' if len(content) > 500 else content,
                'metadata': metadata,
                'similarity_score': float(similarity),
                'text_score': float(text_score),
                'combined_score': float(combined_score)
            })

        conn.close()

        # Sort by combined score and return top results
        results.sort(key=lambda x: x['combined_score'], reverse=True)
        return results[:limit]

    def extract_lessons_learned(self, document_id: int) -> List[Dict]:
        """
        Extract lessons learned from a document using pattern matching and semantic analysis

        Args:
            document_id: ID of the document to analyze

        Returns:
            List of extracted lessons
        """
        conn = sqlite3.connect(str(self.semantic_db_path))
        cursor = conn.cursor()

        # Get document content
        cursor.execute('SELECT content, metadata FROM semantic_documents WHERE id = ?', (document_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return []

        content, metadata_str = result
        metadata = json.loads(metadata_str) if metadata_str else {}

        lessons = []

        # Pattern-based extraction
        lesson_patterns = [
            r'lesson learned:?\s*([^.!?]+)',
            r'key takeaway:?\s*([^.!?]+)',
            r'important:?\s*([^.!?]+)',
            r'note:?\s*([^.!?]+)',
            r'finding:?\s*([^.!?]+)',
            r'conclusion:?\s*([^.!?]+)',
            r'recommendation:?\s*([^.!?]+)'
        ]

        for pattern in lesson_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                lesson_text = match.strip()
                if len(lesson_text) > 10:  # Filter very short matches
                    # Categorize lesson
                    category = self._categorize_lesson(lesson_text)

                    lessons.append({
                        'lesson_text': lesson_text,
                        'category': category,
                        'confidence': 0.8,  # Pattern-based confidence
                        'extraction_method': 'pattern_matching'
                    })

        # Semantic extraction (simplified)
        semantic_lessons = self._extract_semantic_lessons(content)
        lessons.extend(semantic_lessons)

        # Store lessons in database
        for lesson in lessons:
            cursor.execute('''
                INSERT INTO lessons_learned
                (document_id, lesson_text, category, confidence, extracted_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                document_id,
                lesson['lesson_text'],
                lesson['category'],
                lesson['confidence'],
                datetime.now(timezone.utc).isoformat(),
                json.dumps({'extraction_method': lesson['extraction_method']})
            ))

        conn.commit()
        conn.close()

        return lessons

    def _categorize_lesson(self, lesson_text: str) -> str:
        """Categorize a lesson based on content"""
        text_lower = lesson_text.lower()

        categories = {
            'performance': ['performance', 'speed', 'efficiency', 'optimization'],
            'reliability': ['error', 'failure', 'bug', 'crash', 'stability'],
            'usability': ['user', 'interface', 'ui', 'ux', 'experience'],
            'security': ['security', 'vulnerability', 'attack', 'safe'],
            'architecture': ['architecture', 'design', 'structure', 'pattern'],
            'process': ['process', 'workflow', 'methodology', 'practice'],
            'tools': ['tool', 'library', 'framework', 'dependency'],
            'testing': ['test', 'validation', 'quality', 'coverage']
        }

        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category

        return 'general'

    def _extract_semantic_lessons(self, content: str) -> List[Dict]:
        """Extract lessons using semantic analysis (simplified)"""
        # This is a placeholder for more sophisticated semantic extraction
        # In a real implementation, this would use NLP models

        lessons = []

        # Look for sentences containing insight words
        insight_indicators = [
            'realized', 'discovered', 'learned', 'found that', 'important to',
            'critical to', 'key is', 'better to', 'should', 'avoid', 'prevent'
        ]

        sentences = re.split(r'[.!?]+', content)

        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(indicator in sentence_lower for indicator in insight_indicators):
                if len(sentence) > 20:  # Filter short sentences
                    lessons.append({
                        'lesson_text': sentence.strip(),
                        'category': 'semantic_insight',
                        'confidence': 0.6,  # Lower confidence for semantic extraction
                        'extraction_method': 'semantic_analysis'
                    })

        return lessons

    def create_prediction_test(self, test_name: str, description: str,
                             test_data: Dict, expected_outcome: str) -> int:
        """
        Create a prediction test based on mega.md methodology

        Args:
            test_name: Name of the test
            description: Test description
            test_data: Test data/parameters
            expected_outcome: Expected prediction outcome

        Returns:
            Test ID
        """
        conn = sqlite3.connect(str(self.semantic_db_path))
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO prediction_tests
            (test_name, description, test_data, expected_outcome, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            test_name,
            description,
            json.dumps(test_data),
            expected_outcome,
            datetime.now(timezone.utc).isoformat()
        ))

        test_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return test_id

    def run_prediction_test(self, test_id: int, actual_outcome: str, confidence: float) -> bool:
        """
        Run a prediction test and record results

        Args:
            test_id: Test ID
            actual_outcome: Actual outcome
            confidence: Confidence in prediction

        Returns:
            Success status
        """
        conn = sqlite3.connect(str(self.semantic_db_path))
        cursor = conn.cursor()

        # Get expected outcome
        cursor.execute('SELECT expected_outcome FROM prediction_tests WHERE id = ?', (test_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False

        expected_outcome = result[0]
        success = actual_outcome.lower() == expected_outcome.lower()

        # Update test results
        cursor.execute('''
            UPDATE prediction_tests
            SET actual_outcome = ?, confidence = ?, success = ?, completed_at = ?
            WHERE id = ?
        ''', (
            actual_outcome,
            confidence,
            success,
            datetime.now(timezone.utc).isoformat(),
            test_id
        ))

        conn.commit()
        conn.close()

        return success

    def random_relationship_research(self, start_doc_id: int, max_depth: int = 5,
                                   branching_factor: int = 3) -> Dict:
        """
        Perform random research of relationship depths between documented tasks
        Based on mega.md "learning to guess" methodology

        Args:
            start_doc_id: Starting document ID
            max_depth: Maximum exploration depth
            branching_factor: Number of relationships to explore per level

        Returns:
            Research results
        """
        conn = sqlite3.connect(str(self.semantic_db_path))
        cursor = conn.cursor()

        explored = set()
        research_path = []

        def explore_relationships(doc_id: int, depth: int):
            if depth > max_depth or doc_id in explored:
                return

            explored.add(doc_id)
            research_path.append(doc_id)

            # Find related documents (simplified - in real implementation would use complex relationship analysis)
            cursor.execute('''
                SELECT target_doc_id FROM knowledge_relationships
                WHERE source_doc_id = ? ORDER BY confidence DESC LIMIT ?
            ''', (doc_id, branching_factor))

            related_docs = cursor.fetchall()

            for related_doc, in related_docs:
                explore_relationships(related_doc, depth + 1)

        explore_relationships(start_doc_id, 0)

        # Analyze the research path
        path_analysis = self._analyze_research_path(research_path)

        conn.close()

        return {
            'start_document': start_doc_id,
            'explored_documents': len(explored),
            'research_path': research_path,
            'max_depth_achieved': max(path_analysis['depths']) if path_analysis['depths'] else 0,
            'path_analysis': path_analysis,
            'insights': self._generate_research_insights(research_path)
        }

    def _analyze_research_path(self, path: List[int]) -> Dict:
        """Analyze the research path for patterns and insights"""
        # Simplified analysis
        depths = []
        categories = []

        conn = sqlite3.connect(str(self.semantic_db_path))
        cursor = conn.cursor()

        for doc_id in path:
            cursor.execute('SELECT metadata FROM semantic_documents WHERE id = ?', (doc_id,))
            result = cursor.fetchone()
            if result:
                metadata = json.loads(result[0]) if result[0] else {}
                categories.append(metadata.get('category', 'unknown'))
                depths.append(metadata.get('depth', 0))

        conn.close()

        return {
            'depths': depths,
            'categories': categories,
            'category_distribution': {cat: categories.count(cat) for cat in set(categories)},
            'avg_depth': sum(depths) / len(depths) if depths else 0
        }

    def _generate_research_insights(self, path: List[int]) -> List[str]:
        """Generate insights from research path"""
        insights = []

        if len(path) > 1:
            insights.append(f"Explored relationship chain of {len(path)} documents")

        # Add more sophisticated insights based on path analysis
        insights.append("Research path analysis completed")
        insights.append("Ready for prediction testing integration")

        return insights

    def get_knowledge_stats(self) -> Dict:
        """Get statistics about the knowledge base"""
        conn = sqlite3.connect(str(self.semantic_db_path))
        cursor = conn.cursor()

        stats = {}

        # Document count
        cursor.execute('SELECT COUNT(*) FROM semantic_documents')
        stats['total_documents'] = cursor.fetchone()[0]

        # Lessons learned count
        cursor.execute('SELECT COUNT(*) FROM lessons_learned')
        stats['total_lessons'] = cursor.fetchone()[0]

        # Prediction tests
        cursor.execute('SELECT COUNT(*), AVG(confidence), AVG(success) FROM prediction_tests')
        test_count, avg_confidence, avg_success = cursor.fetchone()
        stats['prediction_tests'] = {
            'count': test_count,
            'avg_confidence': avg_confidence or 0,
            'avg_success_rate': avg_success or 0
        }

        # Category distribution
        cursor.execute('SELECT category, COUNT(*) FROM lessons_learned GROUP BY category')
        category_dist = dict(cursor.fetchall())
        stats['lesson_categories'] = category_dist

        conn.close()

        return stats


def demo_semantic_search():
    """Demonstration of semantic search and knowledge extraction"""
    workspace = Path(__file__).parent

    # Initialize search engine
    engine = SemanticSearchEngine(workspace)

    print("Semantic Search Engine initialized")

    # Index some sample documents
    sample_docs = [
        {
            'file': 'sample_report.md',
            'content': '''
            # Sample Report

            ## Key Findings
            The optimization improved performance by 40%.
            Lesson learned: Always profile before optimizing.

            ## Recommendations
            Use vectorized operations for better performance.
            Important: Test on real data before deployment.
            ''',
            'metadata': {'type': 'report', 'category': 'performance'}
        },
        {
            'file': 'architecture_guide.md',
            'content': '''
            # Architecture Guide

            ## Design Principles
            Keep it simple and maintainable.
            Critical: Document all assumptions.

            ## Best Practices
            Use type hints for better code quality.
            Avoid global state when possible.
            ''',
            'metadata': {'type': 'guide', 'category': 'architecture'}
        }
    ]

    for doc in sample_docs:
        doc_id = engine.index_document(doc['file'], doc['content'], doc['metadata'])
        print(f"Indexed document: {doc['file']} (ID: {doc_id})")

        # Extract lessons
        lessons = engine.extract_lessons_learned(doc_id)
        print(f"Extracted {len(lessons)} lessons from {doc['file']}")

    # Perform semantic search
    search_results = engine.semantic_search("performance optimization", limit=5)
    print(f"\nSearch results for 'performance optimization': {len(search_results)} found")

    for result in search_results[:3]:
        print(f"- {result['source_file']}: {result['combined_score']:.3f}")

    # Create prediction test
    test_id = engine.create_prediction_test(
        "Performance Prediction Test",
        "Test prediction of optimization impact",
        {"optimization_type": "vectorization", "data_size": "large"},
        "40% improvement"
    )
    print(f"\nCreated prediction test (ID: {test_id})")

    # Run prediction test
    success = engine.run_prediction_test(test_id, "35% improvement", 0.8)
    print(f"Prediction test result: {'Success' if success else 'Failed'}")

    # Get knowledge stats
    stats = engine.get_knowledge_stats()
    print(f"\nKnowledge base stats: {stats}")

    print("\nSemantic search and knowledge extraction demo completed")


if __name__ == "__main__":
    demo_semantic_search()
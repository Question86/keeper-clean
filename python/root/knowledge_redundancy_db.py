#!/usr/bin/env python3
"""
Knowledge Redundancy Database
Maintains multiple knowledge representations for resilience and continuity
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import hashlib

class KnowledgeRedundancyDB:
    """Database for knowledge redundancy with multiple representations"""

    def __init__(self, db_path: str = "keeper_knowledge_redundancy.db"):
        self.db_path = Path(db_path)
        self.init_database()

    def init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_redundancy (
                    id INTEGER PRIMARY KEY,
                    primary_key TEXT UNIQUE,
                    json_repr TEXT,
                    text_repr TEXT,
                    structured_repr TEXT,
                    vector_repr TEXT,
                    source_file TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    checksum TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons_learned (
                    id INTEGER PRIMARY KEY,
                    knowledge_id INTEGER,
                    lesson_text TEXT,
                    category TEXT,
                    confidence REAL,
                    extracted_from TEXT,
                    extracted_at TIMESTAMP,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge_redundancy(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_search_index (
                    id INTEGER PRIMARY KEY,
                    knowledge_id INTEGER,
                    search_vector TEXT,
                    keywords TEXT,
                    relevance_score REAL,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge_redundancy(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cross_references (
                    id INTEGER PRIMARY KEY,
                    source_id INTEGER,
                    target_id INTEGER,
                    relationship_type TEXT,
                    strength REAL,
                    created_at TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES knowledge_redundancy(id),
                    FOREIGN KEY (target_id) REFERENCES knowledge_redundancy(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY,
                    knowledge_id INTEGER,
                    backup_data TEXT,
                    backup_type TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge_redundancy(id)
                )
            """)

    def add_knowledge(self, primary_key: str, data: Dict[str, Any], source_file: str) -> int:
        """Add knowledge with multiple representations"""
        json_repr = json.dumps(data, indent=2)
        text_repr = self._dict_to_text(data)
        structured_repr = self._structure_data(data)
        vector_repr = self._create_vector_repr(data)
        checksum = hashlib.md5(json_repr.encode()).hexdigest()

        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO knowledge_redundancy
                (primary_key, json_repr, text_repr, structured_repr, vector_repr,
                 source_file, created_at, updated_at, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (primary_key, json_repr, text_repr, structured_repr, vector_repr,
                  source_file, now, now, checksum))

            knowledge_id = cursor.lastrowid

            # Create backup
            self._create_backup(knowledge_id, data)

            return knowledge_id

    def get_knowledge(self, primary_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve knowledge by primary key"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT json_repr FROM knowledge_redundancy
                WHERE primary_key = ?
            """, (primary_key,)).fetchone()

            if row:
                return json.loads(row[0])
            return None

    def extract_lessons_learned(self, knowledge_id: int, content: str) -> List[Dict[str, Any]]:
        """Extract lessons learned from content"""
        lessons = []

        # Simple pattern-based extraction (can be enhanced with ML)
        lesson_patterns = [
            r"lesson learned: (.+?)(?:\n|$)",
            r"key insight: (.+?)(?:\n|$)",
            r"important: (.+?)(?:\n|$)",
            r"critical: (.+?)(?:\n|$)"
        ]

        for pattern in lesson_patterns:
            import re
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                lesson = {
                    'text': match.strip(),
                    'category': 'general',
                    'confidence': 0.8,
                    'extracted_from': 'content_analysis'
                }
                lessons.append(lesson)

        # Store lessons
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            for lesson in lessons:
                conn.execute("""
                    INSERT INTO lessons_learned
                    (knowledge_id, lesson_text, category, confidence, extracted_from, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (knowledge_id, lesson['text'], lesson['category'],
                      lesson['confidence'], lesson['extracted_from'], now))

        return lessons

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search across knowledge"""
        # Simple keyword-based search (can be enhanced with vector similarity)
        query_lower = query.lower()

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT kr.primary_key, kr.json_repr, kr.text_repr,
                       ssi.relevance_score, kr.source_file
                FROM knowledge_redundancy kr
                LEFT JOIN semantic_search_index ssi ON kr.id = ssi.knowledge_id
                WHERE LOWER(kr.text_repr) LIKE ?
                ORDER BY ssi.relevance_score DESC, kr.updated_at DESC
                LIMIT ?
            """, (f'%{query_lower}%', limit)).fetchall()

        results = []
        for row in rows:
            results.append({
                'key': row[0],
                'data': json.loads(row[1]),
                'text': row[2],
                'score': row[3] or 0.5,
                'source': row[4]
            })

        return results

    def validate_knowledge(self, primary_key: str) -> Dict[str, Any]:
        """Validate knowledge integrity and cross-references"""
        validation = {
            'exists': False,
            'checksum_valid': False,
            'cross_references': 0,
            'lessons_count': 0,
            'backup_exists': False
        }

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT id, json_repr, checksum FROM knowledge_redundancy
                WHERE primary_key = ?
            """, (primary_key,)).fetchone()

            if row:
                validation['exists'] = True
                knowledge_id, json_repr, stored_checksum = row

                # Validate checksum
                current_checksum = hashlib.md5(json_repr.encode()).hexdigest()
                validation['checksum_valid'] = current_checksum == stored_checksum

                # Count cross-references
                validation['cross_references'] = conn.execute("""
                    SELECT COUNT(*) FROM cross_references
                    WHERE source_id = ? OR target_id = ?
                """, (knowledge_id, knowledge_id)).fetchone()[0]

                # Count lessons
                validation['lessons_count'] = conn.execute("""
                    SELECT COUNT(*) FROM lessons_learned
                    WHERE knowledge_id = ?
                """, (knowledge_id,)).fetchone()[0]

                # Check backup
                validation['backup_exists'] = conn.execute("""
                    SELECT COUNT(*) FROM backups
                    WHERE knowledge_id = ?
                """, (knowledge_id,)).fetchone()[0] > 0

        return validation

    def _dict_to_text(self, data: Dict[str, Any]) -> str:
        """Convert dict to readable text"""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for subkey, subvalue in value.items():
                    lines.append(f"  {subkey}: {subvalue}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _structure_data(self, data: Dict[str, Any]) -> str:
        """Create structured representation"""
        return json.dumps(data, separators=(',', ':'))  # Compact JSON

    def _create_vector_repr(self, data: Dict[str, Any]) -> str:
        """Create vector representation (placeholder for ML)"""
        # Placeholder - would use sentence transformers in real implementation
        text = self._dict_to_text(data)
        # Simple hash-based vector representation
        vector = [hash(word) % 1000 for word in text.split()]
        return json.dumps(vector)

    def _create_backup(self, knowledge_id: int, data: Dict[str, Any]):
        """Create backup of knowledge"""
        backup_data = json.dumps(data)
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO backups (knowledge_id, backup_data, backup_type, created_at)
                VALUES (?, ?, ?, ?)
            """, (knowledge_id, backup_data, 'full', now))

# Example usage
if __name__ == "__main__":
    db = KnowledgeRedundancyDB()

    # Add sample knowledge
    sample_data = {
        "topic": "AI Integration",
        "lesson": "Always validate AI outputs before integration",
        "importance": "high"
    }

    knowledge_id = db.add_knowledge("ai_integration_lesson", sample_data, "example.py")
    print(f"Added knowledge with ID: {knowledge_id}")

    # Extract lessons
    lessons = db.extract_lessons_learned(knowledge_id, "lesson learned: AI outputs need validation")
    print(f"Extracted {len(lessons)} lessons")

    # Search
    results = db.semantic_search("AI validation")
    print(f"Search results: {len(results)}")

    # Validate
    validation = db.validate_knowledge("ai_integration_lesson")
    print(f"Validation: {validation}")

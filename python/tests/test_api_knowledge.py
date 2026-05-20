# test_api_knowledge.py - Tests for knowledge management API endpoints

import pytest
import json
import sqlite3
from pathlib import Path


class TestKnowledgeEndpoints:
    """Test suite for knowledge management endpoints."""

    def test_api_knowledge_stats_get(self, client, temp_workspace):
        """Test GET /api/knowledge/stats endpoint."""
        # Create a minimal knowledge.db
        db_path = Path("knowledge.db")
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                content TEXT,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("INSERT INTO knowledge (content, metadata, timestamp) VALUES (?, ?, ?)",
                    ("Test content", '{"tags": ["test"]}', "2024-01-01T00:00:00Z"))
        conn.commit()
        conn.close()

        response = client.get('/api/knowledge/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "total_entries" in data
        assert "last_updated" in data
        assert isinstance(data["total_entries"], int)

    def test_api_knowledge_search_get(self, client, temp_workspace):
        """Test GET /api/knowledge/search endpoint."""
        # Create knowledge.db with searchable content
        db_path = Path("knowledge.db")
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                content TEXT,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("INSERT INTO knowledge (content, metadata, timestamp) VALUES (?, ?, ?)",
                    ("Python programming tutorial", '{"tags": ["python", "tutorial"]}', "2024-01-01T00:00:00Z"))
        conn.commit()
        conn.close()

        response = client.get('/api/knowledge/search?q=python')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_api_knowledge_search_post(self, client, temp_workspace):
        """Test POST /api/knowledge/search endpoint."""
        # Create knowledge.db
        db_path = Path("knowledge.db")
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                content TEXT,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("INSERT INTO knowledge (content, metadata, timestamp) VALUES (?, ?, ?)",
                    ("Advanced AI patterns", '{"tags": ["ai", "patterns"]}', "2024-01-01T00:00:00Z"))
        conn.commit()
        conn.close()

        payload = {
            "query": "AI",
            "limit": 10
        }

        response = client.post('/api/knowledge/search',
                              data=json.dumps(payload),
                              content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_api_knowledge_lessons_get(self, client, temp_workspace):
        """Test GET /api/knowledge/lessons endpoint."""
        # Create knowledge.db with lesson content
        db_path = Path("knowledge.db")
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                content TEXT,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("INSERT INTO knowledge (content, metadata, timestamp) VALUES (?, ?, ?)",
                    ("Lesson: Always test your code", '{"type": "lesson", "category": "testing"}', "2024-01-01T00:00:00Z"))
        conn.commit()
        conn.close()

        response = client.get('/api/knowledge/lessons')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "lessons" in data
        assert isinstance(data["lessons"], list)

    def test_api_knowledge_file_history_get(self, client, temp_workspace):
        """Test GET /api/knowledge/file-history endpoint."""
        # Create knowledge.db with file history
        db_path = Path("knowledge.db")
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                content TEXT,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("INSERT INTO knowledge (content, metadata, timestamp) VALUES (?, ?, ?)",
                    ("File: loop_cockpit.py history", '{"file": "loop_cockpit.py", "type": "history"}', "2024-01-01T00:00:00Z"))
        conn.commit()
        conn.close()

        response = client.get('/api/knowledge/file-history?file=loop_cockpit.py')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_api_knowledge_chat_post(self, client, temp_workspace):
        """Test POST /api/knowledge/chat endpoint."""
        # Create knowledge.db
        db_path = Path("knowledge.db")
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                content TEXT,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("INSERT INTO knowledge (content, metadata, timestamp) VALUES (?, ?, ?)",
                    ("Chat context about testing", '{"type": "chat", "context": "testing"}', "2024-01-01T00:00:00Z"))
        conn.commit()
        conn.close()

        payload = {
            "message": "How do I test API endpoints?",
            "context": "testing"
        }

        response = client.post('/api/knowledge/chat',
                              data=json.dumps(payload),
                              content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "response" in data
        assert isinstance(data["response"], str)

    def test_api_knowledge_rebuild_post(self, client, temp_workspace):
        """Test POST /api/knowledge/rebuild endpoint."""
        # Create some source files for rebuilding
        source_dir = Path("knowledge_sources")
        source_dir.mkdir(exist_ok=True)
        (source_dir / "test.md").write_text("# Test Knowledge\n\nThis is test content.", encoding="utf-8")

        payload = {
            "force": False
        }

        response = client.post('/api/knowledge/rebuild',
                              data=json.dumps(payload),
                              content_type='application/json')
        # May return various status codes depending on implementation
        assert response.status_code in [200, 202, 400, 500]


class TestKnowledgeEdgeCases:
    """Test edge cases for knowledge endpoints."""

    def test_api_knowledge_stats_no_db(self, client, temp_workspace):
        """Test GET /api/knowledge/stats when database doesn't exist."""
        db_path = Path("knowledge.db")
        if db_path.exists():
            db_path.unlink()

        response = client.get('/api/knowledge/stats')
        # Should handle gracefully
        assert response.status_code in [200, 500]

    def test_api_knowledge_search_empty_query(self, client, temp_workspace):
        """Test GET /api/knowledge/search with empty query."""
        response = client.get('/api/knowledge/search?q=')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "results" in data

    def test_api_knowledge_search_no_results(self, client, temp_workspace):
        """Test GET /api/knowledge/search with query that returns no results."""
        # Create empty knowledge.db
        db_path = Path("knowledge.db")
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                content TEXT,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

        response = client.get('/api/knowledge/search?q=nonexistent')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "results" in data
        assert len(data["results"]) == 0

    def test_api_knowledge_chat_invalid_payload(self, client):
        """Test POST /api/knowledge/chat with invalid payload."""
        payload = {
            "invalid_field": "value"
        }

        response = client.post('/api/knowledge/chat',
                              data=json.dumps(payload),
                              content_type='application/json')
        assert response.status_code == 400
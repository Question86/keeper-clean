#!/usr/bin/env python3
"""
Test Maintenance Automation

Tests for the knowledge maintenance automation system.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from scripts.maintenance_general import KnowledgeMaintenance
from scripts.maintenance_knowledge_maintenance import build_result

class TestKnowledgeMaintenance:
    """Test cases for knowledge maintenance functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        # Create test schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE docs (
                id INTEGER PRIMARY KEY,
                title TEXT,
                path TEXT,
                category TEXT,
                tags TEXT,
                indexed_at TEXT
            )
        """)

        # Insert test data
        base_time = datetime.now(timezone.utc)
        test_data = [
            (1, 'Test Doc 1', '/path/to/doc1.md', 'architecture', 'tag1,tag2', (base_time - timedelta(days=100)).isoformat()),
            (2, 'Test Doc 2', '/path/to/doc2.md', 'audit', 'tag3', (base_time - timedelta(days=50)).isoformat()),
            (3, 'Test Doc 3', '/path/to/doc3.md', 'documentation', 'tag4', (base_time - timedelta(days=20)).isoformat()),
            (4, 'Missing Doc', '/path/to/missing.md', 'planning', 'tag5', (base_time - timedelta(days=100)).isoformat()),
        ]

        cursor.executemany("INSERT INTO docs VALUES (?, ?, ?, ?, ?, ?)", test_data)
        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        os.unlink(db_path)

    def test_get_outdated_items(self, temp_db):
        """Test retrieval of outdated items."""
        maintainer = KnowledgeMaintenance(temp_db)
        outdated = maintainer.get_outdated_items(days_threshold=90)

        assert len(outdated) == 2  # Two items older than 90 days
        assert outdated[0]['id'] == 1
        assert outdated[1]['id'] == 4

    def test_update_item_freshness(self, temp_db):
        """Test updating item freshness."""
        maintainer = KnowledgeMaintenance(temp_db)

        # Update item 1
        success = maintainer.update_item_freshness(1)
        assert success

        # Verify update
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT indexed_at FROM docs WHERE id = 1")
        result = cursor.fetchone()
        conn.close()

        updated_time = datetime.fromisoformat(result[0])
        now = datetime.now(timezone.utc)
        assert (now - updated_time).total_seconds() < 60  # Within last minute

    def test_validate_item_exists(self, temp_db):
        """Test file existence validation."""
        maintainer = KnowledgeMaintenance(temp_db)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            assert maintainer.validate_item_exists(temp_file)
            assert not maintainer.validate_item_exists('/nonexistent/file.md')
        finally:
            os.unlink(temp_file)

    def test_perform_maintenance_dry_run(self, temp_db):
        """Test maintenance dry run."""
        maintainer = KnowledgeMaintenance(temp_db)
        results = maintainer.perform_maintenance(dry_run=True)

        assert results['total_outdated'] == 2
        assert results['updated'] == 0  # Files don't exist, so skipped even in dry run
        assert results['skipped_missing'] == 2

    def test_perform_maintenance_actual(self, temp_db):
        """Test actual maintenance run."""
        maintainer = KnowledgeMaintenance(temp_db)
        results = maintainer.perform_maintenance(dry_run=False)

        assert results['total_outdated'] == 2
        assert results['updated'] == 0  # Files don't exist, so skipped
        assert results['skipped_missing'] == 2

    def test_categories_covered(self, temp_db):
        """Test that all expected categories are handled."""
        maintainer = KnowledgeMaintenance(temp_db)
        assert len(maintainer.categories) == 16
        assert 'architecture' in maintainer.categories
        assert 'success' in maintainer.categories
        assert 'warning' in maintainer.categories
        assert 'failure' in maintainer.categories

    def test_coverage_drift_structure(self, temp_db):
        """Test DB/FS drift summary schema."""
        maintainer = KnowledgeMaintenance(temp_db, workspace_root=".")
        drift = maintainer.get_coverage_drift()
        assert isinstance(drift, dict)
        assert "docs" in drift
        assert "db" in drift["docs"]
        assert "fs" in drift["docs"]
        assert "missing" in drift["docs"]


class TestKnowledgeMaintenanceAudit:
    """Validation for TASK_0226 maintenance audit script."""

    @pytest.fixture
    def audit_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("CREATE TABLE docs (id TEXT, path TEXT, indexed_at TEXT)")
        cur.execute("CREATE TABLE reports (id TEXT, path TEXT, indexed_at TEXT)")
        cur.execute("CREATE TABLE tasks (id TEXT, path TEXT, indexed_at TEXT)")
        cur.execute("CREATE TABLE archives (id TEXT, path TEXT, indexed_at TEXT)")
        cur.execute("CREATE TABLE bugs (id TEXT, path TEXT, indexed_at TEXT)")
        cur.execute("CREATE TABLE code (id TEXT, path TEXT, indexed_at TEXT)")

        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=120)).isoformat()
        new = (now - timedelta(days=1)).isoformat()

        cur.execute("INSERT INTO docs VALUES (?, ?, ?)", ("DOC_A", "docs/missing_a.md", old))
        cur.execute("INSERT INTO reports VALUES (?, ?, ?)", ("REP_A", "reports/missing_r.md", new))
        cur.execute("INSERT INTO tasks VALUES (?, ?, ?)", ("TASK_A", "tasks/missing_t.md", old))
        cur.execute("INSERT INTO archives VALUES (?, ?, ?)", ("ARCHIV_A", "archive/missing_ar.md", new))
        cur.execute("INSERT INTO bugs VALUES (?, ?, ?)", ("BUG_A", "bugs/missing_b.md", None))
        cur.execute("INSERT INTO code VALUES (?, ?, ?)", ("CODE_A", "code/missing_c.md", new))

        conn.commit()
        conn.close()
        yield db_path
        os.unlink(db_path)

    def test_build_result_has_required_sections(self, audit_db):
        result = build_result(
            db_path=Path(audit_db),
            workspace_root=Path(".").resolve(),
            days=90,
            min_freshness_score=0.60,
        )
        assert "maintenance_scope" in result
        assert "quality_checks" in result
        assert "automation_opportunities" in result
        assert "update_procedures" in result
        assert "process_improvements" in result

    def test_build_result_detects_stale_tables(self, audit_db):
        result = build_result(
            db_path=Path(audit_db),
            workspace_root=Path(".").resolve(),
            days=90,
            min_freshness_score=0.60,
        )
        tables = {entry["table"] for entry in result["maintenance_scope"]}
        assert "docs" in tables
        assert "tasks" in tables
        assert "bugs" in tables

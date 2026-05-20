#!/usr/bin/env python3
"""Tests for TASK_0225 AI integration coverage analysis."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

from scripts.ai_integration_analysis import analyze_ai_coverage, render_markdown_plan


def _create_table(cur: sqlite3.Cursor, name: str, fields: str) -> None:
    cur.execute(f"CREATE TABLE {name} ({fields})")


def test_ai_coverage_detects_underrepresented_tables():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        _create_table(cur, "docs", "id TEXT, title TEXT, path TEXT, category TEXT, tags TEXT, content_full TEXT")
        _create_table(cur, "reports", "id TEXT, task_id TEXT, path TEXT, goal TEXT, tags TEXT, keywords TEXT, content_full TEXT")
        _create_table(cur, "tasks", "id TEXT, path TEXT, objective TEXT, seed_idea TEXT, tags TEXT")
        _create_table(cur, "archives", "id TEXT, path TEXT, summary TEXT, lessons_learned TEXT, content_full TEXT")
        _create_table(cur, "bugs", "id TEXT, title TEXT, path TEXT, tags TEXT, content_full TEXT")
        _create_table(cur, "code", "id TEXT, title TEXT, path TEXT, category TEXT, tags TEXT, content_full TEXT")

        cur.execute("INSERT INTO docs VALUES ('DOC1', 'Architecture', 'docs/a.md', 'architecture', 'core', 'no ai terms here')")
        cur.execute("INSERT INTO docs VALUES ('DOC2', 'AI Design', 'docs/b.md', 'architecture', 'ai', 'openai agent embedding')")
        cur.execute("INSERT INTO tasks VALUES ('TASK1', 'tasks/t1.md', 'build pipeline', 'seed', 'automation')")
        cur.execute("INSERT INTO reports VALUES ('REP1', 'TASK1', 'reports/r1.md', 'goal', 'tag', 'keyword', 'general status')")
        cur.execute("INSERT INTO code VALUES ('CODE1', 'Inference', 'code/c1.py', 'ml', 'ai', 'model inference')")
        conn.commit()
        conn.close()

        result = analyze_ai_coverage(db_path=db_path, target_coverage=0.50)
        assert "docs" in [x["table"] for x in result["per_table"]]
        assert len(result["underrepresented_tables"]) >= 1
        assert result["total_items"] > 0
        assert "required_content" in result
        assert "implementation_plan" in result
        assert "cross_references" in result
    finally:
        os.unlink(db_path)


def test_markdown_plan_renders_sections():
    sample = {
        "generated_at": "2026-02-16T00:00:00Z",
        "target_coverage": 0.15,
        "overall_coverage": 0.10,
        "total_ai_related": 10,
        "total_items": 100,
        "required_content": [
            {
                "table": "tasks",
                "current_coverage": 0.05,
                "target_coverage": 0.15,
                "recommended_new_items": 4,
            }
        ],
        "implementation_plan": ["step-a", "step-b"],
        "cross_references": [
            {
                "from_table": "tasks",
                "from_id": "TASK_0001",
                "to_table": "reports",
                "to_id": "report_TASK_0001_L01_v01",
                "reason": "traceability",
            }
        ],
    }
    md = render_markdown_plan(sample)
    assert "# AI Integration Expansion Plan" in md
    assert "## Coverage Snapshot" in md
    assert "## Underrepresented Tables" in md
    assert "## Implementation Plan" in md
    assert "## Cross-Reference Actions" in md

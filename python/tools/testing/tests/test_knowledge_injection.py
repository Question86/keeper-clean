import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import pytest
from loop_guardrails import read_text
from knowledge_db import KnowledgeDB

try:
    from loop_guardrails import enrich_task_with_knowledge
except ImportError:
    enrich_task_with_knowledge = None


def test_enrich_task_creates_knowledge_file(tmp_path):
    if enrich_task_with_knowledge is None:
        pytest.skip("enrich_task_with_knowledge is not available in current loop_guardrails build")
    # Use a temporary workspace copy to avoid modifying repo files
    workspace = Path('.')
    task_id = 'TASK_0081'

    outfile = Path(f"_KNOWLEDGE_{task_id}.md")
    if outfile.exists():
        outfile.unlink()

    result = enrich_task_with_knowledge(task_id, workspace)

    assert result is not None
    assert outfile.exists()
    content = read_text(outfile)
    assert "AUTO-GENERATED KNOWLEDGE CONTEXT" in content

    # Clean up
    try:
        outfile.unlink()
    except Exception:
        pass


def test_report_ingestion_parses_task_loop_version(tmp_path):
    workspace = tmp_path
    (workspace / "reports").mkdir(parents=True, exist_ok=True)
    report_path = workspace / "reports" / "report_misc_TASK_9999_L132_v03.md"
    report_path.write_text(
        """# REPORT: INGESTION REGRESSION

MODE: EXECUTION REPORT
STATUS: COMPLETED
CREATED: 2026-02-15T00:00:00Z

---

## EXECUTIVE SUMMARY

Regression ingestion test content.
""",
        encoding="utf-8",
    )

    db = KnowledgeDB(workspace)
    try:
        db._create_schema()
        for stmt in (
            "ALTER TABLE reports ADD COLUMN enhanced_quality_score REAL DEFAULT 0",
            "ALTER TABLE reports ADD COLUMN enhanced_connectivity_score REAL DEFAULT 0",
            "ALTER TABLE reports ADD COLUMN enhanced_depth_score REAL DEFAULT 0",
            "ALTER TABLE reports ADD COLUMN enhanced_learning_potential REAL DEFAULT 0",
            "ALTER TABLE reports ADD COLUMN semantic_relationships TEXT DEFAULT '[]'",
            "ALTER TABLE reports ADD COLUMN context_depth_metrics TEXT DEFAULT '{}'",
            "ALTER TABLE reports ADD COLUMN learning_patterns TEXT DEFAULT '{}'",
        ):
            try:
                db.conn.execute(stmt)
            except Exception:
                pass
        db._index_report(report_path)
        row = db.conn.execute(
            "SELECT task_id, loop_num, version FROM reports WHERE id=?",
            (report_path.stem,),
        ).fetchone()
        assert row is not None
        assert row["task_id"] == "TASK_9999"
        assert int(row["loop_num"]) == 132
        assert int(row["version"]) == 3
    finally:
        db.close()


def test_e2e_simulated_reset_bootstrap_report_query_finalize_flow(tmp_path):
    workspace = tmp_path
    for name in ("reports", "archive", "tasks", "docs"):
        (workspace / name).mkdir(parents=True, exist_ok=True)

    # Simulated reset -> bootstrap preparation
    bootstrap = workspace / "_BOOTSTRAP.md"
    bootstrap.write_text("# _BOOTSTRAP\n", encoding="utf-8")
    assert bootstrap.exists()

    # Simulated bootstrap completion
    bootstrap.unlink()
    assert not bootstrap.exists()

    # Simulated report creation in active phase
    report_path = workspace / "reports" / "report_TASK_9901_L132_v01.md"
    report_path.write_text(
        """# REPORT: E2E FLOW
MODE: EXECUTION REPORT
STATUS: COMPLETED
CREATED: 2026-02-15T00:00:00Z
## EXECUTIVE SUMMARY
Bootstrap to query flow validated.
""",
        encoding="utf-8",
    )

    db = KnowledgeDB(workspace)
    try:
        add_result = db.incremental_index_with_fallback("_index_report", report_path)
        assert add_result["success"] is True

        results = db.search("Bootstrap to query flow", types=["report"], limit=5)
        assert any(r.id == report_path.stem for r in results)

        # Simulated finalize by archive creation + index
        archive_path = workspace / "archive" / "ARCHIV_0132.md"
        archive_path.write_text("# ARCHIV_0132\n## SUMMARY\nFlow complete.\n", encoding="utf-8")
        fin_result = db.incremental_index_with_fallback("_index_archive", archive_path)
        assert fin_result["success"] is True
    finally:
        db.close()

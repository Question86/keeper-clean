import time
from pathlib import Path

import loop_cockpit
from knowledge_db import KnowledgeDB


def _mk_workspace(root: Path) -> None:
    for name in ("reports", "tasks", "archive", "docs", "bugs", "code"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "current.json").write_text(
        '{"STATE":{"loop":132,"status":"ACTIVE"}}',
        encoding="utf-8",
    )


def _write_report(path: Path, created: str = "2026-02-15T00:00:00Z") -> None:
    path.write_text(
        f"""# REPORT: TEST EVENT

MODE: EXECUTION REPORT
STATUS: COMPLETED
CREATED: {created}

---

## EXECUTIVE SUMMARY

This is a test report for incremental indexing verification.

---

END OF REPORT
""",
        encoding="utf-8",
    )


def _write_task(path: Path) -> None:
    path.write_text(
        """MODE: ACTIVE
CREATED: 2026-02-15T00:00:00Z
STATUS: ACTIVE
PHASE: PLANNED
GOAL: Test event indexing

## OBJECTIVE

Verify event-driven task indexing.
""",
        encoding="utf-8",
    )


def test_on_report_created_indexes_report(tmp_path, monkeypatch):
    _mk_workspace(tmp_path)
    monkeypatch.setattr(loop_cockpit, "WORKSPACE_ROOT", tmp_path)

    report_path = tmp_path / "reports" / "report_TASK_9001_L132_v01.md"
    _write_report(report_path)

    loop_cockpit.KnowledgeDBEventHandler.on_report_created(report_path)

    db = KnowledgeDB(tmp_path)
    try:
        row = db.conn.execute(
            "SELECT id, loop_num, task_id FROM reports WHERE id=?",
            (report_path.stem,),
        ).fetchone()
        assert row is not None
        assert row["task_id"] == "TASK_9001"
        assert int(row["loop_num"]) == 132
    finally:
        db.close()


def test_on_task_changed_refreshes_indexed_at(tmp_path, monkeypatch):
    _mk_workspace(tmp_path)
    monkeypatch.setattr(loop_cockpit, "WORKSPACE_ROOT", tmp_path)

    task_path = tmp_path / "tasks" / "task_TASK_9002.md"
    _write_task(task_path)

    loop_cockpit.KnowledgeDBEventHandler.on_task_changed(task_path)
    db = KnowledgeDB(tmp_path)
    try:
        first = db.conn.execute(
            "SELECT indexed_at FROM tasks WHERE id='TASK_9002'"
        ).fetchone()
        assert first is not None
        first_ts = first["indexed_at"]
    finally:
        db.close()

    time.sleep(1.1)
    task_path.write_text(task_path.read_text(encoding="utf-8") + "\n## SCOPE\n\n- event refresh\n", encoding="utf-8")
    loop_cockpit.KnowledgeDBEventHandler.on_task_changed(task_path)

    db2 = KnowledgeDB(tmp_path)
    try:
        second = db2.conn.execute(
            "SELECT indexed_at FROM tasks WHERE id='TASK_9002'"
        ).fetchone()
        assert second is not None
        assert second["indexed_at"] != first_ts
    finally:
        db2.close()


def test_incremental_index_falls_back_to_rebuild_on_inconsistency(tmp_path):
    _mk_workspace(tmp_path)
    report_path = tmp_path / "reports" / "report_TASK_9003_L132_v01.md"
    _write_report(report_path)

    db = KnowledgeDB(tmp_path)
    try:
        # Force incremental failure via invalid index function name.
        result = db.incremental_index_with_fallback("_index_missing", report_path)
        assert result["fallback_used"] is True
        assert result["success"] is True
        stats = result.get("rebuild_stats") or {}
        assert int(stats.get("reports_indexed", 0)) >= 1
    finally:
        db.close()


def test_on_bug_changed_indexes_bug(tmp_path, monkeypatch):
    _mk_workspace(tmp_path)
    monkeypatch.setattr(loop_cockpit, "WORKSPACE_ROOT", tmp_path)

    bug_path = tmp_path / "bugs" / "BUG_9001.md"
    bug_path.write_text("# BUG_9001\n\nSEVERITY: HIGH\n\nBug detail.\n", encoding="utf-8")

    loop_cockpit.KnowledgeDBEventHandler.on_bug_changed(bug_path)

    db = KnowledgeDB(tmp_path)
    try:
        row = db.conn.execute("SELECT id, severity FROM bugs WHERE id='BUG_9001'").fetchone()
        assert row is not None
        assert row["severity"] == "high"
    finally:
        db.close()


def test_on_code_changed_indexes_code(tmp_path, monkeypatch):
    _mk_workspace(tmp_path)
    monkeypatch.setattr(loop_cockpit, "WORKSPACE_ROOT", tmp_path)

    code_path = tmp_path / "code" / "CODE_9001.md"
    code_path.write_text("# CODE_9001\n\nIntegration implementation detail.\n", encoding="utf-8")

    loop_cockpit.KnowledgeDBEventHandler.on_code_changed(code_path)

    db = KnowledgeDB(tmp_path)
    try:
        row = db.conn.execute("SELECT id FROM code WHERE id='CODE_9001'").fetchone()
        assert row is not None
    finally:
        db.close()

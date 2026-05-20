from knowledge_db import KnowledgeDB


def _mk_workspace(root):
    for name in ("reports", "tasks", "archive", "docs", "bugs", "code"):
        (root / name).mkdir(parents=True, exist_ok=True)


def test_rebuild_indexes_bug_and_code_tables(tmp_path):
    _mk_workspace(tmp_path)
    (tmp_path / "bugs" / "BUG_SAMPLE_0001.md").write_text(
        "# BUG_SAMPLE_0001\n\nSEVERITY: HIGH\n\n## ROOT CAUSE\n\nRegression.\n",
        encoding="utf-8",
    )
    (tmp_path / "code" / "CODE_SAMPLE_0001.md").write_text(
        "# CODE_SAMPLE_0001\n\nIntegration implementation details.\n",
        encoding="utf-8",
    )

    db = KnowledgeDB(tmp_path)
    try:
        stats = db.rebuild_with_write_guard(timeout_seconds=30)
        assert int(stats.get("bugs_indexed", 0)) == 1
        assert int(stats.get("code_indexed", 0)) == 1

        bug_row = db.conn.execute("SELECT id, severity FROM bugs WHERE id='BUG_SAMPLE_0001'").fetchone()
        code_row = db.conn.execute("SELECT id, category FROM code WHERE id='CODE_SAMPLE_0001'").fetchone()
        assert bug_row is not None
        assert bug_row["severity"] == "high"
        assert code_row is not None
    finally:
        db.close()

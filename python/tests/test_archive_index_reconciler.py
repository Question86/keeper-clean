from pathlib import Path

import loop_cockpit


def test_archive_reconcile_success_after_retry(monkeypatch, tmp_path):
    archive_path = tmp_path / "archive" / "ARCHIV_9999.md"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text("# ARCHIV_9999\n", encoding="utf-8")

    calls = {"index": 0, "exists": 0}
    logs = []

    def fake_on_archive_changed(path, actor="system"):
        calls["index"] += 1
        assert Path(path).name == "ARCHIV_9999.md"
        assert actor == "system"

    def fake_exists(path, workspace_root=None):
        calls["exists"] += 1
        # First attempt not visible, second attempt visible.
        return calls["exists"] >= 2

    def fake_log(op, target, from_value, to_value, outcome, details=""):
        logs.append((op, target, outcome, details))

    monkeypatch.setattr(loop_cockpit.KnowledgeDBEventHandler, "on_archive_changed", staticmethod(fake_on_archive_changed))
    monkeypatch.setattr(loop_cockpit, "_archive_index_exists", fake_exists)
    monkeypatch.setattr(loop_cockpit, "log_transaction", fake_log)

    result = loop_cockpit.reconcile_archive_index_with_retries(
        archive_path,
        retry_budget=3,
        retry_sleep_seconds=0,
        actor="system",
        workspace_root=tmp_path,
    )

    assert result["success"] is True
    assert result["status"] == "indexed"
    assert result["attempts"] == 2
    assert calls["index"] == 2
    assert any(entry[0] == "archive_reconcile" and entry[2] == "SUCCESS" for entry in logs)


def test_archive_reconcile_retry_exhausted(monkeypatch, tmp_path):
    archive_path = tmp_path / "archive" / "ARCHIV_9998.md"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text("# ARCHIV_9998\n", encoding="utf-8")

    logs = []

    def fake_on_archive_changed(path, actor="system"):
        raise RuntimeError("index attempt failed")

    def fake_exists(path, workspace_root=None):
        return False

    def fake_log(op, target, from_value, to_value, outcome, details=""):
        logs.append((op, target, outcome, details))

    monkeypatch.setattr(loop_cockpit.KnowledgeDBEventHandler, "on_archive_changed", staticmethod(fake_on_archive_changed))
    monkeypatch.setattr(loop_cockpit, "_archive_index_exists", fake_exists)
    monkeypatch.setattr(loop_cockpit, "log_transaction", fake_log)

    result = loop_cockpit.reconcile_archive_index_with_retries(
        archive_path,
        retry_budget=2,
        retry_sleep_seconds=0,
        actor="system",
        workspace_root=tmp_path,
    )

    assert result["success"] is False
    assert result["status"] == "retry_exhausted"
    assert result["attempts"] == 2
    assert any(entry[0] == "archive_reconcile" and entry[2] == "FAILED" for entry in logs)

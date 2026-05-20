import json
import threading
from pathlib import Path

import loop_guardrails as lg


def _seed_workspace(root: Path, task_id: str = "TASK_9999", loop: int = 141) -> None:
    (root / "tasks").mkdir(parents=True, exist_ok=True)
    (root / "reports").mkdir(parents=True, exist_ok=True)

    (root / "current.json").write_text(
        json.dumps({"STATE": {"loop": loop, "status": "ACTIVE", "lastTaskWorked": None}}, indent=2),
        encoding="utf-8",
    )
    (root / "tasks" / f"task_{task_id}.md").write_text(
        f"# {task_id}\n\nMODE: TASK SPECIFICATION\nSTATUS: NEW\nCREATED: 2026-02-16T00:00:00Z\n",
        encoding="utf-8",
    )
    (root / "reports" / f"report_{task_id}_L{loop}_v01.md").write_text(
        "# report\n",
        encoding="utf-8",
    )
    (root / "NEU.md").write_text(
        f"# NEU\n\n## TASK QUEUE\n\n[ref:tasks/task_{task_id}.md|v:1|tags:queued|src:test] - test\n  Status: queued\n\nEND OF DOCUMENT\n",
        encoding="utf-8",
    )
    (root / "Alt.md").write_text(
        "# Alt\n\n---\n\nEND OF DOCUMENT\n",
        encoding="utf-8",
    )


def test_close_task_atomic_success_with_alt_section_repair(tmp_path):
    _seed_workspace(tmp_path)

    result = lg.close_task("TASK_9999", tmp_path, "done")
    assert result["success"] is True
    assert result["diagnostics"]["loopSectionCreated"] is True
    assert result["diagnostics"]["neuTaskRemoved"] is True
    assert result["diagnostics"]["altTaskInserted"] is True

    alt = (tmp_path / "Alt.md").read_text(encoding="utf-8")
    neu = (tmp_path / "NEU.md").read_text(encoding="utf-8")
    task = (tmp_path / "tasks" / "task_TASK_9999.md").read_text(encoding="utf-8")
    current = json.loads((tmp_path / "current.json").read_text(encoding="utf-8"))

    assert "## COMPLETED (LOOP 141)" in alt
    assert "task_TASK_9999.md" in alt
    assert "task_TASK_9999.md" not in neu
    assert "STATUS: COMPLETED" in task
    assert current["STATE"]["lastTaskWorked"] == "TASK_9999"


def test_close_task_idempotent_duplicate_request(tmp_path):
    _seed_workspace(tmp_path)
    first = lg.close_task("TASK_9999", tmp_path, "done")
    second = lg.close_task("TASK_9999", tmp_path, "done")

    assert first["success"] is True
    assert second["success"] is True
    assert second.get("idempotent") is True

    alt = (tmp_path / "Alt.md").read_text(encoding="utf-8")
    assert alt.count("task_TASK_9999.md") == 1


def test_close_task_rollback_on_partial_failure(tmp_path, monkeypatch):
    _seed_workspace(tmp_path)
    task_before = (tmp_path / "tasks" / "task_TASK_9999.md").read_text(encoding="utf-8")
    neu_before = (tmp_path / "NEU.md").read_text(encoding="utf-8")
    alt_before = (tmp_path / "Alt.md").read_text(encoding="utf-8")

    original_atomic = lg._write_text_atomic_guardrails
    state = {"calls": 0}

    def flaky(path: Path, content: str):
        state["calls"] += 1
        if state["calls"] == 2:
            raise IOError("simulated write failure")
        return original_atomic(path, content)

    monkeypatch.setattr(lg, "_write_text_atomic_guardrails", flaky)
    result = lg.close_task("TASK_9999", tmp_path, "done")
    assert result["success"] is False

    assert (tmp_path / "tasks" / "task_TASK_9999.md").read_text(encoding="utf-8") == task_before
    assert (tmp_path / "NEU.md").read_text(encoding="utf-8") == neu_before
    assert (tmp_path / "Alt.md").read_text(encoding="utf-8") == alt_before


def test_close_task_race_duplicate_requests_single_alt_entry(tmp_path):
    _seed_workspace(tmp_path)
    results = []

    def worker():
        results.append(lg.close_task("TASK_9999", tmp_path, "done"))

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert all(r.get("success") for r in results)
    alt = (tmp_path / "Alt.md").read_text(encoding="utf-8")
    assert alt.count("task_TASK_9999.md") == 1

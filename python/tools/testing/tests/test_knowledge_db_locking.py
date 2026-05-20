import os
import json
import threading
import time

from knowledge_db import KnowledgeDB


def _mk_workspace(root):
    for name in ("reports", "tasks", "archive", "docs"):
        (root / name).mkdir(parents=True, exist_ok=True)

def _seed_workspace(root):
    (root / "reports" / "report_TASK_9999_L001_v01.md").write_text(
        "# TASK_9999\n\nGOAL: contention test\n\nVALIDATION: PASS\n",
        encoding="utf-8",
    )
    (root / "tasks" / "task_TASK_9999.md").write_text(
        "# TASK_9999\n\nMODE: ACTIVE\nSTATUS: NEW\nOBJECTIVE: contention test\n",
        encoding="utf-8",
    )
    (root / "archive" / "ARCHIV_0001.md").write_text(
        "# ARCHIV_0001\n\nSummary: contention test\n",
        encoding="utf-8",
    )
    (root / "docs" / "LOCK_TEST.md").write_text(
        "# Lock Test\n\nThis doc exists for rebuild coverage.\n",
        encoding="utf-8",
    )


def test_write_guard_reentrant_release(tmp_path):
    _mk_workspace(tmp_path)
    db = KnowledgeDB(tmp_path)
    try:
        acquired_outer = db._acquire_write_guard("test_outer", timeout_seconds=2)
        assert acquired_outer is True
        assert db.write_lock_path.exists()

        acquired_inner = db._acquire_write_guard("test_inner", timeout_seconds=2)
        assert acquired_inner is False
        assert db.write_lock_path.exists()

        db._release_write_guard(acquired_inner)
        assert db.write_lock_path.exists()

        db._release_write_guard(acquired_outer)
        assert not db.write_lock_path.exists()
    finally:
        try:
            db.close()
        except Exception:
            pass
        if db.write_lock_path.exists():
            db.write_lock_path.unlink()


def test_write_guard_reaps_stale_lock(tmp_path):
    _mk_workspace(tmp_path)
    db = KnowledgeDB(tmp_path)
    try:
        db.write_lock_path.write_text("stale", encoding="utf-8")
        stale_ts = time.time() - 600
        os.utime(db.write_lock_path, (stale_ts, stale_ts))

        acquired = db._acquire_write_guard(
            "test_stale_reap",
            timeout_seconds=2,
            stale_after_seconds=1,
            poll_seconds=0.05,
        )
        assert acquired is True
        assert db.write_lock_path.exists()

        db._release_write_guard(acquired)
        assert not db.write_lock_path.exists()
    finally:
        try:
            db.close()
        except Exception:
            pass
        if db.write_lock_path.exists():
            db.write_lock_path.unlink()


def test_concurrent_rebuild_and_incremental_index_avoids_lock_errors(tmp_path):
    _mk_workspace(tmp_path)
    _seed_workspace(tmp_path)

    results = {}
    failures = []
    start_evt = threading.Event()

    def _run_rebuild():
        db = KnowledgeDB(tmp_path)
        try:
            start_evt.wait(timeout=5)
            results["rebuild"] = db.rebuild_with_write_guard(timeout_seconds=30)
        except Exception as exc:
            failures.append(("rebuild", str(exc)))
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _run_incremental():
        db = KnowledgeDB(tmp_path)
        try:
            target = tmp_path / "tasks" / "task_TASK_9999.md"
            start_evt.wait(timeout=5)
            results["incremental"] = db.incremental_index_with_fallback("_index_task", target)
        except Exception as exc:
            failures.append(("incremental", str(exc)))
        finally:
            try:
                db.close()
            except Exception:
                pass

    rebuild_thread = threading.Thread(target=_run_rebuild, daemon=True)
    incremental_thread = threading.Thread(target=_run_incremental, daemon=True)
    rebuild_thread.start()
    incremental_thread.start()
    start_evt.set()
    rebuild_thread.join(timeout=120)
    incremental_thread.join(timeout=120)

    assert not rebuild_thread.is_alive()
    assert not incremental_thread.is_alive()
    assert failures == []
    assert "rebuild" in results
    assert "incremental" in results
    assert results["incremental"]["success"] is True
    assert "database is locked" not in json.dumps(results).lower()
    assert not (tmp_path / "keeper_knowledge.db.write.lock").exists()

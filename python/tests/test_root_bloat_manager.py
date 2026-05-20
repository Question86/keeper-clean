import json
from pathlib import Path

from scripts.root_bloat_manager import RootBloatManager


def _write_policy(path: Path) -> None:
    policy = {
        "protected_files": ["current.json", "NEU.md", "Alt.md"],
        "protected_globs": ["_LOOP_GATE.md"],
        "move_rules": [
            {"name": "tmp_files", "glob": "tmp_*", "destination": "tmp"},
            {"name": "test_reports", "glob": "test_report.*", "destination": "reports/testing"},
            {"name": "logs", "glob": "*.log", "destination": "logs"},
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(policy), encoding="utf-8")


def test_build_plan_respects_protection_and_limits(tmp_path):
    _write_policy(tmp_path / "config" / "root_cleanup_policy.json")

    (tmp_path / "current.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tmp_network.html").write_text("tmp", encoding="utf-8")
    (tmp_path / "test_report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "worker.log").write_text("log", encoding="utf-8")
    (tmp_path / "random.bin").write_bytes(b"\x00" * 10)

    manager = RootBloatManager(tmp_path)
    plan = manager.build_plan(max_files=2, max_bytes=1024)

    assert plan["scan_summary"]["selected_count"] == 2
    selected_sources = {item["source"] for item in plan["moves"]}
    assert "current.json" not in selected_sources
    assert all(src in {"tmp_network.html", "test_report.json", "worker.log"} for src in selected_sources)


def test_apply_plan_moves_files_and_writes_journal(tmp_path):
    _write_policy(tmp_path / "config" / "root_cleanup_policy.json")
    (tmp_path / "tmp_network.html").write_text("tmp", encoding="utf-8")
    (tmp_path / "test_report.json").write_text("{}", encoding="utf-8")

    manager = RootBloatManager(tmp_path)
    plan = manager.build_plan(max_files=10, max_bytes=4096)
    result = manager.apply_plan(plan)

    assert result["errors"] == 0
    assert result["moved"] >= 1
    assert not (tmp_path / "tmp_network.html").exists()
    assert (tmp_path / "tmp" / "tmp_network.html").exists()
    assert (tmp_path / "logs" / "root_cleanup_moves.jsonl").exists()

import json
from pathlib import Path

import policy_gate


def _write_current(workspace: Path, loop_num: int = 1, status: str = "ACTIVE") -> None:
    (workspace / "current.json").write_text(
        json.dumps({"STATE": {"loop": loop_num, "status": status}}, indent=2),
        encoding="utf-8",
    )


def _write_policy(workspace: Path, max_per_loop: int = 3) -> None:
    cfg_dir = workspace / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "db_write_policy.json").write_text(
        json.dumps(
            {
                "version": 1,
                "enabled": True,
                "operations": {
                    "knowledge.incremental_index": {
                        "actors": ["cockpit_event"],
                        "states": ["ACTIVE"],
                        "allowed_path_prefixes": ["reports/"],
                        "max_per_loop": max_per_loop,
                    }
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_policy_gate_fail_closed_when_no_policy(tmp_path, monkeypatch):
    _write_current(tmp_path)
    monkeypatch.setattr(policy_gate, "_DEFAULT_POLICY_PATH", tmp_path / "missing_default.json")
    decision = policy_gate.enforce_db_write_policy(
        tmp_path,
        operation="knowledge.incremental_index",
        actor="cockpit_event",
        target_path=tmp_path / "reports" / "report_TASK_0001_L01_v01.md",
    )
    assert decision.allowed is False
    assert "fail-closed" in decision.reason


def test_policy_gate_allows_valid_incremental_index(tmp_path):
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    _write_current(tmp_path, loop_num=7, status="ACTIVE")
    _write_policy(tmp_path, max_per_loop=3)
    target = tmp_path / "reports" / "report_TASK_0001_L07_v01.md"
    target.write_text("# test", encoding="utf-8")

    decision = policy_gate.enforce_db_write_policy(
        tmp_path,
        operation="knowledge.incremental_index",
        actor="cockpit_event",
        target_path=target,
    )
    assert decision.allowed is True
    state = json.loads((tmp_path / "logs" / "policy_gate_state.json").read_text(encoding="utf-8"))
    assert state["counters"]["L7:knowledge.incremental_index:cockpit_event"] == 1


def test_policy_gate_denies_disallowed_actor(tmp_path):
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    _write_current(tmp_path, status="ACTIVE")
    _write_policy(tmp_path)
    target = tmp_path / "reports" / "report_TASK_0001_L01_v01.md"
    target.write_text("# test", encoding="utf-8")

    decision = policy_gate.enforce_db_write_policy(
        tmp_path,
        operation="knowledge.incremental_index",
        actor="api",
        target_path=target,
    )
    assert decision.allowed is False
    assert "not allowed" in decision.reason


def test_policy_gate_enforces_per_loop_quota(tmp_path):
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    _write_current(tmp_path, loop_num=11, status="ACTIVE")
    _write_policy(tmp_path, max_per_loop=1)
    target = tmp_path / "reports" / "report_TASK_0001_L11_v01.md"
    target.write_text("# test", encoding="utf-8")

    first = policy_gate.enforce_db_write_policy(
        tmp_path,
        operation="knowledge.incremental_index",
        actor="cockpit_event",
        target_path=target,
    )
    second = policy_gate.enforce_db_write_policy(
        tmp_path,
        operation="knowledge.incremental_index",
        actor="cockpit_event",
        target_path=target,
    )
    assert first.allowed is True
    assert second.allowed is False
    assert "quota exceeded" in second.reason

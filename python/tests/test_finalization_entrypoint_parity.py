import json

import pytest

import loop_cockpit


def test_finalize_api_and_procedure_fail_identically_on_canonical_gate(client, monkeypatch):
    """Both finalize entry paths must use the same canonical gate function."""
    calls = {"count": 0}

    def fake_gate():
        calls["count"] += 1
        return (False, "CANONICAL_GATE_FIXTURE_FAILURE")

    monkeypatch.setattr(loop_cockpit, "validate_finalization_entry_gates", fake_gate)
    monkeypatch.setattr(
        loop_cockpit,
        "read_json_file",
        lambda _path: {"STATE": {"loop": 141, "status": "ACTIVE", "lastTaskWorked": "TASK_0270"}},
    )

    with pytest.raises(ValueError, match="CANONICAL_GATE_FIXTURE_FAILURE"):
        loop_cockpit.finalize_loop_procedure()

    response = client.post("/api/finalize-loop", json={})
    assert response.status_code == 400
    body = json.loads(response.data)
    assert "CANONICAL_GATE_FIXTURE_FAILURE" in body["error"]
    assert calls["count"] == 2


def test_finalize_api_marks_validation_failure_as_blocked(client, monkeypatch):
    """API should preserve blocked semantics when canonical validation fails."""
    monkeypatch.setattr(
        loop_cockpit,
        "validate_finalization_entry_gates",
        lambda: (False, "CANONICAL_BLOCKED_FIXTURE"),
    )
    monkeypatch.setattr(
        loop_cockpit,
        "read_json_file",
        lambda _path: {"STATE": {"loop": 141, "status": "ACTIVE", "lastTaskWorked": "TASK_0270"}},
    )

    response = client.post("/api/finalize-loop", json={})
    assert response.status_code == 400
    body = response.get_json()
    assert body["blocked"] is True
    assert "CANONICAL_BLOCKED_FIXTURE" in body["error"]

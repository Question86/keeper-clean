import json

import loop_cockpit


def test_api_policy_gate_status_returns_snapshot(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "db_write_policy.json").write_text(
        json.dumps(
            {
                "enabled": True,
                "operations": {
                    "knowledge.rebuild": {
                        "actors": ["api"],
                        "states": ["ACTIVE"],
                        "max_per_loop": 2,
                    }
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (tmp_path / "current.json").write_text(
        json.dumps({"STATE": {"loop": 133, "status": "ACTIVE"}}, indent=2),
        encoding="utf-8",
    )

    monkeypatch.setattr(loop_cockpit, "WORKSPACE_ROOT", tmp_path)
    client = loop_cockpit.app.test_client()
    response = client.get("/api/policy-gate/status")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    status = payload["status"]
    assert status["policy_loaded"] is True
    assert status["state"] == "ACTIVE"
    assert "knowledge.rebuild" in status["operations"]

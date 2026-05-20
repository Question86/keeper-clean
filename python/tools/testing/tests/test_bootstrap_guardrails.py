# MODE: TEST\n\nimport importlib
import os
import json
from pathlib import Path
import tempfile

import pytest


def _write_current(path: Path, status: str, loop: int = 999):
    data = {
        "STATE": {
            "loop": loop,
            "status": status,
            "archiveCurrent": "archive/ARCHIV_0001.md",
            "archiveInProgress": None,
            "lastTaskWorked": None,
            "lastUpdate": "2026-01-01T00:00:00Z",
            "summary": "test",
            "validationHash": None,
            "transitionTrigger": None
        }
    }
    (path / "current.json").write_text(json.dumps(data, indent=2))


def test_confirm_blocked_when_bootstrap_present(tmp_path, monkeypatch):
    # Arrange: create isolated workspace with _BOOTSTRAP.md present and READY_FOR_RESET
    ws = tmp_path / "ws"
    ws.mkdir()
    _write_current(ws, "READY_FOR_RESET", loop=42)
    (ws / "_BOOTSTRAP.md").write_text("bootstrap placeholder")

    monkeypatch.setenv("LOOP_WORKSPACE", str(ws))

    # Reload modules to pick up new WORKSPACE_ROOT
    import loop_cockpit as lc
    importlib.reload(lc)

    app = lc.app
    with app.test_client() as client:
        resp = client.post('/api/confirm-bootstrap')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data is not None
        assert data.get('success') is False
        assert "_BOOTSTRAP.md" in data.get('error', '') or "blocked" in data.get('error', '')

        # Confirm state not changed
        cur = json.loads((ws / "current.json").read_text())
        assert cur['STATE']['status'] == 'READY_FOR_RESET'


def test_confirm_allows_with_incident_ack(tmp_path, monkeypatch):
    # Arrange: workspace with bootstrap present but ack provided
    ws = tmp_path / "ws2"
    ws.mkdir()
    _write_current(ws, "READY_FOR_RESET", loop=43)
    (ws / "_BOOTSTRAP.md").write_text("bootstrap placeholder")

    monkeypatch.setenv("LOOP_WORKSPACE", str(ws))
    import loop_cockpit as lc
    importlib.reload(lc)

    app = lc.app
    with app.test_client() as client:
        ack_resp = client.post('/api/ack-incident', json={'id': 'INC_TEST', 'ack_by': 'tester', 'notes': 'recovery'})
        assert ack_resp.status_code == 200
        # Now confirm bootstrap should succeed
        resp = client.post('/api/confirm-bootstrap')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data and data.get('success') is True
        cur = json.loads((ws / "current.json").read_text())
        assert cur['STATE']['status'] == 'ACTIVE'


def test_metadata_lint_flags_bootstrap_present_during_active(tmp_path):
    ws = tmp_path / "ws3"
    ws.mkdir()
    _write_current(ws, "ACTIVE", loop=99)
    (ws / "_BOOTSTRAP.md").write_text("leftover bootstrap")

    import loop_guardrails as lg

    res = lg.metadata_lint(ws)
    assert isinstance(res, dict)
    codes = {e['code'] for e in res.get('errors', [])}
    assert 'BOOTSTRAP_PRESENT_DURING_ACTIVE' in codes

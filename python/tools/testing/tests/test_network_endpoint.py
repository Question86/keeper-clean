# MODE: TEST\n\nimport importlib
import json
from pathlib import Path


def test_api_status_schema(tmp_path, monkeypatch):
    # Arrange: point workspace to tmp (copy minimal current.json)
    ws = tmp_path / "ws"
    ws.mkdir()
    data = {
        "STATE": {
            "loop": 1,
            "status": "ACTIVE",
            "archiveCurrent": "archive/ARCHIV_0001.md",
            "archiveInProgress": None,
            "lastTaskWorked": None,
            "lastUpdate": "2026-01-01T00:00:00Z",
            "summary": "test",
            "validationHash": None,
                                    "transitionTrigger": None
        }
    }
    (ws / "current.json").write_text(json.dumps(data, indent=2))

    monkeypatch.setenv("LOOP_WORKSPACE", str(ws))

    import loop_cockpit as lc
    importlib.reload(lc)
    app = lc.app

    with app.test_client() as client:
        resp = client.get('/api/status')
        assert resp.status_code == 200
        body = resp.get_json()
        assert isinstance(body, dict)
        # Basic schema expectations
        assert 'loop' in body and isinstance(body['loop'], int)
        assert 'status' in body and isinstance(body['status'], str)
        assert 'summary' in body and isinstance(body['summary'], str)
        assert 'activeTasks' in body and isinstance(body['activeTasks'], int)
        assert 'gateStatus' in body

# MODE: TEST\n\nimport json
from pathlib import Path
import pytest

import loop_cockpit as lc


def setup_workspace(ws: Path):
    ws.mkdir(parents=True, exist_ok=True)
    (ws / 'reports').mkdir()
    # NEU.md with TASK QUEUE section
    (ws / 'NEU.md').write_text('# NEU\n\n## TASK QUEUE\n\n')
    # Alt.md contains a blocked task reference (task 0001)
    (ws / 'Alt.md').write_text('# ALT\n\n- tasks/task_0001.md - blocked')


def test_reopen_emits_ready_marker(tmp_path, monkeypatch):
    ws = tmp_path / 'ws'
    setup_workspace(ws)

    # Configure workspace in module
    monkeypatch.setattr(lc, 'WORKSPACE_ROOT', ws)
    monkeypatch.setattr(lc, 'CURRENT_JSON', ws / 'current.json')
    monkeypatch.setattr(lc, 'NEU_MD', ws / 'NEU.md')
    monkeypatch.setattr(lc, 'ALT_MD', ws / 'Alt.md')

    # Create a minimal current.json so reopen may succeed
    cur = {"STATE": {"loop": 10, "status": "ACTIVE", "archiveCurrent": None,
                      "archiveInProgress": None, "lastTaskWorked": None}}
    (ws / 'current.json').write_text(json.dumps(cur, indent=2))

    client = lc.app.test_client()
    resp = client.post('/api/reopen-task', json={'task_id': '0001', 'reason': 'test'})
    data = resp.get_json()
    assert data.get('success') is True

    report = ws / 'reports' / 'report_TASK_0001_L10_v01.md'
    ready = ws / 'reports' / 'report_TASK_0001_L10_v01.md.ready'

    assert report.exists(), "Report should exist after reopen"
    assert ready.exists(), "Ready marker should have been emitted automatically"
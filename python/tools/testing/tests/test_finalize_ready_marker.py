# MODE: TEST\n\nimport json
import os
import time
from pathlib import Path

import pytest

import loop_cockpit as lc
from loop_cockpit import finalize_loop_procedure


def write_current(ws: Path, loop=400, status='ACTIVE', last=None):
    cur = {"STATE": {"loop": loop, "status": status, "archiveCurrent": "archive/ARCHIV_0399.md",
                      "archiveInProgress": None, "lastTaskWorked": last, "lastUpdate": "2026-01-01T00:00:00Z",
                      "summary": "test", "validationHash": None, "transitionTrigger": None}}
    (ws / 'current.json').write_text(json.dumps(cur, indent=2))


def test_finalize_accepts_ready_marker(tmp_path, monkeypatch):
    ws = tmp_path / 'ws'
    ws.mkdir()
    (ws / 'reports').mkdir()

    write_current(ws, loop=400, status='ACTIVE', last='TASK_0001')

    report_path = ws / 'reports' / 'report_TASK_0001_L400_v01.md'
    report_path.write_text('# report')
    # create .ready marker immediately
    ready_path = ws / 'reports' / 'report_TASK_0001_L400_v01.md.ready'
    ready_path.write_text('ready')

    monkeypatch.setattr(lc, 'WORKSPACE_ROOT', ws)
    monkeypatch.setattr(lc, 'CURRENT_JSON', ws / 'current.json')
    monkeypatch.setattr(lc, 'NEU_MD', ws / 'NEU.md')
    monkeypatch.setattr(lc, 'ALT_MD', ws / 'Alt.md')
    (ws / 'NEU.md').write_text('# NEU')
    (ws / 'Alt.md').write_text('# Alt')
    monkeypatch.setattr(lc, 'metadata_lint', lambda w: {'errors': [], 'warnings': []})
    monkeypatch.setattr(lc, 'check_archive_consistency', lambda ws: {'is_consistent': True, 'warnings': []})

    res = finalize_loop_procedure()
    assert res.get('success') is True
    archiv = ws / f"ARCHIV_{400:04d}.md"
    assert archiv.exists()

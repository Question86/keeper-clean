# MODE: TEST\n\nimport json
import time
from pathlib import Path

import pytest

import loop_cockpit as lc
from loop_cockpit import finalize_loop_procedure


def write_current(ws: Path, loop=200, status='ACTIVE', last=None):
    cur = {"STATE": {"loop": loop, "status": status, "archiveCurrent": "archive/ARCHIV_0199.md",
                      "archiveInProgress": None, "lastTaskWorked": last, "lastUpdate": "2026-01-01T00:00:00Z",
                      "summary": "test", "validationHash": None, "transitionTrigger": None}}
    (ws / 'current.json').write_text(json.dumps(cur, indent=2))


def test_finalize_blocks_on_fresh_report(tmp_path, monkeypatch):
    ws = tmp_path / 'ws'
    ws.mkdir()
    (ws / 'reports').mkdir()

    write_current(ws, loop=200, status='ACTIVE', last='TASK_0001')

    # create a fresh report (mtime = now)
    report_path = ws / 'reports' / 'report_TASK_0001_L200_v01.md'
    report_path.write_text('# report')

    # Point the workspace used by loop_cockpit to our tmp ws
    monkeypatch.setattr(lc, 'WORKSPACE_ROOT', ws)
    monkeypatch.setattr(lc, 'CURRENT_JSON', ws / 'current.json')
    monkeypatch.setattr(lc, 'NEU_MD', ws / 'NEU.md')
    monkeypatch.setattr(lc, 'ALT_MD', ws / 'Alt.md')
    (ws / 'NEU.md').write_text('# NEU')
    (ws / 'Alt.md').write_text('# Alt')
    # Stub metadata_lint to avoid unrelated lint failures
    monkeypatch.setattr(lc, 'metadata_lint', lambda w: {'errors': [], 'warnings': []})
    # Also stub check_archive_consistency to avoid external checks
    monkeypatch.setattr(lc, 'check_archive_consistency', lambda ws: {'is_consistent': True, 'warnings': []})

    with pytest.raises(ValueError) as ei:
        finalize_loop_procedure()
    assert 'REPORT_TOO_FRESH' in str(ei.value)


def test_finalize_allows_on_old_report(tmp_path, monkeypatch):
    ws = tmp_path / 'ws2'
    ws.mkdir()
    (ws / 'reports').mkdir()

    write_current(ws, loop=201, status='ACTIVE', last='TASK_0001')

    report_path = ws / 'reports' / 'report_TASK_0001_L201_v01.md'
    report_path.write_text('# report')
    # set mtime to old (2 minutes ago)
    old_ts = int(time.time()) - 120
    Path(report_path).stat().st_mtime
    import os
    os.utime(report_path, (old_ts, old_ts))

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
    # cleanup created archiv
    archiv = ws / f"ARCHIV_{201:04d}.md"
    assert archiv.exists()

# MODE: TEST\n\nimport json
import os
import time
import threading
from pathlib import Path

import pytest

import loop_cockpit as lc
from loop_cockpit import finalize_loop_procedure


def write_current(ws: Path, loop=300, status='ACTIVE', last=None):
    cur = {"STATE": {"loop": loop, "status": status, "archiveCurrent": "archive/ARCHIV_0299.md",
                      "archiveInProgress": None, "lastTaskWorked": last, "lastUpdate": "2026-01-01T00:00:00Z",
                      "summary": "test", "validationHash": None, "transitionTrigger": None}}
    (ws / 'current.json').write_text(json.dumps(cur, indent=2))


def test_finalize_retries_and_succeeds(tmp_path, monkeypatch):
    ws = tmp_path / 'ws'
    ws.mkdir()
    (ws / 'reports').mkdir()

    write_current(ws, loop=300, status='ACTIVE', last='TASK_0001')

    report_path = ws / 'reports' / 'report_TASK_0001_L300_v01.md'
    report_path.write_text('# report')

    # make settings short for test
    monkeypatch.setattr(lc, 'REPORT_FRESHNESS_SECONDS', 60)
    monkeypatch.setattr(lc, 'REPORT_FRESHNESS_MAX_RETRIES', 3)
    monkeypatch.setattr(lc, 'REPORT_FRESHNESS_RETRY_INTERVAL', 1)

    # point workspace
    monkeypatch.setattr(lc, 'WORKSPACE_ROOT', ws)
    monkeypatch.setattr(lc, 'CURRENT_JSON', ws / 'current.json')
    monkeypatch.setattr(lc, 'NEU_MD', ws / 'NEU.md')
    monkeypatch.setattr(lc, 'ALT_MD', ws / 'Alt.md')
    (ws / 'NEU.md').write_text('# NEU')
    (ws / 'Alt.md').write_text('# Alt')
    monkeypatch.setattr(lc, 'metadata_lint', lambda w: {'errors': [], 'warnings': []})
    monkeypatch.setattr(lc, 'check_archive_consistency', lambda ws: {'is_consistent': True, 'warnings': []})

    # Background thread to 'finalize' report by moving mtime to old after 1s
    def make_report_old_later():
        time.sleep(1)
        old_ts = int(time.time()) - 120
        os.utime(report_path, (old_ts, old_ts))

    t = threading.Thread(target=make_report_old_later)
    t.start()

    res = finalize_loop_procedure()
    assert res.get('success') is True
    t.join()


def test_finalize_fails_after_retries(tmp_path, monkeypatch):
    ws = tmp_path / 'ws2'
    ws.mkdir()
    (ws / 'reports').mkdir()

    write_current(ws, loop=301, status='ACTIVE', last='TASK_0001')

    report_path = ws / 'reports' / 'report_TASK_0001_L301_v01.md'
    report_path.write_text('# report')

    # configure retries short and freshness long so it remains fresh
    monkeypatch.setattr(lc, 'REPORT_FRESHNESS_SECONDS', 3600)
    monkeypatch.setattr(lc, 'REPORT_FRESHNESS_MAX_RETRIES', 2)
    monkeypatch.setattr(lc, 'REPORT_FRESHNESS_RETRY_INTERVAL', 1)

    monkeypatch.setattr(lc, 'WORKSPACE_ROOT', ws)
    monkeypatch.setattr(lc, 'CURRENT_JSON', ws / 'current.json')
    monkeypatch.setattr(lc, 'NEU_MD', ws / 'NEU.md')
    monkeypatch.setattr(lc, 'ALT_MD', ws / 'Alt.md')
    (ws / 'NEU.md').write_text('# NEU')
    (ws / 'Alt.md').write_text('# Alt')
    monkeypatch.setattr(lc, 'metadata_lint', lambda w: {'errors': [], 'warnings': []})
    monkeypatch.setattr(lc, 'check_archive_consistency', lambda ws: {'is_consistent': True, 'warnings': []})

    with pytest.raises(ValueError) as ei:
        finalize_loop_procedure()
    assert 'REPORT_TOO_FRESH' in str(ei.value)

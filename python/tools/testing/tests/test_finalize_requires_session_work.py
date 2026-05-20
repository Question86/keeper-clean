# MODE: TEST\n\nimport json
import os
from pathlib import Path
import time
import pytest

import loop_cockpit as lc
from loop_cockpit import finalize_loop_procedure


def write_current(ws: Path, loop=500, status='ACTIVE', last=None):
    cur = {"STATE": {"loop": loop, "status": status, "archiveCurrent": None,
                      "archiveInProgress": None, "lastTaskWorked": last, "lastUpdate": "2026-01-01T00:00:00Z",
                      "summary": "test", "validationHash": None, "transitionTrigger": None}}
    (ws / 'current.json').write_text(json.dumps(cur, indent=2))


def append_txn(ws: Path, entry: dict):
    path = ws / '_transaction_log.jsonl'
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def test_blocks_when_no_confirm_bootstrap(tmp_path, monkeypatch):
    ws = tmp_path / 'ws'
    ws.mkdir()
    (ws / 'reports').mkdir()

    write_current(ws, loop=500, status='ACTIVE', last='TASK_0001')

    monkeypatch.setattr(lc, 'WORKSPACE_ROOT', ws)
    monkeypatch.setattr(lc, 'CURRENT_JSON', ws / 'current.json')
    monkeypatch.setattr(lc, 'NEU_MD', ws / 'NEU.md')
    monkeypatch.setattr(lc, 'ALT_MD', ws / 'Alt.md')
    monkeypatch.setattr(lc, 'TRANSACTION_LOG', ws / '_transaction_log.jsonl')
    (ws / 'NEU.md').write_text('# NEU')
    (ws / 'Alt.md').write_text('# Alt')
    # No transaction log entries
    monkeypatch.setattr(lc, 'metadata_lint', lambda w: {'errors': [], 'warnings': []})
    monkeypatch.setattr(lc, 'check_archive_consistency', lambda ws: {'is_consistent': True, 'warnings': []})
    # Bypass REPORT-FIRST audit for session-check unit test
    monkeypatch.setattr(lc, 'audit_loop_integrity', lambda: (True, [], []))

    with pytest.raises(ValueError) as exc:
        finalize_loop_procedure()
    assert 'MISSING_CONFIRM_BOOTSTRAP' in str(exc.value)


def test_blocks_when_no_work_after_confirm(tmp_path, monkeypatch):
    ws = tmp_path / 'ws'
    ws.mkdir()
    (ws / 'reports').mkdir()

    write_current(ws, loop=501, status='ACTIVE', last='TASK_0001')

    # Add a confirm-bootstrap entry only
    ts = "2026-01-24T00:00:00Z"
    append_txn(ws, {"timestamp": ts, "operation": "confirm-bootstrap", "target": "_LOOP_GATE.md", "from": None, "to": "confirm-bootstrap", "outcome": "SUCCESS", "details": ""})

    monkeypatch.setattr(lc, 'WORKSPACE_ROOT', ws)
    monkeypatch.setattr(lc, 'CURRENT_JSON', ws / 'current.json')
    monkeypatch.setattr(lc, 'NEU_MD', ws / 'NEU.md')
    monkeypatch.setattr(lc, 'ALT_MD', ws / 'Alt.md')
    monkeypatch.setattr(lc, 'TRANSACTION_LOG', ws / '_transaction_log.jsonl')
    (ws / 'NEU.md').write_text('# NEU')
    (ws / 'Alt.md').write_text('# Alt')
    monkeypatch.setattr(lc, 'metadata_lint', lambda w: {'errors': [], 'warnings': []})
    monkeypatch.setattr(lc, 'check_archive_consistency', lambda ws: {'is_consistent': True, 'warnings': []})
    # Bypass REPORT-FIRST audit for session-check unit test
    monkeypatch.setattr(lc, 'audit_loop_integrity', lambda: (True, [], []))

    with pytest.raises(ValueError) as exc:
        finalize_loop_procedure()
    assert 'MISSING_SESSION_WORK' in str(exc.value)


def test_allows_when_work_present_after_confirm(tmp_path, monkeypatch):
    ws = tmp_path / 'ws'
    ws.mkdir()
    (ws / 'reports').mkdir()

    write_current(ws, loop=502, status='ACTIVE', last='TASK_0001')

    # Add confirm-bootstrap
    confirm_ts = "2026-01-24T00:00:00Z"
    append_txn(ws, {"timestamp": confirm_ts, "operation": "confirm-bootstrap", "target": "_LOOP_GATE.md", "from": None, "to": "confirm-bootstrap", "outcome": "SUCCESS", "details": ""})
    monkeypatch.setattr(lc, 'TRANSACTION_LOG', ws / '_transaction_log.jsonl')

    # Add a SUCCESSful file_write later
    later_ts = "2026-01-24T00:00:01Z"
    append_txn(ws, {"timestamp": later_ts, "operation": "file_write", "target": "report_TASK_0001_L502_v01.md", "from": None, "to": "written", "outcome": "SUCCESS", "details": ""})

    # Create actual report file so freshness & report checks pass
    report_path = ws / 'reports' / 'report_TASK_0001_L502_v01.md'
    report_path.write_text('# report')

    monkeypatch.setattr(lc, 'WORKSPACE_ROOT', ws)
    monkeypatch.setattr(lc, 'CURRENT_JSON', ws / 'current.json')
    monkeypatch.setattr(lc, 'NEU_MD', ws / 'NEU.md')
    monkeypatch.setattr(lc, 'ALT_MD', ws / 'Alt.md')
    (ws / 'NEU.md').write_text('# NEU')
    (ws / 'Alt.md').write_text('# Alt')
    monkeypatch.setattr(lc, 'metadata_lint', lambda w: {'errors': [], 'warnings': []})
    monkeypatch.setattr(lc, 'check_archive_consistency', lambda ws: {'is_consistent': True, 'warnings': []})
    # Bypass REPORT-FIRST audit and disable freshness waiting for this test
    monkeypatch.setattr(lc, 'audit_loop_integrity', lambda: (True, [], []))
    monkeypatch.setattr(lc, 'REPORT_FRESHNESS_SECONDS', 0)

    res = finalize_loop_procedure()
    assert res.get('success') is True
    archiv = ws / f"ARCHIV_{502:04d}.md"
    assert archiv.exists()

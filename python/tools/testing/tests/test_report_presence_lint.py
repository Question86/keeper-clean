# MODE: TEST\n\nimport json
from pathlib import Path
import tempfile

from loop_guardrails import metadata_lint


def _write_current(tmp, loop=99, status="FINALIZED", lastTaskWorked=None):
    cur = {
        "STATE": {
            "loop": loop,
            "status": status,
            "archiveCurrent": "archive/ARCHIV_0099.md",
            "archiveInProgress": None,
            "lastTaskWorked": lastTaskWorked,
            "lastUpdate": "2026-01-01T00:00:00Z",
            "summary": "test",
            "validationHash": None,
                                    "transitionTrigger": None
        }
    }
    (tmp / "current.json").write_text(json.dumps(cur, indent=2))


def test_finalized_loop_requires_reports(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _write_current(ws, loop=99, status="FINALIZED", lastTaskWorked=None)

    # No reports present
    res = metadata_lint(ws)
    codes = {e['code'] for e in res.get('errors', [])}
    assert 'REPORTS_MISSING_FOR_LOOP' in codes


def test_finalized_loop_with_report_passes(tmp_path):
    ws = tmp_path / "ws2"
    ws.mkdir()
    _write_current(ws, loop=99, status="FINALIZED", lastTaskWorked="TASK_0001")

    # Create a report for loop 99
    (ws / 'reports').mkdir()
    (ws / 'reports' / 'report_TASK_0001_L99_v01.md').write_text('# report')

    res = metadata_lint(ws)
    codes = {e['code'] for e in res.get('errors', [])}
    assert 'REPORTS_MISSING_FOR_LOOP' not in codes

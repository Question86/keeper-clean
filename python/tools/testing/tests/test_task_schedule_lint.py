# MODE: TEST

import json
from pathlib import Path

from loop_guardrails import metadata_lint


def test_schedule_format_check(tmp_path):
    # Create minimal workspace
    (tmp_path / "tasks").mkdir()
    current = {
        "STATE": {
            "loop": 1,
            "status": "READY_FOR_RESET",
            "archiveCurrent": None,
            "archiveInProgress": None,
            "lastTaskWorked": None,
            "lastUpdate": "2026-01-24T00:00:00Z",
            "summary": "test"
        },
        "TASK_REGISTER": {}
    }
    (tmp_path / "current.json").write_text(json.dumps(current))

    # Create a task with a non-numeric SCHEDULED value
    task_path = tmp_path / "tasks" / "task_TASK_9999.md"
    task_path.write_text("""# TASK_9999

MODE: TASK SPECIFICATION
STATUS: NEW
SCHEDULED: NEXT_LOOP
""")

    res = metadata_lint(tmp_path)
    codes = {e['code'] for e in res.get('errors', [])}
    assert 'SCHEDULE_FORMAT' in codes, f"Expected SCHEDULE_FORMAT error in {res}"

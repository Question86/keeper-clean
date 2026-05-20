# MODE: TEST\n\nimport subprocess
from pathlib import Path

TOOLS = Path('tools')
SCRIPT = TOOLS / 'find_jailbreaks.py'


def test_find_jailbreaks_reports_incidents():
    assert SCRIPT.exists()
    proc = subprocess.run(['python', str(SCRIPT)], capture_output=True, text=True)
    # Script returns non-zero when findings are present (expected here)
    assert proc.returncode != 0
    out = proc.stdout
    assert 'findings_count' in out
    assert 'BOOTSTRAP' in out or 'confirm-bootstrap' in out or 'incident_report' in out

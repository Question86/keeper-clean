import subprocess
import sys
from pathlib import Path


def test_query_knowledge_cli_runs():
    script = Path("tools/query_knowledge.py")
    assert script.exists(), "query tool missing"

    proc = subprocess.run(
        [sys.executable, str(script), "bootstrap", "--limit", "2"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "Querying knowledge database for:" in out

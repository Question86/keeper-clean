from pathlib import Path
p=Path('tests/test_task_0022_real_integration.py')
content=r'''# MODE: TEST

"""Integration test for TASK_0022 POC in real mode using local Ollama.

This test runs only when Ollama is reachable and the required model is installed.
It will be skipped otherwise to avoid causing CI failures on systems without Ollama.
"""
import os
import subprocess
import socket
import pytest
from pathlib import Path

POC_SCRIPT = Path("tasks/poc_task_0022.py")
OUTDIR = Path("samples/task_0022_real_integration")
MODEL = os.environ.get("OLLAMA_MODEL", "mixtral:8x7b")
OLLAMA_EXE = r"C:\Users\ambas\AppData\Local\Programs\Ollama\ollama.exe"


def is_ollama_running(host="127.0.0.1", port=11434, timeout=1.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def has_model(model_name: str) -> bool:
    try:
        proc = subprocess.run([OLLAMA_EXE, "list"], capture_output=True, text=True, timeout=5)
        return model_name in proc.stdout
    except Exception:
        return False


@pytest.mark.skipif(not is_ollama_running(), reason="Ollama server not running on localhost:11434")
@pytest.mark.skipif(not has_model(MODEL), reason=f"Required model {MODEL} not available")
def test_poc_real_integration():
    # Run the POC in real mode; it should produce calendar.ics and README.md
    env = os.environ.copy()
    env["OLLAMA_MODEL"] = MODEL
    proc = subprocess.run(["python", str(POC_SCRIPT), "--mode", "real", "--outdir", str(OUTDIR)], env=env)
    assert proc.returncode == 0
    assert (OUTDIR / "calendar.ics").exists()
    assert (OUTDIR / "README.md").exists()
'''
p.write_text(content, encoding='utf-8')
print('written', p)

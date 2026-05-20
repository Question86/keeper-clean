import pytest
import asyncio
import time
import requests
import subprocess
import os
from pathlib import Path

# ─── Einheitlicher Datenpfad ────────────────────────────────────────────────
# FIX: Vorher inkonsistent zwischen /data/jobs und /workspace/data/jobs
DATA_JOBS_DIR = "/workspace/data/jobs"

# Global process list für Cleanup
_procs: list[subprocess.Popen] = []


# ─── Event Loop ─────────────────────────────────────────────────────────────
# FIX: pytest-asyncio ≥ 0.21 deprecates custom event_loop fixtures mit
#      scope="session". Stattdessen asyncio_mode = "auto" in pytest.ini nutzen
#      und hier nur noch den Loop für session-scoped async fixtures bereitstellen.
@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# ─── Redis Readiness ─────────────────────────────────────────────────────────
def _wait_for_redis(timeout: int = 20) -> bool:
    """
    FIX: Vorher nur time.sleep(2) – Race Condition wenn Redis langsam startet.
    Jetzt echter PONG-Check bevor API/Worker gestartet werden.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["redis-cli", "-p", "6379", "ping"],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() == "PONG":
            return True
        time.sleep(0.5)
    return False


def _wait_for_api(url: str, timeout: int = 30) -> bool:
    """Poll API health endpoint bis er antwortet."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{url}/health", timeout=1)
            if r.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    return False


# ─── Services Fixture ────────────────────────────────────────────────────────
# FIX: async fixture mit scope="session" braucht asyncio_mode="auto" (pytest.ini)
#      Außerdem: Services werden jetzt erst gestartet wenn der vorherige ready ist
@pytest.fixture(scope="session")
async def services():
    print("\n🚀 Starting test services...")

    # 1. Redis starten
    redis_proc = subprocess.Popen(
        ["redis-server", "--port", "6379", "--loglevel", "warning"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _procs.append(redis_proc)

    # FIX: Echten PONG-Check statt blindem sleep
    if not _wait_for_redis(timeout=20):
        raise RuntimeError("❌ Redis failed to start within 20s")
    print("✅ Redis is ready")

    # 2. API Service starten
    # FIX: "api-service.app.main:app" ist kein gültiger Python-Modulpfad wegen
    #      des Bindestrichs. uvicorn mit --app-dir aufrufen statt Dot-Notation.
    api_proc = subprocess.Popen(
        [
            "uvicorn", "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--app-dir", "/workspace/api-service",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/workspace",
    )
    _procs.append(api_proc)

    # 3. Worker starten – erst NACHDEM Redis bereit ist
    worker_proc = subprocess.Popen(
        ["python", "worker-service/app/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/workspace",
    )
    _procs.append(worker_proc)

    # 4. Warten bis API antwortet
    api_url = "http://localhost:8000"
    if not _wait_for_api(api_url, timeout=30):
        # Stderr ausgeben um Startup-Fehler sichtbar zu machen
        _, err = api_proc.communicate(timeout=2)
        raise RuntimeError(
            f"❌ API service failed to start within 30s.\nSTDERR: {err.decode()}"
        )
    print("✅ All services are ready")

    yield {
        "api_url": api_url,
        "redis_proc": redis_proc,
        "api_proc": api_proc,
        "worker_proc": worker_proc,
    }

    # ── Cleanup ──────────────────────────────────────────────────────────────
    print("\n🧹 Cleaning up test services...")
    for proc in _procs:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    _procs.clear()


# ─── Sample Data ─────────────────────────────────────────────────────────────
@pytest.fixture
def sample_data(tmp_path):
    """
    FIX: tmp_path statt hardcoded /tmp/zee.txt – verhindert Paralleltest-Konflikte
    und wird automatisch von pytest aufgeräumt.
    """
    zee_content = """\
# Z boson analysis data
# Format: x (energy), w (weight), tag (event type)
12.5 1.2 Signal
15.8 0.8 Background
18.2 1.1 Signal
21.4 0.9 Background
25.6 1.3 Signal
30.1 0.7 Signal
35.2 1.0 Background
40.8 1.4 Signal
"""
    test_file = tmp_path / "zee.txt"
    test_file.write_text(zee_content)
    return str(test_file)


# ─── Session Hooks ───────────────────────────────────────────────────────────
def pytest_sessionstart(session):
    """Sicherstellen dass der einheitliche Datenpfad existiert."""
    # FIX: Einheitlicher Pfad DATA_JOBS_DIR statt /workspace/data/jobs hardcoded
    os.makedirs(DATA_JOBS_DIR, exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    """Letzte Absicherung: alle Prozesse killen."""
    subprocess.run(["taskkill", "/F", "/FI", "IMAGENAME eq uvicorn.exe"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/FI", "IMAGENAME eq python.exe"], capture_output=True)
    subprocess.run(["redis-cli", "shutdown", "nosave"], capture_output=True)

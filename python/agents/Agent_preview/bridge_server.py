#!/usr/bin/env python3
"""
bridge_server.py — Brücke zwischen Control Center UI und Agent.

Starten:  python bridge_server.py
Browser:  Öffne control_center.html  (oder http://localhost:8765)

Endpoints:
  GET  /status          → Services-Status + Agent-Zustand
  POST /agent/run       → Agent einmalig starten
  POST /agent/stop      → Agent stoppen
  POST /agent/test      → Nur Unit-Tests ausführen
  POST /agent/smoke     → Nur Smoke-Test ausführen
  GET  /log/stream      → Server-Sent Events (Live-Log)
  POST /config/save     → Config aus UI speichern → .env + Dateien
  GET  /config/load     → Aktuelle Config laden
"""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# FastAPI (pip install fastapi uvicorn)
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────
BRIDGE_PORT  = 8765
SCRIPT_DIR   = Path(__file__).resolve().parent
WORKSPACE    = Path(os.environ.get("WORKSPACE", str(SCRIPT_DIR)))
AGENT_SCRIPT = WORKSPACE / "autonomous_agent.py"
ENV_FILE     = WORKSPACE / ".env"
CONFIG_FILE  = WORKSPACE / "agent_ui_config.json"
AGENT_PYTHON = os.environ.get("AGENT_PYTHON", sys.executable)

app = FastAPI(title="CERN Scanner Bridge", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── State ─────────────────────────────────────────────────────────────────────
_state = {
    "agent_running": False,
    "agent_proc":    None,       # subprocess.Popen
    "log_lines":     [],         # ring buffer
    "cycle_count":   0,
    "last_cycle":    None,
    "services": {
        "redis":  "unknown",
        "api":    "unknown",
        "worker": "unknown",
    }
}

def _log(level: str, msg: str):
    ts = time.strftime("%H:%M:%S")
    line = {"ts": ts, "level": level, "msg": msg}
    _state["log_lines"].append(line)
    if len(_state["log_lines"]) > 500:
        _state["log_lines"].pop(0)
    try:
        print(f"[{ts}] {level:4s}  {msg}")
    except UnicodeEncodeError:
        safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
        print(f"[{ts}] {level:4s}  {safe_msg}")

# ── SSE Log Stream ─────────────────────────────────────────────────────────────
@app.get("/log/stream")
async def log_stream():
    """Server-Sent Events – UI abonniert diesen Endpoint für Live-Logs."""
    async def generate():
        sent = 0
        while True:
            lines = _state["log_lines"]
            while sent < len(lines):
                line = lines[sent]
                yield f"data: {json.dumps(line)}\n\n"
                sent += 1
            await asyncio.sleep(0.3)
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})

# ── Status ────────────────────────────────────────────────────────────────────
@app.get("/status")
def get_status():
    _check_services()
    return {
        "agent_running": _state["agent_running"],
        "cycle_count":   _state["cycle_count"],
        "last_cycle":    _state["last_cycle"],
        "services":      _state["services"],
        "log_count":     len(_state["log_lines"]),
    }

def _check_services():
    """Schneller Port-Check für Redis und API."""
    import socket
    config = _load_config()
    api_port = int(config.get("apiport", 8000))
    redis_port = 6379

    def port_open(host, port):
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False

    _state["services"]["redis"]  = "up" if port_open("localhost", redis_port) else "down"
    _state["services"]["api"]    = "up" if port_open("localhost", api_port)   else "down"
    # Worker: check if agent proc is alive
    proc = _state.get("agent_proc")
    _state["services"]["worker"] = "up" if (proc and proc.poll() is None) else "down"

def _resolve_existing_path(base_dir: Path, candidates: list[str]) -> str | None:
    for rel in candidates:
        p = base_dir / rel
        if p.exists():
            return str(p)
    return None

# ── Agent Run / Stop ──────────────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    continuous: bool = False
    interval:   int  = 60

@app.post("/agent/run")
def agent_run(req: AgentRunRequest, background_tasks: BackgroundTasks):
    if _state["agent_running"]:
        return {"ok": False, "msg": "Agent already running"}
    background_tasks.add_task(_run_agent, req.continuous, req.interval)
    return {"ok": True, "msg": "Agent started"}

def _run_agent(continuous: bool, interval: int):
    config = _load_config()
    env = _build_env(config)

    cmd = [AGENT_PYTHON, str(AGENT_SCRIPT)]
    if continuous:
        cmd += ["--continuous", str(interval)]

    _state["agent_running"] = True
    _state["cycle_count"] += 1
    _state["last_cycle"] = time.strftime("%H:%M:%S")
    _log("OK", f"Agent started (cycle #{_state['cycle_count']})")

    try:
        proc = subprocess.Popen(
            cmd, cwd=str(WORKSPACE),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', env=env,
            bufsize=1,
        )
        _state["agent_proc"] = proc

        # Stream stdout live into log
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            # Parse agent log format: [HH:MM:SS] 🤖 message
            level = "INFO"
            if "✅" in line or "🎉" in line or "OK" in line:
                level = "OK"
            elif "❌" in line or "💥" in line or "ERR" in line:
                level = "ERR"
            elif "⚠" in line or "WARN" in line:
                level = "WARN"
            _log(level, line)

        proc.wait()
        rc = proc.returncode
        _log("OK" if rc == 0 else "ERR",
             f"Agent exited (code {rc})")
    except Exception as e:
        _log("ERR", f"Agent launch failed: {e}")
    finally:
        _state["agent_running"] = False
        _state["agent_proc"] = None

@app.post("/agent/stop")
def agent_stop():
    proc = _state.get("agent_proc")
    if proc and proc.poll() is None:
        proc.terminate()
        _log("WARN", "Agent stop signal sent")
        return {"ok": True, "msg": "Agent stopped"}
    _state["agent_running"] = False
    return {"ok": True, "msg": "Agent was not running"}

# ── Quick Test Actions ────────────────────────────────────────────────────────

@app.post("/agent/test")
def run_unit_tests(background_tasks: BackgroundTasks):
    config = _load_config()
    base_dir = Path(config.get("workspace", str(WORKSPACE)))
    test_path = _resolve_existing_path(base_dir, ["tests/test_unit.py", "test_unit.py"])
    if not test_path:
        _log("ERR", "Unit test file not found (tests/test_unit.py | test_unit.py)")
        return {"ok": False, "msg": "Unit test file not found"}

    background_tasks.add_task(_run_cmd_logged,
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
        "Unit Tests"
    )
    return {"ok": True, "msg": "Unit tests started"}

@app.post("/agent/smoke")
def run_smoke_test(background_tasks: BackgroundTasks):
    config = _load_config()
    api_url = config.get("apiUrl", "http://localhost:8000")
    base_dir = Path(config.get("workspace", str(WORKSPACE)))
    smoke_path = _resolve_existing_path(base_dir, ["tests/smoke_test.py", "smoke_test.py"])
    if not smoke_path:
        _log("ERR", "Smoke test file not found (tests/smoke_test.py | smoke_test.py)")
        return {"ok": False, "msg": "Smoke test file not found"}

    background_tasks.add_task(_run_cmd_logged,
        [sys.executable, smoke_path, "--api-url", api_url],
        "Smoke Test"
    )
    return {"ok": True, "msg": "Smoke test started"}

def _run_cmd_logged(cmd, label):
    _log("INFO", f"→ {label}: {' '.join(cmd)}")
    config = _load_config()
    env = _build_env(config)
    cwd = config.get("workspace", str(WORKSPACE))
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(cwd),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=env, bufsize=1,
        )
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                level = "OK" if ("PASSED" in line or "passed" in line) else \
                        "ERR" if ("FAILED" in line or "ERROR" in line) else "INFO"
                _log(level, line)
        proc.wait()
        _log("OK" if proc.returncode == 0 else "ERR",
             f"{label} finished (code {proc.returncode})")
    except Exception as e:
        _log("ERR", f"{label} error: {e}")

# ── Config Save / Load ────────────────────────────────────────────────────────

class ConfigPayload(BaseModel):
    workspace:    str  = str(WORKSPACE)
    datadir:      str  = str(WORKSPACE / "data")
    continuous:   bool = False
    autofix:      bool = True
    interval:     int  = 60
    apiport:      int  = 8000
    llmPrimary:   str  = "ollama"
    ollamaUrl:    str  = "http://localhost:11434"
    ollamaModel:  str  = "codellama"
    openaiKey:    str  = ""
    openaiModel:  str  = "gpt-4o-mini"
    llmDisabled:  bool = False
    scanMin:      float = 60.0
    scanMax:      float = 120.0
    windowWidth:  float = 10.0
    windowStep:   float = 5.0
    bins:         int  = 50
    nToys:        int  = 2000
    calibrate:    bool = True
    apiUrl:       str  = "http://localhost:8000"
    redisUrl:     str  = "redis://localhost:6379/0"
    docker:       bool = False
    autostart:    bool = True

@app.post("/config/save")
def config_save(cfg: ConfigPayload):
    data = cfg.model_dump()

    # Persist to JSON
    CONFIG_FILE.write_text(json.dumps(data, indent=2))

    # Write .env
    env_content = f"""# Auto-generated by CERN Scanner Control Center
WORKSPACE={cfg.workspace}
DATA_DIR={cfg.datadir}
OLLAMA_URL={cfg.ollamaUrl}
OLLAMA_MODEL={cfg.ollamaModel}
OPENAI_API_KEY={cfg.openaiKey}
OPENAI_MODEL={cfg.openaiModel}
LLM_PRIMARY={cfg.llmPrimary}
LLM_DISABLED={'1' if cfg.llmDisabled else '0'}
REDIS_URL={cfg.redisUrl}
API_PORT={cfg.apiport}
"""
    ENV_FILE.write_text(env_content)

    # Generate launch command
    cmd = _generate_launch_cmd(data)

    _log("OK", f"Config saved → {CONFIG_FILE.name}, .env written")
    return {"ok": True, "env_file": str(ENV_FILE), "launch_cmd": cmd, "config": data}

@app.get("/config/load")
def config_load():
    return _load_config()

def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return ConfigPayload().model_dump()

def _build_env(config: dict) -> dict:
    env = os.environ.copy()
    env["WORKSPACE"]      = config.get("workspace", str(WORKSPACE))
    env["DATA_DIR"]       = config.get("datadir",   str(WORKSPACE / "data"))
    env["OLLAMA_URL"]     = config.get("ollamaUrl",  "http://localhost:11434")
    env["OLLAMA_MODEL"]   = config.get("ollamaModel","mistral")
    env["LLM_PRIMARY"]    = config.get("llmPrimary", "ollama")
    env["OPENAI_MODEL"]   = config.get("openaiModel", "gpt-4o-mini")
    env["LLM_DISABLED"]   = "1" if config.get("llmDisabled") else "0"
    env["REDIS_URL"]      = config.get("redisUrl",   "redis://localhost:6379/0")
    env["API_PORT"]       = str(config.get("apiport", 8000))
    env["PYTHONPATH"]     = config.get("workspace",  str(WORKSPACE))
    env["PYTHONIOENCODING"] = "utf-8"
    if config.get("openaiKey"):
        env["OPENAI_API_KEY"] = config["openaiKey"]
    return env

def _generate_launch_cmd(cfg: dict) -> str:
    lines = [
        f"WORKSPACE={cfg['workspace']}",
        f"DATA_DIR={cfg['datadir']}",
        f"OLLAMA_MODEL={cfg['ollamaModel']}",
        f"OPENAI_MODEL={cfg.get('openaiModel', 'gpt-4o-mini')}",
        f"LLM_PRIMARY={cfg.get('llmPrimary', 'ollama')}",
    ]
    if cfg.get("llmDisabled"):
        lines.append("LLM_DISABLED=1")
    cmd = " \\\n".join(lines)
    cmd += f" \\\npython autonomous_agent.py"
    if cfg.get("continuous"):
        cmd += f" --continuous {cfg.get('interval', 60)}"
    return cmd

# ── Serve control_center.html at root ────────────────────────────────────────
@app.get("/")
def serve_ui():
    html_path = WORKSPACE / "control_center.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>control_center.html not found in workspace</h1>")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    _log("OK", f"Bridge server starting on http://localhost:{BRIDGE_PORT}")
    _log("INFO", f"Workspace: {WORKSPACE}")
    _log("INFO", f"Agent: {AGENT_SCRIPT}")
    _log("INFO", "Open http://localhost:8765 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=BRIDGE_PORT, log_level="warning")

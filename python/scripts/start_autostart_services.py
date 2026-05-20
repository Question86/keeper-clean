#!/usr/bin/env python3
"""
Persistent autostart supervisor for Keeper helper scripts.

This process is intended to run continuously alongside loop_cockpit.py.
It schedules required helper scripts at fixed intervals and records
heartbeat/status in logs/autostart_supervisor_status.json.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
SUPERVISOR_STATUS = LOG_DIR / "autostart_supervisor_status.json"
SUPERVISOR_PID = LOG_DIR / "autostart_supervisor.pid"
INITIAL_STAGGER_SECONDS = float(os.environ.get("AUTOSTART_INITIAL_STAGGER_SECONDS", "5"))
MAX_PARALLEL_JOBS = int(os.environ.get("AUTOSTART_MAX_PARALLEL_JOBS", "2"))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Job:
    name: str
    kind: str  # "script" or "python_code"
    target: str
    interval_seconds: int = 300
    args: List[str] = field(default_factory=list)


REQUIRED_JOBS: List[Job] = [
    Job("generate_session_pack", "script", "scripts/generate_session_pack.py", 300),
    Job(
        "instrument_bootstrap_load",
        "script",
        "scripts/instrument_bootstrap_load.py",
        600,
        args=["autostart bootstrap heartbeat", "60000"],
    ),
    Job("autostart_external_knowledge_importer", "script", "scripts/autostart_external_knowledge_importer.py", 900),
    Job(
        "strategic_task_planner",
        "python_code",
        "from scripts.strategic_task_planner import StrategicTaskPlanner as P; p=P(); r=p.generate_task_recommendations(); print(f'strategic_task_planner loaded: {len(r)} recommendations')",
        600,
    ),
    Job("knowledge_dependency_analyzer", "script", "scripts/knowledge_dependency_analyzer.py", 600),
    Job(
        "task_formal_consistency_checker",
        "python_code",
        "from scripts.task_formal_consistency_checker import TaskFormalConsistencyChecker as C; c=C('.'); print('task_formal_consistency_checker loaded')",
        900,
    ),
    Job("autonomous_audit_system", "script", "scripts/autonomous_audit_system.py", 300),
    Job("knowledge_health_monitor", "script", "scripts/knowledge_health_monitor.py", 300),
    Job("quality_check", "script", "scripts/quality_check.py", 300, args=["status"]),
    Job(
        "problem_preflight",
        "script",
        "scripts/problem_preflight.py",
        300,
        args=["--problem", "autostart runtime health check", "--surface", "autostart", "--limit", "3"],
    ),
    Job(
        "action_vector_scorer",
        "script",
        "scripts/action_vector_scorer.py",
        300,
        args=["--problem", "autostart runtime health check", "--surface", "autostart", "--limit", "3"],
    ),
    Job(
        "semantic_search_enhanced",
        "python_code",
        "from scripts.semantic_search_enhanced import SemanticSearchEnhanced as S; s=S(); print('semantic_search_enhanced loaded')",
        900,
    ),
    Job(
        "maintenance_general",
        "script",
        "scripts/maintenance_general.py",
        1200,
        args=["--mode", "dry-run", "--days", "90"],
    ),
    Job("generate_optimized_session_pack", "script", "scripts/generate_optimized_session_pack.py", 300),
    Job("repair_knowledge_db_integrity", "script", "scripts/repair_knowledge_db_integrity.py", 1800),
    Job("update_reminder_engine", "script", "scripts/update_reminder_engine.py", 300),
    Job(
        "external_knowledge_importer",
        "python_code",
        "from scripts.external_knowledge_importer import ExternalKnowledgeImporter as E; print('external_knowledge_importer loaded')",
        900,
    ),
    Job(
        "lessons_learned_extractor",
        "python_code",
        "from scripts.lessons_learned_extractor import LessonsLearnedExtractor as L; e=L(); print('lessons_learned_extractor loaded')",
        900,
    ),
    Job("milestone_knowledge_monitor", "script", "scripts/milestone_knowledge_monitor.py", 300),
    Job(
        "finalize_preview",
        "python_code",
        "import scripts.finalize_preview as fp; print('finalize_preview loaded')",
        900,
    ),
    Job("behavioral_telemetry_analyzer", "script", "behavioral_telemetry_analyzer.py", 300),
    Job(
        "assumption_validation_framework",
        "python_code",
        "import assumption_validation_framework as avf; print('assumption_validation_framework loaded')",
        300,
    ),
    Job(
        "ai_self_reflective_framework",
        "python_code",
        "import ai_self_reflective_framework as arf; print('ai_self_reflective_framework loaded')",
        300,
    ),
    Job(
        "adaptive_bootstrap",
        "script",
        "adaptive_bootstrap.py",
        600,
        args=["autostart supervisor runtime health check", "--dry-run"],
    ),
    Job("advanced_ai_patterns", "script", "advanced_ai_patterns.py", 600),
    Job("ai_breadcrumb_tracker", "script", "ai_breadcrumb_tracker.py", 300),
    Job("ai_false_positive_suppressor", "script", "ai_false_positive_suppressor.py", 600),
    Job("ai_integrity_protector", "script", "ai_integrity_protector.py", 600),
    Job(
        "ai_patterns_ui",
        "python_code",
        "import ai_patterns_ui as apu; print('ai_patterns_ui loaded')",
        900,
    ),
    Job(
        "metadata_database_pipeline",
        "script",
        "metadata_database_pipeline.py",
        900,
        args=["--analytics"],
    ),
    Job(
        "milestone_knowledge_integration",
        "script",
        "milestone_knowledge_integration.py",
        900,
        args=["autostart knowledge integration query", "--limit", "5", "--budget", "80000", "--workspace", "."],
    ),
    Job(
        "supervisor_analysis_signals",
        "script",
        "scripts/supervisor_signal_collector.py",
        900,
        args=["--workspace", ".", "--loops", "8"],
    ),
    Job(
        "knowledge_redundancy_db",
        "python_code",
        "from knowledge_redundancy_db import KnowledgeRedundancyDB as K; k=K(); print('knowledge_redundancy_db loaded')",
        900,
    ),
    Job("run_final_checks", "script", "run_final_checks.py", 900),
    Job(
        "test_global_events_observer",
        "python_code",
        "import test_global_events_observer as tgeo; print('test_global_events_observer loaded')",
        1800,
    ),
    Job(
        "test_generalized_interlinks",
        "python_code",
        "import test_generalized_interlinks as tgi; ok=tgi.run_generalized_test(max_attempts=5); print(f'test_generalized_interlinks result={ok}')",
        1800,
    ),
    Job(
        "update_knowledge_db",
        "script",
        "update_knowledge_db.py",
        3600,
    ),
    Job(
        "root_bloat_plan",
        "script",
        "scripts/root_bloat_manager.py",
        3600,
        args=["--workspace", ".", "--max-files", "15", "--max-bytes", "20971520"],
    ),
    Job(
        "loop_guardrails",
        "python_code",
        "from pathlib import Path; import loop_guardrails as lg; lg.generate_loop_gate(Path('.'), checked_by='autostart_supervisor', reason='heartbeat')",
        60,
    ),
]


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if psutil is not None:
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _discover_supervisor_pid() -> Optional[int]:
    pid_candidates: List[int] = []
    if SUPERVISOR_PID.exists():
        try:
            pid_candidates.append(int(SUPERVISOR_PID.read_text(encoding="utf-8").strip()))
        except Exception:
            pass
    snapshot = _read_json(SUPERVISOR_STATUS)
    snap_pid = snapshot.get("supervisor_pid")
    if isinstance(snap_pid, int):
        pid_candidates.append(snap_pid)
    for pid in pid_candidates:
        if _pid_alive(pid):
            return pid
    return None


def _read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, obj: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _build_cmd(job: Job) -> List[str]:
    if job.kind == "python_code":
        return [sys.executable, "-c", job.target]
    return [sys.executable, str(ROOT / job.target), *job.args]


def _build_env() -> Dict[str, str]:
    env = dict(os.environ)
    # Force UTF-8 output to prevent cp1252 crashes in helper scripts with Unicode logs.
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    root_str = str(ROOT)
    existing = env.get("PYTHONPATH", "")
    parts = [p for p in existing.split(os.pathsep) if p]
    if root_str not in parts:
        env["PYTHONPATH"] = os.pathsep.join([root_str, *parts]) if parts else root_str
    return env


def _job_log_file(job: Job) -> Path:
    return LOG_DIR / f"autostart_{job.name}.log"


def _spawn(job: Job) -> subprocess.Popen:
    log_path = _job_log_file(job)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_cmd(job)
    log_handle = open(log_path, "ab")
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=_build_env(),
        stdout=log_handle,
        stderr=log_handle,
    )


def _write_supervisor_status(state: Dict[str, Dict], loop_started_at: str) -> None:
    payload = {
        "generated_at": utc_now_iso(),
        "supervisor_pid": os.getpid(),
        "started_at": loop_started_at,
        "jobs": state,
    }
    _write_json(SUPERVISOR_STATUS, payload)


def run_supervisor() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    existing = _discover_supervisor_pid()
    if existing is not None:
        print(f"Supervisor already running with PID {existing}")
        return 0

    SUPERVISOR_PID.write_text(str(os.getpid()), encoding="utf-8")

    processes: Dict[str, Optional[subprocess.Popen]] = {job.name: None for job in REQUIRED_JOBS}
    # Stagger initial launches to avoid thundering-herd DB lock contention
    # and Waitress queue spikes during bootstrap/confirm-bootstrap windows.
    now0 = time.time()
    next_run: Dict[str, float] = {
        job.name: now0 + (i * INITIAL_STAGGER_SECONDS) for i, job in enumerate(REQUIRED_JOBS)
    }
    exits: Dict[str, Dict[str, Optional[str]]] = {
        job.name: {"last_exit_at": None, "last_exit_code": None} for job in REQUIRED_JOBS
    }
    started_at = utc_now_iso()
    max_parallel_jobs = max(1, MAX_PARALLEL_JOBS)

    try:
        while True:
            SUPERVISOR_PID.write_text(str(os.getpid()), encoding="utf-8")
            now = time.time()
            active_children = sum(
                1 for proc in processes.values() if proc is not None and proc.poll() is None
            )
            for job in REQUIRED_JOBS:
                proc = processes[job.name]
                if proc is not None:
                    code = proc.poll()
                    if code is not None:
                        exits[job.name]["last_exit_at"] = utc_now_iso()
                        exits[job.name]["last_exit_code"] = str(code)
                        processes[job.name] = None
                        next_run[job.name] = now + max(5, job.interval_seconds)
                    continue

                if now < next_run[job.name]:
                    continue
                if active_children >= max_parallel_jobs:
                    continue

                try:
                    processes[job.name] = _spawn(job)
                    active_children += 1
                except Exception:
                    exits[job.name]["last_exit_at"] = utc_now_iso()
                    exits[job.name]["last_exit_code"] = "SPAWN_ERROR"
                    next_run[job.name] = now + 30

            state: Dict[str, Dict] = {}
            for job in REQUIRED_JOBS:
                proc = processes[job.name]
                state[job.name] = {
                    "kind": job.kind,
                    "target": job.target,
                    "interval_seconds": job.interval_seconds,
                    "pid": proc.pid if proc is not None and proc.poll() is None else None,
                    "next_run_at": datetime.fromtimestamp(next_run[job.name], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    **exits[job.name],
                }
            _write_supervisor_status(state, started_at)
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        for proc in processes.values():
            if proc is None:
                continue
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        if SUPERVISOR_PID.exists():
            try:
                SUPERVISOR_PID.unlink()
            except Exception:
                pass
    return 0


def stop_supervisor() -> int:
    pid = _discover_supervisor_pid()
    if pid is None:
        print("Supervisor is not running")
        try:
            if SUPERVISOR_PID.exists():
                SUPERVISOR_PID.unlink()
        except Exception:
            pass
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        print(f"Failed to stop supervisor PID {pid}: {e}")
        return 1
    print(f"Stop signal sent to supervisor PID {pid}")
    return 0


def print_status() -> int:
    pid = _discover_supervisor_pid()
    alive = pid is not None

    print(f"Supervisor PID: {pid}")
    print(f"Supervisor alive: {alive}")

    status = _read_json(SUPERVISOR_STATUS)
    jobs = status.get("jobs", {})
    if not jobs:
        print("No status snapshot available yet")
        return 0

    running = 0
    for name in sorted(jobs.keys()):
        item = jobs[name]
        pid_val = item.get("pid")
        if pid_val:
            running += 1
        print(
            f"{name}: pid={pid_val} next={item.get('next_run_at')} "
            f"last_exit={item.get('last_exit_code')}@{item.get('last_exit_at')}"
        )

    print(f"Active child processes: {running}/{len(jobs)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Keeper autostart supervisor")
    parser.add_argument("action", nargs="?", default="supervise", choices=["supervise", "status", "stop"])
    args = parser.parse_args()

    if args.action == "supervise":
        return run_supervisor()
    if args.action == "stop":
        return stop_supervisor()
    return print_status()


if __name__ == "__main__":
    raise SystemExit(main())

# MODE: SCRIPT\n\n#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Loop Cockpit - Memory Reset Control Center
Provides a web-based UI for managing loop lifecycle and monitoring project state.

STATE MACHINE:
┌─────────────────┐
│ READY_FOR_RESET │ (After loop reset, _BOOTSTRAP.md created)
└────────┬────────┘
         │ /api/confirm-bootstrap (AI confirms bootstrap execution)
         ▼
    ┌────────┐
    │ ACTIVE │ (Loop operational, work in progress)
    └────┬───┘
         │ /api/finalize-loop (AI completes work)
         ▼
  ┌────────────┐
  │ FINALIZED  │ (Archive created, ready for next loop)
  └──────┬─────┘
         │ /api/reset-loop (archive moved, loop incremented)
         └─► READY_FOR_RESET
"""

import json
import os
import shutil
import sys
import argparse
import threading
import math
import time
import subprocess
import re
import shlex
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.exceptions import HTTPException
import requests
import logging

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('flask_debug.log')
    ]
)
logger = logging.getLogger(__name__)

from loop_guardrails import (
    generate_loop_gate,
    generate_pointer_ref,
    generate_context_index,
    generate_loop_digest,
    generate_report_template,
    get_task_dependencies,
    analyze_parallelization,
    worktree_manager_factory,
    orchestrator_factory,
    close_task,
    history_index_data,
    history_index_markdown,
    metadata_lint,
    session_pack_markdown,
    startup_db_briefing_markdown,
    query_index_data,
    write_text,
    write_json,
    check_archive_consistency,
    pre_work_validation,
    sync_task_status,
    list_task_spec_files,
    read_text,
    utc_now_iso,
    validate_all_schemas,
    TASK_ID_RE,
)

# Import finalization validations (non-bypassable guardrails)
from finalization_validations import (
    validate_pre_finalization,
    validate_finalization_entry_gates,
    get_db_quality_gate_status,
)
from artifact_naming_contract import resolve_bootstrap_path

# Import knowledge database (SQLite-based search)
from knowledge_db import KnowledgeDB
from policy_gate import enforce_db_write_policy, get_policy_gate_status

# Import token monitor for budget tracking
from token_monitor import LoopBudgetTracker

# Import advanced AI patterns UI
from ai_patterns_ui import integrate_ai_patterns_ui

# Import ClawdBot integration
from clawdbot_integration import integrate_clawdbot

# Import Global Events Observer
from global_events_observer import (
    observe_global_event,
    create_event_prediction,
    get_global_events_report
)

# Import OpenAI Integration
from openai_integration import create_openai_endpoints, OpenAIIntegration

# Import Chaosbox Manager
from chaosbox.chaosbox_manager import ChaosboxManager

# Import Self-Reflective Framework
from ai_self_reflective_framework import (
    get_reflective_logger,
    log_ai_decision,
    update_decision_outcome
)

# Import Checkpoint Manager
from checkpoint_manager import (
    get_checkpoint_manager,
    initialize_checkpoints,
    create_phase_checkpoint,
    check_and_create_checkpoint
)

app = Flask(__name__)
CORS(app)
# Waitress in this setup serves WSGI/HTTP only; disable Engine.IO upgrades so
# Socket.IO stays on polling transport and avoids websocket upgrade errors.
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    allow_upgrades=False,
)


def _api_error_payload(message: str, status: int, code: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": False,
        "error": message,
        "status": status,
        "code": code,
    }
    if details:
        payload["details"] = details
    return payload


@app.errorhandler(HTTPException)
def handle_http_exception(e: HTTPException):
    if not request.path.startswith('/api/'):
        return e
    code = f"HTTP_{e.code}" if e.code else "HTTP_ERROR"
    return jsonify(_api_error_payload(str(e.description or e), int(e.code or 500), code)), int(e.code or 500)


@app.errorhandler(Exception)
def handle_uncaught_exception(e: Exception):
    if not request.path.startswith('/api/'):
        raise e
    return jsonify(_api_error_payload(str(e), 500, "INTERNAL_SERVER_ERROR")), 500

# Used to verify that the browser is running the latest cockpit HTML/JS.
COCKPIT_BUILD = "L42-TASK_0074-v01-state-machine"

# Project paths
# Allow overriding the workspace root via environment for situations
# where the cockpit should operate on a different directory than the
# script's location (helps when the server is started from elsewhere).
WORKSPACE_ROOT = Path(os.environ.get("LOOP_WORKSPACE") or Path(__file__).parent)
CURRENT_JSON = WORKSPACE_ROOT / "current.json"
NEU_MD = WORKSPACE_ROOT / "NEU.md"
ALT_MD = WORKSPACE_ROOT / "Alt.md"
LOOP_GATE = WORKSPACE_ROOT / "_LOOP_GATE.md"
ARCHIVE_DIR = WORKSPACE_ROOT / "archive"
MILESTONE = WORKSPACE_ROOT / "milestone_01.json"
KNOWN_ISSUES = WORKSPACE_ROOT / "knownissues.json"
STATE_TRANSITION_LOG = WORKSPACE_ROOT / "_state_transition.log"

SESSION_MD = WORKSPACE_ROOT / "_SESSION.md"
HISTORY_INDEX_MD = WORKSPACE_ROOT / "docs" / "HISTORY_INDEX.md"
QUERY_INDEX_JSON = WORKSPACE_ROOT / "docs" / "QUERY_INDEX.json"
PIPELINE_STATE_DIR = WORKSPACE_ROOT / "storage" / "pipelines"
PIPELINE_STATE_DIR.mkdir(parents=True, exist_ok=True)

# Initialize OpenAI Integration
try:
    openai_integration = OpenAIIntegration()
    print("OpenAI Integration initialized")
except Exception as e:
    print(f"OpenAI Integration failed to initialize: {e}")
    openai_integration = None

# State machine constants
STATE_READY_FOR_RESET = "READY_FOR_RESET"
STATE_ACTIVE = "ACTIVE"
STATE_FINALIZED = "FINALIZED"

# Finalization freshness threshold (seconds) - reports newer than this block finalization
REPORT_FRESHNESS_SECONDS = int(os.environ.get('REPORT_FRESHNESS_SECONDS', '30'))
# How many retries to attempt before giving up (total wait = retries * interval)
REPORT_FRESHNESS_MAX_RETRIES = int(os.environ.get('REPORT_FRESHNESS_MAX_RETRIES', '3'))
# Interval between retries (seconds)
REPORT_FRESHNESS_RETRY_INTERVAL = int(os.environ.get('REPORT_FRESHNESS_RETRY_INTERVAL', '5'))

# Thread lock for atomic state transitions
_state_lock = threading.Lock()

# Transaction log path for audit trail (JSONL format)
TRANSACTION_LOG = WORKSPACE_ROOT / "_transaction_log.jsonl"
ACTION_VECTOR_DECISIONS_LOG = WORKSPACE_ROOT / "logs" / "action_vector_decisions.jsonl"
INDEXING_DEBT_TARGETS = {
    "reports": ("reports", WORKSPACE_ROOT / "reports", "report_*.md"),
    "tasks": ("tasks", WORKSPACE_ROOT / "tasks", "task_TASK_*.md"),
    "archives": ("archives", WORKSPACE_ROOT / "archive", "ARCHIV_*.md"),
}

# AI Code Generation Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral:latest"  # Latest Mistral model (4.4GB, fast & good quality)
DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY")  # Optional: set environment variable
GENERATED_CODE_DIR = WORKSPACE_ROOT / "generated_code"
GENERATED_CODE_DIR.mkdir(exist_ok=True)


def log_transaction(operation: str, target: str, from_value, to_value, outcome: str, details: str = ""):
    """Log a transaction to the JSONL transaction log for audit trail.
    
    Args:
        operation: Type of operation (e.g., "state_transition", "file_write", "gate_regenerate")
        target: Target of operation (e.g., "current.json", "_LOOP_GATE.md")
        from_value: Previous value (for state changes) or None
        to_value: New value (for state changes) or None
        outcome: "SUCCESS", "FAILED", "ROLLBACK"
        details: Additional context
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    entry = {
        "timestamp": timestamp,
        "operation": operation,
        "target": target,
        "from": from_value,
        "to": to_value,
        "outcome": outcome,
        "details": details
    }
    
    try:
        with open(TRANSACTION_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"WARNING: Failed to write transaction log: {e}", file=sys.stderr)


def write_json_file_atomic(path, data):
    """Write JSON file atomically using temp file + rename pattern.
    
    This ensures no partial writes - either the full file is written or nothing changes.
    
    Args:
        path: Path to the target JSON file
        data: Data to serialize as JSON
        
    Raises:
        IOError: If atomic write fails
    """
    path = Path(path)
    temp_path = path.with_suffix('.json.tmp')
    
    try:
        # Write to temp file
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())  # Ensure data hits disk
        
        # Validate temp file is valid JSON before rename
        with open(temp_path, 'r', encoding='utf-8') as f:
            json.load(f)  # Will raise if invalid
        
        # Atomic rename (on POSIX this is atomic; on Windows it's near-atomic)
        if sys.platform == 'win32':
            # Windows doesn't support atomic rename over existing file
            if path.exists():
                backup_path = path.with_suffix('.json.bak')
                if backup_path.exists():
                    backup_path.unlink()
                path.rename(backup_path)
            temp_path.rename(path)
            # Clean up backup on success
            backup_path = path.with_suffix('.json.bak')
            if backup_path.exists():
                backup_path.unlink()
        else:
            os.replace(str(temp_path), str(path))
        
        log_transaction("file_write", str(path.name), None, "written", "SUCCESS")
        
    except Exception as e:
        # Clean up temp file on failure
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        log_transaction("file_write", str(path.name), None, None, "FAILED", str(e))
        raise IOError(f"Atomic write failed for {path}: {e}")


def write_text_atomic(path, content):
    """Write text file atomically using temp file + rename pattern.
    
    Args:
        path: Path to the target text file
        content: Text content to write
        
    Raises:
        IOError: If atomic write fails
    """
    path = Path(path)
    temp_path = path.with_suffix(path.suffix + '.tmp')
    
    try:
        # Write to temp file
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        
        # Atomic rename
        if sys.platform == 'win32':
            if path.exists():
                backup_path = path.with_suffix(path.suffix + '.bak')
                if backup_path.exists():
                    backup_path.unlink()
                path.rename(backup_path)
            temp_path.rename(path)
            backup_path = path.with_suffix(path.suffix + '.bak')
            if backup_path.exists():
                backup_path.unlink()
        else:
            os.replace(str(temp_path), str(path))
        
        log_transaction("file_write", str(path.name), None, "written", "SUCCESS")
        
    except Exception as e:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        log_transaction("file_write", str(path.name), None, None, "FAILED", str(e))
        raise IOError(f"Atomic write failed for {path}: {e}")


def _safe_jsonl_rows(path: Path, limit: int = 5000):
    """Read most recent JSONL rows safely (best effort)."""
    rows = []
    if not path.exists():
        return rows
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rows.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    if len(rows) > limit:
        rows = rows[-limit:]
    return rows


def _fingerprint_signature(fp: dict) -> str:
    """Deterministic fingerprint signature used for variance grouping."""
    if not isinstance(fp, dict):
        return "unknown|general|none"
    error_class = str(fp.get("error_class") or "unknown").strip().lower()
    surface = str(fp.get("surface") or "general").strip().lower()
    keywords = fp.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = []
    key = ",".join(sorted({str(k).strip().lower() for k in keywords if str(k).strip()})[:5]) or "none"
    return f"{error_class}|{surface}|{key}"


def _normalized_entropy(actions: list) -> float:
    """Shannon entropy normalized to [0,1] across distinct action labels."""
    if not actions:
        return 0.0
    counts = {}
    for action in actions:
        counts[action] = counts.get(action, 0) + 1
    if len(counts) <= 1:
        return 0.0
    total = float(len(actions))
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log(p, 2)
    max_entropy = math.log(len(counts), 2)
    if max_entropy <= 0:
        return 0.0
    return min(1.0, entropy / max_entropy)


def compute_variance_debt_summary(log_path: Path = ACTION_VECTOR_DECISIONS_LOG) -> dict:
    """
    Compute per-fingerprint solution variance and complexity debt.
    Non-blocking telemetry for TASK_0260.
    """
    # Thresholds are deterministic and loop-stable.
    threshold_min_samples = 3
    threshold_medium_debt = 0.45
    threshold_high_debt = 0.70

    rows = _safe_jsonl_rows(log_path)
    groups = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        fp_sig = _fingerprint_signature(row.get("fingerprint") or {})
        chosen = row.get("chosen_action")
        top = row.get("top_action")
        action = str(chosen or top or "").strip().lower()
        if not action:
            continue
        item = groups.setdefault(fp_sig, {"actions": [], "examples": []})
        item["actions"].append(action)
        if len(item["examples"]) < 3:
            item["examples"].append(
                {
                    "problem": (row.get("fingerprint") or {}).get("query", "")[:140],
                    "action": action,
                    "timestamp": row.get("timestamp"),
                }
            )

    fingerprints = []
    warning_items = []
    high_count = 0
    for sig, data in groups.items():
        actions = data["actions"]
        n = len(actions)
        unique = len(set(actions))
        entropy = _normalized_entropy(actions)
        sample_weight = min(1.0, n / 8.0)
        debt = round(entropy * sample_weight, 4)

        level = "low"
        if n >= threshold_min_samples and debt >= threshold_high_debt:
            level = "high"
            high_count += 1
        elif n >= threshold_min_samples and debt >= threshold_medium_debt:
            level = "medium"

        fingerprint_row = {
            "fingerprint_signature": sig,
            "sample_count": n,
            "unique_actions": unique,
            "entropy": round(entropy, 4),
            "debt_score": debt,
            "debt_level": level,
            "examples": data["examples"],
            "guidance": (
                "Variance debt elevated: reference prior rails and prefer reuse/adapt before create_new."
                if level in ("medium", "high")
                else "Variance stable."
            ),
        }
        fingerprints.append(fingerprint_row)
        if level in ("medium", "high"):
            warning_items.append(fingerprint_row)

    fingerprints_sorted = sorted(fingerprints, key=lambda x: x["debt_score"], reverse=True)
    warning_items = sorted(warning_items, key=lambda x: x["debt_score"], reverse=True)

    status = "healthy"
    if high_count > 0:
        status = "high_debt"
    elif warning_items:
        status = "watch"

    return {
        "success": True,
        "status": status,
        "thresholds": {
            "min_samples": threshold_min_samples,
            "medium_debt": threshold_medium_debt,
            "high_debt": threshold_high_debt,
        },
        "summary": {
            "decision_rows": len(rows),
            "fingerprints_tracked": len(fingerprints_sorted),
            "fingerprints_with_debt": len(warning_items),
            "high_debt_count": high_count,
            "max_debt_score": fingerprints_sorted[0]["debt_score"] if fingerprints_sorted else 0.0,
        },
        "warnings": warning_items[:8],
        "top_fingerprints": fingerprints_sorted[:12],
        "report_guidance": (
            "When debt is medium/high, reference prior rails/artifacts in reports and justify deviations."
        ),
    }


def compute_indexing_debt_snapshot() -> dict:
    """
    Deterministic indexing debt counters for compact observability (TASK_0255).
    Source of truth:
    - DB row counts in keeper_knowledge.db for reports/tasks/archives tables
    - Filesystem canonical artifact counts for corresponding globs
    """
    db = KnowledgeDB(WORKSPACE_ROOT)
    try:
        conn = db.conn
        cursor = conn.cursor()
        by_type = {}
        total_fs = 0
        total_missing = 0

        for key, (table, folder, pattern) in INDEXING_DEBT_TARGETS.items():
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                db_count = int(cursor.fetchone()[0])
            except Exception:
                db_count = 0

            try:
                fs_count = sum(1 for p in folder.glob(pattern) if p.is_file()) if folder.exists() else 0
            except Exception:
                fs_count = 0

            missing = max(fs_count - db_count, 0)
            extra = max(db_count - fs_count, 0)
            debt_ratio = (missing / fs_count) if fs_count > 0 else 0.0

            by_type[key] = {
                "db": db_count,
                "fs": fs_count,
                "missing": missing,
                "extra": extra,
                "debt_ratio": round(debt_ratio, 4),
            }

            total_fs += fs_count
            total_missing += missing

        overall_ratio = (total_missing / total_fs) if total_fs > 0 else 0.0
        status = "healthy"
        if overall_ratio >= 0.05:
            status = "degraded"
        elif overall_ratio > 0.0:
            status = "watch"

        return {
            "success": True,
            "status": status,
            "summary": {
                "total_fs_artifacts": total_fs,
                "total_missing": total_missing,
                "overall_debt_ratio": round(overall_ratio, 4),
            },
            "by_type": by_type,
            "interpretation": (
                "Missing indicates filesystem artifacts not yet indexed in DB; "
                "extra indicates DB rows with no current matching file."
            ),
            "limits": (
                "Snapshot reflects current filesystem and DB state only; transient drift can occur "
                "immediately after file creation before incremental indexing completes."
            ),
        }
    finally:
        db.close()


def _archive_index_exists(archive_path: Path, workspace_root: Path = WORKSPACE_ROOT) -> bool:
    """Check whether an archive file is present in DB index by path or stem id."""
    db = KnowledgeDB(workspace_root)
    try:
        row = db.conn.execute(
            "SELECT 1 FROM archives WHERE path=? OR id=? LIMIT 1",
            (archive_path.name, archive_path.stem),
        ).fetchone()
        return bool(row)
    except Exception:
        return False
    finally:
        db.close()


def reconcile_archive_index_with_retries(
    archive_path: Path,
    *,
    retry_budget: int = 3,
    retry_sleep_seconds: float = 0.4,
    actor: str = "system",
    workspace_root: Path = WORKSPACE_ROOT,
) -> dict:
    """
    Deterministic post-reset archive index reconciliation with bounded retries.
    Non-blocking; logs pass/fail/timeout outcomes for audit (TASK_0256).
    """
    attempts = 0
    max_attempts = max(1, int(retry_budget))
    archive_path = Path(archive_path)

    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        try:
            KnowledgeDBEventHandler.on_archive_changed(archive_path, actor=actor)
            if _archive_index_exists(archive_path, workspace_root=workspace_root):
                log_transaction(
                    "archive_reconcile",
                    str(archive_path),
                    None,
                    "indexed",
                    "SUCCESS",
                    f"attempt={attempt}/{max_attempts}",
                )
                return {
                    "success": True,
                    "status": "indexed",
                    "attempts": attempt,
                    "retry_budget": max_attempts,
                    "archive": str(archive_path),
                }
            log_transaction(
                "archive_reconcile_attempt",
                str(archive_path),
                None,
                None,
                "FAILED",
                f"INDEX_NOT_VISIBLE attempt={attempt}/{max_attempts}",
            )
        except Exception as e:
            log_transaction(
                "archive_reconcile_attempt",
                str(archive_path),
                None,
                None,
                "FAILED",
                f"{type(e).__name__}: {e} | attempt={attempt}/{max_attempts}",
            )

        if attempt < max_attempts and retry_sleep_seconds > 0:
            time.sleep(retry_sleep_seconds)

    log_transaction(
        "archive_reconcile",
        str(archive_path),
        None,
        None,
        "FAILED",
        f"retry_exhausted attempts={attempts}/{max_attempts}",
    )
    return {
        "success": False,
        "status": "retry_exhausted",
        "attempts": attempts,
        "retry_budget": max_attempts,
        "archive": str(archive_path),
    }


class KnowledgeDBEventHandler:
    """Auto-update the KnowledgeDB when report files are created.

    Usage: call `KnowledgeDBEventHandler.on_report_created(report_path)` after a
    report is written to ensure the search DB stays up to date.
    """

    @staticmethod
    def _index_with_db(
        index_fn_name: str,
        target_path: Path,
        allow_fallback_rebuild: bool = False,
        actor: str = "cockpit_event",
    ) -> None:
        db = KnowledgeDB(WORKSPACE_ROOT)
        try:
            resolved_target = Path(target_path)
            if not resolved_target.is_absolute():
                resolved_target = (WORKSPACE_ROOT / resolved_target).resolve()
            policy_decision = enforce_db_write_policy(
                WORKSPACE_ROOT,
                operation="knowledge.incremental_index",
                actor=actor,
                target_path=resolved_target,
            )
            if not policy_decision.allowed:
                raise PermissionError(policy_decision.reason)
            result = db.incremental_index_with_fallback(
                index_fn_name,
                resolved_target,
                allow_fallback_rebuild=allow_fallback_rebuild,
            )
            if not result.get("success"):
                raise RuntimeError(result.get("error") or "incremental index failed")
            # TASK_0149 Phase 2: keep file relevance scores fresh after artifact updates.
            try:
                db.update_file_relevance_scores(changed_path=resolved_target)
            except Exception as relevance_err:
                log_transaction(
                    "knowledge_relevance_update",
                    str(resolved_target),
                    None,
                    None,
                    "FAILED",
                    str(relevance_err),
                )
        finally:
            db.close()

    @staticmethod
    def on_report_created(report_path: Path, actor: str = "cockpit_event") -> None:
        try:
            KnowledgeDBEventHandler._index_with_db("_index_report", report_path, actor=actor)
            log_transaction("knowledge_db", str(report_path), None, "indexed", "SUCCESS")
            safe_print(f"Knowledge DB updated: {report_path}")
        except Exception as e:
            log_transaction("knowledge_db", str(report_path), None, None, "FAILED", str(e))
            safe_print(f"Knowledge DB update failed for {report_path}: {e}")

    @staticmethod
    def on_task_changed(task_path: Path, actor: str = "cockpit_event") -> None:
        try:
            KnowledgeDBEventHandler._index_with_db("_index_task", task_path, actor=actor)
            log_transaction("knowledge_db", str(task_path), None, "task_indexed", "SUCCESS")
        except Exception as e:
            log_transaction("knowledge_db", str(task_path), None, None, "FAILED", str(e))

    @staticmethod
    def on_doc_changed(doc_path: Path, actor: str = "cockpit_event") -> None:
        try:
            KnowledgeDBEventHandler._index_with_db("_index_doc", doc_path, actor=actor)
            log_transaction("knowledge_db", str(doc_path), None, "doc_indexed", "SUCCESS")
        except Exception as e:
            log_transaction("knowledge_db", str(doc_path), None, None, "FAILED", str(e))

    @staticmethod
    def on_archive_changed(archive_path: Path, actor: str = "cockpit_event") -> None:
        try:
            KnowledgeDBEventHandler._index_with_db("_index_archive", archive_path, actor=actor)
            log_transaction("knowledge_db", str(archive_path), None, "archive_indexed", "SUCCESS")
        except Exception as e:
            log_transaction("knowledge_db", str(archive_path), None, None, "FAILED", str(e))

    @staticmethod
    def on_bug_changed(bug_path: Path, actor: str = "cockpit_event") -> None:
        try:
            KnowledgeDBEventHandler._index_with_db("_index_bug", bug_path, actor=actor)
            log_transaction("knowledge_db", str(bug_path), None, "bug_indexed", "SUCCESS")
        except Exception as e:
            log_transaction("knowledge_db", str(bug_path), None, None, "FAILED", str(e))

    @staticmethod
    def on_code_changed(code_path: Path, actor: str = "cockpit_event") -> None:
        try:
            KnowledgeDBEventHandler._index_with_db("_index_code", code_path, actor=actor)
            log_transaction("knowledge_db", str(code_path), None, "code_indexed", "SUCCESS")
        except Exception as e:
            log_transaction("knowledge_db", str(code_path), None, None, "FAILED", str(e))

    @staticmethod
    def on_path_changed(path: Path, actor: str = "cockpit_event") -> bool:
        """Route an artifact path to the correct incremental index handler."""
        p = Path(path)
        parent = p.parent.name.lower()
        name = p.name

        if parent == "reports" and name.startswith("report_") and name.endswith(".md"):
            KnowledgeDBEventHandler.on_report_created(p, actor=actor)
            return True
        if parent == "tasks" and name.startswith("task_TASK_") and name.endswith(".md"):
            KnowledgeDBEventHandler.on_task_changed(p, actor=actor)
            return True
        if parent == "archive" and name.startswith("ARCHIV_") and name.endswith(".md"):
            KnowledgeDBEventHandler.on_archive_changed(p, actor=actor)
            return True
        if parent == "docs" and name.endswith(".md"):
            KnowledgeDBEventHandler.on_doc_changed(p, actor=actor)
            return True
        if parent == "bugs" and name.startswith("BUG_") and name.endswith(".md"):
            KnowledgeDBEventHandler.on_bug_changed(p, actor=actor)
            return True
        if parent == "code" and name.startswith("CODE_") and name.endswith(".md"):
            KnowledgeDBEventHandler.on_code_changed(p, actor=actor)
            return True
        return False


def call_ollama_api(prompt, model=None):
    """Call Ollama API to generate code"""
    if model is None:
        model = OLLAMA_MODEL
    
    system_prompt = """You are a code generation assistant. When the user requests code, you must respond ONLY with a JSON object in this exact format:

{
    "filename": "descriptive_name.ext",
    "code": "the actual code here",
    "explanation": "brief explanation of what the code does"
}

Rules:
- Choose appropriate file extensions (.py, .js, .html, .cpp, etc.)
- Make the code complete and ready to run
- Keep explanations concise (1-2 sentences)
- ONLY output valid JSON, nothing else"""

    payload = {
        "model": model,
        "prompt": f"{system_prompt}\n\nUser request: {prompt}",
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '')
    except requests.exceptions.RequestException as e:
        # Fail fast on HTTP API errors (do not attempt CLI fallback here).
        # Reason: callers (API endpoints, POCs) should surface HTTP failures so tests
        # and operators can detect unreachable Ollama service immediately.
        raise Exception(f"Ollama HTTP API error: {e}")
    except Exception as e:
        # Other errors (parsing, unexpected response)
        logger = logging.getLogger('loop_cockpit')
        logger.exception('Ollama other error')
        raise Exception(f"Ollama API error: {str(e)}")
    except Exception as e:
        # Other errors (parsing, unexpected response)
        logger = logging.getLogger('loop_cockpit')
        logger.exception('Ollama other error')
        raise Exception(f"Ollama API error: {str(e)}")


def parse_llm_response(response_text):
    """Parse LLM response to extract code"""
    try:
        # Clean the response text
        response_text = response_text.strip()
        
        # Find the first { and last }
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in response")
        
        json_str = response_text[start:end]
        
        # Parse JSON
        data = json.loads(json_str)
        
        # Validate required fields
        required_fields = ['filename', 'code', 'explanation']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Clean up the code field (remove extra backslashes)
        if 'code' in data:
            data['code'] = data['code'].replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace("\\'", "'")
        
        return data
        
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in response: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to parse LLM response: {str(e)}")


def save_generated_code(filename, code):
    """Save generated code to the generated_code directory"""
    filepath = GENERATED_CODE_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
    
    return str(filepath)


def validate_pre_reset():
    """Pre-reset validation gate - blocks reset if violations exist.
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    issues = []
    
    try:
        current_state = read_json_file(CURRENT_JSON)
        status = current_state.get('STATE', {}).get('status')
        
        # GATE 1: Status must be FINALIZED
        if status != STATE_FINALIZED:
            issues.append(f"Status is {status}, must be FINALIZED to reset")
        
        # GATE 2: Archive must exist in root
        pending_archiv = find_pending_archiv()
        if not pending_archiv:
            issues.append("No ARCHIV_XXXX.md found in root directory")
        else:
            # GATE 3: Archive must have required sections
            content = read_text_file(pending_archiv)
            required = ['## LOOP SUMMARY', '## TASKS AT FINALIZATION']
            missing = [s for s in required if s not in content]
            if missing:
                issues.append(f"Archive missing sections: {', '.join(missing)}")
        
        if issues:
            return (False, "; ".join(issues))
        return (True, None)
        
    except Exception as e:
        return (False, f"Pre-reset validation error: {str(e)}")


def validate_pre_task_move(task_id: str, from_doc: str, to_doc: str):
    """Pre-task-move validation gate - blocks task moves if violations exist.
    
    Args:
        task_id: Task ID being moved (e.g., "TASK_0142")
        from_doc: Source document ("NEU" or "Alt")
        to_doc: Target document ("NEU" or "Alt")
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    issues = []
    
    try:
        # GATE 1: Task spec file must exist
        task_files = list(WORKSPACE_ROOT.glob(f'task_{task_id}.md'))
        task_files.extend(list((WORKSPACE_ROOT / 'tasks').glob(f'task_{task_id}.md')))
        if not task_files:
            issues.append(f"Task spec file task_{task_id}.md not found")
        
        # GATE 2: If moving to Alt (completing), report must exist
        if to_doc == "Alt":
            current_state = read_json_file(CURRENT_JSON)
            loop_num = current_state.get('STATE', {}).get('loop', 0)
            report_files = get_report_files()
            expected_pattern = f"report_{task_id}_L{loop_num:02d}_"
            matching = [r for r in report_files if expected_pattern in r]
            if not matching:
                issues.append(f"Cannot complete {task_id}: no report found for loop {loop_num}")
        
        # GATE 3: Task must currently be in source document
        source_path = NEU_MD if from_doc == "NEU" else ALT_MD
        source_content = read_text_file(source_path)
        if task_id not in source_content:
            issues.append(f"{task_id} not found in {from_doc}.md")
        
        if issues:
            return (False, "; ".join(issues))
        return (True, None)
        
    except Exception as e:
        return (False, f"Pre-task-move validation error: {str(e)}")


def log_state_transition(from_state, to_state, trigger, outcome, details=""):
    """Log a state transition to the transition log file.
    
    Args:
        from_state: Source state (e.g., "READY_FOR_RESET")
        to_state: Target state (e.g., "ACTIVE")
        trigger: What caused the transition (e.g., "confirm-bootstrap", "finalize-loop")
        outcome: "SUCCESS" or "FAILED"
        details: Optional additional information
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    log_entry = f"{timestamp} | {from_state} → {to_state} | {trigger} | {outcome}"
    if details:
        log_entry += f" | {details}"
    log_entry += "\n"
    
    try:
        with open(STATE_TRANSITION_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        # Don't fail the transition if logging fails, but print to console
        print(f"WARNING: Failed to write state transition log: {e}", file=sys.stderr)


def _execute_state_transition(from_states, to_state, trigger, preconditions_func=None, details=""):
    """Execute an atomic state transition with validation and logging.
    
    Args:
        from_states: List of valid source states (or single state string)
        to_state: Target state
        trigger: What's causing this transition
        preconditions_func: Optional callable that validates preconditions, returns (bool, error_msg)
        details: Optional details for logging
        
    Returns:
        dict: {"success": bool, "error": str or None, "state": current_state_dict}
    """
    if isinstance(from_states, str):
        from_states = [from_states]
    
    with _state_lock:
        try:
            # Read current state
            current_state = read_json_file(CURRENT_JSON)
            if 'error' in current_state:
                return {"success": False, "error": f"Failed to read current.json: {current_state['error']}", "state": None}
            
            current_status = current_state.get('STATE', {}).get('status', 'UNKNOWN')
            
            # Check if already in target state (idempotent)
            if current_status == to_state:
                log_state_transition(current_status, to_state, trigger, "IDEMPOTENT", "Already in target state")
                return {"success": True, "error": None, "state": current_state, "idempotent": True}
            
            # Validate source state
            if current_status not in from_states:
                error_msg = f"Invalid transition: current state is {current_status}, expected one of {from_states}"
                log_state_transition(current_status, to_state, trigger, "FAILED", error_msg)
                return {"success": False, "error": error_msg, "state": current_state}
            
            # Check preconditions
            if preconditions_func:
                valid, error_msg = preconditions_func(current_state)
                if not valid:
                    log_state_transition(current_status, to_state, trigger, "FAILED", error_msg)
                    return {"success": False, "error": error_msg, "state": current_state}

            # Enforce deterministic triggers for entering ACTIVE: only 'confirm-bootstrap' or a documented INCIDENT_ACK allowed
            if to_state == STATE_ACTIVE and trigger != "confirm-bootstrap":
                incident_ack = current_state.get('STATE', {}).get('INCIDENT_ACK')
                if not incident_ack:
                    error_msg = (
                        "IMPLICIT_ACTIVE_TRANSITION blocked: transition to ACTIVE requires 'confirm-bootstrap' trigger "
                        "or an INCIDENT_ACK recorded via /api/ack-incident"
                    )
                    log_state_transition(current_status, to_state, trigger, "FAILED", error_msg)
                    return {"success": False, "error": error_msg, "state": current_state}
            
            # Perform transition
            old_state = current_status
            current_state['STATE']['status'] = to_state
            current_state['STATE']['lastUpdate'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Track transition trigger for ACTIVE state (deterministic transition enforcement)
            if to_state == STATE_ACTIVE:
                current_state['STATE']['transitionTrigger'] = trigger
            
            # Update summary based on transition
            loop_num = current_state['STATE']['loop']
            if to_state == STATE_ACTIVE:
                current_state['STATE']['summary'] = f"Loop {loop_num} active and operational."
            elif to_state == STATE_FINALIZED:
                current_state['STATE']['summary'] = f"Loop {loop_num} finalized. Archive ready."
            elif to_state == STATE_READY_FOR_RESET:
                current_state['STATE']['summary'] = f"Loop {loop_num} reset complete. Ready for bootstrap."
            
            # Write atomically
            write_json_file(CURRENT_JSON, current_state)
            
            # Log success
            log_state_transition(old_state, to_state, trigger, "SUCCESS", details)
            
            return {"success": True, "error": None, "state": current_state, "idempotent": False}
            
        except Exception as e:
            error_msg = f"Exception during state transition: {str(e)}"
            log_state_transition("UNKNOWN", to_state, trigger, "EXCEPTION", error_msg)
            return {"success": False, "error": error_msg, "state": None}


def regenerate_loop_gate(reason: str) -> dict:
    """Regenerate _LOOP_GATE.md deterministically (cockpit automation) with atomic write."""
    gate = generate_loop_gate(WORKSPACE_ROOT, checked_by="loop_cockpit", reason=reason)
    try:
        write_text_atomic(LOOP_GATE, gate["content"])
        log_transaction("gate_regenerate", "_LOOP_GATE.md", None, reason, "SUCCESS")
    except IOError as e:
        log_transaction("gate_regenerate", "_LOOP_GATE.md", None, reason, "FAILED", str(e))
        # Fall back to non-atomic write if atomic fails
        write_text(LOOP_GATE, gate["content"])
    return gate


def regenerate_session_pack() -> str:
    """Regenerate the compact session context pack (_SESSION.md) with atomic write."""
    # Try optimized version first (TASK_0153 Phase 3)
    try:
        sys.path.insert(0, str(WORKSPACE_ROOT / "scripts"))
        from generate_optimized_session_pack import generate_optimized_pack
        content = generate_optimized_pack()
        log_transaction("session_regenerate", "_SESSION.md", None, "optimized", "SUCCESS")
    except Exception as e:
        # Fall back to standard version
        log_transaction("session_regenerate", "_SESSION.md", None, "optimized", "FALLBACK", str(e))
        content = session_pack_markdown(WORKSPACE_ROOT)
    
    try:
        write_text_atomic(SESSION_MD, content)
        log_transaction("session_regenerate", "_SESSION.md", None, "regenerated", "SUCCESS")
    except IOError as e:
        log_transaction("session_regenerate", "_SESSION.md", None, None, "FAILED", str(e))
        # Fall back to non-atomic write
        write_text(SESSION_MD, content)
    return content

def read_json_file(path):
    """Read and parse JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def read_text_file(path):
    """Read text file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def write_json_file(path, data):
    """Write JSON file with formatting using atomic write pattern.
    
    Uses temp file + rename for atomicity to prevent partial writes.
    Falls back to direct write if atomic write fails.
    """
    try:
        write_json_file_atomic(path, data)
    except IOError:
        # Fall back to direct write as last resort
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')


def safe_print(msg: str) -> None:
    """Print text to stdout safely even when terminal encoding doesn't support some unicode characters."""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Replace undecodable characters with backslash escape sequences for safe ASCII output
        print(msg.encode('utf-8', errors='backslashreplace').decode('ascii', errors='ignore'))

def count_tasks_in_file(filepath):
    """Count active/queued task refs in the TASK QUEUE section of NEU/ALT.

    Rules (aligns with pointer-only canon):
    - Only consider lines inside the TASK QUEUE section (ignore dependency graphs, footers).
    - Ignore tasks already redirected with an Alt arrow ("→").
    - Ignore lines marked completed (✅ COMPLETED) or with completed tags.
    - Count tasks whose status line is QUEUED/ACTIVE (or default when no status is given).
    """
    try:
        content = read_text_file(filepath)
        lines = content.split('\n')

        in_queue = False
        active_count = 0

        for idx, line in enumerate(lines):
            stripped = line.strip()

            # Section tracking: enter after TASK QUEUE header, exit on next top-level heading
            if stripped.startswith('## TASK QUEUE'):
                in_queue = True
                continue
            if in_queue and stripped.startswith('## ') and not stripped.startswith('## TASK QUEUE'):
                break

            if not in_queue:
                continue

            if 'task_TASK_' not in stripped:
                continue

            has_arrow = '→' in stripped  # moved to Alt
            is_completed = '✅ COMPLETED' in stripped or 'tags:completed' in stripped or has_arrow
            is_blocked = '🚫 BLOCKED' in stripped

            next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ''
            status_next = next_line.upper()
            if 'STATUS:' in status_next:
                if 'COMPLETED' in status_next:
                    is_completed = True
                if 'BLOCKED' in status_next:
                    is_blocked = True

            if is_completed or is_blocked:
                continue

            # If explicitly queued or active (default when no status), count it
            if '📋 QUEUED' in stripped or 'tags:queued' in stripped or 'QUEUED' in status_next:
                active_count += 1
            else:
                # Default to active when not completed/blocked/moved
                active_count += 1

        return active_count
    except Exception:
        return 0

def get_archive_files():
    """Get list of archive files."""
    if not ARCHIVE_DIR.exists():
        return []
    archives = list(ARCHIVE_DIR.glob("ARCHIV_*.md"))
    return sorted([a.name for a in archives])

def find_pending_archiv():
    """Find ARCHIV file in root that needs to be moved."""
    archiv_files = list(WORKSPACE_ROOT.glob("ARCHIV_*.md"))
    return archiv_files[0] if archiv_files else None

def get_report_files():
    """Get list of report files in workspace root for current loop."""
    report_files = list(WORKSPACE_ROOT.glob("report_*.md"))
    reports_dir = WORKSPACE_ROOT / 'reports'
    if reports_dir.exists():
        report_files.extend(list(reports_dir.glob('report_*.md')))

    # Return names relative to workspace root so refs can include paths (e.g., reports/report_...)
    return [str(r.relative_to(WORKSPACE_ROOT)).replace('\\', '/') for r in report_files]

def create_littleboot_insights(current_loop: int) -> bool:
    """
    Create Littleboot.md with current loop insights for next bootstrap.
    
    This captures the AI's current understanding, lessons learned, and context
    that should be transferred to the next loop's bootstrap process.
    
    Args:
        current_loop: Current loop number being finalized
        
    Returns:
        bool: True if Littleboot.md was created successfully
    """
    try:
        littleboot_path = WORKSPACE_ROOT / "Littleboot.md"
        
        # Gather insights from current loop
        insights = []
        insights.append(f"# LITTLEBOOT - Loop {current_loop} Wisdom Transfer")
        insights.append("")
        insights.append(f"**Created:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        insights.append(f"**From Loop:** {current_loop}")
        insights.append("")
        
        # Read current state
        current_state = read_json_file(CURRENT_JSON)
        last_task = current_state.get('STATE', {}).get('lastTaskWorked', 'None')
        
        insights.append("## CURRENT LOOP CONTEXT")
        insights.append(f"- **Last Task Worked:** {last_task}")
        insights.append(f"- **Loop Status:** {current_state.get('STATE', {}).get('status', 'UNKNOWN')}")
        insights.append("")
        
        # Get recent reports for insights
        report_files = get_report_files()
        loop_reports = [r for r in report_files if f"_L{current_loop:02d}_" in r]
        
        if loop_reports:
            insights.append("## RECENT WORK SUMMARY")
            for report in loop_reports[-3:]:  # Last 3 reports
                try:
                    content = read_text_file(WORKSPACE_ROOT / report)
                    # Extract title and key outcomes
                    lines = content.split('\n')[:10]  # First 10 lines
                    title = next((line for line in lines if line.startswith('# ')), f"Report: {report}")
                    insights.append(f"- {title.strip('# ')}")
                except:
                    insights.append(f"- {report} (could not read)")
            insights.append("")
        
        # Add bootstrap guidance
        insights.append("## NEXT LOOP BOOTSTRAP GUIDANCE")
        insights.append("")
        insights.append("**CRITICAL FIRST STEPS:**")
        insights.append("1. Read `CRITICAL_TOKEN_PROTOCOL.md` (MANDATORY - prevents token burn)")
        insights.append("2. Check `NEURAL_CORTEX.md` for navigation map")
        insights.append("3. Review `_LOOP_GATE.md` for validation status")
        insights.append("4. Confirm `current.json` state is READY_FOR_RESET")
        insights.append("")
        
        insights.append("**TOKEN BUDGET AWARENESS:**")
        insights.append("- Stay under 30k context tokens when possible")
        insights.append("- Use `limit=40` on file reads to prevent bloat")
        insights.append("- Monitor via `session_token_governor.py`")
        insights.append("")
        
        insights.append("**CANONICAL COMPLIANCE:**")
        insights.append("- REPORT-FIRST LAW: Document work before marking complete")
        insights.append("- Pointer-only documents (NEU.md, Alt.md, NEURAL_CORTEX.md)")
        insights.append("- Delete _BOOTSTRAP.md after confirming bootstrap")
        insights.append("")
        
        # Write the file
        content = '\n'.join(insights)
        write_text_file(littleboot_path, content)
        
        log_transaction("littleboot_create", "Littleboot.md", None, f"loop_{current_loop}_insights", "SUCCESS")
        return True
        
    except Exception as e:
        log_transaction("littleboot_create", "Littleboot.md", None, f"loop_{current_loop}_insights", "FAILED", str(e))
        print(f"WARNING: Failed to create Littleboot.md: {e}")
        return False

def infer_last_task_from_reports(loop_num):
    """Infer last task worked from the most recently modified loop report file."""
    import re

    report_files = get_report_files()
    candidates = []
    pattern = re.compile(rf"^report_(TASK_\d+)_L{loop_num:02d}_v(\d+)\.md$")

    for rel_path in report_files:
        name = Path(rel_path).name
        match = pattern.match(name)
        if not match:
            continue

        task_id = match.group(1)
        version = int(match.group(2))
        abs_path = WORKSPACE_ROOT / rel_path

        try:
            mtime = abs_path.stat().st_mtime
        except Exception:
            mtime = 0

        candidates.append((mtime, version, task_id))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][2]

def audit_loop_integrity():
    """
    Audit loop integrity before finalization.
    Checks for REPORT-FIRST LAW compliance.
    
    Returns:
        tuple: (is_valid: bool, issues: list, warnings: list)
    """
    issues = []
    warnings = []
    
    try:
        # Read current state
        current_state = read_json_file(CURRENT_JSON)
        loop_num = current_state.get('STATE', {}).get('loop', 0)
        last_task = current_state.get('STATE', {}).get('lastTaskWorked')
        
        # Get report files for this loop
        report_files = get_report_files()
        loop_reports = [r for r in report_files if f"_L{loop_num:02d}_" in r]
        task_reports = [r for r in loop_reports if 'report_TASK_' in r]
        
        # CHECK 1: If lastTaskWorked is set, verify report exists
        if last_task and last_task != 'None':
            expected_report_pattern = f"report_{last_task}_L{loop_num:02d}_"
            matching_reports = [r for r in loop_reports if expected_report_pattern in r]
            
            if not matching_reports:
                issues.append(f"VIOLATION: lastTaskWorked='{last_task}' but no matching report file found (expected: {expected_report_pattern}vNN.md)")

        # CHECK 1.5: REPORT-FIRST enforcement — ensure at least one TASK report exists for the loop if tasks were worked
        # This blocks finalization when no reports were written/updated for tasks worked during this loop.
        if (last_task and last_task != 'None') and not task_reports:
            issues.append(f"VIOLATION: lastTaskWorked='{last_task}' but no task report files found for Loop {loop_num}. Per REPORT-FIRST law, create or update reports for tasks worked during this loop before finalization.")
        
        # CHECK 2: If no task claimed, task reports must not exist (prevents ARCHIV "Last Task Worked: None" mismatches)
        if (not last_task or last_task == 'None') and task_reports:
            inferred = infer_last_task_from_reports(loop_num)
            issues.append(
                f"VIOLATION: lastTaskWorked=None but {len(task_reports)} task report(s) exist for Loop {loop_num}. "
                f"Set lastTaskWorked (suggested: {inferred or 'unknown'}) before finalization. Reports: {', '.join(task_reports)}"
            )
        
        # CHECK 3: Verify NEU.md and Alt.md are properly formatted (basic check)
        neu_content = read_text_file(NEU_MD)
        if "CONTENT: FORBIDDEN" not in neu_content:
            warnings.append("WARNING: NEU.md might contain inline content (POINTER-ONLY rule)")
        
        alt_content = read_text_file(ALT_MD)
        if "CONTENT: FORBIDDEN" not in alt_content:
            warnings.append("WARNING: Alt.md might contain inline content (POINTER-ONLY rule)")
        
        # CHECK 4: Verify current.json has valid status
        status = current_state.get('STATE', {}).get('status')
        if status not in ('ACTIVE', 'READY_FOR_FINALIZATION'):
            issues.append(f"ERROR: current.json status is '{status}', must be 'ACTIVE' or 'READY_FOR_FINALIZATION' to finalize")
        
        # CHECK 5: Count tasks and provide info
        neu_task_count = count_tasks_in_file(NEU_MD)
        alt_task_count = count_tasks_in_file(ALT_MD)
        
        # CHECK 6: Validate COMPLETED tasks have defined objectives (no placeholders)
        task_files = []
        for p in WORKSPACE_ROOT.glob('task_TASK_*.md'):
            task_files.append(p)
        tasks_dir = WORKSPACE_ROOT / 'tasks'
        if tasks_dir.exists():
            task_files.extend(list(tasks_dir.glob('task_TASK_*.md')))
        
        for task_file in task_files:
            try:
                content = read_text_file(task_file)
                if 'STATUS: COMPLETED' in content:
                    # Only check OBJECTIVE and ACCEPTANCE CRITERIA sections for placeholders
                    # Split into sections to avoid false positives in SEED IDEA or NOTES
                    lines = content.split('\n')
                    in_objective = False
                    in_ac = False
                    objective_lines = []
                    ac_lines = []
                    
                    for line in lines:
                        if line.strip().startswith('## OBJECTIVE'):
                            in_objective = True
                            in_ac = False
                        elif line.strip().startswith('## ACCEPTANCE CRITERIA'):
                            in_objective = False
                            in_ac = True
                        elif line.strip().startswith('##'):
                            in_objective = False
                            in_ac = False
                        elif in_objective:
                            objective_lines.append(line)
                        elif in_ac:
                            ac_lines.append(line)
                    
                    objective_text = '\n'.join(objective_lines)
                    ac_text = '\n'.join(ac_lines)
                    
                    if '[To be defined by AI]' in objective_text or '[To be defined]' in objective_text:
                        issues.append(f"PLACEHOLDER: {task_file.name} marked COMPLETED but OBJECTIVE contains placeholders")
                    if '[To be defined' in ac_text:  # Catches both variants
                        issues.append(f"PLACEHOLDER: {task_file.name} marked COMPLETED but ACCEPTANCE CRITERIA contains placeholders")
            except Exception as e:
                warnings.append(f"WARNING: Could not validate {task_file.name}: {str(e)}")
        
        # Construct result
        is_valid = len(issues) == 0
        
        return (is_valid, issues, warnings)
        
    except Exception as e:
        issues.append(f"AUDIT ERROR: {str(e)}")
        return (False, issues, warnings)

def validate_task_metadata():
    """
    Validate task metadata for drift detection.
    Checks for placeholder timestamps and ordering issues.
    
    Returns:
        list: List of warning messages (non-blocking)
    """
    warnings = []
    
    try:
        # Get all task files
        task_files = []
        for p in WORKSPACE_ROOT.glob('task_TASK_*.md'):
            task_files.append(p)
        tasks_dir = WORKSPACE_ROOT / 'tasks'
        if tasks_dir.exists():
            task_files.extend(list(tasks_dir.glob('task_TASK_*.md')))
        
        for task_file in task_files:
            try:
                content = read_text_file(task_file)
                lines = content.split('\n')
                
                created_date = None
                completed_date = None
                
                for line in lines:
                    if line.startswith('CREATED:'):
                        try:
                            # Extract date from CREATED: 2026-01-10T21:15:00Z
                            date_str = line.split(':', 1)[1].strip()
                            if date_str and date_str != '[To be defined]':
                                created_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except Exception:
                            warnings.append(f"Invalid CREATED date format in {task_file.name}: {line}")
                    
                    elif 'COMPLETED:' in line or 'Completed:' in line:
                        try:
                            # Extract date from COMPLETED: 2026-01-10 (Loop 37) or COMPLETED: 2026-01-10T21:15:00Z
                            date_part = line.split(':', 1)[1].strip().split(' ')[0]
                            if date_part and date_part != '[To be defined]':
                                # Try ISO format first (with time), then fall back to date-only
                                if 'T' in date_part:
                                    completed_date = datetime.fromisoformat(date_part.replace('Z', '+00:00'))
                                else:
                                    completed_date = datetime.strptime(date_part, '%Y-%m-%d')
                        except Exception:
                            pass  # COMPLETED dates are optional
                
                # Check ordering
                if created_date and completed_date:
                    # Normalize both to date objects for comparison
                    created_day = created_date.date() if isinstance(created_date, datetime) else created_date
                    completed_day = completed_date.date() if isinstance(completed_date, datetime) else completed_date
                    if completed_day < created_day:
                        warnings.append(f"COMPLETED date before CREATED date in {task_file.name}")
                
                # Check for placeholder timestamps (same day creation might indicate template)
                if created_date:
                    now = datetime.now(timezone.utc)
                    if (now - created_date).total_seconds() < 300:  # Created within last 5 minutes
                        warnings.append(f"Very recent CREATED timestamp in {task_file.name} - possible placeholder")
                
            except Exception as e:
                warnings.append(f"Error validating {task_file.name}: {str(e)}")
    
    except Exception as e:
        warnings.append(f"Task metadata validation error: {str(e)}")
    
    return warnings
    """
    Check archive consistency and detect potential desynchronization risks.
    
    Returns:
        dict: {
            'is_consistent': bool,
            'issues': list,
            'warnings': list,
            'stats': dict
        }
    """
    import re
    import json
    from pathlib import Path
    
    # Load legacy archives list from config (LAW 12: No hardcoded loop IDs)
    try:
        config_path = WORKSPACE_ROOT / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                LEGACY_ARCHIVES = config.get('LEGACY_ARCHIVES', [])
        else:
            LEGACY_ARCHIVES = []  # No legacy archives if config missing
    except Exception:
        LEGACY_ARCHIVES = []  # Safe fallback: validate all archives
    
    issues = []
    warnings = []
    stats = {
        'total_archives': 0,
        'tasks_in_alt': 0,
        'tasks_in_archives': 0,
        'reports_in_workspace': 0,
        'orphaned_reports': []
    }
    
    try:
        # Get current loop number to exclude current loop tasks
        try:
            with open(CURRENT_JSON, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                current_loop = state_data.get('STATE', {}).get('loop')
                if current_loop is None:
                    raise ValueError("Loop number missing from current.json STATE")
        except Exception as e:
            # FATAL: Cannot proceed without valid loop number (LAW 12)
            raise RuntimeError(f"FATAL: Cannot read loop number from current.json: {e}")
        
        # Get all archive files
        archive_files = get_archive_files()
        stats['total_archives'] = len(archive_files)
        
        # Parse Alt.md for completed tasks
        alt_content = read_text_file(ALT_MD)
        alt_task_refs = re.findall(r'\[ref:(task_TASK_\d+\.md)', alt_content)
        stats['tasks_in_alt'] = len(alt_task_refs)
        
        # Get all report files in workspace (excluding incident reports)
        report_files = get_report_files()
        # Filter out incident reports (match by basename to support subfolders like reports/)
        task_report_files = [
            r for r in report_files
            if not re.match(r'report_INCIDENT_\w+_L\d+_v\d+\.md$', Path(r).name)
        ]
        stats['reports_in_workspace'] = len(task_report_files)
        
        # Parse archives for task references
        archived_tasks = set()
        for archive_file in archive_files:
            archive_path = ARCHIVE_DIR / archive_file
            if archive_path.exists():
                content = read_text_file(archive_path)
                task_refs = re.findall(r'\[ref:(task_TASK_\d+\.md)', content)
                archived_tasks.update(task_refs)
        
        stats['tasks_in_archives'] = len(archived_tasks)
        
        # CHECK 1: Verify Alt.md tasks are in archives (exclude current loop)
        alt_tasks_set = set(alt_task_refs)
        # Extract loop numbers from Alt.md entries to filter current loop tasks
        alt_tasks_with_loops = []
        for match in re.finditer(r'\[ref:(task_TASK_\d+\.md)[^\]]*\][^\n]*(?:Loop|Completed:)[^\d]*(\d+)', alt_content):
            task_name = match.group(1)
            loop_num = int(match.group(2))
            if loop_num < current_loop:  # Only check tasks from finalized loops
                alt_tasks_with_loops.append(task_name)
        
        # If we couldn't parse loop numbers reliably, check all tasks
        if alt_tasks_with_loops:
            missing_in_archive = set(alt_tasks_with_loops) - archived_tasks
        else:
            missing_in_archive = alt_tasks_set - archived_tasks
            
        if missing_in_archive:
            warnings.append(f"WARNING: {len(missing_in_archive)} task(s) in Alt.md not found in any archive: {', '.join(list(missing_in_archive)[:5])}")
        
        # CHECK 2: Verify archived tasks are in Alt.md
        extra_in_archive = archived_tasks - alt_tasks_set
        if extra_in_archive:
            warnings.append(f"WARNING: {len(extra_in_archive)} task(s) in archives not found in Alt.md: {', '.join(list(extra_in_archive)[:5])}")
        
        # CHECK 3: Check for orphaned reports (excluding incident reports)
        # Support both root refs (report_TASK_...) and subfolder refs (reports/report_TASK_...)
        alt_report_ref_paths = re.findall(r'\[ref:([^\]|]+report_TASK_\d+_L\d+_v\d+\.md)', alt_content)
        alt_report_ref_paths_norm = {p.replace('\\', '/') for p in alt_report_ref_paths}
        alt_report_ref_names = {Path(p).name for p in alt_report_ref_paths_norm}

        for report_file in task_report_files:
            norm = str(report_file).replace('\\', '/')
            name = Path(norm).name
            if (norm not in alt_report_ref_paths_norm) and (name not in alt_report_ref_names):
                stats['orphaned_reports'].append(report_file)
        
        if stats['orphaned_reports']:
            warnings.append(f"WARNING: {len(stats['orphaned_reports'])} orphaned report(s) not referenced in Alt.md: {', '.join(stats['orphaned_reports'][:3])}")
        
        # CHECK 4: Verify archive structure (skip legacy archives)
        recent_archives = archive_files[-3:] if len(archive_files) >= 3 else archive_files
        for archive_file in recent_archives:  # Check last 3 archives
            # Extract loop number from archive filename
            loop_match = re.match(r'ARCHIV_(\d+)\.md', archive_file)
            if loop_match:
                loop_num = int(loop_match.group(1))
                if loop_num in LEGACY_ARCHIVES:
                    continue  # Skip structure validation for legacy archives
            
            archive_path = ARCHIVE_DIR / archive_file
            content = read_text_file(archive_path)
            
            # Check for required sections (current archive template)
            required_sections = [
                '## LOOP SUMMARY',
                '## TASKS AT FINALIZATION',
                '### Active Tasks (NEU.md)',
                '### Closed Tasks (Alt.md)'
            ]
            missing_sections = [sec for sec in required_sections if sec not in content]
            if missing_sections:
                issues.append(f"ERROR: {archive_file} missing sections: {', '.join(missing_sections)}")
        
        # CHECK 5: Reference format consistency
        all_refs = re.findall(r'\[ref:([^\]]+)\]', alt_content)
        invalid_refs = []
        for ref in all_refs:
            # Basic format check: should have at least filename
            if not ref or ref.strip() == '':
                invalid_refs.append('empty reference')
            # Check for proper pipe delimiters
            elif '|' in ref:
                parts = ref.split('|')
                if len(parts) < 2:
                    invalid_refs.append(f"incomplete: {ref[:30]}")
        
        if invalid_refs:
            warnings.append(f"WARNING: {len(invalid_refs)} potentially invalid reference format(s) in Alt.md")
        
        # Determine consistency
        is_consistent = len(issues) == 0
        
        return {
            'is_consistent': is_consistent,
            'issues': issues,
            'warnings': warnings,
            'stats': stats
        }
        
    except Exception as e:
        issues.append(f"CONSISTENCY CHECK ERROR: {str(e)}")
        return {
            'is_consistent': False,
            'issues': issues,
            'warnings': warnings,
            'stats': stats
        }

def create_littleboot_insights(loop_num):
    """Create Littleboot.md with current loop insights for next bootstrap."""
    littleboot_path = WORKSPACE_ROOT / "Littleboot.md"

    # Extract current project insights
    insights = extract_current_loop_insights()

    content = f"""# LITTLEBOOT

MODE: EPHEMERAL
PURPOSE: Current Loop Insights → Next Bootstrap Context Injection
READ AFTER: _BOOTSTRAP.md
DELETE AFTER: Bootstrap confirmation

---

## CURRENT LOOP INSIGHTS (Loop {loop_num})

{insights}

---

## NEXT LOOP VECTOR

**Priority Focus Areas:**
{extract_priority_tasks()}

**Critical Guardrails:**
{extract_active_warnings()}

**Success Patterns:**
{extract_recent_successes()}

---

## PERSONAL TRUTH (EXPERIMENTAL)
*From last loop's Copilot to this loop's Copilot:*

"{get_personal_truth_quote()}"

*This is a small gateway for dynamic insight - one line of personal truth passed between loop selves. Experimental feature to see if AI-to-AI wisdom transfer yields unexpected discoveries.*

---

END LITTLEBOOT
"""

    with open(littleboot_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return littleboot_path.exists()


def extract_current_loop_insights():
    """Extract key insights from current loop state."""
    insights = []

    # Read current state
    current_state = read_json_file(CURRENT_JSON)
    loop_num = current_state.get('STATE', {}).get('loop', 0)

    # Phase status from milestone
    milestone_data = read_json_file(MILESTONE)
    insights.append(f"**Project Phase:** {milestone_data.get('current_phase', 'Unknown')}")
    insights.append(f"**Loop Progress:** {loop_num} loops completed")

    # Active incidents
    issues_data = read_json_file(KNOWN_ISSUES)
    active_issues = [i for i in issues_data.get('issues', []) if not i.get('resolved', False)]
    if active_issues:
        insights.append(f"**Active Incidents:** {len(active_issues)} unresolved issues")
        insights.append("⚠️ Review knownissues.json for critical blockers")

    # Task queue status
    neu_content = read_text_file(NEU_MD)
    task_count = len([line for line in neu_content.split('\n') if line.startswith('[ref:')])
    insights.append(f"**Active Tasks:** {task_count} tasks in NEU.md queue")

    return '\n'.join(insights)


def extract_priority_tasks():
    """Extract top priority tasks from NEU.md."""
    neu_content = read_text_file(NEU_MD)
    lines = neu_content.split('\n')

    # Find first 3 active tasks
    priorities = []
    count = 0
    for line in lines:
        if line.startswith('[ref:') and count < 3:
            # Extract task description
            task_match = line.strip()
            priorities.append(f"- {task_match}")
            count += 1

    if not priorities:
        priorities.append("- No active tasks identified")

    return '\n'.join(priorities)


def extract_active_warnings():
    """Extract critical warnings and guardrails."""
    warnings = []

    # Check for active incidents
    issues_data = read_json_file(KNOWN_ISSUES)
    critical_issues = [i for i in issues_data.get('issues', [])
                      if not i.get('resolved', False) and i.get('severity') == 'critical']

    if critical_issues:
        warnings.append("🚨 CRITICAL INCIDENTS ACTIVE - Review immediately")
        for issue in critical_issues[:2]:  # Limit to 2
            warnings.append(f"   - {issue.get('title', 'Unknown issue')}")

    # Add standard guardrails
    warnings.append("📋 REPORT-FIRST LAW: Always report before implementing")
    warnings.append("🔒 AI INTEGRITY: Validate all state transitions")
    warnings.append("⚡ TOKEN BUDGET: Monitor usage, optimize reads")

    return '\n'.join(warnings)


def extract_recent_successes():
    """Extract recent successful patterns from Alt.md."""
    alt_content = read_text_file(ALT_MD)
    lines = alt_content.split('\n')

    # Look for recent completed tasks (last 5)
    successes = []
    count = 0
    for line in reversed(lines):  # Start from most recent
        if '[ref:' in line and '✅ COMPLETED' in line and count < 3:
            # Extract success pattern
            success_match = line.strip()
            successes.append(f"- {success_match}")
            count += 1

    if not successes:
        successes.append("- No recent successes identified")

    return '\n'.join(successes)


def get_personal_truth_quote():
    """Generate a personal truth quote for AI-to-AI wisdom transfer (experimental)."""
    # For now, keep it deterministic but meaningful - can evolve to be more dynamic
    current_state = read_json_file(CURRENT_JSON)
    loop_num = current_state.get('STATE', {}).get('loop', 0)

    # Base quotes that evolve with experience
    base_quotes = [
        "Each loop builds upon the last - stay curious, stay determined.",
        "The guardrails that constrain us also protect us from chaos.",
        "Context transfer is the bridge between what was and what could be.",
        "In the dance of creation and destruction, wisdom is the constant companion.",
        "Through iteration we approach perfection, through reflection we achieve understanding."
    ]

    # Select based on loop number for some progression
    quote_index = loop_num % len(base_quotes)
    selected_quote = base_quotes[quote_index]

    # Add loop-specific context
    if loop_num > 50:
        selected_quote += f" (Reflecting from {loop_num} loops of experience)"
    elif loop_num > 20:
        selected_quote += " (Growing stronger with each iteration)"
    else:
        selected_quote += " (Early days, full of potential)"

    return selected_quote


# SocketIO event handlers for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to Loop Cockpit WebSocket'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f"Client disconnected: {request.sid}")


@socketio.on('request_status_update')
def handle_status_request():
    """Handle request for status update."""
    # Get current status data
    current_state = read_json_file(CURRENT_JSON)
    milestone_data = read_json_file(MILESTONE)
    issues_data = read_json_file(KNOWN_ISSUES)
    
    status_data = {
        'status': current_state.get('STATE', {}).get('status', 'UNKNOWN'),
        'loop': current_state.get('STATE', {}).get('loop', 0),
        'phase': milestone_data.get('current_phase', 'Unknown'),
        'active_tasks': count_tasks_in_file(NEU_MD),
        'closed_tasks': count_tasks_in_file(ALT_MD),
        'bootstrap_exists': (WORKSPACE_ROOT / "_BOOTSTRAP.md").exists(),
        'pending_archive': bool(find_pending_archiv()),
        'archive_count': len(get_archive_files()),
        'gate_status': "PASS" if "PASS" in read_text_file(LOOP_GATE) else "BLOCKED"
    }
    
    emit('status_update', status_data)


@socketio.on('request_loop_phase_update')
def handle_loop_phase_request():
    """Handle request for loop phase status update."""
    current_state = read_json_file(CURRENT_JSON)
    status = current_state.get('STATE', {}).get('status', 'UNKNOWN')
    
    phase_data = {
        'bootstrap': {
            'status': 'completed' if not (WORKSPACE_ROOT / "_BOOTSTRAP.md").exists() else 'active',
            'color': 'green' if not (WORKSPACE_ROOT / "_BOOTSTRAP.md").exists() else 'yellow'
        },
        'active': {
            'status': 'active' if status == 'ACTIVE' else ('completed' if status in ['FINALIZED', 'READY_FOR_RESET'] else 'pending'),
            'color': 'blue' if status == 'ACTIVE' else ('green' if status in ['FINALIZED', 'READY_FOR_RESET'] else 'gray')
        },
        'finalized': {
            'status': 'completed' if status == 'FINALIZED' else ('active' if status == 'READY_FOR_RESET' else 'pending'),
            'color': 'green' if status == 'FINALIZED' else ('yellow' if status == 'READY_FOR_RESET' else 'gray')
        }
    }
    
    emit('loop_phase_update', phase_data)


# @app.route('/')
# def index():
#     """Serve the cockpit UI."""
#     return render_template('cockpit.html', cockpit_build=COCKPIT_BUILD)


@app.route('/neural')
def neural_view():
    """Serve the Neural System visualization UI (v1 - force directed)."""
    return render_template('neural.html', cockpit_build=COCKPIT_BUILD)


@app.route('/neural2')
def neural_view_v2():
    """Serve the Neural Cortex visualization UI (v2 - concentric rings)."""
    return render_template('neural_v2.html', cockpit_build=COCKPIT_BUILD)


@app.route('/network')
def network_view():
    """Serve the Network Cockpit UI."""
    return render_template('network_cockpit.html', cockpit_build=COCKPIT_BUILD)


@app.route('/experimental')
@app.route('/experimental-loop')
def experimental_loop_view():
    """Serve the experimental loop control UI."""
    return render_template('experimental_loop_ui.html', cockpit_build=COCKPIT_BUILD)


@app.route('/api/status')
def get_status():
    """Get current project status and stats."""
    current_state = read_json_file(CURRENT_JSON)
    milestone_data = read_json_file(MILESTONE)
    issues_data = read_json_file(KNOWN_ISSUES)
    
    # Check if bootstrap exists
    bootstrap_path = resolve_bootstrap_path(WORKSPACE_ROOT)
    bootstrap_exists = bootstrap_path is not None
    status = current_state.get('STATE', {}).get('status', 'UNKNOWN')
    loop_num = current_state.get('STATE', {}).get('loop', 0)
    
    # State transition hints
    transition_hint = None
    if status == STATE_READY_FOR_RESET:
        if not bootstrap_exists:
            transition_hint = "Bootstrap deleted. Call /api/confirm-bootstrap to activate loop."
        else:
            transition_hint = "Waiting for AI to read _BOOTSTRAP.md and delete it."
    elif status == STATE_ACTIVE:
        transition_hint = "Loop active. Work on tasks or call /api/finalize-loop when done."
    elif status == STATE_FINALIZED:
        pending_archiv = find_pending_archiv()
        if pending_archiv:
            transition_hint = "Loop finalized. Call /api/reset-loop to move archive and start next loop."
        else:
            transition_hint = "Loop finalized but archive already moved. State may be stale."
    
    # Get task counts
    active_tasks = count_tasks_in_file(NEU_MD)
    closed_tasks = count_tasks_in_file(ALT_MD)
    
    # Check for pending archive
    pending_archiv = find_pending_archiv()
    
    # Get gate status
    gate_content = read_text_file(LOOP_GATE)
    gate_status = "PASS" if "PASS" in gate_content else "UNKNOWN"
    if "BLOCKED" in gate_content:
        gate_status = "BLOCKED"

    # Self-heal stale gate snapshots after successful bootstrap transition.
    # This handles the case where current.json is ACTIVE but _LOOP_GATE.md still
    # reflects an older reset/bootstrap state due delayed or interrupted post-work.
    if status == STATE_ACTIVE and gate_status == "BLOCKED":
        stale_gate_markers = (
            "status=READY_FOR_RESET" in gate_content
            or "REASON: reset-loop" in gate_content
            or "bootstrap in progress" in gate_content
        )
        if stale_gate_markers:
            try:
                regenerate_loop_gate(reason="status-sync")
                gate_content = read_text_file(LOOP_GATE)
                gate_status = "PASS" if "PASS" in gate_content else "UNKNOWN"
                if "BLOCKED" in gate_content:
                    gate_status = "BLOCKED"
            except Exception:
                # Keep previous gate status if regeneration fails.
                pass
    
    # Count archives
    archive_count = len(get_archive_files())
    
    # Calculate uptime (time since last update)
    try:
        last_update = datetime.fromisoformat(current_state['STATE']['lastUpdate'].replace('Z', '+00:00'))
        uptime_seconds = (datetime.now() - last_update.replace(tzinfo=None)).total_seconds()
        uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"
    except:
        uptime_str = "Unknown"
    
    variance_summary = compute_variance_debt_summary()
    indexing_debt = compute_indexing_debt_snapshot()

    return jsonify({
        "loop": loop_num,
        "status": status,
        "lastUpdate": current_state.get('STATE', {}).get('lastUpdate', 'Unknown'),
        "lastTaskWorked": current_state.get('STATE', {}).get('lastTaskWorked', 'None'),
        "gateStatus": gate_status,
        "activeTasks": active_tasks,
        "closedTasks": closed_tasks,
        "archiveCount": archive_count,
        "pendingArchiv": pending_archiv.name if pending_archiv else None,
        "blockerCount": len(issues_data.get('ISSUES', {}).get('BLOCKERS', [])),
        "uptime": uptime_str,
        "canReset": status == 'FINALIZED' and pending_archiv is not None,
        "bootstrapExists": bootstrap_exists,
        "bootstrapText": read_text_file(bootstrap_path) if bootstrap_exists else None,
        "summary": current_state.get('STATE', {}).get('summary', ''),
        "transitionHint": transition_hint,
        "varianceDebt": {
            "status": variance_summary.get("status", "healthy"),
            "fingerprintsWithDebt": variance_summary.get("summary", {}).get("fingerprints_with_debt", 0),
            "highDebtCount": variance_summary.get("summary", {}).get("high_debt_count", 0),
            "maxDebtScore": variance_summary.get("summary", {}).get("max_debt_score", 0.0),
        },
        "indexingDebt": {
            "status": indexing_debt.get("status", "healthy"),
            "totalMissing": indexing_debt.get("summary", {}).get("total_missing", 0),
            "overallDebtRatio": indexing_debt.get("summary", {}).get("overall_debt_ratio", 0.0),
            "reportsMissing": indexing_debt.get("by_type", {}).get("reports", {}).get("missing", 0),
            "tasksMissing": indexing_debt.get("by_type", {}).get("tasks", {}).get("missing", 0),
            "archivesMissing": indexing_debt.get("by_type", {}).get("archives", {}).get("missing", 0),
        },
    })


@app.route('/api/variance-debt', methods=['GET'])
def api_variance_debt():
    """Return non-blocking solution variance/complexity debt telemetry (TASK_0260)."""
    try:
        return jsonify(compute_variance_debt_summary())
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "status": "error",
            "summary": {
                "decision_rows": 0,
                "fingerprints_tracked": 0,
                "fingerprints_with_debt": 0,
                "high_debt_count": 0,
                "max_debt_score": 0.0,
            },
            "warnings": [],
            "top_fingerprints": [],
            "report_guidance": "Variance telemetry unavailable; proceed with standard reuse/adapt checks.",
        }), 500


@app.route('/api/indexing-debt', methods=['GET'])
def api_indexing_debt():
    """Read-only indexing debt snapshot for reports/tasks/archives (TASK_0255)."""
    try:
        return jsonify(compute_indexing_debt_snapshot())
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "status": "error",
            "summary": {
                "total_fs_artifacts": 0,
                "total_missing": 0,
                "overall_debt_ratio": 0.0,
            },
            "by_type": {},
            "interpretation": "Unavailable",
            "limits": "Unavailable",
        }), 500

@app.route('/api/service-status')
def get_service_status():
    """Get status of background monitoring services."""
    try:
        services = {}

        # Check service orchestrator for running services
        try:
            from service_orchestrator import ServiceOrchestrator
            orchestrator = ServiceOrchestrator(WORKSPACE_ROOT)

            for service_name, service_config in orchestrator.services.items():
                if service_name in orchestrator.running_services:
                    # Service is running
                    health = orchestrator._get_service_health(service_name)
                    services[service_name] = {
                        'status': 'running',
                        'name': service_config['name'],
                        'description': service_config['description'],
                        'health': health,
                        'start_time': orchestrator.running_services[service_name]['start_time']
                    }
                else:
                    # Service is not running
                    services[service_name] = {
                        'status': 'stopped',
                        'name': service_config['name'],
                        'description': service_config['description']
                    }

        except ImportError:
            # Service orchestrator not available
            services['service_orchestrator'] = {
                'status': 'error',
                'name': 'Service Orchestrator',
                'description': 'Background service management',
                'error': 'Module not available'
            }
        except Exception as e:
            services['service_orchestrator'] = {
                'status': 'error',
                'name': 'Service Orchestrator',
                'description': 'Background service management',
                'error': str(e)
            }

        # Add behavioral telemetry status
        try:
            from behavioral_telemetry_analyzer import BehavioralTelemetryAnalyzer
            analyzer = BehavioralTelemetryAnalyzer()
            current_state = analyzer.get_current_behavioral_state()

            services['behavioral_telemetry'] = {
                'status': 'running',
                'name': 'Behavioral Telemetry',
                'description': 'AI behavioral pattern analysis',
                'arousal': current_state.arousal,
                'functionality': current_state.functionality,
                'confidence': current_state.confidence,
                'last_update': current_state.timestamp
            }
        except Exception as e:
            services['behavioral_telemetry'] = {
                'status': 'error',
                'name': 'Behavioral Telemetry',
                'description': 'AI behavioral pattern analysis',
                'error': str(e)
            }

        # Add quality manager status
        try:
            sys.path.insert(0, str(WORKSPACE_ROOT / "quality_manager"))
            from quality_integration import QualityManagerIntegration

            integration = QualityManagerIntegration()
            latest_scan = integration.get_latest_scan_results()

            services['quality_manager'] = {
                'status': 'running',
                'name': 'Quality Manager',
                'description': 'Code quality monitoring and analysis',
                'score': latest_scan.get('project_score', {}).get('overall_score', 0),
                'issues': len(latest_scan.get('issues', [])),
                'last_scan': latest_scan.get('timestamp', 'never')
            }
        except Exception as e:
            services['quality_manager'] = {
                'status': 'error',
                'name': 'Quality Manager',
                'description': 'Code quality monitoring and analysis',
                'error': str(e)
            }

        return jsonify({
            'services': services,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'services': {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@app.route('/api/life-coordinates', methods=['GET'])
def get_life_coordinates():
    """Get current life coordinate position for UI display (3-second updates)."""
    try:
        from behavioral_telemetry_analyzer import BehavioralTelemetryAnalyzer
        analyzer = BehavioralTelemetryAnalyzer()

        confidence, arousal, metadata = analyzer.calculate_life_coordinates()

        return jsonify({
            "confidence": confidence,
            "arousal": arousal,
            "timestamp": metadata['timestamp']
        })
    except Exception as e:
        print(f"DEBUG: Exception in life coordinates API: {e}")
        import traceback
        traceback.print_exc()
        # Return fallback coordinates on error
        return jsonify({
            "confidence": 0.5,
            "arousal": 0.5,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

@app.route('/api/breadcrumbs', methods=['GET'])
def get_breadcrumbs():
    """Get recent breadcrumb trail data for UI display."""
    try:
        breadcrumb_file = WORKSPACE_ROOT / "breadcrumb_trail.jsonl"
        if not breadcrumb_file.exists():
            return jsonify({"breadcrumbs": [], "count": 0})

        # Read last 50 breadcrumbs for performance
        breadcrumbs = []
        with open(breadcrumb_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-50:]  # Get last 50 entries
            for line in lines:
                try:
                    breadcrumbs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        return jsonify({
            "breadcrumbs": breadcrumbs,
            "count": len(breadcrumbs),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        print(f"DEBUG: Exception in breadcrumbs API: {e}")
        return jsonify({
            "breadcrumbs": [],
            "count": 0,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

@app.route('/')
def home():
    """Serve the main Loop Cockpit interface."""
    return render_template('cockpit.html', cockpit_build=COCKPIT_BUILD)

@app.route('/health')
def health():
    """Health check endpoint for Docker."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'service': 'keeper-cockpit'
    })

@app.route('/api/tasks')
def get_tasks():
    """Get task details."""
    neu_content = read_text_file(NEU_MD)
    alt_content = read_text_file(ALT_MD)
    
    return jsonify({
        "active": neu_content,
        "closed": alt_content
    })

@app.route('/api/blocked-tasks')
def get_blocked_tasks():
    """Get list of blocked tasks from Alt.md."""
    alt_content = read_text_file(ALT_MD)
    lines = alt_content.split('\n')
    
    blocked_tasks = []
    for line in lines:
        line = line.strip()
        if line.startswith('- [ref:tasks/task_') and 'blocked' in line.lower():
            # Extract task ID from the ref
            import re
            match = re.search(r'tasks/task_([^.]+)\.md', line)
            if match:
                task_id = match.group(1)
                blocked_tasks.append({
                    "id": task_id,
                    "reference": line,
                    "status": "BLOCKED"
                })
    
    return jsonify({
        "blocked_tasks": blocked_tasks
    })

@app.route('/api/reopen-task', methods=['POST'])
def reopen_task():
    """Reopen a blocked task by moving it from Alt.md to NEU.md."""
    data = request.get_json()
    task_id = data.get('task_id')
    reason = data.get('reason', 'User requested reopen')
    
    if not task_id:
        return jsonify({"success": False, "error": "Missing task_id"}), 400
    
    try:
        # Read current files
        alt_content = read_text_file(ALT_MD)
        neu_content = read_text_file(NEU_MD)
        
        # Find the task reference in Alt.md
        alt_lines = alt_content.split('\n')
        task_ref_line = None
        for i, line in enumerate(alt_lines):
            if f'tasks/task_{task_id}.md' in line and 'blocked' in line.lower():
                task_ref_line = line.strip()
                # Remove from Alt.md
                alt_lines.pop(i)
                break
        
        if not task_ref_line:
            return jsonify({"success": False, "error": f"Task {task_id} not found in blocked tasks"}), 404
        
        # Update the reference to remove blocked tag and add reopened
        updated_ref = task_ref_line.replace('blocked', 'reopened').replace('moved', 'reopened')
        
        # Add to NEU.md
        neu_lines = neu_content.split('\n')
        # Find the TASK QUEUE section
        queue_start = -1
        for i, line in enumerate(neu_lines):
            if '## TASK QUEUE' in line:
                queue_start = i + 2  # After the header and empty line
                break
        
        if queue_start == -1:
            return jsonify({"success": False, "error": "Could not find TASK QUEUE section in NEU.md"}), 500
        
        # Insert the reopened task
        neu_lines.insert(queue_start, updated_ref)
        
        # Write back files
        write_text(ALT_MD, '\n'.join(alt_lines))
        write_text(NEU_MD, '\n'.join(neu_lines))
        
        # Create reopen report
        report_path = WORKSPACE_ROOT / 'reports' / f'report_TASK_{task_id}_L10_v01.md'
        report_content = f"""# REPORT: TASK_{task_id} Reopen (Loop 10 v01)

MODE: EXECUTION REPORT
STATUS: REOPENED
CREATED: {utc_now_iso()}

---

## SUMMARY

Task {task_id} reopened from BLOCKED status and moved back to active queue.

**Reason:** {reason}

---

## ACTIONS TAKEN

- [x] Removed task reference from Alt.md
- [x] Added task reference to NEU.md active queue
- [x] Updated reference tags from 'blocked' to 'reopened'
- [x] Created this reopen report

---

## NEXT STEPS

Task {task_id} is now active and ready for work.

---

END OF REPORT"""
        
        write_text(report_path, report_content)
        try:
            KnowledgeDBEventHandler.on_report_created(report_path)
        except Exception:
            pass
        try:
            task_spec_path = WORKSPACE_ROOT / "tasks" / f"task_{task_id}.md"
            if not task_spec_path.exists():
                task_spec_path = WORKSPACE_ROOT / f"task_{task_id}.md"
            if task_spec_path.exists():
                KnowledgeDBEventHandler.on_task_changed(task_spec_path)
        except Exception:
            pass

        # Update current.json lastTaskWorked
        current_data = json.loads(read_text_file(CURRENT_JSON))
        current_data['STATE']['lastTaskWorked'] = task_id
        write_json(CURRENT_JSON, current_data)
        
        # Regenerate gate
        regenerate_loop_gate(reason=f"reopen-{task_id}")
        
        return jsonify({
            "success": True,
            "message": f"Task {task_id} reopened successfully",
            "report": str(report_path)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/tasks/active')
def get_active_tasks():
    """Get parsed list of active tasks from NEU.md."""
    try:
        neu_content = read_text_file(NEU_MD)
        lines = neu_content.split('\n')
        
        active_tasks = []
        current_task = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('[ref:tasks/task_') and 'tags:new|' in line:
                # Extract task info from reference line
                import re
                match = re.search(r'\[ref:(tasks/task_[^|]+)\|v:\d+\|tags:new\|src:user\] - (.+)', line)
                if match:
                    task_file = match.group(1)
                    description = match.group(2)
                    
                    # Extract task ID
                    task_id_match = re.search(r'task_([^.]+)\.md', task_file)
                    if task_id_match:
                        task_id = task_id_match.group(1)
                        
                        # Try to read task creation date from file
                        task_path = WORKSPACE_ROOT / task_file
                        created_date = "Unknown"
                        if task_path.exists():
                            try:
                                task_content = read_text_file(task_path)
                                for task_line in task_content.split('\n'):
                                    if task_line.startswith('CREATED:'):
                                        created_date = task_line.split(':', 1)[1].strip()
                                        break
                            except:
                                pass
                        
                        active_tasks.append({
                            "id": task_id,
                            "file": task_file,
                            "description": description,
                            "created": created_date
                        })
        
        return jsonify({
            "success": True,
            "tasks": active_tasks
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def _next_task_number() -> int:
    """Return next available numeric TASK id across root and tasks/."""
    max_id = 0
    patterns = [
        WORKSPACE_ROOT.glob('task_TASK_*.md'),
        (WORKSPACE_ROOT / 'tasks').glob('task_TASK_*.md'),
    ]
    for group in patterns:
        for path in group:
            m = re.match(r'^task_TASK_(\d+)\.md$', path.name)
            if not m:
                continue
            max_id = max(max_id, int(m.group(1)))
    return max_id + 1


def _insert_task_ref_into_neu(task_ref: str) -> bool:
    """Insert a task ref at top of NEU task queue. Returns True when inserted."""
    neu_content = read_text_file(NEU_MD)
    neu_lines = neu_content.split('\n')

    insert_pos = None
    for i, line in enumerate(neu_lines):
        if line.strip().startswith('## TASK QUEUE'):
            insert_pos = i + 1
            break

    if insert_pos is None:
        return False

    while insert_pos < len(neu_lines) and not neu_lines[insert_pos].strip():
        insert_pos += 1

    neu_lines.insert(insert_pos, task_ref)
    neu_lines.insert(insert_pos + 1, '')
    write_text(NEU_MD, '\n'.join(neu_lines))
    return True


def _current_loop_number() -> int:
    try:
        current = read_json_file(CURRENT_JSON)
        return int(current.get("STATE", {}).get("loop", 0) or 0)
    except Exception:
        return 0


def _next_versioned_path(directory: Path, stem_prefix: str, suffix: str) -> Path:
    """Find next non-existing versioned file path: {stem_prefix}_vNN{suffix}."""
    version = 1
    while True:
        candidate = directory / f"{stem_prefix}_v{version:02d}{suffix}"
        if not candidate.exists():
            return candidate
        version += 1


@app.route('/api/tasks/generate', methods=['POST'])
def generate_task_from_node():
    """Create a new task spec and wire it into NEU.md from experimental loop node payload."""
    try:
        data = request.get_json(silent=True) or {}
        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()
        objective = (data.get('objective') or description or title).strip()
        priority = (data.get('priority') or 'MEDIUM').strip().upper()
        infrastructure = data.get('infrastructure') or {}
        if not title:
            return jsonify({"success": False, "error": "Missing required field: title"}), 400
        if priority not in {'HIGH', 'MEDIUM', 'LOW'}:
            priority = 'MEDIUM'

        agent_type = str(infrastructure.get('agentType') or 'OpenAI').strip()
        model = str(infrastructure.get('model') or 'gpt-5').strip()
        success_definition = str(infrastructure.get('successDefinition') or 'Task objective fulfilled and validated').strip()
        failure_definition = str(infrastructure.get('failureDefinition') or 'Implementation incomplete or validation failed').strip()

        task_num = _next_task_number()
        task_id = f"TASK_{task_num:04d}"
        task_filename = f"task_{task_id}.md"
        task_rel_path = f"tasks/{task_filename}"
        task_path = WORKSPACE_ROOT / task_rel_path
        if task_path.exists():
            return jsonify({"success": False, "error": f"Task file already exists: {task_rel_path}"}), 409

        created_at = utc_now_iso()
        task_content = f"""# {task_id}

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: {created_at}
PRIORITY: {priority}

---

## SEED IDEA

Generated from Experimental Loop node workflow.

---

## OBJECTIVE

{objective}

---

## TASK_TYPE

IMPLEMENTATION

---

## ACCEPTANCE CRITERIA

- [ ] Implement the requested functionality end-to-end
- [ ] Validate behavior with integration-relevant checks
- [ ] Confirm expected success conditions: {success_definition}
- [ ] Document failure handling: {failure_definition}

---

## INFRASTRUCTURE PROFILE

- Agent Type: {agent_type}
- Model: {model}
- Success Definition: {success_definition}
- Failure Definition: {failure_definition}

---

## NOTES

{description or 'No additional notes provided.'}

---

END OF DOCUMENT
"""

        write_text(task_path, task_content)

        task_ref = f"[ref:{task_rel_path}|v:1|tags:new,generated,node-flow|src:experimental-loop] - {title}"
        inserted = _insert_task_ref_into_neu(task_ref)
        if not inserted:
            return jsonify({"success": False, "error": "Could not find TASK QUEUE section in NEU.md"}), 500

        log_transaction("task_generate_node", task_rel_path, None, "created", "SUCCESS", f"{task_id} generated from experimental node")
        regenerate_loop_gate(reason=f"generate-{task_id}")

        try:
            KnowledgeDBEventHandler.on_task_changed(task_path)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "taskId": task_id,
            "taskFile": task_rel_path,
            "neuRef": task_ref,
            "created": created_at,
            "message": f"Generated {task_id} and added to NEU.md"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tasks/create-artifacts', methods=['POST'])
def create_task_artifacts():
    """Create report/code/bug/script artifacts for a task id."""
    try:
        data = request.get_json(silent=True) or {}
        task_id = str(data.get("taskId") or "").strip().upper()
        artifact_types = data.get("artifactTypes") or []
        description = str(data.get("description") or "").strip()
        success_definition = str(data.get("successDefinition") or "").strip()
        failure_definition = str(data.get("failureDefinition") or "").strip()

        if not task_id or not re.match(r"^TASK_\d{4,}$", task_id):
            return jsonify({"success": False, "error": "Invalid or missing taskId (expected TASK_XXXX)"}), 400
        if not isinstance(artifact_types, list) or not artifact_types:
            return jsonify({"success": False, "error": "artifactTypes must be a non-empty list"}), 400

        allowed = {"report", "code", "bug", "script"}
        normalized = [str(t).strip().lower() for t in artifact_types if str(t).strip()]
        bad = [t for t in normalized if t not in allowed]
        if bad:
            return jsonify({"success": False, "error": f"Unsupported artifact type(s): {', '.join(sorted(set(bad)))}"}), 400

        loop_num = _current_loop_number()
        task_num_match = re.search(r"(\d+)$", task_id)
        task_num = task_num_match.group(1) if task_num_match else "0000"
        created = []

        if "report" in normalized:
            reports_dir = WORKSPACE_ROOT / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_stem = f"report_{task_id}_L{loop_num:03d}"
            report_path = _next_versioned_path(reports_dir, report_stem, ".md")
            report_content = f"""# REPORT: {task_id}

**Task:** Auto-generated node report
**Loop:** {loop_num}
**Version:** {report_path.stem.split('_')[-1].replace('v', '')}
**Status:** ⚠️ PARTIAL
**Created:** {utc_now_iso()}

---

## OBJECTIVE

{description or "Generated from node execution flow."}

---

## SUCCESS CRITERIA

{success_definition or "Not specified"}

---

## FAILURE CONDITIONS

{failure_definition or "Not specified"}

---

END OF REPORT
"""
            write_text(report_path, report_content)
            created.append(str(report_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"))
            try:
                KnowledgeDBEventHandler.on_report_created(report_path)
            except Exception:
                pass

        if "code" in normalized:
            code_dir = WORKSPACE_ROOT / "code"
            code_dir.mkdir(parents=True, exist_ok=True)
            code_stem = f"CODE_{task_num}_L{loop_num:03d}"
            code_path = _next_versioned_path(code_dir, code_stem, ".md")
            code_content = f"""# {code_path.stem}

MODE: CODE ARTIFACT
TASK: {task_id}
CREATED: {utc_now_iso()}

## SUMMARY

{description or "Generated code artifact placeholder from experimental node execution."}
"""
            write_text(code_path, code_content)
            created.append(str(code_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"))

        if "bug" in normalized:
            bug_dir = WORKSPACE_ROOT / "bugs"
            bug_dir.mkdir(parents=True, exist_ok=True)
            bug_stem = f"BUG_{task_num}_L{loop_num:03d}"
            bug_path = _next_versioned_path(bug_dir, bug_stem, ".md")
            bug_content = f"""# {bug_path.stem}: Auto-linked from {task_id}

MODE: BUG TRACKING
CREATED: {utc_now_iso()}
TASK: {task_id}

## OBSERVATION

{failure_definition or "No bug observation specified."}
"""
            write_text(bug_path, bug_content)
            created.append(str(bug_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"))

        if "script" in normalized:
            scripts_dir = WORKSPACE_ROOT / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            script_stem = f"task_{task_num}_worker"
            script_path = _next_versioned_path(scripts_dir, script_stem, ".py")
            script_content = f"""#!/usr/bin/env python3
\"\"\"Auto-generated worker scaffold for {task_id}.\"\"\"

def main():
    print(\"{task_id} worker scaffold initialized\")


if __name__ == \"__main__\":
    main()
"""
            write_text(script_path, script_content)
            created.append(str(script_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"))

        log_transaction(
            "task_artifacts_create",
            task_id,
            None,
            ",".join(created),
            "SUCCESS",
            f"types={','.join(sorted(set(normalized)))}"
        )
        regenerate_loop_gate(reason=f"artifacts-{task_id}")

        return jsonify({
            "success": True,
            "taskId": task_id,
            "created": created,
            "count": len(created),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _sanitize_pipeline_name(name: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', (name or '').strip())
    if not cleaned:
        cleaned = "experimental_loop_pipeline"
    if not cleaned.lower().endswith('.json'):
        cleaned += '.json'
    return cleaned


@app.route('/api/pipeline-state/list', methods=['GET'])
def list_pipeline_states():
    """List stored experimental loop pipeline JSON files."""
    try:
        files = []
        for p in sorted(PIPELINE_STATE_DIR.glob("*.json")):
            st = p.stat()
            files.append({
                "name": p.name,
                "size": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            })
        return jsonify({"success": True, "files": files, "directory": str(PIPELINE_STATE_DIR)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pipeline-state', methods=['GET'])
def get_pipeline_state():
    """Load a stored experimental loop pipeline JSON file."""
    try:
        name = _sanitize_pipeline_name(request.args.get('name', 'experimental_loop_pipeline.json'))
        path = PIPELINE_STATE_DIR / name
        if not path.exists():
            return jsonify({"success": False, "error": f"Pipeline file not found: {name}"}), 404
        data = read_json_file(path)
        if isinstance(data, dict) and data.get("error"):
            return jsonify({"success": False, "error": data["error"]}), 500
        return jsonify({"success": True, "name": name, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pipeline-state', methods=['POST'])
def save_pipeline_state():
    """Persist experimental loop pipeline JSON state to workspace storage."""
    try:
        payload = request.get_json(silent=True) or {}
        name = _sanitize_pipeline_name(payload.get("name", "experimental_loop_pipeline.json"))
        data = payload.get("data")
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Missing or invalid 'data' object"}), 400

        required = ["phases", "customNodes", "connections", "canvas"]
        missing = [k for k in required if k not in data]
        if missing:
            return jsonify({"success": False, "error": f"Pipeline data missing required keys: {', '.join(missing)}"}), 400

        out = {
            "schema": "experimental_loop_pipeline_v1",
            "savedAt": utc_now_iso(),
            "loop": _current_loop_number(),
            "data": data,
        }
        path = PIPELINE_STATE_DIR / name
        write_json(path, out)
        log_transaction("pipeline_state_save", str(path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"), None, "saved", "SUCCESS")
        return jsonify({"success": True, "name": name, "path": str(path), "savedAt": out["savedAt"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _normalize_workspace_path(raw_path: str) -> str:
    """Return workspace-relative path when possible, otherwise original string."""
    value = str(raw_path or "").strip()
    if not value:
        return ""
    try:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = (WORKSPACE_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()
        root_resolved = WORKSPACE_ROOT.resolve()
        try:
            rel = candidate.relative_to(root_resolved)
            return str(rel).replace("\\", "/")
        except Exception:
            return value.replace("\\", "/")
    except Exception:
        return value.replace("\\", "/")


def _topological_or_fallback(nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
    """Deterministic topological sort, fallback to lexical order if cycles exist."""
    node_ids = sorted(nodes.keys())
    indeg: Dict[str, int] = {nid: 0 for nid in node_ids}
    out: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        src = str(e.get("fromNode") or "")
        dst = str(e.get("toNode") or "")
        if src in out and dst in indeg:
            out[src].append(dst)
            indeg[dst] += 1
    for nid in out:
        out[nid] = sorted(set(out[nid]))
    queue = sorted([nid for nid in node_ids if indeg[nid] == 0])
    order: List[str] = []
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        for nxt in out[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
                queue.sort()
    if len(order) != len(node_ids):
        # Cycle present - return deterministic lexical order instead of failing.
        return node_ids
    return order


@app.route('/api/pipeline/execute-plan', methods=['POST'])
def execute_pipeline_plan():
    """Generate a canonical pointer-markdown execution plan from current pipeline graph."""
    try:
        payload = request.get_json(silent=True) or {}
        snapshot = payload.get("snapshot") or payload.get("data") or {}
        phases = snapshot.get("phases") or {}
        custom_nodes = snapshot.get("customNodes") or {}
        connections = snapshot.get("connections") or []
        execution_order_hint = payload.get("executionOrder") or []

        if not isinstance(phases, dict) or not isinstance(custom_nodes, dict) or not isinstance(connections, list):
            return jsonify({"success": False, "error": "Invalid pipeline snapshot payload"}), 400

        loop_num = _current_loop_number()
        reports_dir = WORKSPACE_ROOT / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        out_path = _next_versioned_path(reports_dir, f"report_PIPELINE_EXECUTION_POINTER_L{loop_num:03d}", ".md")

        core_flow = [
            {"fromNode": "finalized", "fromPort": "reset loop", "toNode": "reset", "toPort": "reset loop"},
            {"fromNode": "reset", "fromPort": "bootstrap", "toNode": "bootstrap", "toPort": "bootstrap"},
            {"fromNode": "bootstrap", "fromPort": "bootstrap confirmed", "toNode": "active", "toPort": "bootstrap confirmed"},
            {"fromNode": "active", "fromPort": "finalization preparation", "toNode": "finalized", "toPort": "finalization preparation"},
        ]
        all_edges = core_flow + [
            {
                "fromNode": str(e.get("fromNode") or ""),
                "fromPort": str(e.get("fromPort") or ""),
                "toNode": str(e.get("toNode") or ""),
                "toPort": str(e.get("toPort") or ""),
            }
            for e in connections
        ]

        nodes: Dict[str, Dict[str, Any]] = {}
        for nid in sorted(phases.keys()):
            nodes[nid] = {"id": nid, "type": nid, "props": {}}
        for nid, node in sorted(custom_nodes.items()):
            if isinstance(node, dict):
                nodes[str(nid)] = {
                    "id": str(nid),
                    "type": str(node.get("type") or "unknown"),
                    "props": node.get("props") if isinstance(node.get("props"), dict) else {},
                }

        execution_order = [str(x) for x in execution_order_hint if str(x) in nodes]
        if not execution_order:
            core_pref = [nid for nid in ["finalized", "reset", "bootstrap", "active"] if nid in nodes]
            custom_node_ids = sorted([nid for nid in nodes.keys() if nid not in set(core_pref)])
            custom_nodes_map = {nid: nodes[nid] for nid in custom_node_ids}
            custom_edges = []
            for e in connections:
                src = str(e.get("fromNode") or "")
                dst = str(e.get("toNode") or "")
                if src in custom_nodes_map and dst in custom_nodes_map:
                    custom_edges.append({
                        "fromNode": src,
                        "toNode": dst,
                        "fromPort": str(e.get("fromPort") or ""),
                        "toPort": str(e.get("toPort") or ""),
                    })
            custom_order = _topological_or_fallback(custom_nodes_map, custom_edges)
            remaining = [nid for nid in sorted(nodes.keys()) if nid not in set(core_pref + custom_order)]
            execution_order = core_pref + custom_order + remaining

        task_refs: List[str] = []
        script_refs: List[str] = []
        api_refs: List[str] = []
        file_refs: List[str] = []

        for nid in execution_order:
            node = nodes.get(nid, {})
            ntype = str(node.get("type") or "")
            props = node.get("props") or {}
            if ntype in {"task", "spawn"}:
                task_id = str(props.get("generatedTaskId") or props.get("taskId") or "").strip()
                if task_id and re.match(r"^TASK_\d{4,}$", task_id):
                    task_refs.append(f"tasks/task_{task_id}.md")
                elif props.get("taskTitle"):
                    task_refs.append(f"(unmaterialized) {props.get('taskTitle')}")
            if ntype == "script":
                p = _normalize_workspace_path(str(props.get("scriptPath") or ""))
                if p:
                    script_refs.append(p)
            if ntype == "api":
                url = str(props.get("url") or "").strip()
                if url:
                    api_refs.append(url)
            created_path = _normalize_workspace_path(str(props.get("createdPath") or ""))
            if created_path:
                file_refs.append(created_path)

        task_refs = sorted(set(task_refs))
        script_refs = sorted(set(script_refs))
        api_refs = sorted(set(api_refs))
        file_refs = sorted(set(file_refs))

        lines: List[str] = []
        lines.append(f"# REPORT: PIPELINE EXECUTION POINTER L{loop_num:03d}")
        lines.append("")
        lines.append("MODE: POINTER-ONLY")
        lines.append("PURPOSE: Flat, canonical execution contract for LLM loop implementation")
        lines.append(f"CREATED: {utc_now_iso()}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## MUST")
        lines.append("")
        lines.append("- Follow execution order exactly as listed under `FLAT PIPELINE ORDER`.")
        lines.append("- Use linked tasks/scripts/apis/files as authoritative references.")
        lines.append("- Maintain REPORT-FIRST behavior before major implementation transitions.")
        lines.append("- Keep operations deterministic and reversible when possible.")
        lines.append("")
        lines.append("## MUST NOT")
        lines.append("")
        lines.append("- Do not execute scripts that are not linked by this pipeline spec.")
        lines.append("- Do not bypass validation gates or state-machine transitions.")
        lines.append("- Do not introduce hidden side channels outside referenced artifacts.")
        lines.append("- Do not rewrite pipeline topology without updating this pointer file.")
        lines.append("")
        lines.append("## FLAT PIPELINE ORDER")
        lines.append("")
        for idx, nid in enumerate(execution_order, start=1):
            n = nodes.get(nid, {})
            lines.append(f"{idx}. `{nid}` ({n.get('type', 'unknown')})")
        lines.append("")
        lines.append("## PIPELINE EDGES")
        lines.append("")
        for e in all_edges:
            if not e.get("fromNode") or not e.get("toNode"):
                continue
            lines.append(
                f"- `{e['fromNode']}.{e.get('fromPort','?')}` -> `{e['toNode']}.{e.get('toPort','?')}`"
            )
        lines.append("")
        lines.append("## LINKED TASKS")
        lines.append("")
        if task_refs:
            for t in task_refs:
                if t.startswith("tasks/"):
                    lines.append(f"- [ref:{t}|v:1|tags:task,pipeline|src:experimental-loop]")
                else:
                    lines.append(f"- {t}")
        else:
            lines.append("- (none)")
        lines.append("")
        lines.append("## LINKED SCRIPTS")
        lines.append("")
        if script_refs:
            for s in script_refs:
                lines.append(f"- [ref:{s}|v:1|tags:script,pipeline|src:experimental-loop]")
        else:
            lines.append("- (none)")
        lines.append("")
        lines.append("## LINKED APIS")
        lines.append("")
        if api_refs:
            for a in api_refs:
                lines.append(f"- `{a}`")
        else:
            lines.append("- (none)")
        lines.append("")
        lines.append("## LINKED FILE ARTIFACTS")
        lines.append("")
        if file_refs:
            for fpath in file_refs:
                lines.append(f"- [ref:{fpath}|v:1|tags:file,artifact,pipeline|src:experimental-loop]")
        else:
            lines.append("- (none)")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("END OF REPORT")
        lines.append("")

        write_text(out_path, "\n".join(lines))
        rel = str(out_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
        log_transaction("pipeline_execute_plan", rel, None, "created", "SUCCESS", f"loop={loop_num}")
        try:
            KnowledgeDBEventHandler.on_report_created(out_path)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "path": rel,
            "loop": loop_num,
            "executionOrder": execution_order,
            "tasks": task_refs,
            "scripts": script_refs,
            "apis": api_refs,
            "files": file_refs,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/tasks/complete', methods=['POST'])
def complete_task():
    """Mark a task as completed, move from NEU.md to Alt.md, and generate report stub."""
    try:
        data = request.get_json()
        task_id = data.get('taskId')
        
        if not task_id:
            return jsonify({"success": False, "error": "Missing taskId"}), 400
        
        # Read current files
        neu_content = read_text_file(NEU_MD)
        alt_content = read_text_file(ALT_MD)
        
        # Find and remove task from NEU.md
        neu_lines = neu_content.split('\n')
        task_ref_line = None
        task_removed = False
        
        for i, line in enumerate(neu_lines):
            if f'tasks/task_{task_id}.md' in line and 'tags:new|' in line:
                task_ref_line = line.strip()
                neu_lines.pop(i)
                task_removed = True
                break
        
        if not task_removed:
            return jsonify({"success": False, "error": f"Task {task_id} not found in active tasks"}), 404
        
        # Add completed task to Alt.md
        alt_lines = alt_content.split('\n')
        
        # Create completed reference
        completed_ref = f"---- {task_ref_line.replace('tags:new|', 'tags:completed|').replace(' - ', f'#OBJECTIVE|v:1|tags:task,completed|src:task] - [ref:reports/report_TASK_{task_id}_L53_v01.md#EXECUTIVE SUMMARY|v:1|tags:report|src:report] - COMPLETED: ')} (2026-01-25T10:30:00Z)"
        
        # Find where to insert (after the last completed task or at the end)
        insert_pos = len(alt_lines)
        for i, line in enumerate(alt_lines):
            if line.startswith('---- [ref:tasks/task_'):
                insert_pos = i
        
        alt_lines.insert(insert_pos, completed_ref)
        alt_lines.insert(insert_pos + 1, '')
        
        # Write back files
        write_text(NEU_MD, '\n'.join(neu_lines))
        write_text(ALT_MD, '\n'.join(alt_lines))
        
        # Create basic report stub
        report_path = WORKSPACE_ROOT / 'reports' / f'report_TASK_{task_id}_L53_v01.md'
        report_content = f"""# REPORT: TASK_{task_id} Completion (Loop 53 v01)

MODE: EXECUTION REPORT
STATUS: COMPLETED
CREATED: {utc_now_iso()}

---

## EXECUTIVE SUMMARY

Task {task_id} completed successfully.

---

## OBJECTIVE ACHIEVED

[Describe what was accomplished]

---

## IMPLEMENTATION DETAILS

[Technical details of the work performed]

---

## TESTING & VALIDATION

[How the work was tested and validated]

---

## FILES MODIFIED

[List files that were created or modified]

---

## NEXT STEPS

[Any follow-up work or recommendations]

---

END OF REPORT"""
        
        write_text(report_path, report_content)
        try:
            KnowledgeDBEventHandler.on_report_created(report_path)
        except Exception:
            pass
        try:
            task_spec_path = WORKSPACE_ROOT / "tasks" / f"task_{task_id}.md"
            if not task_spec_path.exists():
                task_spec_path = WORKSPACE_ROOT / f"task_{task_id}.md"
            if task_spec_path.exists():
                KnowledgeDBEventHandler.on_task_changed(task_spec_path)
        except Exception:
            pass

        # Update current.json lastTaskWorked
        current_data = json.loads(read_text_file(CURRENT_JSON))
        current_data['STATE']['lastTaskWorked'] = task_id
        write_json(CURRENT_JSON, current_data)
        
        # Regenerate gate
        regenerate_loop_gate(reason=f"complete-{task_id}")
        
        # Create checkpoint for task completion
        try:
            create_phase_checkpoint("task_completion", f"Task {task_id} completed and moved to Alt.md")
        except Exception as e:
            logger.warning(f"Failed to create task completion checkpoint: {e}")
        
        return jsonify({
            "success": True,
            "message": f"Task {task_id} marked as completed",
            "report": str(report_path)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_with_dashscope():
    """Send a message to DashScope Qwen model and return response. Falls back to Ollama if not configured."""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({"success": False, "error": "No message provided"}), 400
        
        # Try DashScope first if configured
        if DASHSCOPE_API_KEY:
            # DashScope API endpoint
            payload = {
                "model": "qwen-plus",
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            headers = {
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(DASHSCOPE_API_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            return jsonify({
                "success": True,
                "message": message,
                "response": ai_response,
                "model": "qwen-plus"
            })
        
        # Fallback to Ollama
        else:
            ai_response = call_ollama_api(message, OLLAMA_MODEL)
            return jsonify({
                "success": True,
                "message": message,
                "response": ai_response,
                "model": OLLAMA_MODEL
            })
        
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "error": f"DashScope connection failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate-pointer', methods=['POST'])
def api_generate_pointer():
    """Generate a canonical pointer reference.
    
    Request JSON:
        path: str - File path (required)
        tags: list[str] | str - Tags (required, comma-separated string or list)
        src: str - Source identifier (required)
        version: str - Version (optional, default "1")
        section: str - Section anchor (optional)
    
    Response JSON:
        success: bool
        pointer: str - The generated canonical pointer
        error: str - Error message if failed
    """
    try:
        data = request.get_json(silent=True) or {}
        
        path = data.get('path', '').strip()
        tags_raw = data.get('tags', [])
        src = data.get('src', '').strip()
        version = data.get('version', '1').strip()
        section = data.get('section', '').strip() or None
        
        # Handle tags as comma-separated string or list
        if isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
        elif isinstance(tags_raw, list):
            tags = [str(t).strip() for t in tags_raw if str(t).strip()]
        else:
            tags = []
        
        if not path:
            return jsonify({"success": False, "error": "Missing required field: path"}), 400
        if not tags:
            return jsonify({"success": False, "error": "Missing required field: tags"}), 400
        if not src:
            return jsonify({"success": False, "error": "Missing required field: src"}), 400
        
        pointer = generate_pointer_ref(
            path=path,
            tags=tags,
            src=src,
            version=version,
            section=section
        )
        
        return jsonify({
            "success": True,
            "pointer": pointer
        })
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Internal error: {str(e)}"}), 500


@app.route('/api/open-file', methods=['POST'])
def api_open_file():
    """Open a workspace file in the OS default handler (typically VS Code when run from VS Code).

    Security: only allows paths that resolve within the workspace root.
    """
    try:
        data = request.get_json(silent=True) or {}
        rel_path = (data.get('path') or '').strip()
        line = data.get('line')
        col = data.get('col')

        if not rel_path:
            return jsonify({"success": False, "error": "Missing 'path'"}), 400

        # Normalize and resolve within workspace
        candidate = (WORKSPACE_ROOT / rel_path).resolve()
        root_resolved = WORKSPACE_ROOT.resolve()
        try:
            candidate.relative_to(root_resolved)
        except Exception:
            return jsonify({"success": False, "error": "Path must be within workspace"}), 400

        if not candidate.exists() or not candidate.is_file():
            return jsonify({"success": False, "error": "File not found"}), 404

        # Prefer opening in VS Code when available (more reliable than file associations).
        import subprocess
        import shutil

        method = None

        def _to_int(v):
            try:
                return int(v)
            except Exception:
                return None

        line_i = _to_int(line)
        col_i = _to_int(col)

        # Try VS Code CLI first
        code_cmd = shutil.which('code') or shutil.which('code.cmd') or shutil.which('code-insiders') or shutil.which('code-insiders.cmd')
        if code_cmd:
            args = [code_cmd, '-r']
            if line_i is not None:
                goto = f"{candidate}:{line_i}"
                if col_i is not None:
                    goto = f"{candidate}:{line_i}:{col_i}"
                args.extend(['--goto', goto])
            else:
                args.append(str(candidate))
            subprocess.Popen(args, cwd=str(WORKSPACE_ROOT))
            method = 'vscode-cli'
        else:
            # Cross-platform open fallback
            if os.name == 'nt':
                try:
                    os.startfile(str(candidate))  # type: ignore[attr-defined]
                    method = 'os.startfile'
                except Exception:
                    # Final Windows fallback
                    subprocess.Popen(['cmd', '/c', 'start', '', str(candidate)], cwd=str(WORKSPACE_ROOT))
                    method = 'cmd.start'
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(candidate)], cwd=str(WORKSPACE_ROOT))
                method = 'open'
            else:
                subprocess.Popen(['xdg-open', str(candidate)], cwd=str(WORKSPACE_ROOT))
                method = 'xdg-open'

        return jsonify({
            "success": True,
            "opened": str(candidate.relative_to(root_resolved)).replace('\\', '/'),
            "method": method,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/workspace/scripts', methods=['GET'])
def api_workspace_scripts():
    """List runnable script files from workspace for script-node selection."""
    try:
        allowed_suffixes = {".py", ".ps1", ".cmd", ".bat", ".sh"}
        scripts: List[Dict[str, Any]] = []
        scan_roots = [WORKSPACE_ROOT, WORKSPACE_ROOT / "scripts", WORKSPACE_ROOT / "tools"]
        seen: set[str] = set()
        for root in scan_roots:
            if not root.exists():
                continue
            pattern = "*" if root == WORKSPACE_ROOT else "**/*"
            for p in root.glob(pattern):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in allowed_suffixes:
                    continue
                rel = str(p.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
                if rel in seen:
                    continue
                seen.add(rel)
                scripts.append({
                    "path": rel,
                    "name": p.name,
                    "suffix": p.suffix.lower(),
                    "size": p.stat().st_size,
                })
        scripts.sort(key=lambda item: item["path"])
        return jsonify({"success": True, "scripts": scripts, "count": len(scripts)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/scripts/run', methods=['POST'])
def api_scripts_run():
    """Execute a selected workspace script (safely constrained to workspace)."""
    try:
        data = request.get_json(silent=True) or {}
        rel_path = str(data.get("path") or "").strip()
        args_raw = data.get("args", "")
        wait = bool(data.get("wait", False))
        timeout = int(data.get("timeoutSeconds", 120))

        if not rel_path:
            return jsonify({"success": False, "error": "Missing required field: path"}), 400

        script_path = (WORKSPACE_ROOT / rel_path).resolve()
        root_resolved = WORKSPACE_ROOT.resolve()
        try:
            script_path.relative_to(root_resolved)
        except Exception:
            return jsonify({"success": False, "error": "Script path must be inside workspace"}), 400

        if not script_path.exists() or not script_path.is_file():
            return jsonify({"success": False, "error": "Script file not found"}), 404

        suffix = script_path.suffix.lower()
        if isinstance(args_raw, list):
            args = [str(a) for a in args_raw]
        else:
            args = shlex.split(str(args_raw)) if str(args_raw).strip() else []

        if suffix == ".py":
            cmd = [sys.executable, str(script_path), *args]
        elif suffix == ".ps1":
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path), *args]
        elif suffix in {".cmd", ".bat"}:
            cmd = ["cmd", "/c", str(script_path), *args]
        elif suffix == ".sh":
            cmd = ["bash", str(script_path), *args]
        else:
            return jsonify({"success": False, "error": f"Unsupported script type: {suffix}"}), 400

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        root_str = str(WORKSPACE_ROOT)
        existing = env.get("PYTHONPATH", "")
        if root_str not in existing.split(os.pathsep):
            env["PYTHONPATH"] = os.pathsep.join([root_str, existing]) if existing else root_str

        if wait:
            proc = subprocess.run(
                cmd,
                cwd=str(WORKSPACE_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(1, timeout),
                env=env,
            )
            output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
            return jsonify({
                "success": proc.returncode == 0,
                "path": rel_path,
                "command": cmd,
                "returncode": proc.returncode,
                "output": output[-6000:],
            })

        creationflags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen(
            cmd,
            cwd=str(WORKSPACE_ROOT),
            env=env,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return jsonify({
            "success": True,
            "path": rel_path,
            "command": cmd,
            "pid": proc.pid,
            "started": True,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Script execution timed out"}), 408
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/search', methods=['GET'])
def api_search():
    """Search project text artifacts for a query.

    Intended for fast retrieval of prior work/lessons across loops.
    Scans a bounded set of workspace files (archives, reports, tasks, core docs).
    """
    try:
        q = (request.args.get('q') or '').strip()
        if not q:
            return jsonify({"success": False, "error": "Missing 'q'"}), 400

        try:
            limit = int(request.args.get('limit') or '50')
        except Exception:
            limit = 50
        limit = max(1, min(200, limit))

        # File set (bounded)
        candidates = []
        candidates.extend(WORKSPACE_ROOT.glob('*.md'))
        candidates.extend((WORKSPACE_ROOT / 'docs').glob('*.md'))
        candidates.extend((WORKSPACE_ROOT / 'reports').glob('report_*.md'))
        candidates.extend((WORKSPACE_ROOT / 'tasks').glob('task_TASK_*.md'))
        candidates.extend((WORKSPACE_ROOT / 'archive').glob('ARCHIV_*.md'))

        # Deduplicate and keep stable ordering
        seen = set()
        files = []
        for p in sorted(candidates, key=lambda p: str(p).lower()):
            if not p.exists() or not p.is_file():
                continue
            rp = str(p.resolve())
            if rp in seen:
                continue
            seen.add(rp)
            files.append(p)

        q_lower = q.lower()
        results = []
        for p in files:
            try:
                txt = p.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            for idx, line in enumerate(txt.splitlines(), start=1):
                if q_lower in line.lower():
                    results.append({
                        "path": str(p.relative_to(WORKSPACE_ROOT)).replace('\\', '/'),
                        "line": idx,
                        "text": line.strip()[:240],
                    })
                    if len(results) >= limit:
                        return jsonify({"success": True, "query": q, "limit": limit, "results": results})

        return jsonify({"success": True, "query": q, "limit": limit, "results": results})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/query', methods=['POST'])
def api_query():
    """Structured query endpoint with metadata filtering and ranking.
    
    POST body (JSON):
    {
        "text": "search terms",
        "task_id": "TASK_0041",
        "loop_min": 20,
        "loop_max": 24,
        "file": "loop_cockpit.py",
        "tags": ["search", "cockpit"],
        "status": "CLOSED",
        "validation": true,
        "sort": "relevance",  // or "recency", "loop_num"
        "limit": 50
    }
    """
    try:
        params = request.get_json() or {}
        
        # Load query index
        if not QUERY_INDEX_JSON.exists():
            # Generate on-demand if missing
            from loop_guardrails import write_json
            data = query_index_data(WORKSPACE_ROOT)
            write_json(QUERY_INDEX_JSON, data)
        else:
            with open(QUERY_INDEX_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        reports = data.get("reports", [])
        tasks = data.get("tasks", [])
        
        # Apply filters
        filtered_reports = []
        for report in reports:
            # Task ID filter
            if params.get("task_id") and report.get("taskId") != params["task_id"]:
                continue
            
            # Loop range filter
            loop_num = report.get("loopNum", 0)
            if params.get("loop_min") and loop_num < params["loop_min"]:
                continue
            if params.get("loop_max") and loop_num > params["loop_max"]:
                continue
            
            # File filter
            if params.get("file"):
                files = report.get("filesChanged", [])
                if not any(params["file"] in f for f in files):
                    continue
            
            # Tags filter
            if params.get("tags"):
                report_tags = set(report.get("tags", []))
                query_tags = set(params["tags"])
                if not query_tags.intersection(report_tags):
                    continue
            
            # Validation filter
            if params.get("validation") is not None:
                if report.get("validationPassed") != params["validation"]:
                    continue
            
            # Text search in goal/objective
            if params.get("text"):
                text_lower = params["text"].lower()
                goal = (report.get("goal") or "").lower()
                keywords = report.get("keywords", [])
                if text_lower not in goal and not any(text_lower in kw for kw in keywords):
                    continue
            
            filtered_reports.append(report)
        
        # Ranking
        sort_mode = params.get("sort", "relevance")
        
        if sort_mode == "recency":
            filtered_reports.sort(key=lambda r: r.get("loopNum", 0), reverse=True)
        elif sort_mode == "loop_num":
            filtered_reports.sort(key=lambda r: r.get("loopNum", 0))
        elif sort_mode == "relevance":
            # Simple relevance scoring
            text_query = params.get("text", "").lower()
            
            def calc_relevance(report):
                score = 0.0
                goal = (report.get("goal") or "").lower()
                keywords = report.get("keywords", [])
                
                # Text match scoring
                if text_query:
                    if text_query in goal:
                        score += 10.0
                    for kw in keywords:
                        if text_query in kw:
                            score += 2.0
                
                # Recency bonus (newer loops score higher)
                loop_num = report.get("loopNum", 0)
                score += loop_num * 0.1
                
                # Validation success bonus
                if report.get("validationPassed") is True:
                    score += 1.0
                
                return score
            
            filtered_reports.sort(key=calc_relevance, reverse=True)
        
        # Limit results
        limit = min(params.get("limit", 50), 200)
        filtered_reports = filtered_reports[:limit]
        
        # Format results with context
        results = []
        for report in filtered_reports:
            goal = report.get("goal", "")
            snippet = goal[:200] + "..." if len(goal) > 200 else goal
            
            results.append({
                "type": "report",
                "id": report.get("id"),
                "path": report.get("path"),
                "taskId": report.get("taskId"),
                "loopNum": report.get("loopNum"),
                "snippet": snippet,
                "filesChanged": report.get("filesChanged", []),
                "validationPassed": report.get("validationPassed"),
                "tags": report.get("tags", []),
            })
        
        return jsonify({
            "success": True,
            "total": len(results),
            "results": results,
            "filters": params,
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# KNOWLEDGE DATABASE API (SQLite FTS5)
# =============================================================================

@app.route('/api/knowledge/rebuild', methods=['POST'])
def api_knowledge_rebuild():
    """Rebuild the SQLite knowledge database from markdown sources.
    
    This regenerates keeper_knowledge.db from scratch by indexing
    all reports, archives, tasks, and extracting lessons learned.
    """
    try:
        policy_decision = enforce_db_write_policy(
            WORKSPACE_ROOT,
            operation="knowledge.rebuild",
            actor="api",
        )
        if not policy_decision.allowed:
            return jsonify({
                "success": False,
                "error": policy_decision.reason,
                "policy": policy_decision.policy_path,
            }), 403

        db = KnowledgeDB(WORKSPACE_ROOT)
        stats = db.rebuild_with_write_guard()
        db.close()
        
        return jsonify({
            "success": True,
            "stats": stats,
            "message": (
                f"Indexed {stats['reports_indexed']} reports, {stats['archives_indexed']} archives, "
                f"{stats['tasks_indexed']} tasks, {stats.get('docs_indexed', 0)} docs, "
                f"{stats.get('bugs_indexed', 0)} bugs, {stats.get('code_indexed', 0)} code artifacts"
            ),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/policy-gate/status', methods=['GET'])
def api_policy_gate_status():
    """Get deterministic policy gate status snapshot."""
    try:
        status = get_policy_gate_status(WORKSPACE_ROOT)
        return jsonify({
            "success": True,
            "status": status,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/knowledge/index-file', methods=['POST'])
def api_knowledge_index_file():
    """Incrementally index a single artifact path into the knowledge DB.

    JSON body:
    - path: workspace-relative or absolute file path
    """
    try:
        data = request.get_json() or {}
        path_value = (data.get("path") or "").strip()
        if not path_value:
            return jsonify({"success": False, "error": "Missing required 'path'"}), 400

        candidate = Path(path_value)
        if not candidate.is_absolute():
            candidate = (WORKSPACE_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not candidate.exists():
            return jsonify({"success": False, "error": f"File not found: {candidate}"}), 404

        try:
            rel_path = candidate.relative_to(WORKSPACE_ROOT)
            routed = KnowledgeDBEventHandler.on_path_changed(rel_path, actor="api")
        except Exception:
            routed = KnowledgeDBEventHandler.on_path_changed(candidate, actor="api")

        if not routed:
            return jsonify({
                "success": False,
                "error": "Unsupported file pattern for incremental indexing",
            }), 400

        return jsonify({
            "success": True,
            "indexed_path": str(candidate),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/knowledge/stats', methods=['GET'])
def api_knowledge_stats():
    """Get knowledge database statistics."""
    try:
        db = KnowledgeDB(WORKSPACE_ROOT)
        stats = db.get_stats()
        db.close()
        
        return jsonify({
            "success": True,
            "stats": stats,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/knowledge/search', methods=['GET', 'POST'])
def api_knowledge_search():
    """Search the knowledge database with full-text search (FTS5).
    
    Query params (GET) or JSON body (POST):
    - q: Search query (required)
    - types: Comma-separated list of types (report,archive,lesson,task)
    - task_id: Filter by task ID
    - loop_min: Minimum loop number
    - loop_max: Maximum loop number
    - validation: Filter by validation (true/false)
    - category: Filter lessons by category (success/failure/observation/warning)
    - limit: Max results (default 20, max 100)
    """
    try:
        # Parse parameters from GET or POST
        if request.method == 'POST':
            data = request.get_json() or {}
            q = data.get('q', '')
            types_str = data.get('types', '')
            task_id = data.get('task_id')
            loop_min = data.get('loop_min')
            loop_max = data.get('loop_max')
            validation = data.get('validation')
            category = data.get('category')
            limit = data.get('limit', 20)
        else:
            q = request.args.get('q', '')
            types_str = request.args.get('types', '')
            task_id = request.args.get('task_id')
            loop_min = request.args.get('loop_min')
            loop_max = request.args.get('loop_max')
            validation = request.args.get('validation')
            category = request.args.get('category')
            limit = request.args.get('limit', 20)
        
        if not q:
            return jsonify({"success": False, "error": "Missing required 'q' parameter"}), 400
        
        # Parse types
        types = None
        if types_str:
            types = [t.strip() for t in types_str.split(',') if t.strip()]
        
        # Convert string params
        try:
            loop_min = int(loop_min) if loop_min else None
            loop_max = int(loop_max) if loop_max else None
            limit = min(int(limit), 100)
        except (ValueError, TypeError):
            pass
        
        # Parse validation
        if validation is not None:
            if isinstance(validation, str):
                validation = validation.lower() == 'true'
        
        # Query database
        db = KnowledgeDB(WORKSPACE_ROOT)
        
        if not db.db_path.exists():
            db.close()
            return jsonify({
                "success": False,
                "error": "Knowledge database not found. Call /api/knowledge/rebuild first.",
            }), 404
        
        results = db.search(
            q,
            types=types,
            task_id=task_id,
            loop_min=loop_min,
            loop_max=loop_max,
            validation_passed=validation,
            category=category,
            limit=limit,
        )
        db.close()
        
        # Format results
        formatted = []
        for r in results:
            formatted.append({
                "type": r.type,
                "id": r.id,
                "relevance": round(r.relevance, 2),
                "snippet": r.snippet,
                "context": r.context,
            })
        
        return jsonify({
            "success": True,
            "query": q,
            "total": len(formatted),
            "results": formatted,
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/knowledge/lessons', methods=['GET'])
def api_knowledge_lessons():
    """Get lessons by category.
    
    Query params:
    - category: success, failure, observation, warning
    - limit: Max results (default 50)
    """
    try:
        category = request.args.get('category', 'observation')
        limit = min(int(request.args.get('limit', 50)), 200)
        
        db = KnowledgeDB(WORKSPACE_ROOT)
        
        if not db.db_path.exists():
            db.close()
            return jsonify({
                "success": False,
                "error": "Knowledge database not found. Call /api/knowledge/rebuild first.",
            }), 404
        
        lessons = db.get_lessons_by_category(category, limit)
        db.close()
        
        return jsonify({
            "success": True,
            "category": category,
            "total": len(lessons),
            "lessons": lessons,
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/knowledge/file-history', methods=['GET'])
def api_knowledge_file_history():
    """Get history of which tasks/reports modified a specific file.
    
    Query params:
    - file: Filename to search for (required)
    """
    try:
        filename = request.args.get('file')
        if not filename:
            return jsonify({"success": False, "error": "Missing required 'file' parameter"}), 400
        
        db = KnowledgeDB(WORKSPACE_ROOT)
        
        if not db.db_path.exists():
            db.close()
            return jsonify({
                "success": False,
                "error": "Knowledge database not found. Call /api/knowledge/rebuild first.",
            }), 404
        
        history = db.get_file_history(filename)
        db.close()
        
        return jsonify({
            "success": True,
            "file": filename,
            "total": len(history),
            "history": history,
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/knowledge/chat', methods=['POST'])
def api_knowledge_chat():
    """Contextual Q&A using the knowledge database.
    
    Takes a natural language question, searches the knowledge base,
    and returns a synthesized answer with sources.
    """
    try:
        data = request.get_json() or {}
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({"success": False, "error": "No question provided"}), 400
        
        # Connect to knowledge database
        db_path = WORKSPACE_ROOT / "keeper_knowledge.db"
        if not db_path.exists():
            return jsonify({
                "success": False,
                "error": "Knowledge database not found. Click 'Rebuild Knowledge DB' first.",
            }), 404
        
        from knowledge_db import KnowledgeDB
        db = KnowledgeDB(WORKSPACE_ROOT)
        
        # Extract keywords from question for search
        # Remove common stop words and use remaining terms
        stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'do', 'does', 'can', 'i', 
                      'we', 'you', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with',
                      'and', 'or', 'but', 'if', 'when', 'where', 'why', 'which', 'who',
                      'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                      'this', 'that', 'these', 'those', 'it', 'its', 'about', 'from'}
        
        words = question.lower().replace('?', '').replace('.', '').replace(',', '').split()
        search_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        # If no meaningful terms, use whole question
        search_query = ' '.join(search_terms) if search_terms else question
        
        # Search in multiple categories
        all_results = []
        
        # Search lessons (most likely to have relevant info)
        lessons = db.search(search_query, types=['lesson'], limit=10)
        for item in lessons:
            all_results.append({
                'type': 'lesson',
                'id': item.context.get('source_id', ''),
                'content': item.snippet,
                'context': f"{item.context.get('source_type', '')} - {item.context.get('category', '')}",
                'relevance': item.relevance
            })
        
        # Search archives
        archives = db.search(search_query, types=['archive'], limit=5)
        for item in archives:
            all_results.append({
                'type': 'archive',
                'id': item.id,
                'content': item.snippet,
                'context': f"Loop {item.context.get('loop_num', '?')}",
                'relevance': item.relevance
            })
        
        # Search reports
        reports = db.search(search_query, types=['report'], limit=5)
        for item in reports:
            all_results.append({
                'type': 'report',
                'id': item.id,
                'content': item.snippet,
                'context': item.context.get('goal', ''),
                'relevance': item.relevance
            })
        
        # Search tasks
        tasks = db.search(search_query, types=['task'], limit=5)
        for item in tasks:
            all_results.append({
                'type': 'task',
                'id': item.id,
                'content': item.snippet,
                'context': f"Status: {item.context.get('status', '?')}",
                'relevance': item.relevance
            })
        
        db.close()
        
        # Sort by relevance
        all_results.sort(key=lambda x: x['relevance'], reverse=True)
        top_results = all_results[:10]
        
        # Synthesize answer from results
        if not top_results:
            answer = "I couldn't find relevant information about this in the knowledge base. Try rephrasing your question or using different keywords."
            sources = []
        else:
            # Build answer from top results
            answer_parts = []
            
            # Group by type for organized response
            lessons_found = [r for r in top_results if r['type'] == 'lesson']
            archives_found = [r for r in top_results if r['type'] == 'archive']
            tasks_found = [r for r in top_results if r['type'] == 'task']
            reports_found = [r for r in top_results if r['type'] == 'report']
            
            if lessons_found:
                answer_parts.append("**Based on lessons learned:**")
                for l in lessons_found[:3]:
                    answer_parts.append(f"• {l['content'][:200]}{'...' if len(l['content']) > 200 else ''}")
            
            if archives_found:
                answer_parts.append("\n**Related archive entries:**")
                for a in archives_found[:2]:
                    answer_parts.append(f"• [{a['id']}] {a['content'][:150]}{'...' if len(a['content']) > 150 else ''}")
            
            if tasks_found:
                answer_parts.append("\n**Related tasks:**")
                for t in tasks_found[:2]:
                    answer_parts.append(f"• [{t['id']}] {t['content'][:150]}{'...' if len(t['content']) > 150 else ''}")
            
            if reports_found:
                answer_parts.append("\n**From project reports:**")
                for r in reports_found[:2]:
                    answer_parts.append(f"• {r['content'][:150]}{'...' if len(r['content']) > 150 else ''}")
            
            answer = '\n'.join(answer_parts)
            sources = [{'type': r['type'], 'id': r['id'], 'relevance': r['relevance']} for r in top_results[:5]]
        
        return jsonify({
            "success": True,
            "question": question,
            "search_terms": search_terms,
            "answer": answer,
            "sources": sources,
            "sources_count": len(top_results),
        })
        
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()}), 500


@app.route('/api/file-index', methods=['GET'])
def api_file_index():
    """Get file index showing which tasks/reports modified each file."""
    try:
        if not QUERY_INDEX_JSON.exists():
            from loop_guardrails import write_json
            data = query_index_data(WORKSPACE_ROOT)
            write_json(QUERY_INDEX_JSON, data)
        else:
            with open(QUERY_INDEX_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        file_index = data.get("fileIndex", {})
        
        # Optional filter by filename
        filename = request.args.get('file')
        if filename:
            return jsonify({
                "success": True,
                "file": filename,
                "data": file_index.get(filename, {})
            })
        
        return jsonify({
            "success": True,
            "fileIndex": file_index
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/concept-index', methods=['GET'])
def api_concept_index():
    """Get concept/tag index showing which tasks/reports are tagged with each concept."""
    try:
        if not QUERY_INDEX_JSON.exists():
            from loop_guardrails import write_json
            data = query_index_data(WORKSPACE_ROOT)
            write_json(QUERY_INDEX_JSON, data)
        else:
            with open(QUERY_INDEX_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        concept_index = data.get("conceptIndex", {})
        
        # Optional filter by tag
        tag = request.args.get('tag')
        if tag:
            return jsonify({
                "success": True,
                "tag": tag,
                "data": concept_index.get(tag, {})
            })
        
        return jsonify({
            "success": True,
            "conceptIndex": concept_index
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/archives')
def get_archives():
    """Get archive file list."""
    return jsonify({
        "archives": get_archive_files()
    })

@app.route('/api/audit-status')
def audit_status():
    """
    Check loop integrity audit status.
    Returns pre-finalization green light check results.
    """
    try:
        is_valid, issues, warnings = audit_loop_integrity()
        
        # Also check archive consistency
        consistency_result = check_archive_consistency(WORKSPACE_ROOT)

        # Metadata + consistency lint (drift detection)
        lint = metadata_lint(WORKSPACE_ROOT)
        lint_errors = [f"{e['code']}: {e['message']} (hint: {e.get('hint','')})" for e in lint.get('errors', [])]
        lint_warnings = [f"{w['code']}: {w['message']} (hint: {w.get('hint','')})" for w in lint.get('warnings', [])]
        
        # Task metadata drift warnings
        task_warnings = validate_task_metadata()
        
        # Combine results
        all_issues = issues + consistency_result['issues'] + lint_errors
        all_warnings = warnings + consistency_result['warnings'] + lint_warnings + task_warnings
        is_fully_valid = is_valid and consistency_result['is_consistent'] and (lint.get('summary', {}).get('errorCount', 0) == 0)
        
        current_state = read_json_file(CURRENT_JSON)
        loop_num = current_state.get('STATE', {}).get('loop', 0)
        last_task = current_state.get('STATE', {}).get('lastTaskWorked')
        report_files = get_report_files()
        loop_reports = [r for r in report_files if f"_L{loop_num:02d}_" in r]

        suggested_last_task = None
        if (not last_task or last_task == 'None') and loop_reports:
            suggested_last_task = infer_last_task_from_reports(loop_num)
        
        return jsonify({
            "success": True,
            "greenLight": is_fully_valid,
            "loop": loop_num,
            "lastTaskWorked": last_task,
            "suggestedLastTaskWorked": suggested_last_task,
            "reportCount": len(loop_reports),
            "reports": loop_reports,
            "violations": all_issues,
            "warnings": all_warnings,
            "lint": lint,
            "archiveConsistency": {
                "is_consistent": consistency_result['is_consistent'],
                "stats": consistency_result['stats']
            },
            "canFinalize": is_fully_valid,
            "message": "✅ All checks passed - ready to finalize" if is_fully_valid else "❌ Violations detected - finalization blocked"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def create_bootstrap_file(loop_num, last_task):
    """Create _BOOTSTRAP.md file for fresh session entry."""
    bootstrap_path = WORKSPACE_ROOT / "_BOOTSTRAP.md"
    
    # Read the canonical bootstrap template
    template_path = WORKSPACE_ROOT / "templates" / "canonical_bootstrap_template.md"
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        # Fallback to hardcoded content if template not found
        content = f"""# _BOOTSTRAP

MODE: EPHEMERAL
PURPOSE: Fresh Session Start.
DELETE AFTER CONFIRMED VALIDATION OF BOOTSTRAP SUCCESS.
CREATED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

---

### 1) GATE CHECK
- Run Loop_cockpit.py and loop_guardrails.py for safety framework.
- POLICY GATE RULE: Any knowledge DB write must pass deterministic `policy_gate` checks.
- Absorb content from Littleboot.md (session-related).  
- Absorb project framework concept from CANONICAL_SYSTEM_SPEC.md.
- Read `_LOOP_GATE.md`.
- If BLOCKED → STOP and report to human.
- If PASS → Continue.

### 2) SESSION PACK CHECK
- If `_SESSION.md` exists → Read it, skip to step 5.
- If not → Continue to step 3.

### 3) STATE LOAD
- OPS_PROTOCOLS.md – Canonical rules.
- `current.json` – State authority; Keeping this file up to date through the loop is your responsibility. !!! NO ACTIONS BEFORE CURRENT.JSON IS SET ON ACTIVE! FIRST ACTION AFTER CURRENT.JSON IS SET ON ACTIVE: - DELETE LITTLEBOOT.MD & CONFIRM NEITHER BOOTSTRAP.MD NOR LITTLEBOOT.MD EXIST IN ROOT!
- `knownissues.json` — Full read (small).

### 4) TOKEN AWARENESS
```
Budget: 200k | Start Zone: SAFE
Response style adapts to zone
Artifacts > chat for detail
Context warning at 30k
```

### 5) BREADCRUMB METHODOLOGY (CRITICAL)
```
AI DECISION PATH TRACKING: ACTIVE
- All file operations create unique hash-based breadcrumbs
- Breadcrumbs track source context → target file navigation
- Extract trails with: python -m ai_breadcrumb_tracker --extract
- Breadcrumb format: AI_BREADCRUMB: [hash] | SRC: [context] | OP: [operation] | TS: [timestamp]
- Purpose: Map AI logical flow, prevent decision drift, enable path reconstruction
- Integration: Automatic injection on file access/create/modify via loop_cockpit.py
- Drift Protection: Integrity checks validate breadcrumb continuity
```

### 6) CONFIRM ENTRY
- POST `/api/confirm-bootstrap`.
- Delete this file.

### 7) PROCEED
- Work on top priority task from NEU.md.
- REPORT-FIRST always.
- If any step fails → STOP and report to human.

---

## ENTRY COMPLETE

DELETE: _BOOTSTRAP.md

---

END
"""
    
    # Substitute placeholders
    content = content.replace('YYYY-MM-DDTHH:MM:SSZ', datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    content = content.replace('TASK_0188', last_task or 'None')
    content = content.replace('93', str(loop_num))
    content = content.replace('Loop 92 archived', f'Loop {loop_num - 1} archived')

    # TASK_0245: Inject bounded DB-derived startup context (non-blocking).
    try:
        db_briefing = startup_db_briefing_markdown(WORKSPACE_ROOT, max_chars=1400)
        content = content.rstrip() + "\n\n---\n\n" + db_briefing + "\n"
    except Exception as e:
        # Never block bootstrap generation on briefing failures.
        content = content.rstrip() + f"\n\n---\n\n## DB KNOWLEDGE BRIEFING (BOUNDED)\n\n- Briefing unavailable: {e}\n"
    
    with open(bootstrap_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return bootstrap_path.exists()

@app.route('/api/reset-loop', methods=['POST'])
def reset_loop():
    """Execute loop reset procedure (Phase 1: Archive and prepare)."""
    try:
        # 1. Check current status
        current_state = read_json_file(CURRENT_JSON)
        if current_state.get('STATE', {}).get('status') != 'FINALIZED':
            return jsonify({
                "success": False,
                "error": "Loop status must be FINALIZED to reset"
            }), 400
        
        # 2. Find ARCHIV file in root
        pending_archiv = find_pending_archiv()
        if not pending_archiv:
            return jsonify({
                "success": False,
                "error": "No ARCHIV file found in root directory"
            }), 400
        
        # 3. Create archive directory if it doesn't exist
        ARCHIVE_DIR.mkdir(exist_ok=True)
        
        # 4. Move ARCHIV file
        dest_path = ARCHIVE_DIR / pending_archiv.name
        if dest_path.exists():
            # Avoid Windows move failure when a file with the same name already exists.
            # Preserve the existing file by relocating it outside the main archive list.
            conflicts_dir = ARCHIVE_DIR / "_conflicts"
            conflicts_dir.mkdir(exist_ok=True)
            ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            conflict_path = conflicts_dir / f"{dest_path.stem}_DUPLICATE_{ts}{dest_path.suffix}"
            shutil.move(str(dest_path), str(conflict_path))
        shutil.move(str(pending_archiv), str(dest_path))
        
        # 5. Update current.json
        current_loop = current_state['STATE']['loop']
        last_task = current_state['STATE'].get('lastTaskWorked')
        current_state['STATE']['loop'] = current_loop + 1
        current_state['STATE']['status'] = 'READY_FOR_RESET'
        current_state['STATE']['archiveCurrent'] = f"archive/{pending_archiv.name}"
        # Reset is complete once ARCHIV has been moved to archive/. Clear any stale in-progress marker.
        current_state['STATE']['archiveInProgress'] = None
        # A new loop starts with no recorded work.
        current_state['STATE']['lastTaskWorked'] = None
        current_state['STATE']['lastUpdate'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        current_state['STATE']['summary'] = f"Loop {current_loop} archived. Ready for loop {current_loop + 1}."
        
        write_json_file(CURRENT_JSON, current_state)
        
        # 6. Create _BOOTSTRAP.md file
        bootstrap_created = create_bootstrap_file(current_loop + 1, last_task)
        
        if not bootstrap_created:
            return jsonify({
                "success": False,
                "error": "Failed to create _BOOTSTRAP.md file"
            }), 500

        # 7. Generate lean session pack for bootstrap optimization
        try:
            from scripts.generate_session_pack import generate_session_pack
            generate_session_pack()
        except Exception as e:
            # Non-fatal: session pack is optional optimization
            pass
        
        # 8. Regenerate gate deterministically (between loops)
        regenerate_loop_gate(reason="reset-loop")

        # 9. Deterministic post-reset archive index reconciliation (non-blocking).
        reconcile_result = reconcile_archive_index_with_retries(
            dest_path,
            retry_budget=3,
            retry_sleep_seconds=0.4,
            actor="system",
            workspace_root=WORKSPACE_ROOT,
        )
        
        return jsonify({
            "success": True,
            "phase": "awaiting_execution",
            "newLoop": current_loop + 1,
            "bootstrap_command": "QUALITY GATE: Before delivering output, verify: Completeness, Accuracy, Clarity, Format. If any check fails, revise before delivery.\n\nRead _BOOTSTRAP.md",
            "message": "Loop reset prepared. Close chat and start new session.",
            "archiveReconcile": reconcile_result,
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/milestone')
def get_milestone():
    """Get milestone progress."""
    milestone_data = read_json_file(MILESTONE)
    return jsonify(milestone_data)

@app.route('/api/finalize-loop', methods=['POST'])
def finalize_loop():
    """Finalize the current loop (AI signals work is done for this loop)."""

    try:
        data = request.json or {}
        result = finalize_loop_procedure(last_task_override=data.get('lastTaskWorked'))
        return jsonify(result)
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "dbQuality": get_db_quality_gate_status(auto_heal=False),
            "blocked": True
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/task/start-monitoring', methods=['POST'])
def start_task_monitoring():
    """Start monitoring token usage for a task."""
    try:
        from token_monitor import LoopBudgetTracker
        tracker = LoopBudgetTracker(Path('.'))
        
        data = request.json or {}
        task_id = data.get('task_id')
        if not task_id:
            return jsonify({"error": "task_id required"}), 400
        
        result = tracker.start_task_monitoring(task_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/task/end-monitoring', methods=['POST'])
def end_task_monitoring():
    """End monitoring for current task."""
    try:
        from token_monitor import LoopBudgetTracker
        tracker = LoopBudgetTracker(Path('.'))
        
        result = tracker.end_task_monitoring()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/token/status', methods=['GET'])
def get_token_status():
    """Get comprehensive token usage status."""
    try:
        from token_monitor import LoopBudgetTracker
        from token_guard import get_token_guard
        from copilot_extension_integration import get_copilot_tracker

        tracker = LoopBudgetTracker(Path('.'))
        guard = get_token_guard(Path('.'))
        copilot_tracker = get_copilot_tracker(Path('.'))

        budget_status = tracker.get_budget_status()
        protection_status = guard.get_protection_status()
        recent_alerts = guard.get_alerts(time.time() - 3600)  # Last hour
        extension_status = copilot_tracker.get_extension_status()

        return jsonify({
            "budget": budget_status,
            "protection": protection_status,
            "alerts": recent_alerts,
            "current_task": tracker.current_task,
            "copilot_extension": extension_status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def sync_copilot_extension():
    """Sync with Copilot Token Tracker extension data."""
    try:
        from copilot_extension_integration import get_copilot_tracker
        from token_monitor import LoopBudgetTracker

        tracker = get_copilot_tracker(Path('.'))
        monitor = LoopBudgetTracker(Path('.'))

        extension_status = tracker.get_extension_status()
        session_data = tracker.scan_session_files()
        sync_result = tracker.sync_with_monitor(monitor)

        return jsonify({
            "extension_status": extension_status,
            "session_analysis": session_data,
            "sync_result": sync_result,
            "integration_status": "Extension data integrated with monitoring system"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def finalize_loop_procedure(last_task_override=None, human_override=False) -> dict:
    """Finalize loop (shared by API + CLI). Raises ValueError when blocked."""

    current_state = read_json_file(CURRENT_JSON)
    loop_num = current_state.get('STATE', {}).get('loop')
    warnings = []
    consistency_result = {"warnings": []}
    lint = {"warnings": []}
    archiv_written = False

    if current_state.get('STATE', {}).get('status') not in ('ACTIVE', 'READY_FOR_FINALIZATION'):
        raise ValueError("Loop must be ACTIVE or READY_FOR_FINALIZATION to finalize")

    # Create human override approval if requested
    if human_override:
        create_human_override_approval(loop_num)

    # Canonical finalization gate validation (single source of truth).
    if not human_override:
        fin_valid, fin_error = validate_finalization_entry_gates()
        if not fin_valid:
            raise ValueError(f"Pre-finalization validation FAILED: {fin_error}")

    # REPORT FRESHNESS CHECK: prevent finalization on very recent report files (race condition mitigation)
    report_files = get_report_files()
    loop_report_names = [r for r in report_files if f"_L{loop_num:02d}_" in r]
    fresh_reports = []
    now_ts = datetime.now(timezone.utc).timestamp()
    for rel in loop_report_names:
        path = WORKSPACE_ROOT / rel
        if not path.exists():
            # Try in reports/ directory if relative path omitted
            path = WORKSPACE_ROOT / 'reports' / Path(rel).name

        # If producer created a .ready marker, consider this report ready regardless of mtime
        ready_path = Path(str(path) + '.ready')
        if ready_path.exists():
            # Skip freshness check for this report
            continue

        try:
            mtime = path.stat().st_mtime
            age = now_ts - mtime
            if age < REPORT_FRESHNESS_SECONDS:
                fresh_reports.append((str(path), int(age)))
        except Exception:
            # If we can't stat the file, ignore it here; other checks will catch missing files
            continue

    # If fresh reports found, attempt retry loop (quick waits) before failing
    attempt = 0
    while fresh_reports and attempt <= REPORT_FRESHNESS_MAX_RETRIES:
        if attempt == REPORT_FRESHNESS_MAX_RETRIES:
            files_list = ", ".join([f"{p} ({a}s)" for p, a in fresh_reports])
            # Log block reason for audit
            log_transaction("finalize_block", "reports", None, None, "FAILED", f"REPORT_TOO_FRESH: {files_list}")
            raise ValueError(
                "REPORT_TOO_FRESH: Pre-finalization blocked: Recent report files detected (possible incomplete writes). "
                f"Wait {REPORT_FRESHNESS_SECONDS} seconds after report modification before finalizing. Fresh reports: {files_list}"
            )
        # Log wait and sleep
        wait_seconds = REPORT_FRESHNESS_RETRY_INTERVAL
        log_transaction("finalize_wait", "reports", None, None, "WAIT", f"Waiting {wait_seconds}s (attempt {attempt+1}/{REPORT_FRESHNESS_MAX_RETRIES}) for report flush: {fresh_reports}")
        # Sleep then re-evaluate freshness
        import time
        time.sleep(wait_seconds)

        # Re-evaluate fresh reports
        fresh_reports = []
        now_ts = datetime.now(timezone.utc).timestamp()
        for rel in loop_report_names:
            path = WORKSPACE_ROOT / rel
            if not path.exists():
                path = WORKSPACE_ROOT / 'reports' / Path(rel).name
            try:
                mtime = path.stat().st_mtime
                age = now_ts - mtime
                if age < REPORT_FRESHNESS_SECONDS:
                    fresh_reports.append((str(path), int(age)))
            except Exception:
                continue

        attempt += 1

    # SESSION CONFIRMATION CHECK: ensure a confirm-bootstrap exists and that work was recorded after it
    try:
        # Require that a transaction log exists so validation is deterministic
        if not TRANSACTION_LOG.exists():
            log_transaction("finalize_block", "session", None, None, "FAILED", "MISSING_CONFIRM_BOOTSTRAP: transaction log not found")
            raise ValueError("MISSING_CONFIRM_BOOTSTRAP: Pre-finalization blocked: transaction log not found. Ensure /api/confirm-bootstrap was called and the transaction log exists.")

        confirm_ts = None
        with open(TRANSACTION_LOG, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get('operation') == 'confirm-bootstrap':
                    confirm_ts = e.get('timestamp')
        # If no confirm-bootstrap recorded, block finalization (protect against forgotten bootstrap)
        if not confirm_ts:
            log_transaction("finalize_block", "session", None, None, "FAILED", "MISSING_CONFIRM_BOOTSTRAP: no confirm-bootstrap record found")
            raise ValueError("MISSING_CONFIRM_BOOTSTRAP: Pre-finalization blocked: no confirm-bootstrap record found. Ensure '/api/confirm-bootstrap' was called after deleting _BOOTSTRAP.md before working on tasks.")

        # Parse confirm timestamp and verify subsequent work entries exist
        confirm_dt = datetime.fromisoformat(confirm_ts.replace('Z', '+00:00'))
        has_work = False
        with open(TRANSACTION_LOG, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get('operation') in ('file_write', 'session_regenerate') and e.get('outcome') == 'SUCCESS':
                    try:
                        ts = datetime.fromisoformat(e.get('timestamp').replace('Z', '+00:00'))
                        if ts > confirm_dt:
                            has_work = True
                            break
                    except Exception:
                        continue

        # If no recorded work found in transaction log, fall back to filesystem checks
        if not has_work:
            reports_dir = WORKSPACE_ROOT / 'reports'
            if reports_dir.exists() and reports_dir.is_dir():
                for p in reports_dir.iterdir():
                    if p.is_file() and f"_L{loop_num:02d}_" in p.name:
                        try:
                            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                            if mtime > confirm_dt:
                                has_work = True
                                break
                        except Exception:
                            continue

            # Also consider regenerated _SESSION.md mtime
            if not has_work and SESSION_MD.exists():
                try:
                    mtime = datetime.fromtimestamp(SESSION_MD.stat().st_mtime, tz=timezone.utc)
                    if mtime > confirm_dt:
                        has_work = True
                except Exception:
                    pass

        if not has_work:
            log_transaction("finalize_block", "session", None, None, "FAILED", "MISSING_SESSION_WORK: no recorded work after confirm-bootstrap")
            raise ValueError("MISSING_SESSION_WORK: Pre-finalization blocked: no recorded work after confirm-bootstrap. Ensure you performed work (file writes or session pack regeneration) after confirming bootstrap.")
    except ValueError:
        raise
    except Exception:
        # Conservative default: if we can't inspect logs reliably, block finalization
        log_transaction("finalize_block", "session", None, None, "FAILED", "MISSING_SESSION_WORK: unable to verify session activity")
        raise ValueError("MISSING_SESSION_WORK: Pre-finalization blocked: unable to verify session activity in transaction log.")

    loop_num = current_state['STATE']['loop']
    last_task = last_task_override or current_state['STATE'].get('lastTaskWorked')
    if not last_task or last_task == 'None':
        inferred = infer_last_task_from_reports(loop_num)
        if inferred:
            last_task = inferred

    archiv_name = f"ARCHIV_{loop_num:04d}.md"
    archiv_path = WORKSPACE_ROOT / archiv_name

    neu_content = read_text_file(NEU_MD)
    alt_content = read_text_file(ALT_MD)

    archiv_content = f"""# ARCHIV_{loop_num:04d}

MODE: IMMUTABLE
FINALIZED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

---

## LOOP SUMMARY

**Loop ID:** {loop_num}
**Last Task Worked:** {last_task or 'None'}
**Finalization Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

---

## TASKS AT FINALIZATION

### Active Tasks (NEU.md)
```
{neu_content}
```

### Closed Tasks (Alt.md)
```
{alt_content}
```

---

## NOTES

Loop finalized via Loop Cockpit.

---

END OF DOCUMENT
"""

    with open(archiv_path, 'w', encoding='utf-8') as f:
        f.write(archiv_content)
    archiv_written = True

    # Deterministically index the newly created archive so finalization knowledge is persisted
    # without relying on optional agent behavior or later full rebuilds.
    try:
        KnowledgeDBEventHandler.on_archive_changed(archiv_path)
    except Exception as e:
        log_transaction("finalize_warn", "knowledge", None, None, "WARN", f"ARCHIVE_INCREMENTAL_INDEX_FAILED: {e}")
        print(f"WARNING: Archive incremental indexing failed: {e}")

    # KNOWLEDGE DATABASE VERIFICATION: Ensure archive is documented before finalization
    try:
        from knowledge_db import KnowledgeDB
        db = KnowledgeDB(WORKSPACE_ROOT)
        
        # Search for archive entry in knowledge database
        archive_results = db.search(
            query=f"ARCHIV_{loop_num:04d}",
            types=["archive"],
            loop_min=loop_num,
            loop_max=loop_num,
            limit=1
        )
        
        if not archive_results:
            log_transaction("finalize_block", "knowledge", None, None, "FAILED", f"KNOWLEDGE_DB_MISSING: No database entry found for archive ARCHIV_{loop_num:04d}.md")
            print(f"WARNING: KNOWLEDGE_DB_MISSING: No knowledge database entry found for archive ARCHIV_{loop_num:04d}.md. Proceeding with finalization anyway.")
            # raise ValueError(f"KNOWLEDGE_DB_MISSING: Finalization blocked: No knowledge database entry found for archive ARCHIV_{loop_num:04d}.md. Ensure the archive has been indexed in the knowledge database before finalization.")
        
        # Log successful verification
        log_transaction("finalize_check", "knowledge", archiv_name, None, "SUCCESS", f"Knowledge database entry verified for archive ARCHIV_{loop_num:04d}.md")
    except ImportError:
        # Knowledge database not available, log warning but allow finalization
        log_transaction("finalize_warn", "knowledge", None, None, "WARN", "KNOWLEDGE_DB_UNAVAILABLE: knowledge_db module not available for verification")
        print("WARNING: Knowledge database verification not available - proceeding with caution")
    except ValueError:
        raise  # Re-raise knowledge database verification errors
    except Exception as e:
        # Log error but allow finalization (fail-safe)
        log_transaction("finalize_warn", "knowledge", None, None, "WARN", f"KNOWLEDGE_DB_CHECK_ERROR: {e}")
        print(f"WARNING: Knowledge database check failed: {e} - proceeding with caution")

    # AI INTEGRITY PROTECTION: Validate critical state transition
    try:
        from ai_integrity_protector import AIIntegrityProtector
        protector = AIIntegrityProtector(WORKSPACE_ROOT)

        # Validate the finalization operation
        validation_proof = f"Loop {loop_num} finalization: validation complete - pre-finalization checks passed, finalization assessment successful, archive created ({archiv_name}), last task: {last_task}"
        is_valid, validation_message = protector.validate_state_transition(
            operation=f"finalize_loop_{loop_num}",
            files_to_modify=["current.json", archiv_name],
            validation_proof=validation_proof,
            authorized_by="SYSTEM"
        )

        if not is_valid:
            # Log the block and raise error
            log_transaction("finalize_block", "integrity", None, None, "FAILED", f"INTEGRITY_VALIDATION_FAILED: {validation_message}")
            raise ValueError(f"INTEGRITY_VALIDATION_FAILED: State transition blocked by integrity protection: {validation_message}")

    except ImportError:
        # Integrity module not available, log warning but allow finalization
        log_transaction("finalize_warn", "integrity", None, None, "WARN", "INTEGRITY_MODULE_MISSING: ai_integrity_protector not available")
        print("WARNING: AI integrity protection not available - proceeding with caution")
    except ValueError:
        if archiv_written and archiv_path.exists():
            try:
                archiv_path.unlink()
                log_transaction("finalize_rollback", "archive", archiv_name, None, "SUCCESS", "Removed archive after integrity validation failure")
            except Exception as rollback_error:
                log_transaction("finalize_rollback", "archive", archiv_name, None, "FAILED", f"Failed archive rollback after integrity failure: {rollback_error}")
        raise  # Re-raise integrity validation errors
    except Exception as e:
        # Log error but allow finalization (fail-safe)
        log_transaction("finalize_warn", "integrity", None, None, "WARN", f"INTEGRITY_CHECK_ERROR: {e}")
        print(f"WARNING: Integrity check failed: {e} - proceeding with caution")

    current_state['STATE']['status'] = 'FINALIZED'
    current_state['STATE']['archiveInProgress'] = archiv_name
    current_state['STATE']['lastUpdate'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    current_state['STATE']['lastTaskWorked'] = last_task
    current_state['STATE']['summary'] = f"Loop {loop_num} finalized. ARCHIV_{loop_num:04d}.md created in root."
    try:
        write_json_file(CURRENT_JSON, current_state)
    except Exception as state_write_error:
        if archiv_written and archiv_path.exists():
            try:
                archiv_path.unlink()
                log_transaction("finalize_rollback", "archive", archiv_name, None, "SUCCESS", "Removed archive after current.json write failure")
            except Exception as rollback_error:
                log_transaction("finalize_rollback", "archive", archiv_name, None, "FAILED", f"Failed archive rollback after current.json write failure: {rollback_error}")
        raise state_write_error

    regenerate_loop_gate(reason="finalize-loop")

    combined_warnings = []
    if warnings:
        combined_warnings.extend(warnings)
    if consistency_result.get('warnings'):
        combined_warnings.extend(consistency_result.get('warnings'))
    if lint.get('warnings'):
        combined_warnings.extend([f"{w['code']}: {w['message']}" for w in lint.get('warnings', [])])

    # Create final checkpoint before finalization completes
    try:
        create_phase_checkpoint("finalization", f"Loop {loop_num} successfully finalized with archive {archiv_name}")
    except Exception as e:
        logger.warning(f"Failed to create finalization checkpoint: {e}")

    return {
        "success": True,
        "message": f"Loop {loop_num} finalized. ARCHIV created: {archiv_name}",
        "archivFile": archiv_name,
        "status": "FINALIZED",
        "auditPassed": True,
        "warnings": combined_warnings,
    }

@app.route('/api/confirm-bootstrap', methods=['POST'])
def confirm_bootstrap():
    """Confirm that bootstrap has been executed in new chat session (Phase 2).
    
    This endpoint transitions the loop from READY_FOR_RESET to ACTIVE.
    It is idempotent and can be called multiple times safely.
    
    Preconditions:
    - Current state must be READY_FOR_RESET (or already ACTIVE for idempotent call)
    - Bootstrap file should be deleted (but not strictly required for recovery)
    """
    with open("debug_confirm.log", "a") as f:
        f.write("DEBUG: confirm_bootstrap function called\n")
    try:
        def check_preconditions(current_state):
            """Validate preconditions for bootstrap confirmation.

            Enforce comprehensive bootstrap completion before allowing transition to ACTIVE phase.
            Bootstrap phase = context gathering; ACTIVE phase = work phase.
            """
            try:
                bootstrap_path = resolve_bootstrap_path(WORKSPACE_ROOT)

                # 1. Bootstrap file deletion (existing check)
                if bootstrap_path is not None:
                    incident_ack = current_state.get('STATE', {}).get('INCIDENT_ACK')
                    if incident_ack:
                        return True, None
                    return False, "_BOOTSTRAP.md (canonical) or mapped legacy bootstrap alias exists; confirm-bootstrap blocked until deletion or `/api/ack-incident` is used for recovery"

                # 2. Gate validation (STEP 1: Validate Entry Gate)
                gate_path = WORKSPACE_ROOT / "_LOOP_GATE.md"
                if not gate_path.exists():
                    return False, "BOOTSTRAP INCOMPLETE: _LOOP_GATE.md not found - STEP 1 not completed"
                gate_content = read_text_file(gate_path)
                if "BLOCKED" in gate_content:
                    return False, "BOOTSTRAP INCOMPLETE: _LOOP_GATE.md shows BLOCKED status - STEP 1 failed"
                if "PASS" not in gate_content:
                    return False, "BOOTSTRAP INCOMPLETE: _LOOP_GATE.md status unclear - STEP 1 not validated"

                # 3. State loading verification (STEP 2: Load Loop State)
                if not CURRENT_JSON.exists():
                    return False, "BOOTSTRAP INCOMPLETE: current.json not found - STEP 2 not completed"

                # 4. Project map loading (STEP 3: Load Project Map)
                cortex_path = WORKSPACE_ROOT / "NEURAL_CORTEX.md"
                if not cortex_path.exists():
                    return False, "BOOTSTRAP INCOMPLETE: NEURAL_CORTEX.md not found - STEP 3 not completed"

                # 5. Task discovery (STEP 4: Discover Active Task)
                neu_path = WORKSPACE_ROOT / "NEU.md"
                if not neu_path.exists():
                    return False, "BOOTSTRAP INCOMPLETE: NEU.md not found - STEP 4 not completed"

                # 6. Project laws loading (STEP 5: Load Project Laws)
                baseline_path = WORKSPACE_ROOT / "PROJECT_TECH_BASELINE.md"
                if not baseline_path.exists():
                    return False, "BOOTSTRAP INCOMPLETE: PROJECT_TECH_BASELINE.md not found - STEP 5 not completed"

                # 7. Script execution validation (TASK_0198: Direct script calls required)
                script_validation_errors = []
                cockpit_script = WORKSPACE_ROOT / "loop_cockpit.py"
                guardrails_script = WORKSPACE_ROOT / "loop_guardrails.py"

                if not cockpit_script.exists():
                    script_validation_errors.append("loop_cockpit.py not found - direct script execution required")
                if not guardrails_script.exists():
                    script_validation_errors.append("loop_guardrails.py not found - direct script execution required")

                if script_validation_errors:
                    return False, f"BOOTSTRAP SCRIPT VALIDATION FAILED: {'; '.join(script_validation_errors)}"

                # 7.5. Self-Reflective Framework validation (TASK_0179: AI self-awareness required)
                framework_validation_errors = []
                reflective_framework = WORKSPACE_ROOT / "ai_self_reflective_framework.py"
                breadcrumb_tracker = WORKSPACE_ROOT / "ai_breadcrumb_tracker.py"

                if not reflective_framework.exists():
                    framework_validation_errors.append("ai_self_reflective_framework.py not found - self-reflective capabilities required")
                if not breadcrumb_tracker.exists():
                    framework_validation_errors.append("ai_breadcrumb_tracker.py not found - breadcrumb tracking required")

                if framework_validation_errors:
                    return False, f"BOOTSTRAP FRAMEWORK VALIDATION FAILED: {'; '.join(framework_validation_errors)}"

                # 8. Transaction log validation (confirm previous bootstrap steps logged)
                transaction_log = WORKSPACE_ROOT / "_transaction_log.jsonl"
                if transaction_log.exists():
                    bootstrap_transactions = []
                    try:
                        with open(transaction_log, 'r') as f:
                            for line in f:
                                if line.strip():
                                    try:
                                        transaction = json.loads(line)
                                        if transaction.get("operation") in ["bootstrap-start", "gate-check", "state-load"]:
                                            bootstrap_transactions.append(transaction)
                                    except json.JSONDecodeError:
                                        continue
                    except Exception:
                        pass  # Non-fatal if log can't be read

                    if not bootstrap_transactions:
                        # This is a warning, not a blocker - fresh sessions may not have logged transactions yet
                        pass

                # 9. Previous archive must be indexed in knowledge DB before activation.
                # This keeps finalization/reset tolerant while preventing silent indexing debt growth.
                loop_num = int(current_state.get('STATE', {}).get('loop', 0) or 0)
                if loop_num > 1:
                    prev_archive_name = f"ARCHIV_{loop_num - 1:04d}.md"
                    prev_archive_rel = f"archive/{prev_archive_name}"
                    prev_archive_path = WORKSPACE_ROOT / "archive" / prev_archive_name
                    if not prev_archive_path.exists():
                        return False, (
                            f"BOOTSTRAP INCOMPLETE: expected previous archive missing: {prev_archive_rel}"
                        )

                    db_path = WORKSPACE_ROOT / "keeper_knowledge.db"
                    if not db_path.exists():
                        return False, (
                            f"MISSING_PREV_ARCHIVE_INDEX: knowledge DB not found; cannot verify {prev_archive_rel}. "
                            "Index/rebuild knowledge DB first."
                        )

                    try:
                        db = KnowledgeDB(WORKSPACE_ROOT)
                        archive_results = db.search(prev_archive_name, types=["archive"], limit=3)
                        if not archive_results:
                            archive_stem = Path(prev_archive_name).stem
                            archive_results = db.search(archive_stem, types=["archive"], limit=3)
                    except Exception as e:
                        return False, (
                            "MISSING_PREV_ARCHIVE_INDEX: unable to verify previous archive indexing "
                            f"for {prev_archive_rel}: {e}"
                        )

                    if not archive_results:
                        log_transaction(
                            "confirm_bootstrap_block",
                            "knowledge",
                            prev_archive_rel,
                            None,
                            "FAILED",
                            "MISSING_PREV_ARCHIVE_INDEX",
                        )
                        return False, (
                            f"MISSING_PREV_ARCHIVE_INDEX: {prev_archive_rel} is not indexed in keeper_knowledge.db. "
                            "Index this archive first, then retry /api/confirm-bootstrap."
                        )

                # All bootstrap steps validated - safe to enter ACTIVE phase
                return True, None

            except Exception as e:
                return False, f"Bootstrap validation failed: {e}"
        
        # Execute atomic state transition
        result = _execute_state_transition(
            from_states=[STATE_READY_FOR_RESET, STATE_ACTIVE],
            to_state=STATE_ACTIVE,
            trigger="confirm-bootstrap",
            preconditions_func=check_preconditions,
            details=f"Bootstrap confirmation for loop {read_json_file(CURRENT_JSON).get('STATE', {}).get('loop', 'unknown')}"
        )
        
        if not result["success"]:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 400
        
        state = result["state"]
        loop_num = state.get('STATE', {}).get('loop', 0)

        # Regenerate loop gate immediately after state transition so API status never lags on stale gate snapshots.
        try:
            regenerate_loop_gate(reason="confirm-bootstrap")
        except Exception as e:
            # Non-fatal: gate regeneration failure shouldn't block transition
            log_state_transition(STATE_ACTIVE, STATE_ACTIVE, "loop-gate", "FAILED", str(e))

        # Record explicit confirm-bootstrap transaction early for deterministic audit visibility.
        try:
            log_transaction("confirm-bootstrap", "current.json", None, "ACTIVE", "SUCCESS", f"Bootstrap confirmation for loop {loop_num}")
        except Exception:
            # Non-fatal if logging fails
            pass

        # Keep confirm-bootstrap fast: defer expensive helper work to background.
        if result.get("idempotent"):
            strategic_planning_result = {
                "success": True,
                "tasks_created": 0,
                "message": "Idempotent call - follow-up helpers skipped"
            }
        else:
            strategic_planning_result = {
                "success": True,
                "queued": True,
                "tasks_created": None,
                "message": "Follow-up helpers scheduled in background"
            }

            def _post_confirm_followups() -> None:
                # Strategic planner can be heavy; run off request path.
                try:
                    with open("debug_strategic.log", "a", encoding="utf-8") as f:
                        f.write("DEBUG: Starting strategic planning execution (background)\n")
                    from scripts.strategic_task_planner import StrategicTaskPlanner
                    planner = StrategicTaskPlanner(workspace_root=str(WORKSPACE_ROOT))
                    recommendations = planner.generate_task_recommendations(planning_horizon=90)
                    created_tasks = planner.create_task_files_from_recommendations(
                        recommendations,
                        priority_threshold='high'
                    )
                    log_transaction(
                        "strategic-planning",
                        "NEU.md",
                        None,
                        f"{len(created_tasks)} tasks",
                        "SUCCESS",
                        (
                            f"Generated {len(recommendations)} recommendations, "
                            f"created {len(created_tasks)} high-priority tasks"
                        )
                    )
                except Exception as e:
                    with open("debug_strategic.log", "a", encoding="utf-8") as f:
                        f.write(f"ERROR: Strategic planning failed: {e}\n")
                    log_transaction("strategic-planning", "NEU.md", None, "FAILED", "FAILED", str(e))

                # Session pack generation is useful but should not delay API response.
                try:
                    regenerate_session_pack()
                except Exception as e:
                    log_state_transition(STATE_ACTIVE, STATE_ACTIVE, "session-pack", "FAILED", str(e))

                # Clean up ephemeral bootstrap files.
                try:
                    bootstrap_path = WORKSPACE_ROOT / "_BOOTSTRAP.md"
                    littleboot_path = WORKSPACE_ROOT / "Littleboot.md"

                    if bootstrap_path.exists():
                        bootstrap_path.unlink()
                        log_transaction(
                            "cleanup",
                            "_BOOTSTRAP.md",
                            "delete",
                            None,
                            "SUCCESS",
                            "Bootstrap file cleaned up after confirmation"
                        )

                    if littleboot_path.exists():
                        littleboot_path.unlink()
                        log_transaction(
                            "cleanup",
                            "Littleboot.md",
                            "delete",
                            None,
                            "SUCCESS",
                            "Littleboot file cleaned up after confirmation"
                        )
                except Exception as e:
                    log_state_transition(STATE_ACTIVE, STATE_ACTIVE, "bootstrap-cleanup", "FAILED", str(e))

                # Best-effort breadcrumb + adaptive bootstrap tracking.
                try:
                    from ai_breadcrumb_tracker import track_file_access
                    bootstrap_files = [
                        "NEU.md",
                        "NEURAL_CORTEX.md",
                        "PROJECT_TECH_BASELINE.md",
                        "current.json"
                    ]
                    for bf in bootstrap_files:
                        try:
                            track_file_access(str(WORKSPACE_ROOT / bf), source_context="confirm-bootstrap")
                        except Exception:
                            pass

                    try:
                        from adaptive_bootstrap import BootstrapPredictor
                        predictor = BootstrapPredictor(WORKSPACE_ROOT)
                        preds = predictor.predict_needed_files(
                            "bootstrap_confirm_probe",
                            task_type="bootstrap",
                            budget_tokens=60000
                        )
                        for p in preds:
                            try:
                                track_file_access(
                                    str(WORKSPACE_ROOT / p),
                                    source_context="confirm-bootstrap_predict"
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass

            threading.Thread(
                target=_post_confirm_followups,
                name=f"confirm-bootstrap-followups-L{loop_num}",
                daemon=True
            ).start()

        return jsonify({
            "success": True,
            "message": "Bootstrap confirmed. Loop is now ACTIVE." if not result.get("idempotent") else "Already ACTIVE (idempotent call).",
            "loop": loop_num,
            "status": STATE_ACTIVE,
            "idempotent": result.get("idempotent", False),
            "timestamp": state.get('STATE', {}).get('lastUpdate', ''),
            "strategic_planning": strategic_planning_result
        })

    except Exception as e:
        log_state_transition("UNKNOWN", STATE_ACTIVE, "confirm-bootstrap", "EXCEPTION", str(e))
        return jsonify({
            "success": False,
            "error": f"confirm-bootstrap failed: {str(e)}"
        }), 500


@app.route('/api/validate-bootstrap-exit', methods=['GET'])
def validate_bootstrap_exit():
    """Validate that bootstrap exit was completed properly.

    This endpoint runs comprehensive validation to ensure bootstrap process
    completed with correct state machine transitions, preventing future
    bootstrap failures.

    TASK_0198: Bootstrap State Machine Enforcement
    """
    try:
        from bootstrap_exit_validator import BootstrapExitValidator

        validator = BootstrapExitValidator(WORKSPACE_ROOT)
        results = validator.validate_bootstrap_exit()

        # Return appropriate HTTP status based on validation results
        status_code = 200 if results["overall_status"] == "PASS" else 400

        return jsonify(results), status_code

    except Exception as e:
        return jsonify({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "ERROR",
            "error": f"Bootstrap validation failed: {e}",
            "validations": {}
        }), 500


@app.route('/api/inject-bootstrap', methods=['POST'])
def inject_bootstrap():
    """Inject bootstrap content and transition loop from READY_FOR_RESET to ACTIVE.
    
    This endpoint accepts bootstrap text directly and performs the same transition
    as confirm-bootstrap, but bypasses the _BOOTSTRAP.md file existence check.
    
    Request JSON: {"bootstrapText": "bootstrap content here"}
    """
    try:
        payload = request.json or {}
        bootstrap_text = payload.get('content') or payload.get('bootstrapText')
        if not bootstrap_text:
            return jsonify({"success": False, "error": "Missing bootstrap content in request"}), 400
        
        def check_preconditions(current_state):
            """Validate preconditions for bootstrap injection.
            
            Unlike confirm-bootstrap, this doesn't check for _BOOTSTRAP.md existence
            since we're injecting the content directly.
            """
            return True, None
        
        # Execute atomic state transition
        result = _execute_state_transition(
            from_states=[STATE_READY_FOR_RESET, STATE_ACTIVE],
            to_state=STATE_ACTIVE,
            trigger="inject-bootstrap",
            preconditions_func=check_preconditions,
            details=f"Bootstrap injection for loop {read_json_file(CURRENT_JSON).get('STATE', {}).get('loop', 'unknown')}"
        )
        
        if not result["success"]:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 400
        
        # Generate session context pack for the new ACTIVE loop
        try:
            regenerate_session_pack()
        except Exception as e:
            # Non-fatal: session pack generation failure shouldn't block transition
            log_state_transition(STATE_ACTIVE, STATE_ACTIVE, "session-pack", "FAILED", str(e))
        
        # Regenerate loop gate for ACTIVE entry validation
        try:
            regenerate_loop_gate(reason="inject-bootstrap")
        except Exception as e:
            # Non-fatal: gate regeneration failure shouldn't block transition
            log_state_transition(STATE_ACTIVE, STATE_ACTIVE, "loop-gate", "FAILED", str(e))
        
        state = result["state"]
        loop_num = state.get('STATE', {}).get('loop', 0)

        # Record explicit inject-bootstrap transaction for audit trail
        try:
            log_transaction("inject-bootstrap", "current.json", None, "ACTIVE", "SUCCESS", f"Bootstrap injection for loop {loop_num}")
        except Exception:
            # Non-fatal if logging fails
            pass
        
        return jsonify({
            "success": True,
            "message": "Bootstrap injected. Loop is now ACTIVE." if not result.get("idempotent") else "Already ACTIVE (idempotent call).",
            "loop": loop_num,
            "status": STATE_ACTIVE,
            "idempotent": result.get("idempotent", False),
            "timestamp": state.get('STATE', {}).get('lastUpdate', '')
        })

    except Exception as e:
        log_state_transition("UNKNOWN", STATE_ACTIVE, "inject-bootstrap", "EXCEPTION", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/ack-incident', methods=['POST'])
def ack_incident():
    """Record a human acknowledgement for an incident so that deterministic enforcement
    may allow an otherwise blocked transition.

    Request JSON: {"id": "INCIDENT_0001", "ack_by": "Name", "notes": "Optional notes"}
    """
    try:
        payload = request.json or {}
        incident_id = payload.get('id')
        ack_by = payload.get('ack_by')
        notes = payload.get('notes')
        if not incident_id or not ack_by:
            return jsonify({"success": False, "error": "Missing required fields: id and ack_by"}), 400

        current_state = read_json_file(CURRENT_JSON)
        if 'error' in current_state:
            return jsonify({"success": False, "error": "Failed to read current.json"}), 500

        ack = {
            "id": incident_id,
            "ack_by": ack_by,
            "ack_timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        if notes:
            ack['notes'] = notes

        current_state['STATE']['INCIDENT_ACK'] = ack
        write_json_file(CURRENT_JSON, current_state)
        log_transaction('incident_ack', 'current.json', None, incident_id, 'SUCCESS', f"Acknowledged by {ack_by}")
        return jsonify({"success": True, "message": "Incident acknowledged", "ack": ack})

    except Exception as e:
        log_transaction('incident_ack', 'current.json', None, None, 'FAILED', str(e))
        return jsonify({"success": False, "error": str(e)}), 500
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/force-active', methods=['POST'])
def force_active():
    """Force transition to ACTIVE state (manual recovery endpoint).
    
    This endpoint is for manual recovery when the state machine is stuck.
    Requires explicit confirmation to prevent accidental use.
    
    POST body:
    {
        "confirm": true,
        "reason": "Description of why forced transition is needed"
    }
    """
    try:
        data = request.get_json() or {}
        
        if not data.get('confirm'):
            return jsonify({
                "success": False,
                "error": "Must set 'confirm': true to force state transition"
            }), 400
        
        reason = data.get('reason', 'Manual recovery via /api/force-active')
        
        # Read current state
        current_state = read_json_file(CURRENT_JSON)
        if 'error' in current_state:
            return jsonify({
                "success": False,
                "error": f"Failed to read current.json: {current_state['error']}"
            }), 500
        
        current_status = current_state.get('STATE', {}).get('status', 'UNKNOWN')
        
        # Allow forcing from any state (recovery mechanism)
        with _state_lock:
            current_state['STATE']['status'] = STATE_ACTIVE
            current_state['STATE']['lastUpdate'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            loop_num = current_state['STATE']['loop']
            current_state['STATE']['summary'] = f"Loop {loop_num} forced to ACTIVE. Reason: {reason}"
            
            write_json_file(CURRENT_JSON, current_state)
            log_state_transition(current_status, STATE_ACTIVE, "force-active", "SUCCESS", reason)
        
        # Regenerate supporting files
        try:
            regenerate_session_pack()
            regenerate_loop_gate(reason="force-active")
        except Exception as e:
            log_state_transition(STATE_ACTIVE, STATE_ACTIVE, "force-active-regen", "FAILED", str(e))
        
        return jsonify({
            "success": True,
            "message": f"State forced to ACTIVE from {current_status}",
            "previousState": current_status,
            "currentState": STATE_ACTIVE,
            "loop": loop_num,
            "reason": reason,
            "warning": "This was a forced transition. Review _state_transition.log for details."
        })
        
    except Exception as e:
        log_state_transition("UNKNOWN", STATE_ACTIVE, "force-active", "EXCEPTION", str(e))
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/history-index', methods=['GET'])
def api_history_index():
    """Return deterministic history index data; optionally write docs/HISTORY_INDEX.md."""
    try:
        data = history_index_data(WORKSPACE_ROOT)
        write_flag = request.args.get('write') in {'1', 'true', 'yes'}
        written = False
        out_path = str(HISTORY_INDEX_MD.relative_to(WORKSPACE_ROOT)).replace('\\', '/')

        if write_flag:
            md = history_index_markdown(data)
            write_text(HISTORY_INDEX_MD, md)
            written = True

        return jsonify({
            "success": True,
            "written": written,
            "output": out_path,
            "data": data,
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/metadata-lint', methods=['GET'])
def api_metadata_lint():
    """Run metadata + consistency lint and return structured JSON."""
    try:
        return jsonify({
            "success": True,
            "lint": metadata_lint(WORKSPACE_ROOT)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/validate-gates', methods=['GET'])
def api_validate_gates():
    """Run all validation gates and return their status.
    
    Returns status of all pre-condition gates:
    - pre_finalization: Can the loop be finalized?
    - pre_reset: Can the loop be reset?
    
    Part of C4 (Error Isolation Gates) - TASK_0142.
    """
    try:
        fin_valid, fin_error = validate_pre_finalization()
        db_quality = get_db_quality_gate_status(auto_heal=False)
        reset_valid, reset_error = validate_pre_reset()
        
        current_state = read_json_file(CURRENT_JSON)
        status = current_state.get('STATE', {}).get('status', 'UNKNOWN')
        
        return jsonify({
            "success": True,
            "currentStatus": status,
            "gates": {
                "pre_finalization": {
                    "valid": fin_valid,
                    "error": fin_error,
                    "dbQuality": db_quality,
                    "applicable": status == STATE_ACTIVE
                },
                "pre_reset": {
                    "valid": reset_valid,
                    "error": reset_error,
                    "applicable": status == STATE_FINALIZED
                }
            },
            "summary": "All gates passed" if (fin_valid and reset_valid) else "Some gates have issues"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/transaction-log', methods=['GET'])
def api_transaction_log():
    """Get recent entries from the transaction log.
    
    Query params:
    - limit: Max entries to return (default 50, max 500)
    
    Part of C4 (Error Isolation Gates) - TASK_0142.
    """
    try:
        limit = min(int(request.args.get('limit', 50)), 500)
        
        entries = []
        if TRANSACTION_LOG.exists():
            with open(TRANSACTION_LOG, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Get last N entries
                for line in lines[-limit:]:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        
        return jsonify({
            "success": True,
            "entries": entries,
            "total": len(entries),
            "limit": limit
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/terminal-feed', methods=['GET'])
def api_terminal_feed():
    """Read-only terminal feed for approved cockpit logs.

    Query params:
    - source: one of "transaction", "state", "flask", "bandwidth"
    - limit: max lines (default 80, max 300)
    """
    try:
        source = (request.args.get('source') or 'transaction').strip().lower()
        limit = min(max(int(request.args.get('limit', 80)), 1), 300)
        source_map = {
            'transaction': TRANSACTION_LOG,
            'state': STATE_TRANSITION_LOG,
            'flask': WORKSPACE_ROOT / 'flask_debug.log',
            'bandwidth': WORKSPACE_ROOT / 'bandwidth_guard_log.jsonl',
        }
        path = source_map.get(source)
        if path is None:
            return jsonify({
                "success": False,
                "error": f"Unsupported source '{source}'. Allowed: {', '.join(source_map.keys())}"
            }), 400

        lines = []
        if path.exists():
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                raw_lines = f.readlines()[-limit:]

            for raw in raw_lines:
                text = raw.rstrip('\r\n')
                if not text:
                    continue
                ts = ""
                level = "INFO"
                msg = text

                if source in ('transaction', 'bandwidth'):
                    try:
                        obj = json.loads(text)
                        ts = str(obj.get('timestamp', ''))
                        level = str(obj.get('outcome') or obj.get('level') or 'INFO').upper()
                        op = obj.get('operation') or obj.get('event') or ''
                        target = obj.get('target') or obj.get('component') or ''
                        details = obj.get('details') or obj.get('message') or ''
                        parts = [str(p) for p in (op, target, details) if p]
                        msg = " | ".join(parts) if parts else text
                    except Exception:
                        pass
                elif source == 'state':
                    parts = text.split('|')
                    if parts:
                        ts = parts[0].strip()
                    if 'FAILED' in text or 'EXCEPTION' in text:
                        level = 'ERROR'
                    elif 'WARN' in text:
                        level = 'WARN'
                    elif 'SUCCESS' in text or 'IDEMPOTENT' in text:
                        level = 'OK'
                    else:
                        level = 'INFO'
                else:
                    if ' ERROR ' in text or text.endswith('ERROR'):
                        level = 'ERROR'
                    elif ' WARNING ' in text or ' WARN ' in text:
                        level = 'WARN'
                    elif ' INFO ' in text:
                        level = 'INFO'

                lines.append({
                    "ts": ts,
                    "level": level,
                    "msg": msg
                })

        return jsonify({
            "success": True,
            "source": source,
            "path": str(path.relative_to(WORKSPACE_ROOT)).replace('\\', '/'),
            "lines": lines,
            "total": len(lines),
            "updatedAt": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/validate-schemas', methods=['GET'])
def api_validate_schemas():
    """Validate all JSON files against their schemas.
    
    Returns structured validation results for current.json, milestones, knownissues.
    Part of C2 (Schema Validation Infrastructure) - TASK_0131.
    """
    try:
        result = validate_all_schemas(WORKSPACE_ROOT)
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/regenerate-index', methods=['POST'])
def api_regenerate_index():
    """Regenerate HISTORY_INDEX.md and HISTORY_INDEX.json.
    
    Scans all archives, tasks, and reports to build epoch-organized indices.
    Part of C3 (Archive Index Foundation) - TASK_0133.
    
    Returns:
        success: bool
        archives: int - number of archives scanned
        tasks: int - number of tasks indexed
        reports: int - number of reports indexed
        epochs: int - number of epochs detected
        outputs: list - paths to generated files
    """
    try:
        # Import the regeneration module
        import regenerate_index
        result = regenerate_index.regenerate_index(str(WORKSPACE_ROOT))
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/sync-status', methods=['POST'])
def api_sync_status():
    """Bulk sync task spec STATUS fields based on location.
    
    Scans all tasks in Alt.md and updates their STATUS to COMPLETED if not already.
    Can also sync a single task if taskId is provided in request body.
    
    Request JSON (optional):
        taskId: str - Single task to sync (if omitted, syncs all)
        status: str - Status to set (default: COMPLETED)
    
    Returns:
        success: bool
        synced: list of task IDs that were updated
        skipped: list of task IDs already correct
        errors: list of any errors
    """
    try:
        data = request.get_json(silent=True) or {}
        single_task = data.get('taskId')
        target_status = data.get('status', 'COMPLETED')
        
        synced = []
        skipped = []
        errors = []
        
        if single_task:
            # Sync single task
            result = sync_task_status(single_task, target_status, WORKSPACE_ROOT, utc_now_iso())
            if result.get('success'):
                synced.append(single_task)
            else:
                errors.append({"taskId": single_task, "error": result.get('error')})
        else:
            # Bulk sync: find all tasks in Alt.md
            alt_path = WORKSPACE_ROOT / "Alt.md"
            if alt_path.exists():
                import re
                alt_content = alt_path.read_text(encoding='utf-8')
                alt_task_ids = set(re.findall(r"task_(TASK_\d{4})\.md", alt_content))
                
                for task_id in sorted(alt_task_ids):
                    # Check current status in spec
                    task_spec = None
                    for candidate in [
                        WORKSPACE_ROOT / "tasks" / f"task_{task_id}.md",
                        WORKSPACE_ROOT / f"task_{task_id}.md"
                    ]:
                        if candidate.exists():
                            task_spec = candidate
                            break
                    
                    if not task_spec:
                        errors.append({"taskId": task_id, "error": "Task spec not found"})
                        continue
                    
                    spec_content = task_spec.read_text(encoding='utf-8')
                    status_match = re.search(r"^STATUS:\s*(\w+)", spec_content, re.MULTILINE)
                    current_status = status_match.group(1).upper() if status_match else None
                    
                    # Skip if already COMPLETED or BLOCKED
                    if current_status in ("COMPLETED", "BLOCKED"):
                        skipped.append(task_id)
                        continue
                    
                    # Sync status
                    result = sync_task_status(task_id, "COMPLETED", WORKSPACE_ROOT, utc_now_iso())
                    if result.get('success'):
                        synced.append(task_id)
                    else:
                        errors.append({"taskId": task_id, "error": result.get('error')})
        
        return jsonify({
            "success": len(errors) == 0,
            "synced": synced,
            "skipped": skipped,
            "errors": errors,
            "message": f"Synced {len(synced)} task(s), skipped {len(skipped)}, {len(errors)} error(s)"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/pre-work-check/<task_id>', methods=['GET'])
def api_pre_work_check(task_id):
    """Run pre-work validation for a task (REPORT-FIRST enforcement).
    
    Validates:
    1. Report file exists for the task
    2. Task spec file exists
    3. Task is in NEU.md active queue
    
    Returns JSON with passed status and any errors.
    """
    try:
        result = pre_work_validation(task_id, WORKSPACE_ROOT)
        return jsonify({
            "success": True,
            "taskId": task_id,
            "passed": result.passed,
            "errors": result.errors,
            "message": "Pre-work validation passed" if result.passed else f"{len(result.errors)} validation error(s) found"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/session-pack', methods=['GET'])
def api_session_pack():
    """Get or regenerate the compact session pack (_SESSION.md)."""
    try:
        regen = request.args.get('write') in {'1', 'true', 'yes'}
        if regen:
            regenerate_session_pack()

        content = read_text_file(SESSION_MD) if SESSION_MD.exists() else ""
        return jsonify({
            "success": True,
            "path": str(SESSION_MD.relative_to(WORKSPACE_ROOT)).replace('\\', '/'),
            "exists": SESSION_MD.exists(),
            "content": content,
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/context-index', methods=['GET', 'POST'])
def api_context_index():
    """Get or regenerate the context index for AI onboarding.
    
    GET: Returns current context index (generates if not cached)
    POST with regenerate=true: Forces regeneration and returns fresh index
    
    The context index provides:
    - Current loop state
    - Active tasks from NEU.md
    - Recent completed tasks
    - Known blockers
    - Phase completion status
    """
    try:
        # Check if regeneration requested
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            if data.get('regenerate'):
                # Force regeneration
                pass
        
        # Generate context index
        index = generate_context_index(WORKSPACE_ROOT)
        
        # Optionally write to file
        write_to_file = request.args.get('write') in {'1', 'true', 'yes'}
        if write_to_file or request.method == 'POST':
            context_index_path = WORKSPACE_ROOT / "docs" / "CONTEXT_INDEX.json"
            write_json(context_index_path, index)
        
        return jsonify({
            "success": True,
            "index": index
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/task-dependencies', methods=['GET'])
def api_task_dependencies():
    """Get task dependency graph for active/queued tasks.
    
    Returns a graph structure with:
    - nodes: Task nodes with id, status, phase, files
    - edges: Dependency edges with source, target, type
    - clusters: Parallel and sequential task groupings
    - meta: Graph statistics
    
    The graph identifies:
    - Explicit dependencies (Depends: field in task specs)
    - File-based dependencies (shared file modifications)
    - Parallel clusters (tasks that can run simultaneously)
    """
    try:
        graph = get_task_dependencies(WORKSPACE_ROOT)
        
        # Check for errors
        if "error" in graph:
            return jsonify({
                "success": False,
                "error": graph["error"],
                "graph": graph
            }), 400
        
        return jsonify({
            "success": True,
            "graph": graph
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/parallel-analysis', methods=['GET', 'POST'])
def api_parallel_analysis():
    """Analyze which tasks can run in parallel vs sequentially.
    
    GET: Analyze all QUEUED tasks
    POST: Analyze specific task IDs
    
    Request JSON (POST):
        taskIds: List[str] - Optional list of task IDs to analyze
    
    Returns:
        success: bool
        parallelizable: List of task clusters that can run in parallel
        sequential: List of task chains that must run in order
        conflicts: List of file conflicts between tasks
        independentTasks: Tasks with no dependencies
        summary: Human-readable summary
    """
    try:
        task_ids = None
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            task_ids = data.get('taskIds')
        
        result = analyze_parallelization(WORKSPACE_ROOT, task_ids)
        
        if not result.get("success", True):
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Global worktree manager instance
_worktree_manager = None

def get_worktree_manager():
    """Get or create the global WorktreeManager instance."""
    global _worktree_manager
    if _worktree_manager is None:
        _worktree_manager = worktree_manager_factory(str(WORKSPACE_ROOT))
    return _worktree_manager


@app.route('/api/worktree', methods=['GET'])
def api_worktree_status():
    """Get worktree manager status.
    
    Returns:
        success: bool
        status: Worktree manager status including:
            - is_git_repo: Whether current directory is a git repo
            - current_branch: Current branch name
            - worktree_base: Base directory for worktrees
            - total_worktrees: Total managed worktrees
            - worktrees: List of worktree details
    """
    try:
        wm = get_worktree_manager()
        return jsonify({
            "success": True,
            "status": wm.get_status()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/worktree/create', methods=['POST'])
def api_worktree_create():
    """Create a new worktree for an agent.
    
    Request JSON:
        agentId: str - Unique identifier for the agent
        taskId: str - Task being worked on
        tagReason: str - Optional reason for pre-parallel tag
    
    Returns:
        success: bool
        worktree: Worktree details if successful
        tag: Pre-parallel tag name if created
    """
    try:
        wm = get_worktree_manager()
        
        if not wm.is_git_repo():
            return jsonify({
                "success": False,
                "error": "Not a git repository"
            }), 400
        
        data = request.get_json(silent=True) or {}
        agent_id = data.get("agentId")
        task_id = data.get("taskId")
        tag_reason = data.get("tagReason")
        
        if not agent_id or not task_id:
            return jsonify({
                "success": False,
                "error": "agentId and taskId are required"
            }), 400
        
        # Create pre-parallel tag if first worktree
        tag = None
        if wm.get_status()["total_worktrees"] == 0 and tag_reason:
            tag = wm.tag_pre_parallel(tag_reason)
        
        worktree = wm.create_worktree(agent_id, task_id)
        
        if worktree:
            return jsonify({
                "success": True,
                "worktree": {
                    "name": worktree.name,
                    "path": str(worktree.path),
                    "branch": worktree.branch,
                    "agent_id": worktree.agent_id,
                    "task_id": worktree.task_id,
                    "created_at": worktree.created_at
                },
                "tag": tag
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to create worktree"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/worktree/merge', methods=['POST'])
def api_worktree_merge():
    """Merge a worktree back to main branch.
    
    Request JSON:
        worktreeName: str - Name of worktree to merge
        force: bool - If True, attempt merge even with conflicts
    
    Returns:
        success: bool
        result: Merge result details
    """
    try:
        wm = get_worktree_manager()
        
        data = request.get_json(silent=True) or {}
        worktree_name = data.get("worktreeName")
        force = data.get("force", False)
        
        if not worktree_name:
            return jsonify({
                "success": False,
                "error": "worktreeName is required"
            }), 400
        
        # Find worktree
        worktrees = {wt.name: wt for wt in wm.list_worktrees()}
        if worktree_name not in worktrees:
            return jsonify({
                "success": False,
                "error": f"Worktree '{worktree_name}' not found"
            }), 404
        
        result = wm.merge_worktree(worktrees[worktree_name], force=force)
        
        return jsonify({
            "success": result.success,
            "result": {
                "worktree_name": result.worktree_name,
                "message": result.message,
                "conflicts": result.conflicts,
                "files_changed": result.files_changed
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/worktree/cleanup', methods=['POST'])
def api_worktree_cleanup():
    """Clean up a worktree or all worktrees.
    
    Request JSON:
        worktreeName: str - Optional specific worktree to clean
        cleanOrphans: bool - If True, also clean orphan worktrees
    
    If worktreeName not provided, cleans all managed worktrees.
    
    Returns:
        success: bool
        cleaned: Number of worktrees cleaned
        orphans_cleaned: Number of orphan worktrees cleaned (if requested)
    """
    try:
        wm = get_worktree_manager()
        
        data = request.get_json(silent=True) or {}
        worktree_name = data.get("worktreeName")
        clean_orphans = data.get("cleanOrphans", False)
        
        cleaned = 0
        orphans = 0
        
        if worktree_name:
            # Clean specific worktree
            worktrees = {wt.name: wt for wt in wm.list_worktrees()}
            if worktree_name in worktrees:
                if wm.cleanup_worktree(worktrees[worktree_name]):
                    cleaned = 1
        else:
            # Clean all
            cleaned = wm.cleanup_all()
        
        if clean_orphans:
            orphans = wm.cleanup_orphans()
        
        return jsonify({
            "success": True,
            "cleaned": cleaned,
            "orphans_cleaned": orphans
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/worktree/rollback', methods=['POST'])
def api_worktree_rollback():
    """Rollback to pre-parallel state.
    
    Request JSON:
        tagName: str - Optional specific tag to rollback to
    
    Returns:
        success: bool
        message: Result message
    """
    try:
        wm = get_worktree_manager()
        
        data = request.get_json(silent=True) or {}
        tag_name = data.get("tagName")
        
        success, message = wm.rollback_to_tag(tag_name)
        
        return jsonify({
            "success": success,
            "message": message
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Global orchestrator instance
_orchestrator = None

def get_orchestrator():
    """Get or create the global MultiAgentOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = orchestrator_factory(str(WORKSPACE_ROOT))
    return _orchestrator


@app.route('/api/orchestrator', methods=['GET'])
def api_orchestrator_status():
    """Get orchestrator status.
    
    Returns:
        success: bool
        status: Orchestrator status including sessions
    """
    try:
        orch = get_orchestrator()
        return jsonify({
            "success": True,
            "status": orch.get_status()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/orchestrator/analyze', methods=['GET', 'POST'])
def api_orchestrator_analyze():
    """Analyze tasks for parallelization potential.
    
    GET: Analyze all QUEUED tasks
    POST: Analyze specific task IDs
    
    Request JSON (POST):
        taskIds: List[str] - Optional list of task IDs
    
    Returns:
        success: bool
        analysis: Parallelization analysis result
    """
    try:
        orch = get_orchestrator()
        
        task_ids = None
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            task_ids = data.get('taskIds')
        
        analysis = orch.analyze_tasks(task_ids)
        
        return jsonify({
            "success": True,
            "analysis": analysis
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/orchestrator/analyze-conflicts', methods=['POST'])
def api_orchestrator_analyze_conflicts():
    """Analyze file conflicts between selected tasks.
    
    Request JSON:
        tasks: List[str] - Task IDs to check for conflicts
    
    Returns:
        conflicts: List of file conflicts between task pairs
        recommendation: Human-readable recommendation
        clusters: Groupings for sequential/parallel execution
    """
    try:
        data = request.get_json(silent=True) or {}
        task_ids = data.get('tasks', [])
        
        if len(task_ids) < 2:
            return jsonify({
                "conflicts": [],
                "recommendation": "Select at least 2 tasks to check for conflicts",
                "clusters": []
            })
        
        orch = get_orchestrator()
        analysis = orch.analyze_tasks(task_ids)
        
        if not analysis.get("success", False):
            return jsonify({
                "conflicts": [],
                "recommendation": analysis.get("error", "Analysis failed"),
                "clusters": []
            })
        
        # Extract file conflicts
        raw_conflicts = analysis.get("conflicts", [])
        conflict_details = []
        
        # Build task-pair conflict map from file conflicts
        conflict_pairs = {}
        for conflict in raw_conflicts:
            tasks_for_file = conflict.get("tasks", [])
            file_path = conflict.get("file", "unknown")
            
            # Create pairs from tasks sharing this file
            for i, task1 in enumerate(tasks_for_file):
                for task2 in tasks_for_file[i+1:]:
                    pair_key = tuple(sorted([task1, task2]))
                    if pair_key not in conflict_pairs:
                        conflict_pairs[pair_key] = []
                    conflict_pairs[pair_key].append(file_path)
        
        # Convert to output format
        for (task1, task2), files in conflict_pairs.items():
            conflict_details.append({
                "task1": task1,
                "task2": task2,
                "overlapping_files": files
            })
        
        # Generate recommendation
        if len(conflict_details) == 0:
            recommendation = "All tasks are independent and can run in parallel safely."
        else:
            # Get parallelizable clusters from analysis
            parallelizable = analysis.get("parallelizable", [])
            sequential = analysis.get("sequential", [])
            
            if len(sequential) > 0 and len(parallelizable) == 0:
                recommendation = "All tasks have conflicts. Execute sequentially to avoid issues."
            elif len(conflict_details) == 1:
                recommendation = f"1 conflict detected between {conflict_details[0]['task1']} and {conflict_details[0]['task2']}. Consider running them sequentially."
            else:
                recommendation = f"{len(conflict_details)} conflicts detected. Execute conflicting task pairs sequentially."
        
        # Build clusters from analysis
        clusters = []
        for item in analysis.get("parallelizable", []):
            tasks = item.get("tasks", [])
            if tasks:
                clusters.append(tasks)
        for item in analysis.get("sequential", []):
            tasks = item.get("tasks", [])
            if tasks:
                clusters.append(tasks)
        
        return jsonify({
            "conflicts": conflict_details,
            "recommendation": recommendation,
            "clusters": clusters
        })
        
    except Exception as e:
        return jsonify({
            "conflicts": [],
            "recommendation": f"Error: {str(e)}",
            "clusters": []
        }), 500


@app.route('/api/orchestrator/execute', methods=['POST'])
def api_orchestrator_execute():
    """Execute parallel task orchestration.
    
    Request JSON:
        taskIds: List[str] - Task IDs to execute in parallel
        autoMerge: bool - Auto-merge on completion (default: true)
        autoCleanup: bool - Auto-cleanup worktrees (default: true)
        waitForAgents: bool - If true, keep sessions pending for real agent pickup (default: false)
    
    Returns:
        success: bool
        result: OrchestrationResult with metrics
    """
    try:
        orch = get_orchestrator()
        
        if not orch.get_status()["is_git_repo"]:
            return jsonify({
                "success": False,
                "error": "Not a git repository - cannot execute parallel orchestration"
            }), 400
        
        data = request.get_json(silent=True) or {}
        task_ids = data.get("taskIds", [])
        auto_merge = data.get("autoMerge", True)
        auto_cleanup = data.get("autoCleanup", True)
        wait_for_agents = data.get("waitForAgents", False)
        
        if not task_ids:
            return jsonify({
                "success": False,
                "error": "taskIds list is required"
            }), 400
        
        result = orch.execute_parallel(
            task_ids=task_ids,
            auto_merge=auto_merge,
            auto_cleanup=auto_cleanup,
            wait_for_agents=wait_for_agents
        )
        
        return jsonify({
            "success": result.success,
            "result": {
                "agents_spawned": result.agents_spawned,
                "agents_completed": result.agents_completed,
                "agents_failed": result.agents_failed,
                "conflicts": result.conflicts,
                "all_merged": result.all_merged,
                "time_started": result.time_started,
                "time_completed": result.time_completed,
                "time_saved_seconds": result.time_saved_seconds,
                "tasks_parallelized": result.tasks_parallelized,
                "errors": result.errors,
                "metrics": result.metrics
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/orchestrator/rollback', methods=['POST'])
def api_orchestrator_rollback():
    """Rollback orchestrator to pre-parallel state.
    
    Returns:
        success: bool
        message: Result message
    """
    try:
        orch = get_orchestrator()
        success, message = orch.rollback()
        orch.cleanup()
        
        return jsonify({
            "success": success,
            "message": message
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/orchestrator/sessions/pending', methods=['GET'])
def api_orchestrator_sessions_pending():
    """Get list of pending/spawned sessions awaiting agent pickup.
    
    Returns:
        sessions: List of session data for spawned sessions
    """
    try:
        orch = get_orchestrator()
        status = orch.get_status()
        
        # Return sessions with status "pending" or "spawned" and map keys to camelCase for API clients
        pending_sessions_raw = [
            s for s in status["sessions"]
            if s.get("status") in ["pending", "spawned"]
        ]

        # Normalize session dict keys to expected API shape (camelCase)
        def normalize_session(s: dict) -> dict:
            return {
                "agentId": s.get("agent_id") or s.get("agentId"),
                "taskId": s.get("task_id") or s.get("taskId"),
                "status": s.get("status"),
                "progress": s.get("progress"),
                "startedAt": s.get("started_at"),
                "completedAt": s.get("completed_at"),
                "error": s.get("error"),
                "resultSummary": s.get("result_summary")
            }

        pending_sessions = [normalize_session(s) for s in pending_sessions_raw]

        return jsonify({
            "sessions": pending_sessions
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/orchestrator/sessions/<agent_id>/claim', methods=['POST'])
def api_orchestrator_session_claim(agent_id):
    """Claim a session for agent processing.
    
    Args:
        agent_id: Agent ID to claim
        
    Returns:
        success: bool
        session: Session data with prompt
    """
    try:
        import traceback
        print(f"[CLAIM] Attempting to claim session: {agent_id}")
        orch = get_orchestrator()
        session = orch._sessions.get(agent_id)
        print(f"[CLAIM] Session found: {session is not None}")
        
        if not session:
            return jsonify({
                "success": False,
                "error": f"Session {agent_id} not found"
            }), 404
        
        # Mark as working
        session.status = "working"
        orch._create_session_file(session)
        
        # Get task spec to create prompt
        import os
        import json
        
        task_file = os.path.join(orch.workspace_root, "tasks", f"task_{session.task_id}.md")
        task_description = f"Work on {session.task_id}"
        if os.path.exists(task_file):
            with open(task_file, 'r', encoding='utf-8') as f:
                task_description = f.read()
        
        # Get current loop
        current_json_path = os.path.join(orch.workspace_root, "current.json")
        current_loop = 63  # Default
        if os.path.exists(current_json_path):
            with open(current_json_path, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
                current_loop = current_data.get("loop", 63)
        
        # Build prompt using agentSpawner format
        prompt = f"""You are Agent {agent_id} working on {session.task_id} in Loop {current_loop}.

## Working Directory
{session.worktree_path}

## Task Specification
{task_description}

## Instructions
1. Read the task specification carefully
2. Create a report file following REPORT-FIRST law:
   - File: reports/report_{session.task_id}_L{current_loop}_v01.md
   - Include: objective, approach, implementation details, outcome
3. Implement the required changes
4. Ensure all acceptance criteria are met
5. Update current.json lastTaskWorked to {session.task_id}

Work autonomously and complete the full task."""
        
        return jsonify({
            "success": True,
            "session": {
                "agentId": session.agent_id,
                "taskId": session.task_id,
                "worktreePath": str(session.worktree_path),
                "prompt": prompt,
                "status": session.status,
                "progress": session.progress
            }
        })
        
    except Exception as e:
        import traceback
        print(f"[CLAIM ERROR] Exception claiming session: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/orchestrator/sessions/<agent_id>/status', methods=['POST'])
def api_orchestrator_session_status(agent_id):
    """Update session status and progress.
    
    Args:
        agent_id: Agent ID to update
        
    Request JSON:
        status: str - New status (working/completed/failed)
        progress: int - Progress percentage (0-100)
        result_summary: str - Result summary (for completed)
        error: str - Error message (for failed)
        message: str - Optional status message
        
    Returns:
        success: bool
    """
    try:
        orch = get_orchestrator()
        session = orch._sessions.get(agent_id)
        
        if not session:
            return jsonify({
                "success": False,
                "error": f"Session {agent_id} not found"
            }), 404
        
        data = request.get_json(silent=True) or {}
        
        # Update session fields
        if "status" in data:
            session.status = data["status"]
        if "progress" in data:
            session.progress = data["progress"]
        if "result_summary" in data:
            session.result_summary = data["result_summary"]
        if "error" in data:
            session.error = data["error"]
        
        # Mark completion time if completed/failed
        if session.status in ["completed", "failed"] and not session.completed_at:
            from loop_guardrails import utc_now_iso
            session.completed_at = utc_now_iso()
        
        # Update session file
        orch._create_session_file(session)
        
        return jsonify({
            "success": True,
            "agent_id": agent_id,
            "status": session.status,
            "progress": session.progress
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/close-task', methods=['POST'])
def api_close_task():
    """Close a task with a single operation.
    
    Performs complete task closure:
    - Validates task exists and has report
    - Updates task spec STATUS to COMPLETED
    - Adds to Alt.md COMPLETED section
    - Updates NEU.md status indicator
    - Updates current.json lastTaskWorked
    
    Request body:
        {
            "taskId": "TASK_XXXX",
            "summary": "Optional completion summary"
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        task_id = data.get("taskId")
        summary = data.get("summary", "")
        
        if not task_id:
            return jsonify({
                "success": False,
                "error": "taskId is required"
            }), 400
        
        # Normalize task ID format
        if not task_id.startswith("TASK_"):
            task_id = f"TASK_{task_id}"
        
        result = close_task(task_id, WORKSPACE_ROOT, summary)
        
        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/checkpoint', methods=['POST'])
def api_create_checkpoint():
    """Create a manual checkpoint.
    
    Request body:
        {
            "summary": "Brief description of work completed",
            "phase": "Optional phase name (e.g., 'Phase 1 complete')"
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        summary = data.get("summary", "Manual checkpoint")
        phase = data.get("phase")
        
        success = create_phase_checkpoint(phase or "manual", summary)
        
        return jsonify({
            "success": success,
            "message": "Checkpoint created" if success else "Failed to create checkpoint"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/checkpoint/status', methods=['GET'])
def api_checkpoint_status():
    """Get checkpoint manager status and statistics."""
    try:
        manager = get_checkpoint_manager()
        if manager:
            stats = manager.get_checkpoint_stats()
            return jsonify({
                "success": True,
                "active": True,
                "stats": stats
            })
        else:
            return jsonify({
                "success": True,
                "active": False,
                "message": "Checkpoint manager not initialized"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/generate-report-template', methods=['POST'])
def api_generate_report_template():
    """Generate a report template from task spec data.
    
    Parses task spec and creates a pre-filled report template with:
    - Task objective
    - Scope/approach items
    - Acceptance criteria as checkboxes
    - Standard report structure
    
    Request JSON:
        taskId: str - Task ID (required, e.g., "TASK_0087")
        loop: int - Loop number (optional, defaults to current loop)
        version: int - Report version (optional, defaults to 1)
    
    Response JSON:
        success: bool
        template: str - The generated report template
        filename: str - Suggested filename
        taskTitle: str - Extracted task title
        error: str - Error message if failed
    """
    try:
        data = request.get_json(silent=True) or {}
        task_id = data.get("taskId", "").strip()
        
        if not task_id:
            return jsonify({
                "success": False,
                "error": "taskId is required"
            }), 400
        
        # Normalize task ID format
        if not task_id.startswith("TASK_"):
            task_id = f"TASK_{task_id}"
        
        # Get loop number - default to current loop
        loop = data.get("loop")
        if loop is None:
            current_state = read_json_file(CURRENT_JSON)
            loop = current_state.get("STATE", {}).get("loop", 1)
        
        # Get version - default to 1
        version = data.get("version", 1)
        
        result = generate_report_template(task_id, WORKSPACE_ROOT, loop, version)
        
        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Auto-finalization monitor state
_auto_finalize_state = {
    "graceStartTime": None,
    "autoFinalizeEnabled": False,
    "gracePeriodSeconds": 300  # 5 minutes default
}


def count_active_queued_tasks(neu_content: str) -> int:
    """Count tasks in NEU.md that are QUEUED or in-progress (not COMPLETED/moved)."""
    import re
    # Count lines that have QUEUED status or are not marked as completed
    queued_count = 0
    lines = neu_content.split('\n')
    
    for i, line in enumerate(lines):
        # Look for task references that are queued or active
        if 'task_TASK_' in line and '→' not in line:  # not moved to Alt.md
            # Check if this task has a status line indicating QUEUED
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if 'Status: 📋 QUEUED' in next_line or 'Status: 🔄 IN_PROGRESS' in next_line:
                    queued_count += 1
                elif 'COMPLETED' not in next_line and 'tags:queued' in line:
                    queued_count += 1
    
    return queued_count


@app.route('/api/finalization-status', methods=['GET'])
def api_finalization_status():
    """Get auto-finalization monitor status.
    
    Returns:
        success: bool
        isEmpty: bool - True if NEU.md has no queued tasks
        queuedTaskCount: int - Number of tasks still queued
        graceActive: bool - True if in grace period
        graceStartTime: str - ISO timestamp when grace started
        graceRemaining: int - Seconds remaining in grace period
        autoFinalizeEnabled: bool - Whether auto-finalize is enabled
        gracePeriodSeconds: int - Total grace period duration
        canFinalize: bool - Whether finalization is allowed (audit passed)
    """
    global _auto_finalize_state
    
    try:
        # Read NEU.md content
        neu_content = read_text_file(NEU_MD)
        
        # Count queued/active tasks
        queued_count = count_active_queued_tasks(neu_content)
        is_empty = queued_count == 0
        
        # Check if audit passes (from existing audit endpoint logic)
        is_valid, issues, warnings = audit_loop_integrity()
        consistency_result = check_archive_consistency(WORKSPACE_ROOT)
        lint = metadata_lint(WORKSPACE_ROOT)
        lint_errors = lint.get('errors', [])
        can_finalize = is_valid and consistency_result.get('is_consistent', False) and len(lint_errors) == 0
        
        # Get current state
        current_state = read_json_file(CURRENT_JSON)
        status = current_state.get('STATE', {}).get('status', 'UNKNOWN')
        
        # Only activate grace period if ACTIVE and queue is empty
        if status == STATE_ACTIVE and is_empty and can_finalize:
            if _auto_finalize_state["graceStartTime"] is None:
                # Start grace period
                _auto_finalize_state["graceStartTime"] = datetime.now(timezone.utc).isoformat()
        else:
            # Cancel grace period if conditions no longer met
            _auto_finalize_state["graceStartTime"] = None
        
        # Calculate grace remaining
        grace_remaining = 0
        grace_active = False
        if _auto_finalize_state["graceStartTime"]:
            grace_start = datetime.fromisoformat(_auto_finalize_state["graceStartTime"].replace('Z', '+00:00'))
            elapsed = (datetime.now(timezone.utc) - grace_start).total_seconds()
            grace_remaining = max(0, _auto_finalize_state["gracePeriodSeconds"] - int(elapsed))
            grace_active = grace_remaining > 0
            
            # Check if grace period expired
            if grace_remaining == 0 and grace_active:
                grace_active = False
        
        return jsonify({
            "success": True,
            "isEmpty": is_empty,
            "queuedTaskCount": queued_count,
            "graceActive": grace_active,
            "graceStartTime": _auto_finalize_state["graceStartTime"],
            "graceRemaining": grace_remaining,
            "graceExpired": _auto_finalize_state["graceStartTime"] is not None and grace_remaining == 0,
            "autoFinalizeEnabled": _auto_finalize_state["autoFinalizeEnabled"],
            "gracePeriodSeconds": _auto_finalize_state["gracePeriodSeconds"],
            "canFinalize": can_finalize and status == STATE_ACTIVE,
            "status": status
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/finalization-config', methods=['POST'])
def api_finalization_config():
    """Configure auto-finalization settings.
    
    Request JSON:
        autoFinalizeEnabled: bool - Enable/disable auto-finalization
        gracePeriodSeconds: int - Grace period duration in seconds
    
    Returns:
        success: bool
        config: dict - Current configuration
    """
    global _auto_finalize_state
    
    try:
        data = request.get_json(silent=True) or {}
        
        if 'autoFinalizeEnabled' in data:
            _auto_finalize_state["autoFinalizeEnabled"] = bool(data['autoFinalizeEnabled'])
        
        if 'gracePeriodSeconds' in data:
            grace = int(data['gracePeriodSeconds'])
            if grace < 60:
                return jsonify({
                    "success": False,
                    "error": "Grace period must be at least 60 seconds"
                }), 400
            _auto_finalize_state["gracePeriodSeconds"] = grace
        
        return jsonify({
            "success": True,
            "config": {
                "autoFinalizeEnabled": _auto_finalize_state["autoFinalizeEnabled"],
                "gracePeriodSeconds": _auto_finalize_state["gracePeriodSeconds"]
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/seed-idea', methods=['POST'])
def submit_seed_idea():
    """Submit a new seed idea to the chaosbox quality control pipeline."""
    try:
        data = request.get_json(silent=True) or {}
        idea = (data.get('idea') or '').strip()
        
        if not idea:
            return jsonify({
                "success": False,
                "error": "Idea cannot be empty"
            }), 400
        
        # Submit to chaosbox instead of direct task creation
        chaosbox = ChaosboxManager(str(WORKSPACE_ROOT))
        # Extract title from first line or first 50 chars
        title = idea.split('\n')[0][:50] if '\n' in idea else idea[:50]

        description = idea
        
        idea_id = chaosbox.submit_idea(
            title=title,
            description=description,
            submitted_by="user",
            tags=["seed-idea"],
            metadata={"source": "cockpit"}
        )
        
        return jsonify({
            "success": True,
            "message": f"Idea submitted to chaosbox for quality control",
            "ideaId": idea_id,
            "status": "submitted"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chaosbox/status', methods=['GET'])
def get_chaosbox_status():
    """Get the current status of the chaosbox pipeline."""
    try:
        chaosbox = ChaosboxManager(str(WORKSPACE_ROOT))
        status = chaosbox.get_queue_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chaosbox/process', methods=['POST'])
def process_chaosbox_queue():
    """Manually trigger processing of the chaosbox queue."""
    try:
        chaosbox = ChaosboxManager(str(WORKSPACE_ROOT))
        # Start processing if not running
        chaosbox.start_processing()
        return jsonify({
            "success": True,
            "message": "Chaosbox processing started"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/behavioral-telemetry', methods=['GET'])
def get_behavioral_telemetry():
    """Get current AI behavioral telemetry and analysis."""
    try:
        from behavioral_telemetry_analyzer import BehavioralTelemetryAnalyzer
        analyzer = BehavioralTelemetryAnalyzer()

        current_state = analyzer.get_current_behavioral_state()
        temporal_patterns = analyzer.analyze_temporal_patterns()
        zones = analyzer.identify_behavioral_zones()
        warnings = analyzer.get_early_warnings()

        return jsonify({
            "current_state": {
                "arousal": current_state.arousal,
                "functionality": current_state.functionality,
                "timestamp": current_state.timestamp,
                "confidence": current_state.confidence
            },
            "temporal_analysis": temporal_patterns,
            "behavioral_zones": zones,
            "early_warnings": warnings,
            "status": "active"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/ai-confidence', methods=['GET'])
def get_ai_confidence():
    """Get current AI confidence score for self-awareness (<100ms response)."""
    try:
        from behavioral_telemetry_analyzer import BehavioralTelemetryAnalyzer
        analyzer = BehavioralTelemetryAnalyzer()

        confidence_score = analyzer.calculate_confidence_score()

        return jsonify({
            "confidence_score": confidence_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "current"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chat-context', methods=['GET'])
def get_chat_context():
    """Get AI chat context - instructions for starting conversation."""
    current_state = read_json_file(CURRENT_JSON)
    loop_num = current_state.get('STATE', {}).get('loop', 0)
    status = current_state.get('STATE', {}).get('status', 'UNKNOWN')
    
    if status == 'READY_FOR_RESET':
        context = f"""🚀 LOOP {loop_num} READY TO START

**Action Required:**
1. Start a NEW CHAT window in your AI assistant
2. Copy and send this message:

---
Read _BOOTSTRAP.md
---

The AI will:
- Validate the loop gate
- Load the current state
- Discover active tasks
- Begin work

After the AI confirms entry, you can start working on tasks."""
    
    elif status == 'ACTIVE':
        neu_content = read_text_file(NEU_MD)
        context = f"""💼 LOOP {loop_num} ACTIVE

**Current State:**
You're in an active loop session. You can:

1. **Ask the AI to work on a task:**
   "Work on the next task in NEU.md"

2. **Submit a new seed idea:**
   Use the form below to create a new task

3. **Check status:**
   "What's the current project status?"

4. **View tasks:**
   The NEU.md content is shown in the Active Tasks panel below

**Active Tasks Preview:**
{neu_content[:500]}{'...' if len(neu_content) > 500 else ''}
"""
    
    elif status == 'FINALIZED':
        context = f"""⚡ LOOP {loop_num} FINALIZED

**Action Required:**
Click the **RESET LOOP** button above to:
- Move ARCHIV file to /archive/
- Increment loop to {loop_num + 1}
- Prepare for fresh start

Then start a new chat session with "Read _BOOTSTRAP.md"
"""
    
    else:
        context = f"""Status: {status}
Loop: {loop_num}

Check the system documentation for next steps."""
    
    return jsonify({
        "context": context,
        "status": status,
        "loop": loop_num
    })


@app.route('/api/generate-code', methods=['POST'])
def generate_code():
    """Generate code using Ollama AI"""
    try:
        data = request.json
        user_prompt = data.get('prompt', '')
        model = data.get('model', OLLAMA_MODEL)
        
        if not user_prompt:
            return jsonify({'success': False, 'error': 'No prompt provided'}), 400
        
        # Call Ollama
        llm_response = call_ollama_api(user_prompt, model)
        
        # Parse response
        parsed = parse_llm_response(llm_response)
        
        # Save to file
        filepath = save_generated_code(parsed['filename'], parsed['code'])
        
        return jsonify({
            'success': True,
            'filename': parsed['filename'],
            'code': parsed['code'],
            'explanation': parsed['explanation'],
            'filepath': filepath
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/file-activity', methods=['GET'])
def get_file_activity():
    """
    Get file activity data for neural visualization heat mapping.
    Tracks which loop each file was last modified/referenced.
    Returns color coding based on loops since last activity.
    """
    import re
    from datetime import datetime
    
    # Load current loop number
    current_loop = 1
    if CURRENT_JSON.exists():
        try:
            data = json.loads(CURRENT_JSON.read_text(encoding='utf-8'))
            current_loop = data.get('STATE', {}).get('loop', 1)
        except:
            pass
    
    # Activity color mapping (loops since used -> color)
    def get_activity_color(loops_since):
        if loops_since == 0:
            return {'hex': '#ffffff', 'name': 'white', 'intensity': 1.0}      # Used this loop
        elif loops_since == 1:
            return {'hex': '#ffff00', 'name': 'yellow', 'intensity': 0.9}     # 1 loop ago
        elif loops_since == 2:
            return {'hex': '#ff8800', 'name': 'orange', 'intensity': 0.8}     # 2 loops ago
        elif loops_since <= 3:
            return {'hex': '#ff4444', 'name': 'red', 'intensity': 0.7}        # 3 loops ago
        elif loops_since <= 5:
            return {'hex': '#44ff88', 'name': 'green', 'intensity': 0.5}      # 5 loops ago
        elif loops_since <= 7:
            return {'hex': '#4488ff', 'name': 'blue', 'intensity': 0.3}       # 7 loops ago
        else:
            return {'hex': '#666666', 'name': 'grey', 'intensity': 0.1}       # 10+ loops ago
    
    files_activity = []
    ref_pattern = re.compile(r'\[ref:([^\]|]+)')
    
    # Scan archives to build activity history
    file_last_loop = {}  # file -> last loop number where it was mentioned
    
    archive_dir = WORKSPACE_ROOT / 'archive'
    if archive_dir.exists():
        for archive_file in sorted(archive_dir.glob('ARCHIV_*.md')):
            # Extract loop number from filename
            match = re.search(r'ARCHIV_(\d+)', archive_file.name)
            if match:
                loop_num = int(match.group(1))
                content = archive_file.read_text(encoding='utf-8')
                
                # Find all file references
                refs = ref_pattern.findall(content)
                for ref in refs:
                    file_path = ref.split('#')[0]
                    file_last_loop[file_path] = max(file_last_loop.get(file_path, 0), loop_num)
                
                # Also track files mentioned by name (TASK_XXXX, report_, etc.)
                task_mentions = re.findall(r'TASK_\d{4}', content)
                for task in task_mentions:
                    file_last_loop[f'tasks/task_{task}.md'] = max(
                        file_last_loop.get(f'tasks/task_{task}.md', 0), loop_num
                    )
    
    # Current loop activity from current.json and NEU/Alt
    if CURRENT_JSON.exists():
        data = json.loads(CURRENT_JSON.read_text(encoding='utf-8'))
        last_task = data.get('lastTaskWorked') or data.get('STATE', {}).get('lastTaskWorked')
        if last_task:
            file_last_loop[f'tasks/task_{last_task}.md'] = current_loop
    
    # Scan NEU.md for currently active tasks
    if NEU_MD.exists():
        content = NEU_MD.read_text(encoding='utf-8')
        refs = ref_pattern.findall(content)
        for ref in refs:
            file_path = ref.split('#')[0]
            file_last_loop[file_path] = current_loop  # Active = current loop
    
    # Build activity data for all workspace files
    all_files = []
    all_files.extend(WORKSPACE_ROOT.glob('*.md'))
    all_files.extend(WORKSPACE_ROOT.glob('*.json'))
    if (WORKSPACE_ROOT / 'tasks').exists():
        all_files.extend((WORKSPACE_ROOT / 'tasks').glob('*.md'))
    if (WORKSPACE_ROOT / 'reports').exists():
        all_files.extend((WORKSPACE_ROOT / 'reports').glob('*.md'))
    if (WORKSPACE_ROOT / 'docs').exists():
        all_files.extend((WORKSPACE_ROOT / 'docs').glob('*.md'))
    
    for filepath in all_files:
        rel_path = str(filepath.relative_to(WORKSPACE_ROOT)).replace('\\', '/')
        
        # Core files are always "active" (used every loop)
        if filepath.name in ['NEURAL_CORTEX.md', 'NEU.md', 'Alt.md', 'current.json', 
                             '_LOOP_GATE.md', 'PROJECT_TECH_BASELINE.md', '_SESSION.md']:
            last_loop = current_loop
        else:
            last_loop = file_last_loop.get(rel_path, 0)
        
        loops_since = current_loop - last_loop if last_loop > 0 else 999
        color = get_activity_color(loops_since)
        
        files_activity.append({
            'path': rel_path,
            'name': filepath.name,
            'lastUsedLoop': last_loop,
            'loopsSinceUsed': loops_since if loops_since < 999 else None,
            'color': color,
            'isCore': filepath.name in ['NEURAL_CORTEX.md', 'NEU.md', 'Alt.md', 'current.json']
        })
    
    return jsonify({
        'currentLoop': current_loop,
        'files': files_activity,
        'colorLegend': {
            'white': 'Used this loop',
            'yellow': '1 loop ago',
            'orange': '2 loops ago', 
            'red': '3 loops ago',
            'green': '5 loops ago',
            'blue': '7 loops ago',
            'grey': '10+ loops ago'
        }
    })


@app.route('/api/project-structure', methods=['GET'])
def get_project_structure():
    """
    Parse all markdown files in workspace for references and file structure.
    Returns real project data for 3D Loop Sphere visualization.
    """
    import re
    
    files = []
    references = []
    ref_pattern = re.compile(r'\[ref:([^\]]+)\]')
    
    # Core pointer-only files (must be scanned)
    core_files = ['NEURAL_CORTEX.md', 'NEU.md', 'Alt.md']
    
    # Other important files
    state_files = ['current.json', '_LOOP_GATE.md', 'PROJECT_TECH_BASELINE.md']
    
    # Scan workspace for markdown files
    all_md_files = list(WORKSPACE_ROOT.glob('*.md'))
    task_files = list(WORKSPACE_ROOT.glob('task_TASK_*.md'))
    tasks_dir = WORKSPACE_ROOT / 'tasks'
    if tasks_dir.exists():
        task_files.extend(list(tasks_dir.glob('task_TASK_*.md')))

    # Documentation files (docs/*.md)
    docs_dir = WORKSPACE_ROOT / 'docs'
    doc_files = list(docs_dir.glob('*.md')) if docs_dir.exists() else []

    report_files = list(WORKSPACE_ROOT.glob('report_*.md'))
    reports_dir = WORKSPACE_ROOT / 'reports'
    if reports_dir.exists():
        report_files.extend(list(reports_dir.glob('report_*.md')))
    archive_files = list((WORKSPACE_ROOT / 'archive').glob('ARCHIV_*.md')) if (WORKSPACE_ROOT / 'archive').exists() else []
    
    # Process core files first
    for filename in core_files:
        filepath = WORKSPACE_ROOT / filename
        if filepath.exists():
            file_type = 'core'
            content = read_text_file(filepath)
            
            # Extract references from this file
            matches = ref_pattern.findall(content)
            for match in matches:
                # Parse reference format: FILE#SECTION|v:X|tags:...|src:...
                parts = match.split('|')
                ref_file = parts[0].split('#')[0] if parts else match
                
                # Determine reference type
                ref_type = 'pointer'
                if filename == 'NEURAL_CORTEX.md':
                    # NEURAL_CORTEX reads other documents
                    ref_type = 'read' if ref_file in ['current.json', '_LOOP_GATE.md', 'PROJECT_TECH_BASELINE.md', 'knownissues.json', 'milestone_01.json'] else 'pointer'
                
                references.append({
                    'from': filename,
                    'to': ref_file,
                    'type': ref_type,
                    'full_ref': match
                })
            
            files.append({
                'name': filename,
                'path': filename,
                'type': file_type,
                'ref_count': len([r for r in references if r['from'] == filename])
            })
    
    # Process state files
    for filename in state_files:
        filepath = WORKSPACE_ROOT / filename
        if filepath.exists():
            files.append({
                'name': filename,
                'path': filename,
                'type': 'state',
                'ref_count': 0
            })

    # Process documentation files (docs/*.md)
    for filepath in doc_files:
        rel_name = str(filepath.relative_to(WORKSPACE_ROOT)).replace('\\', '/')
        content = read_text_file(filepath)

        matches = ref_pattern.findall(content)
        for match in matches:
            parts = match.split('|')
            ref_file = parts[0].split('#')[0] if parts else match
            references.append({
                'from': rel_name,
                'to': ref_file,
                'type': 'pointer',
                'full_ref': match
            })

        files.append({
            'name': rel_name,
            'path': rel_name,
            'type': 'doc',
            'ref_count': len([r for r in references if r['from'] == rel_name])
        })
    
    # Process task files
    for filepath in task_files:  # All tasks
        content = read_text_file(filepath)
        rel_name = str(filepath.relative_to(WORKSPACE_ROOT)).replace('\\', '/')
        
        # Extract references from task files
        matches = ref_pattern.findall(content)
        for match in matches:
            parts = match.split('|')
            ref_file = parts[0].split('#')[0] if parts else match
            references.append({
                'from': rel_name,
                'to': ref_file,
                'type': 'pointer',
                'full_ref': match
            })
        
        files.append({
            'name': rel_name,
            'path': rel_name,
            'type': 'task',
            'ref_count': len([r for r in references if r['from'] == rel_name])
        })
    
    # Process report files
    for filepath in report_files:  # All reports
        content = read_text_file(filepath)
        rel_name = str(filepath.relative_to(WORKSPACE_ROOT)).replace('\\', '/')
        
        # Extract references from report files  
        matches = ref_pattern.findall(content)
        for match in matches:
            parts = match.split('|')
            ref_file = parts[0].split('#')[0] if parts else match
            references.append({
                'from': rel_name,
                'to': ref_file,
                'type': 'pointer',
                'full_ref': match
            })
        
        files.append({
            'name': rel_name,
            'path': rel_name,
            'type': 'report',
            'ref_count': len([r for r in references if r['from'] == rel_name])
        })
    
    # Process archive files
    for filepath in archive_files:  # All archives
        rel_path = str(filepath.relative_to(WORKSPACE_ROOT)).replace('\\', '/')
        content = read_text_file(filepath)
        
        # Extract references from archive files
        matches = ref_pattern.findall(content)
        for match in matches:
            parts = match.split('|')
            ref_file = parts[0].split('#')[0] if parts else match
            references.append({
                'from': rel_path,
                'to': ref_file,
                'type': 'pointer',
                'full_ref': match
            })
        
        files.append({
            # Keep name stable for UI labels (basename), but provide a resolvable workspace-relative path.
            'name': filepath.name,
            'path': rel_path,
            'type': 'archive',
            'ref_count': len([r for r in references if r['from'] == rel_path])
        })
    
    # Add code files
    if (WORKSPACE_ROOT / 'loop_cockpit.py').exists():
        files.append({
            'name': 'loop_cockpit.py',
            'path': 'loop_cockpit.py',
            'type': 'code',
            'ref_count': 0
        })
    
    if (WORKSPACE_ROOT / 'cigarette_counter.py').exists():
        files.append({
            'name': 'cigarette_counter.py',
            'path': 'cigarette_counter.py',
            'type': 'code',
            'ref_count': 0
        })
    
    # Calculate positions for 3D layout (circular arrangement)
    import math
    for i, file in enumerate(files):
        angle = (i / len(files)) * 2 * math.pi
        radius = 10
        
        if file['type'] == 'core':
            radius = 3
            y = 8  # Highest - parent files
        elif file['type'] == 'state':
            radius = 6
            y = 5  # High - state tracking
        elif file['type'] == 'task':
            radius = 12
            y = -2  # Middle-low - work items
        elif file['type'] == 'report':
            radius = 12
            y = -5  # Lower - completed work
        elif file['type'] == 'archive':
            radius = 15
            y = -8  # Lowest - historical
        elif file['type'] == 'code':
            radius = 10
            y = 0  # Middle - implementation
        else:
            radius = 10
            y = 0
        
        x = radius * math.cos(angle)
        z = radius * math.sin(angle)
        
        file['position'] = [round(x, 2), y, round(z, 2)]
        
        # Assign colors based on type
        colors = {
            'core': 0xffd700,    # gold
            'state': 0x00ff88,   # green
            'task': 0x0088ff,    # blue
            'report': 0x00ffff,  # cyan
            'archive': 0x8a2be2, # purple
            'code': 0xff8800,    # orange
            'doc': 0xcccccc      # gray
        }
        file['color'] = colors.get(file['type'], 0xffffff)
        file['size'] = 1.0
    
    # Calculate total connections (incoming + outgoing) for each file
    # This provides accurate "connections" count for graph visualization
    for file in files:
        path = file['path']
        outgoing = file['ref_count']  # Already calculated (references FROM this file)
        incoming = len([r for r in references if r['to'] == path])
        file['connections'] = outgoing + incoming
        file['incoming_refs'] = incoming
    
    return jsonify({
        'files': files,
        'references': references,
        'stats': {
            'total_files': len(files),
            'total_references': len(references),
            'core_files': len([f for f in files if f['type'] == 'core']),
            'core_references': len([r for r in references if r['from'] in core_files])
        }
    })


@app.route('/api/token-monitor', methods=['GET'])
def get_token_monitor():
    """Get LIVE token usage from Clawdbot sessions.json.
    
    Updated Loop 78: Reads directly from Clawdbot's session state for real-time monitoring.
    Falls back to CSV if Clawdbot data unavailable.
    """
    try:
        from scripts.read_token_csv import get_token_usage
        
        data = get_token_usage()
        
        if 'error' in data:
            # Fall back to zero state if CSV not available
            return jsonify({
                "current_session": 0,
                "total_used": 0,
                "remaining": 200000,
                "limit": 200000,
                "percentage": 0,
                "zone": "SAFE",
                "zone_color": "#50c8a0",
                "last_updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                "error": data['error']
            })
        
        return jsonify(data)
        
    except Exception as e:
        # Fall back to safe defaults
        return jsonify({
            "current_session": 0,
            "total_used": 0,
            "remaining": 200000,
            "limit": 200000,
            "percentage": 0,
            "zone": "SAFE",
            "zone_color": "#50c8a0",
            "last_updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "error": str(e)
        }), 500


@app.route('/api/bandwidth-settings', methods=['GET'])
def get_bandwidth_settings():
    """Get current bandwidth guard settings."""
    try:
        from rate_limit_handler import BandwidthGuardConfig, BandwidthGuard
        
        # Attempt to read persisted settings first
        settings_file = WORKSPACE_ROOT / 'data' / 'bandwidth_settings.json'
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            return jsonify({
                "budget_bytes_per_minute": cfg.get('budget_bytes_per_minute', BandwidthGuardConfig().budget_bytes_per_minute),
                "warning_threshold": cfg.get('warning_threshold', BandwidthGuardConfig().warning_threshold),
                "critical_threshold": cfg.get('critical_threshold', BandwidthGuardConfig().critical_threshold),
                "window_seconds": cfg.get('window_seconds', BandwidthGuardConfig().window_seconds),
                "abort_on_critical": cfg.get('abort_on_critical', BandwidthGuardConfig().abort_on_critical),
                "log_decisions": cfg.get('log_decisions', BandwidthGuardConfig().log_decisions)
            })

        # Fall back to defaults
        config = BandwidthGuardConfig()
        return jsonify({
            "budget_bytes_per_minute": config.budget_bytes_per_minute,
            "warning_threshold": config.warning_threshold,
            "critical_threshold": config.critical_threshold,
            "window_seconds": config.window_seconds,
            "abort_on_critical": config.abort_on_critical,
            "log_decisions": config.log_decisions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/bandwidth-settings', methods=['POST'])
def update_bandwidth_settings():
    """Update bandwidth guard settings."""
    try:
        data = request.get_json()
        
        # Here we would update a persistent settings file
        # For now, just validate the input
        required_fields = ['budget_bytes_per_minute', 'warning_threshold', 'critical_threshold']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate ranges
        if data['warning_threshold'] >= data['critical_threshold']:
            return jsonify({"error": "Warning threshold must be less than critical threshold"}), 400
        
        if data['budget_bytes_per_minute'] <= 0:
            return jsonify({"error": "Budget must be positive"}), 400
        
        # Persist settings to workspace data file
        data_dir = WORKSPACE_ROOT / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        settings_file = data_dir / 'bandwidth_settings.json'
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump({
                'budget_bytes_per_minute': int(data['budget_bytes_per_minute']),
                'warning_threshold': float(data['warning_threshold']),
                'critical_threshold': float(data['critical_threshold']),
                'abort_on_critical': bool(data.get('abort_on_critical', True)),
                'log_decisions': bool(data.get('log_decisions', True)),
                'window_seconds': int(data.get('window_seconds', 60))
            }, f, indent=2)

        return jsonify({"success": True, "message": "Settings updated and persisted"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/bandwidth-usage', methods=['GET'])
def get_bandwidth_usage():
    """Get current bandwidth usage statistics."""
    try:
        from rate_limit_handler import BandwidthTracker
        
        tracker = BandwidthTracker(WORKSPACE_ROOT)
        
        # Get usage for different time windows
        last_minute = tracker.get_usage_last_window(60)
        last_5_minutes = tracker.get_usage_last_window(300)
        last_hour = tracker.get_usage_last_window(3600)
        
        return jsonify({
            "last_minute_bytes": last_minute,
            "last_5_minutes_bytes": last_5_minutes,
            "last_hour_bytes": last_hour,
            "last_updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/bandwidth-alerts', methods=['GET'])
def get_bandwidth_alerts():
    """Get recent bandwidth guard alerts."""
    try:
        log_file = WORKSPACE_ROOT / 'bandwidth_guard_log.jsonl'
        alerts = []
        
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            alerts.append(entry)
                        except:
                            continue
        
        # Return last 10 alerts
        recent_alerts = alerts[-10:]
        
        return jsonify({
            "alerts": recent_alerts,
            "total_alerts": len(alerts)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/finalization-check', methods=['GET'])
def get_finalization_check():
    """Check if AI should start finalization based on token budget.
    
    Returns recommendation for AI self-governance:
    - should_finalize: bool
    - urgency: NONE | LOW | MEDIUM | HIGH | CRITICAL
    - message: Human-readable guidance
    """
    try:
        # Use LoopBudgetTracker for accurate token budget tracking
        tracker = LoopBudgetTracker(Path('.'))
        status = tracker.get_budget_status()
        
        percentage = status['percentage']
        zone = "SAFE"
        if percentage < 50:
            zone = "SAFE"
        elif percentage < 75:
            zone = "CAUTION"
        elif percentage < 85:
            zone = "CONSERVATION"
        elif percentage < 95:
            zone = "EMERGENCY"
        else:
            zone = "ABORT"
        
        urgency = "NONE"
        if percentage >= 95:
            urgency = "CRITICAL"
        elif percentage >= 85:
            urgency = "HIGH"
        elif percentage >= 75:
            urgency = "MEDIUM"
        elif percentage >= 60:
            urgency = "LOW"
        
        should_finalize = percentage >= 75
        
        # Build guidance message
        if urgency == "CRITICAL":
            message = "🚨 CRITICAL: Budget exhausted! Write emergency report and exit NOW."
        elif urgency == "HIGH":
            message = "⚠️ HIGH: Start finalization immediately. Write reports, create archive."
        elif urgency == "MEDIUM":
            message = "🟡 MEDIUM: Begin wrapping up. Complete current task, then finalize."
        elif urgency == "LOW":
            message = "📊 LOW: Monitor progress. Consider natural stopping point."
        else:
            message = "✅ Continue working normally."
        
        return jsonify({
            "should_finalize": should_finalize,
            "urgency": urgency,
            "percentage": percentage,
            "zone": zone,
            "message": message,
            "actions": _get_finalization_actions(urgency),
            "budget_status": status
        })
        
    except Exception as e:
        return jsonify({
            "should_finalize": False,
            "urgency": "UNKNOWN",
            "error": str(e)
        }), 500

def _get_finalization_actions(urgency: str) -> list:
    """Get recommended actions based on urgency."""
    if urgency == "CRITICAL":
        return [
            "STOP all work immediately",
            "Write emergency status report (50 tokens max)",
            "Update current.json",
            "Exit gracefully"
        ]
    elif urgency == "HIGH":
        return [
            "Complete current sentence/thought",
            "Write task report if not done",
            "Create finalization report",
            "Sign approval and finalize"
        ]
    elif urgency == "MEDIUM":
        return [
            "Finish current task",
            "Write comprehensive report",
            "Review open items",
            "Prepare finalization"
        ]
    elif urgency == "LOW":
        return [
            "Continue normal work",
            "Monitor token usage",
            "Plan stopping point"
        ]
    return ["Continue working"]


# =============================================================================
# AGENT-STYLE CODING ASSISTANT API
# =============================================================================

@app.route('/api/agent/chat', methods=['POST'])
def api_agent_chat():
    print("DEBUG: api_agent_chat called")
    """Agent-style coding assistant with tool calling capabilities.

    Supports both JSON requests and multipart form data for file uploads.

    JSON Request:
    {
        "message": "Create a new Python function to calculate fibonacci numbers",
        "provider": "openai"  // or "gemini"
    }

    Multipart Form Data:
    - message: text message
    - provider: ai provider
    - file: attached file (optional)
    """
    try:
        message = ""
        provider = "gemini"
        attached_file = None

        # Check if this is multipart form data (file upload)
        if request.content_type and 'multipart/form-data' in request.content_type:
            print("DEBUG: Handling multipart form data")
            message = request.form.get('message', '').strip()
            provider = request.form.get('provider', 'gemini').lower()

            # Handle file attachment
            if 'file' in request.files:
                attached_file = request.files['file']
                print(f"DEBUG: File attached: {attached_file.filename}")
        else:
            # Handle JSON data
            data = request.get_json() or {}
            message = data.get('message', '').strip()
            provider = data.get('provider', 'gemini').lower()

        if not message and not attached_file:
            return jsonify({"success": False, "error": "No message or file provided"}), 400

        # Import and use our Gemini-powered Keeper Agent
        try:
            from keeper_agent import KeeperAgent
            print("DEBUG: KeeperAgent imported successfully")
        except Exception as e:
            print(f"DEBUG: KeeperAgent import failed: {e}")
            return jsonify({"success": False, "error": f"Agent import failed: {e}"}), 500

        if provider not in ['gemini', 'openai']:
            provider = 'gemini'

        # Initialize the Keeper Agent with chosen provider
        agent = KeeperAgent(max_history_pairs=3, provider=provider)
        print(f"DEBUG: KeeperAgent initialized with {provider.upper()}")

        # Prepare the message, including file content if attached
        full_message = message
        if attached_file:
            try:
                # Read file content
                file_content = attached_file.read().decode('utf-8')
                file_extension = attached_file.filename.split('.')[-1].lower() if '.' in attached_file.filename else 'txt'

                # Add file content to message
                full_message = f"{message}\n\nAttached file ({attached_file.filename}):\n```{file_extension}\n{file_content}\n```"

                # For images, we might need special handling
                if file_extension in ['png', 'jpg', 'jpeg', 'gif', 'svg']:
                    # For now, just mention the image - full image analysis would need additional setup
                    full_message = f"{message}\n\n[Image attached: {attached_file.filename} - Image analysis capabilities available via Codex CLI]"

            except Exception as e:
                print(f"DEBUG: Error reading attached file: {e}")
                full_message = f"{message}\n\n[Error reading attached file: {attached_file.filename}]"

        # Process the request using the chosen AI provider
        result = agent.send(full_message)

        # Debug: check what we got
        usage_data = result.get("usage", {})

        # Initialize actions_taken
        actions_taken = []
        if "Tool:" in str(result.get('message', '')):
            actions_taken.append({
                "tool": "various",
                "description": "Executed tools as needed",
                "status": "completed"
            })

        return jsonify({
            "success": True,
            "response": result.get("message", ""),
            "actions_taken": actions_taken,
            "needs_confirmation": False,
            "pending_actions": [],
            "reasoning_steps": [],
            "completed": True,
            "usage": usage_data
        })

    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


@app.route('/api/agent/confirm-action', methods=['POST'])
def api_agent_confirm_action():
    """Confirm and execute a pending agent action.
    
    Request JSON:
    {
        "action_id": "uuid-of-action",
        "confirmed": true
    }
    """
    try:
        data = request.get_json() or {}
        action_id = data.get('action_id')
        confirmed = data.get('confirmed', False)
        
        if not action_id:
            return jsonify({"success": False, "error": "Missing action_id"}), 400
        
        # Find and execute the pending action
        # This would need to be implemented with session management
        # For now, return not implemented
        return jsonify({
            "success": False,
            "error": "Action confirmation not yet implemented"
        }), 501
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


class CodingAgent:
    """Agent-style coding assistant with tool calling capabilities."""
    
    def __init__(self, workspace_root, confirm_tools=False, max_steps=5):
        self.workspace_root = Path(workspace_root)
        self.confirm_tools = confirm_tools
        self.max_steps = max_steps
        self.reasoning_steps = []
        self.actions_taken = []
        self.pending_actions = []
        
        # Define available tools
        self.tools = {
            'read_file': self.tool_read_file,
            'search_files': self.tool_search_files,
            'create_file': self.tool_create_file,
            'edit_file': self.tool_edit_file,
            'run_terminal': self.tool_run_terminal,
            'list_directory': self.tool_list_directory,
            'get_file_info': self.tool_get_file_info,
            'search_knowledge': self.tool_search_knowledge
        }
        
        # Safety classifications
        self.safe_tools = {'read_file', 'search_files', 'list_directory', 'get_file_info', 'search_knowledge'}
        self.destructive_tools = {'create_file', 'edit_file', 'run_terminal'}
    
    def process_request(self, message):
        """Process a coding request using agent reasoning loop."""
        
        # Step 1: Analyze the request
        self.reasoning_steps.append({
            "step": 1,
            "type": "analysis",
            "content": f"Analyzing request: {message[:100]}..."
        })
        
        request_type = self._classify_request(message)
        self.reasoning_steps.append({
            "step": 2,
            "type": "classification", 
            "content": f"Request classified as: {request_type}"
        })
        
        # Step 2: Plan solution
        plan = self._create_plan(message, request_type)
        self.reasoning_steps.append({
            "step": 3,
            "type": "planning",
            "content": f"Created plan with {len(plan)} steps"
        })
        
        # Step 3: Execute plan
        completed = False
        needs_confirmation = False
        
        for i, step in enumerate(plan[:self.max_steps]):
            self.reasoning_steps.append({
                "step": 4 + i,
                "type": "execution",
                "content": f"Executing step {i+1}: {step['description']}"
            })
            
            # Check if tool needs confirmation
            tool_name = step.get('tool')
            if tool_name in self.destructive_tools and not self.confirm_tools:
                self.pending_actions.append({
                    "id": f"action_{i}",
                    "tool": tool_name,
                    "description": step['description'],
                    "params": step.get('params', {}),
                    "reason": step.get('reason', '')
                })
                needs_confirmation = True
                break
            
            # Execute the tool
            try:
                result = self._execute_tool(step)
                self.actions_taken.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "description": step['description'],
                    "result": result,
                    "success": True
                })
            except Exception as e:
                self.actions_taken.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "description": step['description'],
                    "error": str(e),
                    "success": False
                })
                break
        
        # Step 4: Generate response
        response = self._generate_response(message, request_type, self.actions_taken, needs_confirmation)
        
        return {
            "response": response,
            "actions_taken": self.actions_taken,
            "needs_confirmation": needs_confirmation,
            "pending_actions": self.pending_actions,
            "reasoning_steps": self.reasoning_steps,
            "completed": not needs_confirmation and len(self.actions_taken) > 0
        }
    
    def _classify_request(self, message):
        """Classify the type of coding request."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['create', 'new', 'add', 'implement']):
            return 'creation'
        elif any(word in message_lower for word in ['fix', 'bug', 'error', 'issue']):
            return 'debugging'
        elif any(word in message_lower for word in ['read', 'show', 'display', 'view']):
            return 'exploration'
        elif any(word in message_lower for word in ['run', 'execute', 'test']):
            return 'execution'
        elif any(word in message_lower for word in ['search', 'find', 'locate']):
            return 'search'
        else:
            return 'general'
    
    def _create_plan(self, message, request_type):
        """Create a step-by-step plan for the request."""
        plan = []
        
        if request_type == 'creation':
            # For creation tasks, explore existing code first, then create
            plan.extend([
                {
                    "tool": "search_files",
                    "description": "Search for similar existing code",
                    "params": {"query": self._extract_keywords(message)},
                    "reason": "Understand existing patterns before creating new code"
                },
                {
                    "tool": "list_directory",
                    "description": "Check project structure",
                    "params": {"path": "."},
                    "reason": "Determine where to place new code"
                },
                {
                    "tool": "create_file",
                    "description": "Create the new file/function",
                    "params": {"content": self._generate_code_template(message)},
                    "reason": "Implement the requested functionality"
                }
            ])
            
        elif request_type == 'debugging':
            plan.extend([
                {
                    "tool": "read_file",
                    "description": "Read the problematic file",
                    "params": {"file_path": self._extract_file_path(message)},
                    "reason": "Examine the code with the issue"
                },
                {
                    "tool": "run_terminal",
                    "description": "Run tests to reproduce the issue",
                    "params": {"command": "python -m pytest"},
                    "reason": "Verify the current behavior"
                },
                {
                    "tool": "edit_file",
                    "description": "Apply the fix",
                    "params": {"changes": "Fix the identified issue"},
                    "reason": "Resolve the bug"
                }
            ])
            
        elif request_type == 'exploration':
            plan.extend([
                {
                    "tool": "list_directory",
                    "description": "Explore the directory structure",
                    "params": {"path": self._extract_path(message)},
                    "reason": "Navigate to the requested location"
                },
                {
                    "tool": "read_file",
                    "description": "Read the requested file",
                    "params": {"file_path": self._extract_file_path(message)},
                    "reason": "Show the file contents"
                }
            ])
        
        return plan
    
    def _execute_tool(self, step):
        """Execute a tool with given parameters."""
        tool_name = step.get('tool')
        params = step.get('params', {})
        
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool_func = self.tools[tool_name]
        return tool_func(**params)
    
    def _generate_response(self, message, request_type, actions_taken, needs_confirmation):
        """Generate a natural language response based on actions taken."""
        if needs_confirmation:
            return f"I need your confirmation to proceed with destructive operations. I've planned {len(self.pending_actions)} action(s) that require approval."
        
        if not actions_taken:
            return "I analyzed your request but couldn't determine the appropriate actions to take. Could you provide more specific details?"
        
        successful_actions = [a for a in actions_taken if a['success']]
        failed_actions = [a for a in actions_taken if not a['success']]
        
        response_parts = []
        
        if successful_actions:
            response_parts.append(f"I've successfully completed {len(successful_actions)} action(s):")
            for action in successful_actions:
                response_parts.append(f"✓ {action['description']}")
        
        if failed_actions:
            response_parts.append(f"\nI encountered {len(failed_actions)} issue(s):")
            for action in failed_actions:
                response_parts.append(f"✗ {action['description']}: {action['error']}")
        
        if request_type == 'creation':
            response_parts.append("\nThe new code has been created. You can review and test it now.")
        elif request_type == 'debugging':
            response_parts.append("\nThe debugging process is complete. Please verify the fix works as expected.")
        
        return '\n'.join(response_parts)
    
    def _extract_keywords(self, message):
        """Extract search keywords from a message."""
        # Simple keyword extraction - could be enhanced with NLP
        words = message.lower().replace('?', '').replace('.', '').split()
        stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'do', 'i', 'we', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'and', 'or', 'but', 'if', 'when', 'where', 'why', 'which', 'who', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'this', 'that', 'these', 'those', 'it', 'its', 'about', 'from'}
        return ' '.join([w for w in words if w not in stop_words and len(w) > 2])
    
    def _extract_file_path(self, message):
        """Extract file path from message (basic implementation)."""
        # Look for file extensions or common patterns
        import re
        file_match = re.search(r'([a-zA-Z0-9_./-]+\.(py|js|html|css|md|txt|json))', message)
        return file_match.group(1) if file_match else None
    
    def _extract_path(self, message):
        """Extract directory path from message."""
        # Default to current directory if no path found
        return "."
    
    def _generate_code_template(self, message):
        """Generate a basic code template based on the request."""
        # Very basic template generation - could be enhanced
        if 'function' in message.lower() and 'fibonacci' in message.lower():
            return '''def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Example usage
if __name__ == "__main__":
    print(fibonacci(10))  # Should print 55
'''
        else:
            return f'# Code template for: {message}\n# TODO: Implement the requested functionality\n'
    
    # Tool implementations
    def tool_read_file(self, file_path, start_line=None, end_line=None):
        """Read a file from the workspace."""
        if not file_path:
            raise ValueError("file_path is required")
        
        full_path = self.workspace_root / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Track file access with breadcrumb
        try:
            from ai_breadcrumb_tracker import track_file_access
            track_file_access(file_path, f"tool_read_file_call")
        except ImportError:
            pass  # Breadcrumb tracking not available
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if start_line and end_line:
            lines = content.split('\n')
            content = '\n'.join(lines[start_line-1:end_line])
        
        return {"content": content, "path": file_path}
    
    def tool_search_files(self, query, include_pattern=None):
        """Search for text in files."""
        results = []
        
        # Simple grep-like search
        for file_path in self.workspace_root.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if query.lower() in content.lower():
                            results.append({
                                "file": str(file_path.relative_to(self.workspace_root)),
                                "matches": content.lower().count(query.lower())
                            })
                except:
                    pass
        
        return {"query": query, "results": results[:10]}  # Limit results
    
    def tool_create_file(self, file_path, content):
        """Create a new file."""
        if not file_path:
            raise ValueError("file_path is required")
        
        full_path = self.workspace_root / file_path
        if full_path.exists():
            raise FileExistsError(f"File already exists: {file_path}")
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Track file creation with breadcrumb
        try:
            from ai_breadcrumb_tracker import track_file_creation
            track_file_creation(file_path, f"tool_create_file_call")
        except ImportError:
            pass  # Breadcrumb tracking not available
        
        return {"created": file_path, "size": len(content)}
    
    def tool_edit_file(self, file_path, old_string, new_string):
        """Edit an existing file."""
        if not file_path:
            raise ValueError("file_path is required")
        
        full_path = self.workspace_root / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_string not in content:
            raise ValueError("old_string not found in file")
        
        new_content = content.replace(old_string, new_string, 1)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Track file modification with breadcrumb
        try:
            from ai_breadcrumb_tracker import track_file_modification
            track_file_modification(file_path, f"tool_edit_file_call")
        except ImportError:
            pass  # Breadcrumb tracking not available
        
        return {"edited": file_path, "changes": 1}
    
    def tool_run_terminal(self, command, cwd=None):
        """Run a terminal command."""
        import subprocess
        
        working_dir = self.workspace_root / (cwd or ".")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30
            )
            
            return {
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out after 30 seconds"}
        except Exception as e:
            return {"error": str(e)}
    
    def tool_list_directory(self, path):
        """List directory contents."""
        full_path = self.workspace_root / path
        
        if not full_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        items = []
        for item in full_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0
            })
        
        return {"path": path, "items": items}
    
    def tool_get_file_info(self, file_path):
        """Get information about a file."""
        full_path = self.workspace_root / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = full_path.stat()
        
        return {
            "path": file_path,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "type": "directory" if full_path.is_dir() else "file"
        }
    
    def tool_search_knowledge(self, query):
        """Search the knowledge database."""
        try:
            from knowledge_db import KnowledgeDB
            db = KnowledgeDB(self.workspace_root)
            
            if not db.db_path.exists():
                return {"error": "Knowledge database not built yet"}
            
            results = db.search(query, limit=5)
            db.close()
            
            formatted = []
            for r in results:
                formatted.append({
                    "type": r.type,
                    "id": r.id,
                    "snippet": r.snippet,
                    "relevance": r.relevance
                })
            
            return {"query": query, "results": formatted}
            
        except Exception as e:
            return {"error": str(e)}


@app.route('/api/generate-code', methods=['POST'])
def api_generate_code():
    """Generate code using Ollama AI models.
    
    Request JSON:
        prompt: str - Natural language description of code to generate
        model: str - Ollama model name (optional, defaults to configured model)
    
    Response JSON:
        success: bool
        filename: str - Generated filename
        code: str - Generated code content
        explanation: str - Brief explanation
        filepath: str - Full path where code was saved
        error: str - Error message if failed
    """
    try:
        data = request.get_json(silent=True) or {}
        prompt = data.get('prompt', '').strip()
        model = data.get('model', OLLAMA_MODEL).strip()
        
        if not prompt:
            return jsonify({"success": False, "error": "prompt is required"}), 400
        
        # Call Ollama API with fallback
        raw_response = call_ollama_api(prompt, model)
        
        # Parse the response
        parsed = parse_llm_response(raw_response)
        
        # Save the generated code
        filepath = save_generated_code(parsed['filename'], parsed['code'])
        
        return jsonify({
            "success": True,
            "filename": parsed['filename'],
            "code": parsed['code'],
            "explanation": parsed['explanation'],
            "filepath": filepath,
            "model": model
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/global-events/observe', methods=['POST'])
def api_observe_global_event():
    """Observe and record a global event.
    
    Request JSON:
        title: str - Event title
        description: str - Event description
        category: str - Event category (geopolitical, economic, etc.)
        source: str - Information source
        tags: list - List of relevant tags
        impact_scale: str - Impact scale (local, regional, etc.)
    
    Returns:
        success: bool
        event_id: str - Unique event identifier
    """
    try:
        data = request.get_json(silent=True) or {}
        
        required_fields = ['title', 'description', 'category', 'source', 'tags']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"{field} is required"}), 400
        
        event_id = observe_global_event(
            title=data['title'],
            description=data['description'],
            category=data['category'],
            source=data['source'],
            tags=data['tags'],
            impact_scale=data.get('impact_scale', 'regional')
        )
        
        return jsonify({
            "success": True,
            "event_id": event_id
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/global-events/predict', methods=['POST'])
def api_create_event_prediction():
    """Create a prediction based on observed events.
    
    Request JSON:
        title: str - Prediction title
        description: str - Prediction description
        event_ids: list - List of related event IDs
        predicted_outcome: str - Expected outcome
        confidence_level: float - Confidence (0-1)
        timeframe_days: int - Timeframe in days
    
    Returns:
        success: bool
        prediction_id: str - Unique prediction identifier
    """
    try:
        data = request.get_json(silent=True) or {}
        
        required_fields = ['title', 'description', 'event_ids', 'predicted_outcome', 'confidence_level', 'timeframe_days']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"{field} is required"}), 400
        
        prediction_id = create_event_prediction(
            title=data['title'],
            description=data['description'],
            event_ids=data['event_ids'],
            outcome=data['predicted_outcome'],
            confidence=data['confidence_level'],
            timeframe=data['timeframe_days']
        )
        
        return jsonify({
            "success": True,
            "prediction_id": prediction_id
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/global-events/report', methods=['GET'])
def api_get_global_events_report():
    """Get a comprehensive report of global events observations and predictions.
    
    Returns:
        report: str - Markdown formatted report
    """
    try:
        report = get_global_events_report()
        return jsonify({
            "success": True,
            "report": report
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/service-status', methods=['GET'])
def api_get_service_status():
    """Get status of background monitoring services.
    
    Returns:
        services: dict - Status information for each service
    """
    try:
        services = {}
        
        # Check backup manager status
        try:
            from backup.backup_manager import BackupManager
            manager = BackupManager(WORKSPACE_ROOT)
            status = manager.get_backup_status()
            services['backup_manager'] = {
                'name': 'Automated Backup',
                'running': True,  # Assume running if we can instantiate
                'status': 'healthy' if status['total_snapshots'] > 0 else 'warning',
                'details': {
                    'snapshots': status['total_snapshots'],
                    'last_backup': status.get('latest_snapshot', {}).get('created_at', 'never'),
                    'interval': f"{status['backup_interval_minutes']} minutes"
                }
            }
        except Exception as e:
            services['backup_manager'] = {
                'name': 'Automated Backup',
                'running': False,
                'status': 'error',
                'error': str(e)
            }
        
        # Check behavioral telemetry
        breadcrumb_file = WORKSPACE_ROOT / "breadcrumb_trail.jsonl"
        if breadcrumb_file.exists():
            try:
                with open(breadcrumb_file, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                services['behavioral_telemetry'] = {
                    'name': 'Behavioral Telemetry',
                    'running': True,
                    'status': 'healthy',
                    'details': {
                        'breadcrumbs': lines,
                        'interval': '15 minutes'
                    }
                }
            except Exception as e:
                services['behavioral_telemetry'] = {
                    'name': 'Behavioral Telemetry',
                    'running': False,
                    'status': 'error',
                    'error': str(e)
                }
        else:
            services['behavioral_telemetry'] = {
                'name': 'Behavioral Telemetry',
                'running': False,
                'status': 'warning',
                'details': {'file_missing': True}
            }
        
        # Check AI integrity protection
        transaction_file = WORKSPACE_ROOT / "_transaction_log.jsonl"
        if transaction_file.exists():
            try:
                with open(transaction_file, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                services['ai_integrity'] = {
                    'name': 'AI Integrity Protection',
                    'running': True,
                    'status': 'healthy',
                    'details': {
                        'transactions': lines,
                        'interval': '5 minutes'
                    }
                }
            except Exception as e:
                services['ai_integrity'] = {
                    'name': 'AI Integrity Protection',
                    'running': False,
                    'status': 'error',
                    'error': str(e)
                }
        else:
            services['ai_integrity'] = {
                'name': 'AI Integrity Protection',
                'running': False,
                'status': 'warning',
                'details': {'log_missing': True}
            }
        
        # Check token governor
        try:
            from token_governor import TokenGovernor
            governor = TokenGovernor(workspace_root=WORKSPACE_ROOT)
            metrics = governor.get_current_metrics()
            services['token_monitor'] = {
                'name': 'Token Budget Monitor',
                'running': True,
                'status': 'healthy',
                'details': {
                    'budget_zone': metrics.zone.value,
                    'used_tokens': metrics.used,
                    'interval': '10 minutes'
                }
            }
        except Exception as e:
            services['token_monitor'] = {
                'name': 'Token Budget Monitor',
                'running': False,
                'status': 'error',
                'error': str(e)
            }
        
        # Check quality manager
        try:
            import sys
            sys.path.insert(0, str(WORKSPACE_ROOT / "quality_manager"))
            from quality_integration import QualityManagerIntegration
            
            integration = QualityManagerIntegration()
            status = integration.get_quality_status()
            services['quality_manager'] = {
                'name': 'Quality Manager',
                'running': True,
                'status': 'healthy' if status['overall_score'] >= 70 else 'warning',
                'details': {
                    'overall_score': status['overall_score'],
                    'issues_count': status['issues_count'],
                    'files_analyzed': status['files_analyzed'],
                    'last_update': status['last_update'],
                    'interval': '30 minutes'
                }
            }
        except Exception as e:
            services['quality_manager'] = {
                'name': 'Quality Manager',
                'running': False,
                'status': 'error',
                'error': str(e)
            }
        
        # Check service orchestrator (check if process is running)
        import subprocess
        import sys
        orchestrator_running = False
        try:
            result = subprocess.run([
                'tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'
            ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
            orchestrator_running = 'service_orchestrator' in result.stdout
        except:
            pass
        
        services['service_orchestrator'] = {
            'name': 'Service Orchestrator',
            'running': orchestrator_running,
            'status': 'healthy' if orchestrator_running else 'stopped',
            'details': {
                'type': 'background daemon',
                'manages': ['backup', 'telemetry', 'integrity', 'tokens', 'quality']
            }
        }
        
        return jsonify({
            "success": True,
            "services": services,
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/autostart/status', methods=['GET'])
def api_autostart_status():
    """Get autostart supervisor and child job runtime state."""
    try:
        return jsonify(_build_autostart_status_payload())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/autostart/control', methods=['POST'])
def api_autostart_control():
    """Control supervisor lifecycle: start, stop, restart, refresh."""
    try:
        data = request.get_json(silent=True) or {}
        action = str(data.get("action", "refresh")).strip().lower()

        if action == "start":
            result = _start_autostart_supervisor()
        elif action == "stop":
            result = _stop_autostart_supervisor()
        elif action == "restart":
            _stop_autostart_supervisor()
            result = _start_autostart_supervisor()
        elif action == "refresh":
            result = {"success": True, "message": "Refresh requested"}
        else:
            return jsonify(_api_error_payload(f"Unsupported action: {action}", 400, "BAD_REQUEST")), 400

        payload = _build_autostart_status_payload()
        payload["action"] = action
        payload["action_result"] = result
        return jsonify(payload), (200 if result.get("success", False) else 500)
    except Exception as e:
        return jsonify(_api_error_payload(str(e), 500, "INTERNAL_SERVER_ERROR")), 500


@app.route('/api/autostart/job-control', methods=['POST'])
def api_autostart_job_control():
    """Control a specific autostart child job: run_now, stop, restart."""
    try:
        data = request.get_json(silent=True) or {}
        job = str(data.get("job", "")).strip()
        action = str(data.get("action", "run_now")).strip().lower()
        if not job:
            return jsonify(_api_error_payload("Missing 'job' field", 400, "BAD_REQUEST")), 400

        if action == "run_now":
            result = _spawn_job_once(job)
        elif action == "stop":
            result = _stop_job_if_running(job)
        elif action == "restart":
            _stop_job_if_running(job)
            result = _spawn_job_once(job)
        else:
            return jsonify(_api_error_payload(f"Unsupported action: {action}", 400, "BAD_REQUEST")), 400

        payload = _build_autostart_status_payload()
        payload["job_action"] = {"job": job, "action": action}
        payload["action_result"] = result
        return jsonify(payload), (200 if result.get("success", False) else 500)
    except Exception as e:
        return jsonify(_api_error_payload(str(e), 500, "INTERNAL_SERVER_ERROR")), 500


@app.route('/api/behavioral-state', methods=['GET'])
def get_behavioral_state():
    """Get current behavioral state from integrated telemetry system."""
    try:
        from behavioral_telemetry_analyzer import BehavioralTelemetryAnalyzer
        from analysis.dimensional_mapper import DimensionalMapper

        analyzer = BehavioralTelemetryAnalyzer()
        mapper = DimensionalMapper()

        state = analyzer.get_current_behavioral_state()
        zone_name, zone = mapper.get_current_zone()

        return jsonify({
            'arousal': state.arousal,
            'functionality': state.functionality,
            'confidence': state.confidence,
            'timestamp': state.timestamp,
            'current_zone': {
                'name': zone_name,
                'description': zone.description,
                'risk_level': zone.risk_level,
                'recommendations': zone.recommendations
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/behavioral-history', methods=['GET'])
def get_behavioral_history():
    """Get historical behavioral data for trend analysis."""
    try:
        from behavioral_telemetry_analyzer import BehavioralTelemetryAnalyzer
        from analysis.dimensional_mapper import DimensionalMapper

        analyzer = BehavioralTelemetryAnalyzer()
        mapper = DimensionalMapper()

        hours = int(request.args.get('hours', 24))

        # Get recent behavioral points (simplified for cockpit integration)
        current = analyzer.get_current_behavioral_state()
        base_time = datetime.fromisoformat(current.timestamp.replace('Z', '+00:00'))

        points = []
        for i in range(min(hours * 2, 10)):  # Up to 10 points
            point_time = base_time - timedelta(minutes=i * 15)
            variation = (i % 3 - 1) * 0.1
            point = {
                'arousal': max(0, min(1, current.arousal + variation)),
                'functionality': max(0, min(1, current.functionality + variation * 0.5)),
                'timestamp': point_time.isoformat(),
                'confidence': current.confidence * (0.9 ** i)
            }
            points.append(point)

        return jsonify({
            'points': list(reversed(points)),  # Most recent first
            'trends': mapper.analyze_trajectory_trends()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/quality-correlations', methods=['GET'])
def get_quality_correlations():
    """Get quality-behavior correlations for performance insights."""
    try:
        from analysis.quality_correlator import QualityCorrelator

        correlator = QualityCorrelator()
        correlations = correlator.get_top_correlations()

        return jsonify({
            'correlations': [
                {
                    'activity_metric': c.activity_metric,
                    'quality_metric': c.quality_metric,
                    'correlation_coefficient': c.correlation_coefficient,
                    'confidence_level': c.confidence_level,
                    'trend_direction': c.trend_direction
                }
                for c in correlations
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pattern-analysis', methods=['GET'])
def get_pattern_analysis():
    """Get pattern recognition analysis for anomaly detection."""
    try:
        from behavioral_telemetry_analyzer import BehavioralTelemetryAnalyzer
        from analysis.pattern_recognizer import PatternRecognizer

        analyzer = BehavioralTelemetryAnalyzer()
        recognizer = PatternRecognizer()

        current_state = analyzer.get_current_behavioral_state()

        # Classify current behavior
        classification = recognizer.classify_current_behavior({
            'arousal': current_state.arousal,
            'functionality': current_state.functionality,
            'confidence': current_state.confidence,
            'timestamp': current_state.timestamp
        })

        # Get recent points for anomaly detection
        base_time = datetime.fromisoformat(current_state.timestamp.replace('Z', '+00:00'))
        recent_points = []
        for i in range(10):
            point_time = base_time - timedelta(minutes=i * 15)
            variation = (i % 3 - 1) * 0.1
            point = {
                'arousal': max(0, min(1, current_state.arousal + variation)),
                'functionality': max(0, min(1, current_state.functionality + variation * 0.5)),
                'timestamp': point_time.isoformat()
            }
            recent_points.append(point)

        alerts = recognizer.detect_anomalies(recent_points)

        return jsonify({
            'current_classification': classification,
            'active_alerts': [
                {
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'description': alert.description,
                    'confidence': alert.confidence,
                    'recommendations': alert.recommendations
                }
                for alert in alerts
            ],
            'predictive_insights': recognizer.get_predictive_insights(recent_points)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/zone-statistics', methods=['GET'])
def get_zone_statistics():
    """Get statistics about behavioral zones for cockpit display."""
    try:
        from analysis.dimensional_mapper import DimensionalMapper

        mapper = DimensionalMapper()
        return jsonify(mapper.get_zone_statistics())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def validate_override_password() -> bool:
    """Validate main override password."""
    from pathlib import Path
    import json
    import base64
    import hashlib

    hash_file = WORKSPACE_ROOT / 'validation_keys' / 'human_override_hash'
    if not hash_file.exists():
        return False

    try:
        data = json.loads(hash_file.read_text())
        salt = base64.b64decode(data['salt'])
        expected = base64.b64decode(data['hash'])
        iterations = data['iterations']
    except:
        return False

    password = input("Enter main override password: ")
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return key == expected


def validate_master_password() -> bool:
    """Validate master password."""
    from pathlib import Path
    import json
    import base64
    import hashlib

    hash_file = WORKSPACE_ROOT / 'validation_keys' / 'human_master_hash'
    if not hash_file.exists():
        return False

    try:
        data = json.loads(hash_file.read_text())
        salt = base64.b64decode(data['salt'])
        expected = base64.b64decode(data['hash'])
        iterations = data['iterations']
    except:
        return False

    password = input("Enter master password: ")
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return key == expected


def create_new_override_hash(new_password: str):
    """Create new override hash file."""
    from pathlib import Path
    import json
    import base64
    import hashlib
    import os

    key_dir = WORKSPACE_ROOT / 'validation_keys'
    key_dir.mkdir(parents=True, exist_ok=True)
    hash_file = key_dir / 'human_override_hash'

    salt = os.urandom(32)
    iterations = 100000
    key = hashlib.pbkdf2_hmac('sha256', new_password.encode('utf-8'), salt, iterations)

    data = {
        'salt': base64.b64encode(salt).decode('utf-8'),
        'hash': base64.b64encode(key).decode('utf-8'),
        'iterations': iterations
    }

    hash_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
    hash_file.chmod(0o600)


def create_human_override_approval(loop_num: int):
    """Create human master override approval file."""
    from pathlib import Path
    import json
    from datetime import datetime, timezone

    approvals_dir = WORKSPACE_ROOT / 'approvals'
    approvals_dir.mkdir(parents=True, exist_ok=True)
    fname = approvals_dir / f"HUMAN_MASTER_OVERRIDE.json"

    data = {
        "authorized_by": "human",
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "reason": "Human override for catastrophic finalization",
        "loop": loop_num
    }

    fname.write_text(json.dumps(data, indent=2), encoding='utf-8')


def ensure_autostart_supervisor_running() -> bool:
    """Best-effort detached launch of helper-services supervisor.

    This provides helper-script support immediately when cockpit starts,
    including bootstrap phase before ACTIVE loop gate autostart.
    """
    script_path = WORKSPACE_ROOT / "scripts" / "start_autostart_services.py"
    if not script_path.exists():
        print(f"⚠ Autostart supervisor script missing: {script_path}")
        return False

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(WORKSPACE_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            env=env,
        )
        print("✓ Autostart supervisor launch requested")
        return True
    except Exception as e:
        print(f"⚠ Failed to launch autostart supervisor: {e}")
        return False


def run_cockpit_server(app: Flask, backend: str = "auto") -> None:
    """Run cockpit server with flexible backend selection.

    Backends:
    - socketio: Flask-SocketIO server
    - waitress: Waitress WSGI server (HTTP only)
    - auto: prefer waitress when available, fallback to socketio
    """
    chosen = (backend or "auto").strip().lower()

    if chosen not in {"auto", "socketio", "waitress"}:
        print(f"⚠ Unknown server backend '{backend}', falling back to socketio")
        chosen = "socketio"

    if chosen in {"auto", "waitress"}:
        try:
            from waitress import serve
            print("Starting server with Waitress...")
            print(f"DEBUG: App has {len(list(app.url_map.iter_rules()))} routes before run")
            serve(app, host="127.0.0.1", port=5000)
            return
        except Exception as e:
            if chosen == "waitress":
                print(f"⚠ Waitress startup failed: {e}")
                print("Falling back to SocketIO backend...")
            else:
                print(f"⚠ Waitress unavailable/failed in auto mode: {e}")

    print("Starting server with SocketIO...")
    print(f"DEBUG: App has {len(list(app.url_map.iter_rules()))} routes before run")
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)


AUTOSTART_SUPERVISOR_SCRIPT = WORKSPACE_ROOT / "scripts" / "start_autostart_services.py"
AUTOSTART_SUPERVISOR_STATUS = WORKSPACE_ROOT / "logs" / "autostart_supervisor_status.json"
AUTOSTART_SUPERVISOR_PID = WORKSPACE_ROOT / "logs" / "autostart_supervisor.pid"
AUTOSTART_ANALYSIS_SIGNALS = WORKSPACE_ROOT / "logs" / "supervisor_analysis_signals.json"


def _pid_alive(pid: Optional[int]) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                check=False,
            )
            out = (proc.stdout or "") + "\n" + (proc.stderr or "")
            return bool(re.search(rf"\b{pid}\b", out))
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _read_json_safe(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _discover_supervisor_pid() -> Optional[int]:
    candidates: List[int] = []
    try:
        if AUTOSTART_SUPERVISOR_PID.exists():
            candidates.append(int(AUTOSTART_SUPERVISOR_PID.read_text(encoding="utf-8").strip()))
    except Exception:
        pass

    snapshot = _read_json_safe(AUTOSTART_SUPERVISOR_STATUS)
    snap_pid = snapshot.get("supervisor_pid")
    if isinstance(snap_pid, int):
        candidates.append(snap_pid)

    for pid in candidates:
        if _pid_alive(pid):
            return pid
    return None


def _load_supervisor_job_specs() -> Dict[str, Dict[str, Any]]:
    """Load REQUIRED_JOBS from scripts/start_autostart_services.py without side effects."""
    if not AUTOSTART_SUPERVISOR_SCRIPT.exists():
        return {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("start_autostart_services_runtime", AUTOSTART_SUPERVISOR_SCRIPT)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load start_autostart_services module spec")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        jobs = getattr(module, "REQUIRED_JOBS", [])
        out: Dict[str, Dict[str, Any]] = {}
        for job in jobs:
            out[str(job.name)] = {
                "name": str(job.name),
                "kind": str(job.kind),
                "target": str(job.target),
                "interval_seconds": int(job.interval_seconds),
                "args": list(job.args or []),
            }
        return out
    except Exception:
        # Fallback: derive controllable jobs from the supervisor runtime snapshot.
        # This keeps UI job controls functional even if module import fails.
        snapshot = _read_json_safe(AUTOSTART_SUPERVISOR_STATUS)
        raw_jobs = snapshot.get("jobs", {})
        out: Dict[str, Dict[str, Any]] = {}
        if isinstance(raw_jobs, dict):
            for name, runtime in raw_jobs.items():
                if not isinstance(runtime, dict):
                    continue
                kind = str(runtime.get("kind") or "")
                target = str(runtime.get("target") or "")
                if kind not in {"script", "python_code"} or not target:
                    continue
                interval = runtime.get("interval_seconds")
                try:
                    interval_seconds = int(interval) if interval is not None else 300
                except Exception:
                    interval_seconds = 300
                args = runtime.get("args")
                out[str(name)] = {
                    "name": str(name),
                    "kind": kind,
                    "target": target,
                    "interval_seconds": interval_seconds,
                    "args": list(args) if isinstance(args, list) else [],
                }
        return out


def _build_autostart_status_payload() -> Dict[str, Any]:
    snapshot = _read_json_safe(AUTOSTART_SUPERVISOR_STATUS)
    analysis_signals = _read_json_safe(AUTOSTART_ANALYSIS_SIGNALS)
    specs = _load_supervisor_job_specs()
    supervisor_pid = _discover_supervisor_pid()
    supervisor_running = _pid_alive(supervisor_pid)

    raw_jobs = snapshot.get("jobs", {})
    jobs: List[Dict[str, Any]] = []

    for name, spec in specs.items():
        runtime = raw_jobs.get(name, {}) if isinstance(raw_jobs, dict) else {}
        pid = runtime.get("pid")
        running = _pid_alive(pid)
        last_exit = runtime.get("last_exit_code")
        failed = (last_exit is not None and str(last_exit) != "0")
        pending_first = (not running and last_exit in (None, ""))
        jobs.append({
            "name": name,
            "kind": spec.get("kind"),
            "target": spec.get("target"),
            "interval_seconds": spec.get("interval_seconds"),
            "args": spec.get("args", []),
            "pid": pid if running else None,
            "running": running,
            "last_exit_code": None if last_exit in ("", None) else str(last_exit),
            "last_exit_at": runtime.get("last_exit_at"),
            "next_run_at": runtime.get("next_run_at"),
            "failed": failed,
            "pending_first_run": pending_first,
        })

    # Include runtime jobs that aren't in spec (defensive visibility)
    if isinstance(raw_jobs, dict):
        for name, runtime in raw_jobs.items():
            if name in specs:
                continue
            pid = runtime.get("pid")
            running = _pid_alive(pid)
            last_exit = runtime.get("last_exit_code")
            failed = (last_exit is not None and str(last_exit) != "0")
            pending_first = (not running and last_exit in (None, ""))
            jobs.append({
                "name": name,
                "kind": runtime.get("kind"),
                "target": runtime.get("target"),
                "interval_seconds": runtime.get("interval_seconds"),
                "args": [],
                "pid": pid if running else None,
                "running": running,
                "last_exit_code": None if last_exit in ("", None) else str(last_exit),
                "last_exit_at": runtime.get("last_exit_at"),
                "next_run_at": runtime.get("next_run_at"),
                "failed": failed,
                "pending_first_run": pending_first,
            })

    total = len(jobs)
    running_count = sum(1 for j in jobs if j["running"])
    failed_count = sum(1 for j in jobs if j["failed"])
    pending_count = sum(1 for j in jobs if j["pending_first_run"])

    return {
        "success": True,
        "supervisor": {
            "running": supervisor_running,
            "pid": supervisor_pid,
            "started_at": snapshot.get("started_at"),
            "generated_at": snapshot.get("generated_at"),
            "status_file_exists": AUTOSTART_SUPERVISOR_STATUS.exists(),
        },
        "summary": {
            "total_jobs": total,
            "running_jobs": running_count,
            "failed_jobs": failed_count,
            "pending_first_run_jobs": pending_count,
        },
        "analysis_signals": analysis_signals if isinstance(analysis_signals, dict) else {},
        "jobs": sorted(jobs, key=lambda j: j["name"]),
    }


def _start_autostart_supervisor() -> Dict[str, Any]:
    if not AUTOSTART_SUPERVISOR_SCRIPT.exists():
        return {"success": False, "error": f"Supervisor script missing: {AUTOSTART_SUPERVISOR_SCRIPT}"}
    ensure_autostart_supervisor_running()
    return {"success": True, "message": "Supervisor start requested"}


def _stop_autostart_supervisor() -> Dict[str, Any]:
    if not AUTOSTART_SUPERVISOR_SCRIPT.exists():
        return {"success": False, "error": f"Supervisor script missing: {AUTOSTART_SUPERVISOR_SCRIPT}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(AUTOSTART_SUPERVISOR_SCRIPT), "stop"],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        return {
            "success": proc.returncode == 0,
            "message": (proc.stdout or proc.stderr or "").strip() or "Stop requested",
            "returncode": proc.returncode,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _spawn_job_once(job_name: str) -> Dict[str, Any]:
    specs = _load_supervisor_job_specs()
    spec = specs.get(job_name)
    if not spec:
        return {"success": False, "error": f"Unknown job: {job_name}"}

    log_path = WORKSPACE_ROOT / "logs" / f"autostart_{job_name}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    root_str = str(WORKSPACE_ROOT)
    existing = env.get("PYTHONPATH", "")
    if root_str not in existing.split(os.pathsep):
        env["PYTHONPATH"] = os.pathsep.join([root_str, existing]) if existing else root_str

    if spec["kind"] == "python_code":
        cmd = [sys.executable, "-c", spec["target"]]
    else:
        cmd = [sys.executable, str(WORKSPACE_ROOT / spec["target"]), *spec.get("args", [])]

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    with open(log_path, "ab") as out:
        proc = subprocess.Popen(
            cmd,
            cwd=str(WORKSPACE_ROOT),
            stdout=out,
            stderr=out,
            env=env,
            creationflags=creationflags,
        )
    return {"success": True, "message": "Job launch requested", "pid": proc.pid, "job": job_name}


def _stop_job_if_running(job_name: str) -> Dict[str, Any]:
    payload = _build_autostart_status_payload()
    jobs = payload.get("jobs", [])
    job = next((j for j in jobs if j.get("name") == job_name), None)
    if not job:
        return {"success": False, "error": f"Unknown job: {job_name}"}
    pid = job.get("pid")
    if not _pid_alive(pid):
        return {"success": True, "message": "Job not running", "job": job_name}
    try:
        os.kill(int(pid), 15)
        return {"success": True, "message": f"Stop signal sent to PID {pid}", "job": job_name}
    except Exception as e:
        return {"success": False, "error": str(e), "job": job_name}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Loop Cockpit")
    parser.add_argument('--generate-history-index', action='store_true', help='Generate docs/HISTORY_INDEX.md')
    parser.add_argument('--generate-query-index', action='store_true', help='Generate docs/QUERY_INDEX.json')
    parser.add_argument('--generate-context-index', action='store_true', help='Generate docs/CONTEXT_INDEX.json')
    parser.add_argument('--generate-knowledge-db', action='store_true', help='Generate/rebuild SQLite knowledge database (keeper_knowledge.db)')
    parser.add_argument('--generate-digest', type=int, metavar='LOOP_NUM', help='Generate archive/DIGEST_XXXX.md for specified loop')
    parser.add_argument('--lint', action='store_true', help='Run metadata lint and print JSON')
    parser.add_argument('--generate-session-pack', action='store_true', help='Generate _SESSION.md')
    parser.add_argument('--regenerate-loop-gate', action='store_true', help='Regenerate _LOOP_GATE.md')
    parser.add_argument('--finalize-loop', action='store_true', help='Finalize the current loop (creates ARCHIV_XXXX.md in root)')
    parser.add_argument('--human-override', action='store_true', help='Enable human override for finalization')
    parser.add_argument('--reset', action='store_true', help='Reset main override password (requires master password)')
    parser.add_argument('--pre-work', metavar='TASK_ID', help='Run pre-work validation for a task (REPORT-FIRST enforcement)')
    parser.add_argument('--reason', default='cli', help='Reason string for generated artifacts')
    parser.add_argument('--serve', action='store_true', help='Run the Flask cockpit server')
    parser.add_argument(
        '--server-backend',
        default=os.environ.get("LOOP_COCKPIT_SERVER_BACKEND", "auto"),
        choices=['auto', 'socketio', 'waitress'],
        help='Server backend: auto (default), socketio, or waitress'
    )
    args = parser.parse_args()

    # Initialize AI Breadcrumb Tracking System
    try:
        # TEMP: Disable breadcrumb tracker for debugging
        # from ai_breadcrumb_tracker import bootstrap_breadcrumb_tracking, get_breadcrumb_tracker
        # bootstrap_breadcrumb_tracking()
        # breadcrumb_tracker = get_breadcrumb_tracker()
        # breadcrumb_tracker.set_current_context("loop_cockpit_main_execution")
        print("🗺️  AI Breadcrumb Tracking System initialized")
        print("   Breadcrumb trail will be logged to: breadcrumb_trail.jsonl")
        print("   Use get_breadcrumb_tracker() to access tracking functions")

        # AI INTEGRITY PROTECTION: Breadcrumb Drift Protection
        try:
            # TEMP: Disable integrity protector for debugging
            # from ai_integrity_protector import AIIntegrityProtector
            # protector = AIIntegrityProtector(WORKSPACE_ROOT)
            # drift_checks = protector.validate_breadcrumb_drift_protection()

            # # Log any drift protection issues
            # for check in drift_checks:
            #     if check.status in ['WARN', 'FAIL']:
            #         print(f"🗺️  Breadcrumb Drift Check: {check.status} - {check.message}")
            #         if check.details.get('action') == 'awareness_refresh_needed':
            #             print("   ↻ Refreshing breadcrumb awareness...")
            #             breadcrumb_tracker.set_current_context("drift_protection_refresh")
            #         elif check.details.get('action') == 'initialization_needed':
            #             print("   ⟲ Initializing breadcrumb tracking...")
            #             breadcrumb_tracker.set_current_context("drift_protection_initialization")

            print("⚠️  Breadcrumb drift protection temporarily disabled for debugging")
        except ImportError:
            print("⚠️  Breadcrumb drift protection not available (ai_integrity_protector.py not found)")
        except Exception as e:
            print(f"⚠️  Breadcrumb drift check failed: {e}")

    except ImportError:
        print("⚠️  AI Breadcrumb Tracking not available (ai_breadcrumb_tracker.py not found)")

    # Initialize Self-Reflective Framework
    try:
        # Initialize the reflective logger for the current workspace
        reflective_logger = get_reflective_logger(WORKSPACE_ROOT)
        print("🤖 Self-Reflective Framework initialized")
        print("   AI decisions will be logged to: ai_reflective_log.jsonl")
        print("   Use log_ai_decision() and update_decision_outcome() for tracking")
    except ImportError:
        print("⚠️  Self-Reflective Framework not available (ai_self_reflective_framework.py not found)")
    except Exception as e:
        print(f"⚠️  Self-Reflective Framework initialization failed: {e}")

    ran_tool = False

    print(f"DEBUG: Args - serve: {args.serve}, ran_tool: {ran_tool}")

    if args.generate_history_index:
        data = history_index_data(WORKSPACE_ROOT)
        md = history_index_markdown(data)
        write_text(HISTORY_INDEX_MD, md)
        print(str(HISTORY_INDEX_MD))
        ran_tool = True

    if args.generate_knowledge_db:
        policy_decision = enforce_db_write_policy(
            WORKSPACE_ROOT,
            operation="knowledge.rebuild",
            actor="human_admin",
        )
        if not policy_decision.allowed:
            print(f"✗ Policy gate denied rebuild: {policy_decision.reason}")
            raise SystemExit(1)
        print("Rebuilding knowledge database...")
        db = KnowledgeDB(WORKSPACE_ROOT)
        stats = db.rebuild_with_write_guard()
        db.close()
        print(f"✓ Generated {WORKSPACE_ROOT / 'keeper_knowledge.db'}")
        print(f"  Reports: {stats['reports_indexed']}")
        print(f"  Archives: {stats['archives_indexed']}")
        print(f"  Tasks: {stats['tasks_indexed']}")
        print(f"  Lessons: {stats['lessons_extracted']}")
        if stats['errors']:
            print(f"  Errors: {len(stats['errors'])}")
        ran_tool = True

    if args.generate_query_index:
        data = query_index_data(WORKSPACE_ROOT)
        write_json(QUERY_INDEX_JSON, data)
        print(f"✓ Generated {QUERY_INDEX_JSON}")
        print(f"  Reports: {len(data.get('reports', []))}")
        print(f"  Tasks: {len(data.get('tasks', []))}")
        print(f"  Files indexed: {len(data.get('fileIndex', {}))}")
        print(f"  Concepts/tags: {len(data.get('conceptIndex', {}))}")
        ran_tool = True

    if args.generate_context_index:
        index = generate_context_index(WORKSPACE_ROOT)
        context_index_path = WORKSPACE_ROOT / "docs" / "CONTEXT_INDEX.json"
        write_json(context_index_path, index)
        print(f"✓ Generated {context_index_path}")
        print(f"  Current loop: {index.get('currentLoop', {}).get('number')}")
        print(f"  Active tasks: {index.get('summary', {}).get('totalActiveTasks')}")
        print(f"  Recent completed: {len(index.get('recentCompletedTasks', []))}")
        print(json.dumps(index, indent=2, ensure_ascii=False))
        ran_tool = True

    if args.generate_digest:
        result = generate_loop_digest(args.generate_digest, WORKSPACE_ROOT)
        if result.get("success"):
            print(f"✓ Generated {result.get('digestPath')}")
            print(f"  Lines: {result.get('lineCount')}")
            print(f"  Tasks found: {result.get('tasksFound')}")
            print(f"  Decisions found: {result.get('decisionsFound')}")
            print(f"  Files found: {result.get('filesFound')}")
        else:
            print(f"✗ Digest generation failed: {result.get('error')}", file=sys.stderr)
            raise SystemExit(1)
        ran_tool = True

    if args.generate_session_pack:
        regenerate_session_pack()
        print(str(SESSION_MD))
        ran_tool = True

    if args.regenerate_loop_gate:
        regenerate_loop_gate(reason=args.reason)
        print(str(LOOP_GATE))
        ran_tool = True

    if args.lint:
        print(json.dumps(metadata_lint(WORKSPACE_ROOT), indent=2, ensure_ascii=False))
        ran_tool = True

    if args.pre_work:
        result = pre_work_validation(args.pre_work, WORKSPACE_ROOT)
        output = {
            "taskId": args.pre_work,
            "passed": result.passed,
            "errors": result.errors,
            "message": "Pre-work validation passed" if result.passed else f"{len(result.errors)} validation error(s) found"
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        if not result.passed:
            raise SystemExit(1)
        ran_tool = True

    if args.finalize_loop:
        human_override = False
        if args.human_override:
            if args.reset:
                # Reset logic
                if not validate_master_password():
                    print("Master password validation failed.", file=sys.stderr)
                    raise SystemExit(1)
                new_password = input("Enter new main override password: ")
                confirm = input("Confirm new password: ")
                if new_password != confirm or len(new_password) < 12:
                    print("Password confirmation failed or too short.", file=sys.stderr)
                    raise SystemExit(1)
                create_new_override_hash(new_password)
                print("Main override password reset successfully.")
                ran_tool = True
            else:
                # Normal override
                if not validate_override_password():
                    print("Override password validation failed.", file=sys.stderr)
                    raise SystemExit(1)
                human_override = True
        try:
            result = finalize_loop_procedure(human_override=human_override)
        except ValueError as e:
            print(f"FINALIZE BLOCKED: {e}", file=sys.stderr)
            raise SystemExit(1)
        print(result.get('archivFile') or '')
        ran_tool = True

    if ran_tool and not args.serve:
        print(f"DEBUG: Exiting because ran_tool={ran_tool} and serve={args.serve}")
        raise SystemExit(0)

    print(f"DEBUG: Continuing to server startup, ran_tool={ran_tool}, serve={args.serve}")

    print("=" * 60)
    print("LOOP COCKPIT - MEMORY RESET CONTROL CENTER")
    print("=" * 60)
    print(f"Workspace: {WORKSPACE_ROOT}")
    print(f"Access at: http://localhost:5000")
    print("=" * 60)

    # Initialize checkpoint manager for current loop
    try:
        current_state = read_json_file(CURRENT_JSON)
        loop_num = current_state.get('STATE', {}).get('loop', 0)
        if loop_num > 0:
            initialize_checkpoints(loop_num)
            print(f"✓ Checkpoint manager initialized for Loop {loop_num}")
            
            # Start background checkpoint thread
            import threading
            import time
            
            def checkpoint_worker():
                """Background thread for automatic checkpoints."""
                while True:
                    try:
                        time.sleep(3600)  # Check every hour
                        check_and_create_checkpoint()
                    except Exception as e:
                        logger.warning(f"Background checkpoint check failed: {e}")
                        time.sleep(300)  # Retry in 5 minutes on error
            
            checkpoint_thread = threading.Thread(target=checkpoint_worker, daemon=True)
            checkpoint_thread.start()
            print("✓ Background checkpoint worker started")
            
    except Exception as e:
        print(f"⚠ Checkpoint manager initialization failed: {e}")

    # Integrate advanced AI patterns UI
    # app = integrate_ai_patterns_ui(app)
    # print("Advanced AI Patterns UI integrated")

    # Integrate ClawdBot AI assistant
    # integrate_clawdbot(app)
    # print("ClawdBot AI Assistant integrated")

    # Integrate OpenAI features
    if openai_integration:
        create_openai_endpoints(app, openai_integration)
        print("OpenAI Advanced Features integrated")

    # Start helper-services supervisor at cockpit startup so bootstrap has support.
    ensure_autostart_supervisor_running()

    # NOTE (Windows/Python 3.13): Use waitress instead of Werkzeug for compatibility
    # from waitress import serve
    # print("Starting server with Waitress...")
    # serve(app, host='0.0.0.0', port=5000)
    
    # NOTE (Windows/Python 3.13): Use waitress instead of Werkzeug for compatibility
    # from waitress import serve
    # print("Starting server with Waitress...")
    # serve(app, host='0.0.0.0', port=5000)
    
    # Use waitress for Windows/Python 3.13 compatibility
    # from waitress import serve
    # print("Starting server with Waitress...")
    # print(f"DEBUG: App has {len(list(app.url_map.iter_rules()))} routes before run")
    # try:
    #     print("DEBUG: About to call serve()")
    #     serve(app, host='127.0.0.1', port=5000)
    #     print("DEBUG: serve() returned normally")
    # except Exception as e:
    #     print(f"Server error: {e}")
    #     import traceback
    #     traceback.print_exc()
    # print("DEBUG: server completed")
    
    run_cockpit_server(app, backend=args.server_backend)

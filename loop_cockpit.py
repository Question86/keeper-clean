#!/usr/bin/env python3
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
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

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
    query_index_data,
    write_text,
    write_json,
    check_archive_consistency,
    pre_work_validation,
    sync_task_status,
    list_task_spec_files,
    read_text,
    utc_now_iso,
    TASK_ID_RE,
)

app = Flask(__name__)
CORS(app)

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

# State machine constants
STATE_READY_FOR_RESET = "READY_FOR_RESET"
STATE_ACTIVE = "ACTIVE"
STATE_FINALIZED = "FINALIZED"

# Thread lock for atomic state transitions
_state_lock = threading.Lock()


# Thread lock for atomic state transitions
_state_lock = threading.Lock()


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
    """Regenerate _LOOP_GATE.md deterministically (cockpit automation)."""
    gate = generate_loop_gate(WORKSPACE_ROOT, checked_by="loop_cockpit", reason=reason)
    write_text(LOOP_GATE, gate["content"])
    return gate


def regenerate_session_pack() -> str:
    """Regenerate the compact session context pack (_SESSION.md)."""
    content = session_pack_markdown(WORKSPACE_ROOT)
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
    """Write JSON file with formatting."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')

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
        
        # CHECK 1: If lastTaskWorked is set, verify report exists
        if last_task and last_task != 'None':
            expected_report_pattern = f"report_{last_task}_L{loop_num:02d}_"
            matching_reports = [r for r in loop_reports if expected_report_pattern in r]
            
            if not matching_reports:
                issues.append(f"VIOLATION: lastTaskWorked='{last_task}' but no matching report file found (expected: {expected_report_pattern}vNN.md)")
        
        # CHECK 2: If no task claimed, reports must not exist (prevents ARCHIV "Last Task Worked: None" mismatches)
        if (not last_task or last_task == 'None') and loop_reports:
            inferred = infer_last_task_from_reports(loop_num)
            issues.append(
                f"VIOLATION: lastTaskWorked=None but {len(loop_reports)} report(s) exist for Loop {loop_num}. "
                f"Set lastTaskWorked (suggested: {inferred or 'unknown'}) before finalization. Reports: {', '.join(loop_reports)}"
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
        if status != 'ACTIVE':
            issues.append(f"ERROR: current.json status is '{status}', must be 'ACTIVE' to finalize")
        
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

def create_bootstrap_file(loop_num, last_task):
    """Create _BOOTSTRAP.md file for fresh session entry."""
    bootstrap_path = WORKSPACE_ROOT / "_BOOTSTRAP.md"
    
    content = f"""# BOOTSTRAP - NEW SESSION ENTRY POINT

MODE: EPHEMERAL (DELETE AFTER USE)
CREATED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

**PURPOSE:** This file signals a fresh loop start and guides session entry.

---

## INSTRUCTIONS FOR HUMAN

You are starting a new loop session. Follow these steps:

1. **Start a new chat window** (fresh AI session with amnesia)
2. **Point AI to this file first:** "Read _BOOTSTRAP.md"
3. **AI will auto-discover project state** and begin work
4. **This file will self-delete** after successful entry

---

## INSTRUCTIONS FOR AI

Execute this sequence in order:

### STEP 1: Validate Entry Gate
Read [ref:_LOOP_GATE.md#STATUS|v:current|tags:validator|src:system]
- If STATUS = BLOCKED → STOP and report violations
- If STATUS = PASS → Continue to Step 2

### STEP 2: Load Loop State
Read [ref:current.json#STATE|v:dynamic|tags:state|src:system]
- Extract: loop number, status, last task, archive refs
- Confirm loop is ACTIVE or READY_FOR_RESET

### STEP 3: Load Project Map
Read [ref:NEURAL_CORTEX.md#ENTRY PROTOCOL|v:dynamic|tags:cortex|src:system]
- Understand project axis and navigation
- Load pointer map

### STEP 4: Discover Active Task
Read [ref:NEU.md#TASK QUEUE|v:dynamic|tags:active|src:system]
- Identify highest priority task
- Confirm task spec file exists

### STEP 5: Load Project Laws
Read [ref:PROJECT_TECH_BASELINE.md#UNIVERSAL LAWS|v:immutable|tags:baseline|src:system]
- Internalize non-negotiable rules
- Understand document structure requirements

### STEP 5.5: Load Operational Protocols
Read [ref:docs/OPS_PROTOCOLS.md#INDEX|v:1|tags:ops|src:doc]
- Understand finalization procedures
- Review task creation and reference management rules

### STEP 6: Self-Destruct
**DELETE THIS FILE** after successful completion of steps 1-5.

### STEP 7: Begin Work
Announce to human:
- "Loop [N] entry complete. Current task: [TASK_ID]"
- "Gate status: PASS. Ready to begin work."

**AUTONOMOUS EXECUTION MODE:**
Work through all tasks in NEU.md autonomously until:
- All tasks are completed and moved to Alt.md, OR
- All UNIVERSAL LAWS are satisfied and no actionable work remains, OR
- You encounter a blocker requiring human intervention

Follow all rules, create reports for all work, and proceed systematically through the task queue without waiting for additional prompts unless blocked or requiring clarification.

---

## LOOP CONTEXT (REFERENCE)

**Current Loop:** {loop_num}
**Last Task Worked:** {last_task or 'None'}
**Next Task:** See NEU.md for current priority

**Archive Status:**
- Loop {loop_num - 1} archived
- Fresh memory reset executed

---

## VALIDATION CHECKPOINT

Before deleting this file, confirm:
- [ ] _LOOP_GATE.md status = PASS
- [ ] current.json loaded successfully
- [ ] NEURAL_CORTEX.md structure understood
- [ ] NEU.md active task identified (or empty for initial)
- [ ] PROJECT_TECH_BASELINE.md laws internalized
- [ ] docs/OPS_PROTOCOLS.md operational procedures reviewed

If any checkpoint fails → STOP and report issue.

---

END OF DOCUMENT
"""
    
    with open(bootstrap_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return bootstrap_path.exists()

@app.route('/')
def index():
    """Serve the cockpit UI."""
    return render_template('cockpit.html', cockpit_build=COCKPIT_BUILD)

@app.route('/api/status')
def get_status():
    """Get current project status and stats."""
    current_state = read_json_file(CURRENT_JSON)
    milestone_data = read_json_file(MILESTONE)
    issues_data = read_json_file(KNOWN_ISSUES)
    
    # Check if bootstrap exists
    bootstrap_exists = (WORKSPACE_ROOT / "_BOOTSTRAP.md").exists()
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
    
    # Count archives
    archive_count = len(get_archive_files())
    
    # Calculate uptime (time since last update)
    try:
        last_update = datetime.fromisoformat(current_state['STATE']['lastUpdate'].replace('Z', '+00:00'))
        uptime_seconds = (datetime.now() - last_update.replace(tzinfo=None)).total_seconds()
        uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"
    except:
        uptime_str = "Unknown"
    
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
        "summary": current_state.get('STATE', {}).get('summary', ''),
        "transitionHint": transition_hint
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

        # 7. Regenerate gate deterministically (between loops)
        regenerate_loop_gate(reason="reset-loop")
        
        return jsonify({
            "success": True,
            "phase": "awaiting_execution",
            "newLoop": current_loop + 1,
            "bootstrap_command": "Read _BOOTSTRAP.md",
            "message": "Loop reset prepared. Close chat and start new session."
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
            "blocked": True
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def finalize_loop_procedure(last_task_override=None) -> dict:
    """Finalize loop (shared by API + CLI). Raises ValueError when blocked."""

    current_state = read_json_file(CURRENT_JSON)

    if current_state.get('STATE', {}).get('status') != 'ACTIVE':
        raise ValueError("Loop must be ACTIVE to finalize")

    # Pre-finalization validations
    is_valid, issues, warnings = audit_loop_integrity()
    consistency_result = check_archive_consistency(WORKSPACE_ROOT)
    lint = metadata_lint(WORKSPACE_ROOT)
    lint_errors = lint.get('errors', [])

    if not is_valid:
        raise ValueError("Pre-finalization audit FAILED - REPORT-FIRST LAW violations detected")
    if not consistency_result.get('is_consistent', False):
        raise ValueError("Pre-finalization consistency check FAILED - desync risks detected")
    if lint_errors:
        raise ValueError("Pre-finalization lint FAILED - structural violations detected")

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

    current_state['STATE']['status'] = 'FINALIZED'
    current_state['STATE']['archiveInProgress'] = archiv_name
    current_state['STATE']['lastUpdate'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    current_state['STATE']['lastTaskWorked'] = last_task
    current_state['STATE']['summary'] = f"Loop {loop_num} finalized. ARCHIV_{loop_num:04d}.md created in root."
    write_json_file(CURRENT_JSON, current_state)

    regenerate_loop_gate(reason="finalize-loop")

    combined_warnings = []
    if warnings:
        combined_warnings.extend(warnings)
    if consistency_result.get('warnings'):
        combined_warnings.extend(consistency_result.get('warnings'))
    if lint.get('warnings'):
        combined_warnings.extend([f"{w['code']}: {w['message']}" for w in lint.get('warnings', [])])

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
    try:
        def check_preconditions(current_state):
            """Validate preconditions for bootstrap confirmation."""
            # Permissive check: allow transition even if bootstrap still exists
            # (supports manual recovery scenarios)
            return True, None
        
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
        
        # Generate session context pack for the new ACTIVE loop
        try:
            regenerate_session_pack()
        except Exception as e:
            # Non-fatal: session pack generation failure shouldn't block transition
            log_state_transition(STATE_ACTIVE, STATE_ACTIVE, "session-pack", "FAILED", str(e))
        
        # Regenerate loop gate for ACTIVE entry validation
        try:
            regenerate_loop_gate(reason="confirm-bootstrap")
        except Exception as e:
            # Non-fatal: gate regeneration failure shouldn't block transition
            log_state_transition(STATE_ACTIVE, STATE_ACTIVE, "loop-gate", "FAILED", str(e))
        
        state = result["state"]
        loop_num = state.get('STATE', {}).get('loop', 0)
        
        return jsonify({
            "success": True,
            "message": "Bootstrap confirmed. Loop is now ACTIVE." if not result.get("idempotent") else "Already ACTIVE (idempotent call).",
            "loop": loop_num,
            "status": STATE_ACTIVE,
            "idempotent": result.get("idempotent", False),
            "timestamp": state.get('STATE', {}).get('lastUpdate', '')
        })

    except Exception as e:
        log_state_transition("UNKNOWN", STATE_ACTIVE, "confirm-bootstrap", "EXCEPTION", str(e))
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
        
        if not task_ids:
            return jsonify({
                "success": False,
                "error": "taskIds list is required"
            }), 400
        
        result = orch.execute_parallel(
            task_ids=task_ids,
            auto_merge=auto_merge,
            auto_cleanup=auto_cleanup
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
    """Submit a new seed idea and create task stub."""
    try:
        data = request.get_json(silent=True) or {}
        idea = (data.get('idea') or '').strip()
        
        if not idea:
            return jsonify({
                "success": False,
                "error": "Idea cannot be empty"
            }), 400
        
        # Load pointer docs (used for NEU insertion + legacy numbering fallback)
        neu_content = read_text_file(NEU_MD)
        alt_content = read_text_file(ALT_MD)

        # Determine next task id using the real filesystem as source of truth.
        # This prevents overwriting a task spec that exists but is not referenced ("lost" tasks).
        import re

        task_numbers = set()

        # 1) Existing task spec files (root + tasks/)
        for p in WORKSPACE_ROOT.glob('task_TASK_*.md'):
            m = re.search(r'TASK_(\d+)', p.name)
            if m:
                task_numbers.add(int(m.group(1)))

        tasks_dir = WORKSPACE_ROOT / 'tasks'
        if tasks_dir.exists():
            for p in tasks_dir.glob('task_TASK_*.md'):
                m = re.search(r'TASK_(\d+)', p.name)
                if m:
                    task_numbers.add(int(m.group(1)))

        # 2) Fallback: referenced IDs in NEU/Alt (covers edge cases where a task ref exists but file was deleted)
        for content in (neu_content, alt_content):
            for m in re.findall(r'TASK_(\d+)', content):
                try:
                    task_numbers.add(int(m))
                except Exception:
                    pass

        next_task_num = (max(task_numbers) if task_numbers else 0) + 1

        # Find an unused task id (avoid collisions across both legacy root and tasks/)
        while True:
            task_id = f"TASK_{next_task_num:04d}"
            candidate_root = WORKSPACE_ROOT / f"task_{task_id}.md"
            candidate_tasks = tasks_dir / f"task_{task_id}.md"
            if candidate_root.exists() or candidate_tasks.exists():
                next_task_num += 1
                continue
            break
        
        # Create task file (prefer tasks/ folder; keep legacy root tasks in place)
        tasks_dir.mkdir(parents=True, exist_ok=True)
        task_file = tasks_dir / f"task_{task_id}.md"
        task_content = f"""# {task_id}

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

---

## SEED IDEA

{idea}

---

## OBJECTIVE

[Derive concrete, measurable objectives from SEED IDEA above. Specify what will be built/fixed/analyzed.]

---

## TASK_TYPE

[ANALYSIS|IMPLEMENTATION|MAINTENANCE]

---

## ACCEPTANCE CRITERIA

[Define checkable criteria. For IMPLEMENTATION tasks, specify files to be modified with evidence of changes.]

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT
"""
        
        # Use exclusive create to guarantee we never overwrite an existing task spec.
        with open(task_file, 'x', encoding='utf-8') as f:
            f.write(task_content)
        
        # Add reference to NEU.md
        neu_lines = neu_content.split('\n')

        task_ref_path = f"tasks/task_{task_id}.md"
        task_ref = f"[ref:{task_ref_path}|v:1|tags:new|src:user] - {idea[:80]}{'...' if len(idea) > 80 else ''}"

        # Insert under the TASK QUEUE header (preferred)
        insert_idx = None
        for i, line in enumerate(neu_lines):
            if line.strip().startswith('## TASK QUEUE'):
                insert_idx = i + 2  # leave a blank line after the header
                break

        if insert_idx is not None:
            # If the queue is marked empty, replace the empty marker.
            for j in range(insert_idx, min(insert_idx + 5, len(neu_lines))):
                if '(Empty - all tasks completed)' in neu_lines[j]:
                    neu_lines[j] = task_ref
                    neu_lines.insert(j + 1, '')
                    break
            else:
                neu_lines.insert(insert_idx, task_ref)
                neu_lines.insert(insert_idx + 1, '')
        else:
            # Fallback: append near the end
            neu_lines.append('')
            neu_lines.append(task_ref)
        
        with open(NEU_MD, 'w', encoding='utf-8') as f:
            f.write('\n'.join(neu_lines))
        
        return jsonify({
            "success": True,
            "message": f"Task {task_id} created successfully",
            "taskId": task_id,
            "taskFile": task_ref_path
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Loop Cockpit")
    parser.add_argument('--generate-history-index', action='store_true', help='Generate docs/HISTORY_INDEX.md')
    parser.add_argument('--generate-query-index', action='store_true', help='Generate docs/QUERY_INDEX.json')
    parser.add_argument('--generate-context-index', action='store_true', help='Generate docs/CONTEXT_INDEX.json')
    parser.add_argument('--generate-digest', type=int, metavar='LOOP_NUM', help='Generate archive/DIGEST_XXXX.md for specified loop')
    parser.add_argument('--lint', action='store_true', help='Run metadata lint and print JSON')
    parser.add_argument('--generate-session-pack', action='store_true', help='Generate _SESSION.md')
    parser.add_argument('--regenerate-loop-gate', action='store_true', help='Regenerate _LOOP_GATE.md')
    parser.add_argument('--finalize-loop', action='store_true', help='Finalize the current loop (creates ARCHIV_XXXX.md in root)')
    parser.add_argument('--pre-work', metavar='TASK_ID', help='Run pre-work validation for a task (REPORT-FIRST enforcement)')
    parser.add_argument('--reason', default='cli', help='Reason string for generated artifacts')
    parser.add_argument('--serve', action='store_true', help='Run the Flask cockpit server')
    args = parser.parse_args()

    ran_tool = False

    if args.generate_history_index:
        data = history_index_data(WORKSPACE_ROOT)
        md = history_index_markdown(data)
        write_text(HISTORY_INDEX_MD, md)
        print(str(HISTORY_INDEX_MD))
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
        try:
            result = finalize_loop_procedure()
        except ValueError as e:
            print(f"FINALIZE BLOCKED: {e}", file=sys.stderr)
            raise SystemExit(1)
        print(result.get('archivFile') or '')
        ran_tool = True

    if ran_tool and not args.serve:
        raise SystemExit(0)

    print("=" * 60)
    print("🚀 LOOP COCKPIT - MEMORY RESET CONTROL CENTER")
    print("=" * 60)
    print(f"Workspace: {WORKSPACE_ROOT}")
    print(f"Access at: http://localhost:5000")
    print("=" * 60)
    # NOTE (Windows/Python 3.13): Werkzeug's watchdog reloader can crash with
    # TypeError: 'handle' must be a _ThreadHandle. Disable reloader for stability.
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

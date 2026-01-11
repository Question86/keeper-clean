#!/usr/bin/env python3
"""
Loop Cockpit - Memory Reset Control Center
Provides a web-based UI for managing loop lifecycle and monitoring project state.
"""

import json
import os
import shutil
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from loop_guardrails import (
    generate_loop_gate,
    history_index_data,
    history_index_markdown,
    metadata_lint,
    session_pack_markdown,
    query_index_data,
    write_text,
)

app = Flask(__name__)
CORS(app)

# Used to verify that the browser is running the latest cockpit HTML/JS.
COCKPIT_BUILD = "L28-TASK_0046-v03-hierarchy-height"

# Project paths
WORKSPACE_ROOT = Path(__file__).parent
CURRENT_JSON = WORKSPACE_ROOT / "current.json"
NEU_MD = WORKSPACE_ROOT / "NEU.md"
ALT_MD = WORKSPACE_ROOT / "Alt.md"
LOOP_GATE = WORKSPACE_ROOT / "_LOOP_GATE.md"
ARCHIVE_DIR = WORKSPACE_ROOT / "archive"
MILESTONE = WORKSPACE_ROOT / "milestone_01.json"
KNOWN_ISSUES = WORKSPACE_ROOT / "knownissues.json"

SESSION_MD = WORKSPACE_ROOT / "_SESSION.md"
HISTORY_INDEX_MD = WORKSPACE_ROOT / "docs" / "HISTORY_INDEX.md"
QUERY_INDEX_JSON = WORKSPACE_ROOT / "docs" / "QUERY_INDEX.json"


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
    """Count task references in a markdown file."""
    try:
        content = read_text_file(filepath)
        # Count lines that look like task references (contain TASK_)
        lines = [l for l in content.split('\n') if 'TASK_' in l and not l.strip().startswith('#')]
        return len(lines)
    except:
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
        
        # Construct result
        is_valid = len(issues) == 0
        
        return (is_valid, issues, warnings)
        
    except Exception as e:
        issues.append(f"AUDIT ERROR: {str(e)}")
        return (False, issues, warnings)

def check_archive_consistency():
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
    
    # Legacy archives with different format (exempt from structure validation)
    LEGACY_ARCHIVES = [1, 2, 3]
    
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
        current_loop = 13  # Default
        try:
            with open(CURRENT_JSON, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                current_loop = state_data.get('STATE', {}).get('loop', 13)
        except:
            pass
        
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
    
    # CRITICAL: Check if bootstrap has been deleted (loop entry completed)
    bootstrap_exists = (WORKSPACE_ROOT / "_BOOTSTRAP.md").exists()
    status = current_state.get('STATE', {}).get('status', 'UNKNOWN')
    loop_num = current_state.get('STATE', {}).get('loop', 0)
    
    # State transition hints (NO AUTO-TRANSITION - deterministic entry required)
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
        "loop": current_state.get('STATE', {}).get('loop', 0),
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
        consistency_result = check_archive_consistency()

        # Metadata + consistency lint (drift detection)
        lint = metadata_lint(WORKSPACE_ROOT)
        lint_errors = [f"{e['code']}: {e['message']} (hint: {e.get('hint','')})" for e in lint.get('errors', [])]
        lint_warnings = [f"{w['code']}: {w['message']} (hint: {w.get('hint','')})" for w in lint.get('warnings', [])]
        
        # Combine results
        all_issues = issues + consistency_result['issues'] + lint_errors
        all_warnings = warnings + consistency_result['warnings'] + lint_warnings
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
    consistency_result = check_archive_consistency()
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
    """Confirm that bootstrap has been executed in new chat session (Phase 2)."""
    try:
        current_state = read_json_file(CURRENT_JSON)
        
        # Check if we're in READY_FOR_RESET state
        if current_state.get('STATE', {}).get('status') != 'READY_FOR_RESET':
            return jsonify({
                "success": False,
                "error": "Loop is not in READY_FOR_RESET state"
            }), 400
        
        # Update state to ACTIVE (new loop has started)
        current_state['STATE']['status'] = 'ACTIVE'
        current_state['STATE']['lastUpdate'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        current_state['STATE']['summary'] = f"Loop {current_state['STATE']['loop']} active and operational."
        
        write_json_file(CURRENT_JSON, current_state)

        # Generate session context pack for the new ACTIVE loop
        regenerate_session_pack()

        # Regenerate loop gate for ACTIVE entry validation
        regenerate_loop_gate(reason="confirm-bootstrap")
        
        return jsonify({
            "success": True,
            "message": "Bootstrap confirmed. Cockpit updated to active loop state.",
            "loop": current_state['STATE']['loop'],
            "status": "ACTIVE"
        })

    except Exception as e:
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

[To be defined by AI]

---

## ACCEPTANCE CRITERIA

- [ ] [To be defined]

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
    parser.add_argument('--lint', action='store_true', help='Run metadata lint and print JSON')
    parser.add_argument('--generate-session-pack', action='store_true', help='Generate _SESSION.md')
    parser.add_argument('--regenerate-loop-gate', action='store_true', help='Regenerate _LOOP_GATE.md')
    parser.add_argument('--finalize-loop', action='store_true', help='Finalize the current loop (creates ARCHIV_XXXX.md in root)')
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
        from loop_guardrails import write_json
        data = query_index_data(WORKSPACE_ROOT)
        write_json(QUERY_INDEX_JSON, data)
        print(f"✓ Generated {QUERY_INDEX_JSON}")
        print(f"  Reports: {len(data.get('reports', []))}")
        print(f"  Tasks: {len(data.get('tasks', []))}")
        print(f"  Files indexed: {len(data.get('fileIndex', {}))}")
        print(f"  Concepts/tags: {len(data.get('conceptIndex', {}))}")
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

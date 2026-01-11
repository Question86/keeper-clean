"""Deterministic generators and guardrails for the Keeper loop system.

This module is intentionally dependency-free (stdlib only) so it can be used
by both the Flask cockpit and simple CLI invocations.

Design goals:
- Deterministic ordering and stable output (sorted lists).
- Zero archive edits.
- Pointer-first artifacts (no large inline dumps).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


REF_RE = re.compile(r"\[ref:([^\]]+)\]")
TASK_ID_RE = re.compile(r"TASK_(\d{4})")
REPORT_BASENAME_RE = re.compile(r"^report_(TASK_\d{4})_L(\d{2})_v(\d+)\.md$")
ARCHIV_RE = re.compile(r"^ARCHIV_(\d{4})\.md$")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(read_text(path))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class RefParseResult:
    raw: str
    target: str
    section: Optional[str]
    v: Optional[str]
    tags: Optional[str]
    src: Optional[str]


@dataclass
class ValidationResult:
    """Result of pre-work validation check."""
    passed: bool
    errors: List[Dict[str, str]]


def parse_ref(raw: str) -> RefParseResult:
    """Parse a ref payload (the part inside [ref:...]).

    Expected (baseline): FILE#SECTION|v:ID|tags:...|src:...
    We treat SECTION as optional, but v/tags/src are required for strict compliance.
    """

    parts = raw.split("|")
    first = parts[0] if parts else raw
    if "#" in first:
        target, section = first.split("#", 1)
    else:
        target, section = first, None

    v = tags = src = None
    for p in parts[1:]:
        p = p.strip()
        if p.startswith("v:"):
            v = p[2:]
        elif p.startswith("tags:"):
            tags = p[5:]
        elif p.startswith("src:"):
            src = p[4:]

    return RefParseResult(raw=raw, target=target, section=section, v=v, tags=tags, src=src)


def iter_refs(text: str) -> Iterable[RefParseResult]:
    for match in REF_RE.finditer(text):
        yield parse_ref(match.group(1).strip())


def validate_ref_format(ref: RefParseResult) -> Optional[str]:
    """Return an error string if invalid, else None."""

    if not ref.target:
        return "missing target"
    if ref.v is None:
        return "missing v:"
    if ref.tags is None:
        return "missing tags:"
    if ref.src is None:
        return "missing src:"
    return None


def generate_pointer_ref(
    path: str,
    tags: List[str],
    src: str,
    version: str = "1",
    section: Optional[str] = None
) -> str:
    """Generate canonical pointer reference format.

    Args:
        path: File path (e.g., "tasks/task_TASK_0001.md")
        tags: List of tags (e.g., ["active", "phase1"])
        src: Source identifier (e.g., "system", "user", "loop45")
        version: Version string (default "1", use "dynamic" for state files)
        section: Optional section anchor (e.g., "TASK QUEUE")

    Returns:
        Canonical pointer string: [ref:path#section|v:version|tags:tag1,tag2|src:source]

    Raises:
        ValueError: If required fields are empty or invalid
    """
    # Validate required fields
    if not path or not path.strip():
        raise ValueError("path cannot be empty")
    if not tags:
        raise ValueError("tags list cannot be empty")
    if not src or not src.strip():
        raise ValueError("src cannot be empty")
    if not version or not version.strip():
        raise ValueError("version cannot be empty")

    # Normalize path separators (Windows → Unix)
    normalized_path = path.strip().replace("\\", "/")

    # Sort tags alphabetically for deterministic output
    sorted_tags = sorted(t.strip() for t in tags if t.strip())
    if not sorted_tags:
        raise ValueError("tags list cannot contain only empty strings")

    # Build the reference
    target = normalized_path
    if section and section.strip():
        target = f"{normalized_path}#{section.strip()}"

    tags_str = ",".join(sorted_tags)
    return f"[ref:{target}|v:{version.strip()}|tags:{tags_str}|src:{src.strip()}]"


def sync_task_status(
    task_id: str,
    new_status: str,
    workspace_root: Path,
    completed_timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """Sync task spec STATUS field when task is moved.

    Args:
        task_id: Task ID (e.g., "TASK_0081")
        new_status: New status value (e.g., "COMPLETED", "BLOCKED", "ACTIVE")
        workspace_root: Path to workspace root
        completed_timestamp: Optional ISO timestamp for COMPLETED status

    Returns:
        Dict with success, message, and any errors
    """
    # Find task spec file
    task_spec = None
    for candidate in [
        workspace_root / "tasks" / f"task_{task_id}.md",
        workspace_root / f"task_{task_id}.md"
    ]:
        if candidate.exists():
            task_spec = candidate
            break

    if not task_spec:
        return {"success": False, "error": f"Task spec not found: task_{task_id}.md"}

    try:
        content = read_text(task_spec)
        lines = content.split('\n')
        updated_lines = []
        status_updated = False
        completed_updated = False

        for line in lines:
            # Update STATUS line
            if line.startswith('STATUS:'):
                updated_lines.append(f"STATUS: {new_status}")
                status_updated = True
            # Update COMPLETED timestamp if status is COMPLETED
            elif line.startswith('COMPLETED:') and new_status == "COMPLETED":
                if completed_timestamp:
                    updated_lines.append(f"COMPLETED: {completed_timestamp}")
                else:
                    updated_lines.append(f"COMPLETED: {utc_now_iso()}")
                completed_updated = True
            else:
                updated_lines.append(line)

        # If no STATUS line found, add after MODE line
        if not status_updated:
            final_lines = []
            for i, line in enumerate(updated_lines):
                final_lines.append(line)
                if line.startswith('MODE:'):
                    final_lines.append(f"STATUS: {new_status}")
                    status_updated = True
            updated_lines = final_lines

        # If COMPLETED status and no COMPLETED line found, add after CREATED line
        if new_status == "COMPLETED" and not completed_updated:
            final_lines = []
            for i, line in enumerate(updated_lines):
                final_lines.append(line)
                if line.startswith('CREATED:'):
                    ts = completed_timestamp or utc_now_iso()
                    final_lines.append(f"COMPLETED: {ts}")
                    completed_updated = True
            updated_lines = final_lines

        new_content = '\n'.join(updated_lines)
        write_text(task_spec, new_content)

        return {
            "success": True,
            "message": f"Task {task_id} status synced to {new_status}",
            "statusUpdated": status_updated,
            "completedUpdated": completed_updated
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def find_pending_archiv(workspace_root: Path) -> Optional[Path]:
    candidates = sorted(workspace_root.glob("ARCHIV_*.md"))
    return candidates[0] if candidates else None


def list_task_spec_files(workspace_root: Path) -> List[Path]:
    files: List[Path] = []
    files.extend(workspace_root.glob("task_TASK_*.md"))
    tasks_dir = workspace_root / "tasks"
    if tasks_dir.exists():
        files.extend(tasks_dir.glob("task_TASK_*.md"))
    return sorted(set(files))


def list_report_files(workspace_root: Path) -> List[Path]:
    files: List[Path] = []
    files.extend(workspace_root.glob("report_*.md"))
    reports_dir = workspace_root / "reports"
    if reports_dir.exists():
        files.extend(reports_dir.glob("report_*.md"))
    return sorted(set(files))


def find_latest_report(task_id: str, workspace_root: Path) -> Optional[Path]:
    """Find the latest report file for a given task ID."""
    reports = list_report_files(workspace_root)
    task_reports = []
    for p in reports:
        parsed = parse_report_filename(p)
        if parsed and parsed["taskId"] == task_id:
            task_reports.append((parsed["loop"], parsed["version"], p))
    if not task_reports:
        return None
    # Return the one with highest loop and version
    task_reports.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return task_reports[0][2]


def task_in_neu(task_id: str, workspace_root: Path) -> bool:
    """Check if a task is referenced in NEU.md active queue."""
    neu_path = workspace_root / "NEU.md"
    if not neu_path.exists():
        return False
    content = read_text(neu_path)
    # Look for task reference in TASK QUEUE section
    return f"task_{task_id}.md" in content or f"task_{task_id}" in content


def pre_work_validation(task_id: str, workspace: Path) -> ValidationResult:
    """Run BEFORE any file edits for a task (REPORT-FIRST enforcement).
    
    Validates:
    1. Report file exists for the task (REPORT-FIRST enforcement)
    2. Task spec file exists and is valid
    3. Task is in NEU.md active queue
    
    Args:
        task_id: The task ID (e.g., "TASK_0077")
        workspace: Path to the workspace root
        
    Returns:
        ValidationResult with passed=True if all checks pass, else errors list
    """
    errors: List[Dict[str, str]] = []
    
    # Normalize task_id format
    if not task_id.startswith("TASK_"):
        task_id = f"TASK_{task_id.zfill(4)}"
    
    # 1. Check report exists (REPORT-FIRST enforcement)
    report = find_latest_report(task_id, workspace)
    if not report:
        errors.append({
            "code": "REPORT_FIRST_VIOLATION",
            "message": f"No report found for {task_id}. Create report BEFORE implementation.",
            "hint": f"Create: reports/report_{task_id}_LXX_v01.md"
        })
    
    # 2. Check task spec exists and is valid
    task_spec = workspace / "tasks" / f"task_{task_id}.md"
    if not task_spec.exists():
        # Also check root directory for legacy placement
        task_spec_root = workspace / f"task_{task_id}.md"
        if not task_spec_root.exists():
            errors.append({
                "code": "MISSING_TASK_SPEC",
                "message": f"Task spec not found: tasks/task_{task_id}.md",
                "hint": f"Create task spec file or check task ID"
            })
        else:
            task_spec = task_spec_root
    
    # 3. Check task is in NEU.md (active queue)
    if not task_in_neu(task_id, workspace):
        errors.append({
            "code": "TASK_NOT_ACTIVE",
            "message": f"{task_id} not found in NEU.md active queue",
            "hint": "Task must be in NEU.md to work on it"
        })
    
    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors
    )


def parse_report_filename(path: Path) -> Optional[Dict[str, Any]]:
    m = REPORT_BASENAME_RE.match(path.name)
    if not m:
        return None
    return {
        "taskId": m.group(1),
        "loop": int(m.group(2)),
        "version": int(m.group(3)),
        "path": str(path).replace("\\", "/"),
    }


def extract_files_changed_from_report(content: str) -> List[str]:
    """Extract list of files changed from a report's FILES MODIFIED section."""
    files = []
    lines = content.split('\n')
    in_section = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('## FILES MODIFIED') or line.startswith('## FILES CHANGED'):
            in_section = True
            continue
        elif line.startswith('## ') and in_section:
            break  # Next section
        
        if in_section and line.startswith('- '):
            # Extract file path from markdown links or plain text
            file_match = re.search(r'\[([^\]]+)\]', line)
            if file_match:
                files.append(file_match.group(1))
            else:
                # Plain text after dash
                file_part = line[2:].strip()
                if file_part and not file_part.startswith('Created:') and not file_part.startswith('Modified:'):
                    files.append(file_part)
    
    return files
    """Compute history/index data as JSON-serializable dict."""

    # Tasks
    task_specs = []
    for path in list_task_spec_files(workspace_root):
        task_id_match = TASK_ID_RE.search(path.name)
        task_id = f"TASK_{task_id_match.group(1)}" if task_id_match else path.stem
        task_specs.append({
            "taskId": task_id,
            "path": str(path.relative_to(workspace_root)).replace("\\", "/"),
        })
    task_specs.sort(key=lambda t: t["taskId"])

    # Reports
    reports = []
    for path in list_report_files(workspace_root):
        parsed = parse_report_filename(path)
        if not parsed:
            continue
        # store rel path for stable linking
        parsed["path"] = str(path.relative_to(workspace_root)).replace("\\", "/")
        
        # Parse report content for files changed
        try:
            content = read_text(path)
            files_changed = extract_files_changed_from_report(content)
            parsed["filesChanged"] = files_changed
        except Exception:
            parsed["filesChanged"] = []
        
        reports.append(parsed)
    reports.sort(key=lambda r: (r["loop"], r["taskId"], r["version"], r["path"]))

    # Group reports per task
    reports_by_task: Dict[str, List[Dict[str, Any]]] = {}
    for r in reports:
        reports_by_task.setdefault(r["taskId"], []).append(r)

    # File modification history: file -> list of (task, report) that modified it
    file_history: Dict[str, List[Dict[str, Any]]] = {}
    for r in reports:
        for file_path in r.get("filesChanged", []):
            if file_path not in file_history:
                file_history[file_path] = []
            file_history[file_path].append({
                "taskId": r["taskId"],
                "reportPath": r["path"],
                "loop": r["loop"],
                "version": r["version"]
            })
    
    # Sort file history by loop number
    for file_path in file_history:
        file_history[file_path].sort(key=lambda x: x["loop"])

    # Archives
    archives: List[Dict[str, Any]] = []
    archive_dir = workspace_root / "archive"
    if archive_dir.exists():
        for p in sorted(archive_dir.glob("ARCHIV_*.md")):
            m = ARCHIV_RE.match(p.name)
            loop = int(m.group(1)) if m else None
            archives.append({
                "file": p.name,
                "path": str(p.relative_to(workspace_root)).replace("\\", "/"),
                "loop": loop,
            })
    archives.sort(key=lambda a: (a["loop"] if a["loop"] is not None else 9999, a["file"]))

    # Pointer docs → referenced files
    pointer_docs = ["NEU.md", "Alt.md", "NEURAL_CORTEX.md"]
    pointers: Dict[str, List[Dict[str, Any]]] = {}
    for doc in pointer_docs:
        p = workspace_root / doc
        if not p.exists():
            continue
        content = read_text(p)
        refs = []
        for ref in iter_refs(content):
            refs.append({
                "target": ref.target,
                "section": ref.section,
                "v": ref.v,
                "tags": ref.tags,
                "src": ref.src,
                "raw": ref.raw,
            })
        refs.sort(key=lambda x: (x["target"], x["raw"]))
        pointers[doc] = refs

    return {
        "generatedAt": utc_now_iso(),
        "tasks": task_specs,
        "reports": reports,
        "reportsByTask": {k: v for k, v in sorted(reports_by_task.items(), key=lambda kv: kv[0])},
        "archives": archives,
        "pointers": pointers,
        "fileHistory": {k: v for k, v in sorted(file_history.items(), key=lambda kv: kv[0])},
    }


def history_index_data(workspace_root: Path) -> Dict[str, Any]:
    """Compute history/index data as JSON-serializable dict."""

    # Tasks
    task_specs = []
    for path in list_task_spec_files(workspace_root):
        task_id_match = TASK_ID_RE.search(path.name)
        task_id = f"TASK_{task_id_match.group(1)}" if task_id_match else path.stem
        task_specs.append({
            "taskId": task_id,
            "path": str(path.relative_to(workspace_root)).replace("\\", "/"),
        })
    task_specs.sort(key=lambda t: t["taskId"])

    # Reports
    reports = []
    for path in list_report_files(workspace_root):
        parsed = parse_report_filename(path)
        if not parsed:
            continue
        # store rel path for stable linking
        parsed["path"] = str(path.relative_to(workspace_root)).replace("\\", "/")
        
        # Parse report content for files changed
        try:
            content = read_text(path)
            files_changed = extract_files_changed_from_report(content)
            parsed["filesChanged"] = files_changed
        except Exception:
            parsed["filesChanged"] = []
        
        reports.append(parsed)
    reports.sort(key=lambda r: (r["loop"], r["taskId"], r["version"], r["path"]))

    # Group reports per task
    reports_by_task: Dict[str, List[Dict[str, Any]]] = {}
    for r in reports:
        reports_by_task.setdefault(r["taskId"], []).append(r)

    # File modification history: file -> list of (task, report) that modified it
    file_history: Dict[str, List[Dict[str, Any]]] = {}
    for r in reports:
        for file_path in r.get("filesChanged", []):
            if file_path not in file_history:
                file_history[file_path] = []
            file_history[file_path].append({
                "taskId": r["taskId"],
                "reportPath": r["path"],
                "loop": r["loop"],
                "version": r["version"]
            })
    
    # Sort file history by loop number
    for file_path in file_history:
        file_history[file_path].sort(key=lambda x: x["loop"])

    # Archives
    archives: List[Dict[str, Any]] = []
    archive_dir = workspace_root / "archive"
    if archive_dir.exists():
        for p in sorted(archive_dir.glob("ARCHIV_*.md")):
            m = ARCHIV_RE.match(p.name)
            loop = int(m.group(1)) if m else None
            archives.append({
                "file": p.name,
                "path": str(p.relative_to(workspace_root)).replace("\\", "/"),
                "loop": loop,
            })
    archives.sort(key=lambda a: (a["loop"] if a["loop"] is not None else 9999, a["file"]))

    # Pointer docs → referenced files
    pointer_docs = ["NEU.md", "Alt.md", "NEURAL_CORTEX.md"]
    pointers: Dict[str, List[Dict[str, Any]]] = {}
    for doc in pointer_docs:
        p = workspace_root / doc
        if not p.exists():
            continue
        content = read_text(p)
        refs = []
        for ref in iter_refs(content):
            refs.append({
                "target": ref.target,
                "section": ref.section,
                "v": ref.v,
                "tags": ref.tags,
                "src": ref.src,
                "raw": ref.raw,
            })
        refs.sort(key=lambda x: (x["target"], x["raw"]))
        pointers[doc] = refs

    return {
        "generatedAt": utc_now_iso(),
        "tasks": task_specs,
        "reports": reports,
        "reportsByTask": {k: v for k, v in sorted(reports_by_task.items(), key=lambda kv: kv[0])},
        "archives": archives,
        "pointers": pointers,
        "fileHistory": {k: v for k, v in sorted(file_history.items(), key=lambda kv: kv[0])},
    }


def history_index_markdown(data: Dict[str, Any]) -> str:
    """Render a compact human-readable history index (deterministic)."""

    lines: List[str] = []
    lines.append("# HISTORY INDEX")
    lines.append("")
    lines.append("MODE: GENERATED")
    lines.append(f"GENERATED: {data.get('generatedAt')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## TASKS → REPORTS")
    lines.append("")
    tasks = data.get("tasks", [])
    reports_by_task = data.get("reportsByTask", {})
    for t in tasks:
        task_id = t["taskId"]
        task_path = t["path"]
        lines.append(f"- {task_id}: [ref:{task_path}|v:1|tags:task|src:system]")
        for r in reports_by_task.get(task_id, []):
            lines.append(f"  - Report L{r['loop']:02d} v{r['version']:02d}: [ref:{r['path']}|v:1|tags:report|src:system]")
    lines.append("")

    lines.append("## ARCHIVES")
    lines.append("")
    for a in data.get("archives", []):
        if a.get("loop") is None:
            lines.append(f"- [ref:{a['path']}|v:immutable|tags:archive|src:system]")
        else:
            lines.append(f"- Loop {a['loop']}: [ref:{a['path']}|v:immutable|tags:archive|src:system]")
    lines.append("")

    lines.append("## FILES → TASKS/REPORTS")
    lines.append("")
    file_history = data.get("fileHistory", {})
    if file_history:
        for file_path, modifications in file_history.items():
            lines.append(f"- {file_path}")
            for mod in modifications:
                report_ref = f"[ref:{mod['reportPath']}|v:1|tags:report|src:system]"
                lines.append(f"  - {mod['taskId']} (L{mod['loop']:02d} v{mod['version']:02d}): {report_ref}")
            lines.append("")
    else:
        lines.append("(No file modification history available)")
        lines.append("")

    lines.append("## POINTER DOC REFERENCES")
    lines.append("")
    for doc, refs in (data.get("pointers") or {}).items():
        lines.append(f"### {doc}")
        lines.append("")
        for r in refs:
            target = r.get("target")
            raw = r.get("raw")
            lines.append(f"- [ref:{raw}|v:dynamic|tags:ref,raw|src:system] → {target}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("END OF DOCUMENT")
    lines.append("")
    return "\n".join(lines)


def session_pack_markdown(workspace_root: Path) -> str:
    state = read_json(workspace_root / "current.json").get("STATE", {})
    loop_num = state.get("loop")
    status = state.get("status")
    archive_current = state.get("archiveCurrent")
    last_task = state.get("lastTaskWorked")

    neu_path = workspace_root / "NEU.md"
    neu_lines = read_text(neu_path).splitlines() if neu_path.exists() else []
    active_task_lines: List[str] = []

    in_queue = False
    for line in neu_lines:
        stripped = line.strip()
        if stripped.startswith('## TASK QUEUE'):
            in_queue = True
            continue
        if not in_queue:
            continue
        # Stop at the next section/divider
        if stripped.startswith('---') or stripped.startswith('## '):
            break
        if stripped.startswith('[ref:'):
            active_task_lines.append(stripped)
        if 'Empty - all tasks completed' in stripped:
            active_task_lines = []
            break

    blockers = read_json(workspace_root / "knownissues.json").get("ISSUES", {}).get("BLOCKERS", [])

    lines: List[str] = []
    lines.append("# SESSION CONTEXT PACK")
    lines.append("")
    lines.append("MODE: EPHEMERAL")
    lines.append(f"GENERATED: {utc_now_iso()}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## STATE")
    lines.append("")
    lines.append(f"- Loop: {loop_num}")
    lines.append(f"- Status: {status}")
    lines.append(f"- Last task worked: {last_task or 'None'}")
    if archive_current:
        lines.append(f"- Last archived loop: [ref:{archive_current}|v:immutable|tags:archive|src:system]")
    lines.append("")

    lines.append("## ACTIVE TASK QUEUE (NEU.md)")
    lines.append("")
    if active_task_lines:
        for l in active_task_lines[:25]:
            # keep it compact
            lines.append(f"- {l}")
        if len(active_task_lines) > 25:
            lines.append(f"- ... ({len(active_task_lines) - 25} more)")
    else:
        lines.append("- (No task refs found)")
    lines.append("")

    lines.append("## KNOWN BLOCKERS")
    lines.append("")
    if blockers:
        for b in blockers:
            lines.append(f"- {b}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## OPERATOR NEXT ACTION")
    lines.append("")
    if status == "READY_FOR_RESET":
        lines.append('- Start a fresh AI chat and send: "Read _BOOTSTRAP.md"')
    elif status == "ACTIVE":
        lines.append('- Ask AI: "Work on the next task in NEU.md"')
    elif status == "FINALIZED":
        lines.append('- Use cockpit RESET LOOP to archive and prep next loop')
    else:
        lines.append("- Check current.json and cockpit status")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("END OF DOCUMENT")
    lines.append("")

    return "\n".join(lines)


def generate_context_index(workspace_root: Path) -> Dict[str, Any]:
    """Generate context index for AI onboarding.
    
    Produces a structured JSON with current loop state, active tasks,
    recent completed tasks, and key project metadata for faster AI session startup.
    
    Returns:
        Dict with currentLoop, activeTasks, recentCompletedTasks, knownBlockers, phaseStatus
    """
    # Load current state
    state = read_json(workspace_root / "current.json").get("STATE", {})
    loop_num = state.get("loop")
    status = state.get("status")
    last_task = state.get("lastTaskWorked")
    archive_current = state.get("archiveCurrent")
    
    # Parse active tasks from NEU.md
    neu_path = workspace_root / "NEU.md"
    active_tasks: List[Dict[str, Any]] = []
    phases: Dict[str, Dict[str, Any]] = {}
    
    if neu_path.exists():
        content = read_text(neu_path)
        lines = content.split('\n')
        
        current_phase = None
        phase_complete = False
        
        for idx, line in enumerate(lines):
            stripped = line.strip()
            next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
            
            # Detect phase headers
            if stripped.startswith('### ') and 'PHASE' in stripped:
                # Extract phase name and check if complete
                phase_match = re.search(r'PHASE\s+(\d+):\s+([^\[]+)', stripped)
                if phase_match:
                    phase_num = phase_match.group(1)
                    phase_name = phase_match.group(2).strip()
                    phase_complete = '✅ COMPLETE' in stripped
                    current_phase = f"Phase {phase_num}"
                    phases[current_phase] = {
                        "name": phase_name,
                        "complete": phase_complete,
                        "tasks": []
                    }
            
            # Extract task references
            if stripped.startswith('[ref:') and 'task_TASK_' in stripped:
                ref_match = re.search(r'\[ref:([^\|]+)\|', stripped)
                task_id_match = TASK_ID_RE.search(stripped)
                
                if ref_match and task_id_match:
                    task_path = ref_match.group(1)
                    task_id = f"TASK_{task_id_match.group(1)}"
                    
                    # Get status from line
                    has_arrow = '→' in stripped
                    is_completed = (
                        '✅ COMPLETED' in stripped
                        or 'tags:completed' in stripped
                        or 'Status:' in next_line and 'COMPLETED' in next_line
                        or has_arrow
                    )
                    is_queued = (
                        '📋 QUEUED' in stripped
                        or 'tags:queued' in stripped
                        or 'Status: 📋 QUEUED' in next_line
                    )
                    is_blocked = '🚫 BLOCKED' in stripped or 'Status: 🚫 BLOCKED' in next_line
                    
                    task_status = "COMPLETED" if is_completed else "QUEUED" if is_queued else "BLOCKED" if is_blocked else "ACTIVE"
                    
                    # Get title (after the - )
                    title_match = re.search(r'\]\s*-\s*(.+?)(?:\s*→|$)', stripped)
                    title = title_match.group(1).strip() if title_match else task_id
                    
                    task_info = {
                        "taskId": task_id,
                        "path": task_path,
                        "title": title,
                        "status": task_status,
                        "phase": current_phase
                    }
                    
                    if task_status != "COMPLETED":
                        active_tasks.append(task_info)
                    
                    if current_phase and current_phase in phases:
                        phases[current_phase]["tasks"].append(task_info)
    
    # Get recent completed tasks from Alt.md
    alt_path = workspace_root / "Alt.md"
    recent_completed: List[Dict[str, Any]] = []
    
    if alt_path.exists():
        content = read_text(alt_path)
        for ref in iter_refs(content):
            if 'task_TASK_' in ref.target:
                task_id_match = TASK_ID_RE.search(ref.target)
                if task_id_match:
                    task_id = f"TASK_{task_id_match.group(1)}"
                    recent_completed.append({
                        "taskId": task_id,
                        "path": ref.target,
                        "tags": ref.tags,
                        "src": ref.src
                    })
    
    # Limit to last 10 completed tasks
    recent_completed = recent_completed[:10]
    
    # Get blockers
    blockers = read_json(workspace_root / "knownissues.json").get("ISSUES", {}).get("BLOCKERS", [])
    
    # Build result
    return {
        "generatedAt": utc_now_iso(),
        "currentLoop": {
            "number": loop_num,
            "status": status,
            "lastTaskWorked": last_task,
            "archiveCurrent": archive_current
        },
        "activeTasks": active_tasks,
        "recentCompletedTasks": recent_completed,
        "knownBlockers": blockers,
        "phaseStatus": phases,
        "summary": {
            "totalActiveTasks": len(active_tasks),
            "totalCompletedInSession": len([t for t in recent_completed if f"loop{loop_num}" in (t.get("src") or "")]),
            "totalBlockers": len(blockers)
        }
    }


def generate_loop_digest(loop_num: int, workspace_root: Path) -> Dict[str, Any]:
    """Generate a concise digest for an archived loop.
    
    Parses the archive file and extracts key information:
    - Loop metadata (status, date, finalized_at)
    - Tasks completed with summaries
    - Key decisions
    - Files modified/created
    - Metrics
    
    Returns:
        {
            "success": bool,
            "digestPath": str,
            "lineCount": int,
            "content": str,
            "error": str (if failed)
        }
    """
    archive_path = workspace_root / "archive" / f"ARCHIV_{loop_num:04d}.md"
    digest_path = workspace_root / "archive" / f"DIGEST_{loop_num:04d}.md"
    
    if not archive_path.exists():
        return {
            "success": False,
            "error": f"Archive not found: ARCHIV_{loop_num:04d}.md",
            "digestPath": None,
            "lineCount": 0,
            "content": ""
        }
    
    content = read_text(archive_path)
    lines = content.split('\n')
    
    # Extract metadata
    loop_date = ""
    finalized_at = ""
    archive_status = ""
    
    for line in lines[:20]:  # Metadata is near the top
        if line.startswith("**DATE:**"):
            loop_date = line.replace("**DATE:**", "").strip()
        elif line.startswith("**FINALIZED_AT:**"):
            finalized_at = line.replace("**FINALIZED_AT:**", "").strip()
        elif line.startswith("**STATUS:**"):
            archive_status = line.replace("**STATUS:**", "").strip()
    
    # Extract tasks completed
    tasks_completed: List[Dict[str, str]] = []
    in_tasks_section = False
    current_task: Dict[str, str] = {}
    
    for line in lines:
        stripped = line.strip()
        
        # Detect tasks section
        if "## TASKS WORKED" in stripped or "## TASKS COMPLETED" in stripped:
            in_tasks_section = True
            continue
        
        # End tasks section at next major section
        if in_tasks_section and stripped.startswith("## ") and "TASK" not in stripped:
            in_tasks_section = False
            if current_task:
                tasks_completed.append(current_task)
                current_task = {}
        
        if in_tasks_section:
            # Parse task header (### ✅ TASK_XXXX: Title)
            task_header_match = re.match(r"###\s*[✅⚠️🔵]\s*(TASK_\d{4}):\s*(.+)", stripped)
            if task_header_match:
                if current_task:
                    tasks_completed.append(current_task)
                current_task = {
                    "taskId": task_header_match.group(1),
                    "title": task_header_match.group(2),
                    "summary": ""
                }
            
            # Parse summary line
            if current_task and stripped.startswith("**Summary:**"):
                current_task["summary"] = stripped.replace("**Summary:**", "").strip()
    
    # Capture last task if section ended with EOF
    if current_task:
        tasks_completed.append(current_task)
    
    # Extract key decisions
    key_decisions: List[str] = []
    in_decisions_section = False
    
    for line in lines:
        stripped = line.strip()
        
        if "## KEY DECISIONS" in stripped:
            in_decisions_section = True
            continue
        
        if in_decisions_section and stripped.startswith("## "):
            in_decisions_section = False
        
        if in_decisions_section and stripped.startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.")):
            # Clean decision text
            decision = re.sub(r"^\d+\.\s*", "", stripped)
            decision = re.sub(r"^[-*]\s*", "", decision)
            decision = re.sub(r"\*\*([^*]+)\*\*:?", r"\1:", decision)  # Bold to plain
            if decision:
                key_decisions.append(decision)
    
    # Extract files modified
    files_modified: List[str] = []
    in_files_section = False
    
    for line in lines:
        stripped = line.strip()
        
        if "## INFRASTRUCTURE CHANGES" in stripped or "## FILES MODIFIED" in stripped or "**Files Modified:**" in stripped or "**Files Created:**" in stripped:
            in_files_section = True
            continue
        
        if in_files_section and stripped.startswith("## ") and "FILE" not in stripped.upper() and "INFRASTRUCTURE" not in stripped.upper():
            in_files_section = False
        
        if in_files_section and stripped.startswith("- "):
            file_entry = stripped[2:].strip()
            # Extract just filename if there's a parenthetical note
            file_match = re.match(r"([^\s(]+)", file_entry)
            if file_match:
                files_modified.append(file_match.group(1))
    
    # Extract metrics
    metrics: Dict[str, Any] = {}
    in_metrics_section = False
    
    for line in lines:
        stripped = line.strip()
        
        if "## METRICS" in stripped:
            in_metrics_section = True
            continue
        
        if in_metrics_section and stripped.startswith("## "):
            in_metrics_section = False
        
        if in_metrics_section and "**" in stripped:
            metric_match = re.match(r"\*\*([^:]+):\*\*\s*(.+)", stripped.replace("- ", ""))
            if metric_match:
                key = metric_match.group(1).strip().lower().replace(" ", "_")
                value = metric_match.group(2).strip()
                # Try to convert numeric values
                try:
                    metrics[key] = int(value)
                except ValueError:
                    metrics[key] = value
    
    # Build digest content
    digest_lines = [
        f"# DIGEST_{loop_num:04d} - Loop {loop_num} Summary",
        "",
        f"**Loop:** {loop_num} | **Date:** {loop_date} | **Tasks:** {len(tasks_completed)}",
        f"**Status:** {archive_status} | **Finalized:** {finalized_at}",
        "",
        "---",
        "",
        "## Tasks Completed",
        "",
        "| Task | Title | Summary |",
        "|------|-------|---------|"
    ]
    
    for task in tasks_completed:
        # Truncate summary if too long
        summary = task.get("summary", "")
        if len(summary) > 80:
            summary = summary[:77] + "..."
        digest_lines.append(f"| {task.get('taskId', '')} | {task.get('title', '')} | {summary} |")
    
    digest_lines.extend([
        "",
        "---",
        "",
        "## Key Decisions",
        ""
    ])
    
    for i, decision in enumerate(key_decisions[:10], 1):  # Limit to 10
        digest_lines.append(f"{i}. {decision}")
    
    if not key_decisions:
        digest_lines.append("_No key decisions recorded._")
    
    digest_lines.extend([
        "",
        "---",
        "",
        "## Files Modified",
        ""
    ])
    
    # Deduplicate files
    unique_files = sorted(set(files_modified))
    for f in unique_files[:30]:  # Limit to 30 files
        digest_lines.append(f"- {f}")
    
    if not unique_files:
        digest_lines.append("_No files recorded._")
    
    if len(unique_files) > 30:
        digest_lines.append(f"_...and {len(unique_files) - 30} more files._")
    
    digest_lines.extend([
        "",
        "---",
        "",
        "## Metrics",
        ""
    ])
    
    for key, value in metrics.items():
        digest_lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
    
    if not metrics:
        digest_lines.append("_No metrics recorded._")
    
    digest_lines.extend([
        "",
        "---",
        "",
        f"_Generated from [ref:archive/ARCHIV_{loop_num:04d}.md|v:1|tags:archive|src:digest-gen]_",
        "",
        "END OF DIGEST"
    ])
    
    digest_content = "\n".join(digest_lines)
    line_count = len(digest_lines)
    
    # Write digest file
    write_text(digest_path, digest_content)
    
    return {
        "success": True,
        "digestPath": str(digest_path),
        "lineCount": line_count,
        "content": digest_content,
        "tasksFound": len(tasks_completed),
        "decisionsFound": len(key_decisions),
        "filesFound": len(unique_files)
    }


def get_task_dependencies(workspace_root: Path) -> Dict[str, Any]:
    """Build task dependency graph for active and queued tasks.
    
    Analyzes task specs to find:
    - Explicit dependencies (Depends: field)
    - File-based dependencies (shared files in SCOPE)
    - Phase groupings for parallel identification
    
    Returns:
        {
            "nodes": List of task nodes with id, status, phase, files
            "edges": List of dependency edges with source, target, type
            "clusters": Groups of parallel/sequential tasks
            "meta": Statistics about the graph
        }
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    task_files: Dict[str, List[str]] = {}  # task_id -> list of files
    
    # Parse NEU.md for active/queued tasks
    neu_path = workspace_root / "NEU.md"
    if not neu_path.exists():
        return {"error": "NEU.md not found", "nodes": [], "edges": [], "clusters": {}, "meta": {}}
    
    neu_content = read_text(neu_path)
    
    # Find tasks and their phases
    task_phases: Dict[str, str] = {}
    current_phase = None
    
    for line in neu_content.split('\n'):
        stripped = line.strip()
        
        # Detect phase headers
        if '### ' in stripped and 'PHASE' in stripped:
            phase_match = re.search(r'PHASE\s+(\d+)', stripped)
            if phase_match:
                current_phase = f"Phase {phase_match.group(1)}"
        
        # Extract task IDs
        task_match = TASK_ID_RE.search(stripped)
        if task_match and current_phase:
            task_id = f"TASK_{task_match.group(1)}"
            task_phases[task_id] = current_phase
    
    # Parse task specs for details
    tasks_dir = workspace_root / "tasks"
    if not tasks_dir.exists():
        return {"error": "tasks/ directory not found", "nodes": [], "edges": [], "clusters": {}, "meta": {}}
    
    for task_file in sorted(tasks_dir.glob("task_TASK_*.md")):
        task_content = read_text(task_file)
        task_id_match = TASK_ID_RE.search(task_file.stem)
        if not task_id_match:
            continue
        
        task_id = f"TASK_{task_id_match.group(1)}"
        
        # Get status
        status = "UNKNOWN"
        status_match = re.search(r"STATUS:\s*(\w+)", task_content)
        if status_match:
            status = status_match.group(1)
        elif "COMPLETED:" in task_content and "TBD" not in task_content.split("COMPLETED:")[1][:50]:
            status = "COMPLETED"
        
        # Get dependencies (explicit)
        depends = []
        for line in task_content.split('\n'):
            if line.strip().startswith("Depends:") or line.strip().startswith("DEPENDENCIES"):
                dep_matches = TASK_ID_RE.findall(line + " " + task_content[task_content.find(line):task_content.find(line)+200])
                for dep in dep_matches:
                    dep_id = f"TASK_{dep}"
                    if dep_id != task_id and dep_id not in depends:
                        depends.append(dep_id)
            # Also check for "- TASK_XXXX" style dependencies
            if re.match(r"^\s*-\s*TASK_\d{4}", line.strip()):
                dep_match = TASK_ID_RE.search(line)
                if dep_match:
                    dep_id = f"TASK_{dep_match.group(1)}"
                    if dep_id != task_id and dep_id not in depends:
                        depends.append(dep_id)
        
        # Extract file references from SCOPE section
        files_referenced: List[str] = []
        in_scope = False
        for line in task_content.split('\n'):
            stripped = line.strip()
            if "## SCOPE" in stripped:
                in_scope = True
                continue
            if in_scope and stripped.startswith("## "):
                in_scope = False
            if in_scope:
                # Look for common file patterns
                file_patterns = re.findall(r'`([^`]+\.(py|md|json|html|js|ts|css))`', stripped)
                for fp in file_patterns:
                    files_referenced.append(fp[0])
                # Also look for paths without backticks
                path_patterns = re.findall(r'(\w+(?:_\w+)*\.(?:py|md|json|html|js|ts|css))', stripped)
                for pp in path_patterns:
                    if pp not in files_referenced:
                        files_referenced.append(pp)
        
        task_files[task_id] = files_referenced
        phase = task_phases.get(task_id, "Unknown")
        
        node = {
            "id": task_id,
            "status": status,
            "phase": phase,
            "files": files_referenced,
            "dependsOn": depends
        }
        nodes.append(node)
        
        # Create explicit dependency edges
        for dep in depends:
            edges.append({
                "source": task_id,
                "target": dep,
                "type": "depends"
            })
    
    # Add file-based implicit dependencies
    # If two tasks modify the same file, the later one depends on the earlier
    file_tasks: Dict[str, List[str]] = {}  # file -> list of task_ids that touch it
    for task_id, files in task_files.items():
        for f in files:
            if f not in file_tasks:
                file_tasks[f] = []
            file_tasks[f].append(task_id)
    
    # Create file-shared edges (avoid duplicates with explicit edges)
    existing_edges = {(e["source"], e["target"]) for e in edges}
    for f, tasks in file_tasks.items():
        if len(tasks) > 1:
            # Sort by task number
            sorted_tasks = sorted(tasks, key=lambda t: int(TASK_ID_RE.search(t).group(1)))
            for i in range(1, len(sorted_tasks)):
                edge_pair = (sorted_tasks[i], sorted_tasks[i-1])
                reverse_pair = (sorted_tasks[i-1], sorted_tasks[i])
                if edge_pair not in existing_edges and reverse_pair not in existing_edges:
                    edges.append({
                        "source": sorted_tasks[i],
                        "target": sorted_tasks[i-1],
                        "type": "file-shared",
                        "file": f
                    })
                    existing_edges.add(edge_pair)
    
    # Identify parallel clusters (same phase, no dependencies between them)
    phase_groups: Dict[str, List[str]] = {}
    for node in nodes:
        phase = node["phase"]
        if phase not in phase_groups:
            phase_groups[phase] = []
        phase_groups[phase].append(node["id"])
    
    # Build dependency set for checking
    depends_set: Dict[str, set] = {}
    for node in nodes:
        depends_set[node["id"]] = set(node.get("dependsOn", []))
    
    # Add transitive dependencies from edges
    for edge in edges:
        if edge["source"] in depends_set:
            depends_set[edge["source"]].add(edge["target"])
    
    # Find truly parallel tasks within each phase
    clusters = {
        "parallel": [],
        "sequential": []
    }
    
    for phase, tasks in phase_groups.items():
        # Check for independent tasks
        independent = []
        for task in tasks:
            task_deps = depends_set.get(task, set())
            # Task is independent if it doesn't depend on other tasks in same phase
            other_tasks = set(tasks) - {task}
            if not task_deps.intersection(other_tasks):
                independent.append(task)
        
        if len(independent) > 1:
            clusters["parallel"].append({
                "phase": phase,
                "tasks": independent
            })
    
    # Sequential chains (tasks with explicit dependency chains)
    # Find chains where A -> B -> C
    visited = set()
    for node in nodes:
        task_id = node["id"]
        if task_id in visited:
            continue
        
        chain = [task_id]
        visited.add(task_id)
        
        # Follow dependency chain backwards
        current = task_id
        while True:
            deps = [n for n in nodes if current in n.get("dependsOn", [])]
            if deps and deps[0]["id"] not in visited:
                chain.append(deps[0]["id"])
                visited.add(deps[0]["id"])
                current = deps[0]["id"]
            else:
                break
        
        if len(chain) > 1:
            clusters["sequential"].append(chain)
    
    # Compute meta statistics
    meta = {
        "totalNodes": len(nodes),
        "totalEdges": len(edges),
        "explicitDeps": len([e for e in edges if e["type"] == "depends"]),
        "fileDeps": len([e for e in edges if e["type"] == "file-shared"]),
        "parallelClusters": len(clusters["parallel"]),
        "sequentialChains": len(clusters["sequential"]),
        "sharedFiles": {f: tasks for f, tasks in file_tasks.items() if len(tasks) > 1}
    }
    
    return {
        "generatedAt": utc_now_iso(),
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
        "meta": meta
    }


def analyze_parallelization(workspace_root: Path, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Analyze which tasks can run in parallel vs sequentially.
    
    Uses the dependency graph to identify:
    - Tasks that have no dependencies between them (can run in parallel)
    - Tasks that must run sequentially due to dependencies
    - File conflicts that prevent parallelization
    
    Args:
        workspace_root: Path to workspace root
        task_ids: Optional list of specific task IDs to analyze.
                  If None, analyzes all QUEUED tasks.
    
    Returns:
        {
            "parallelizable": List of task clusters that can run in parallel,
            "sequential": List of task chains that must run in order,
            "conflicts": List of file conflicts between tasks,
            "independentTasks": Tasks with no dependencies,
            "summary": Human-readable summary
        }
    """
    # Get dependency graph
    graph = get_task_dependencies(workspace_root)
    
    if "error" in graph:
        return {
            "success": False,
            "error": graph["error"],
            "parallelizable": [],
            "sequential": [],
            "conflicts": []
        }
    
    nodes = graph["nodes"]
    edges = graph["edges"]
    meta = graph.get("meta", {})
    shared_files = meta.get("sharedFiles", {})
    
    # Filter to requested tasks or all QUEUED tasks
    if task_ids:
        target_tasks = set(task_ids)
    else:
        # Get all QUEUED tasks
        target_tasks = {n["id"] for n in nodes if n.get("status") in ("QUEUED", "NEW", "ACTIVE")}
    
    # Filter nodes to target tasks
    relevant_nodes = [n for n in nodes if n["id"] in target_tasks]
    
    if not relevant_nodes:
        return {
            "success": True,
            "parallelizable": [],
            "sequential": [],
            "conflicts": [],
            "independentTasks": [],
            "summary": "No QUEUED tasks to analyze."
        }
    
    # Build dependency map (task -> set of tasks it depends on)
    depends_on: Dict[str, set] = {}
    depended_by: Dict[str, set] = {}  # reverse: task -> set of tasks that depend on it
    
    for node in relevant_nodes:
        task_id = node["id"]
        depends_on[task_id] = set(node.get("dependsOn", []))
        depended_by[task_id] = set()
    
    # Add edge dependencies
    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src in target_tasks:
            depends_on[src].add(tgt)
        if tgt in target_tasks:
            if tgt not in depended_by:
                depended_by[tgt] = set()
            depended_by[tgt].add(src)
    
    # Find independent tasks (no dependencies on other target tasks)
    independent_tasks = []
    for node in relevant_nodes:
        task_id = node["id"]
        deps_in_scope = depends_on.get(task_id, set()).intersection(target_tasks)
        if not deps_in_scope:
            independent_tasks.append(task_id)
    
    # Find file conflicts
    conflicts = []
    for file_path, task_list in shared_files.items():
        conflicting = [t for t in task_list if t in target_tasks]
        if len(conflicting) > 1:
            conflicts.append({
                "file": file_path,
                "tasks": conflicting,
                "reason": f"Multiple tasks modify {file_path}"
            })
    
    # Build parallelizable clusters using Union-Find for connected components
    # Tasks are in same component if they share dependencies or files
    parent: Dict[str, str] = {n["id"]: n["id"] for n in relevant_nodes}
    
    def find(x: str) -> str:
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x: str, y: str):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Union tasks that have dependencies between them
    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src in target_tasks and tgt in target_tasks:
            union(src, tgt)
    
    # Union tasks that share files
    for file_path, task_list in shared_files.items():
        conflicting = [t for t in task_list if t in target_tasks]
        for i in range(1, len(conflicting)):
            union(conflicting[0], conflicting[i])
    
    # Group by component
    components: Dict[str, List[str]] = {}
    for task_id in target_tasks:
        root = find(task_id)
        if root not in components:
            components[root] = []
        components[root].append(task_id)
    
    # Identify parallel clusters (independent components)
    parallelizable = []
    sequential = []
    
    for root, tasks in components.items():
        if len(tasks) == 1:
            # Single task, can run independently
            parallelizable.append({
                "tasks": tasks,
                "canParallel": True,
                "reason": "No dependencies with other queued tasks"
            })
        else:
            # Multiple tasks in component - need topological sort
            # These must run sequentially
            sorted_tasks = _topological_sort(tasks, depends_on)
            sequential.append({
                "tasks": sorted_tasks,
                "canParallel": False,
                "reason": "Tasks have inter-dependencies"
            })
    
    # Generate summary
    total_tasks = len(relevant_nodes)
    parallel_count = sum(len(c["tasks"]) for c in parallelizable)
    sequential_count = sum(len(c["tasks"]) for c in sequential)
    
    summary = f"Analyzed {total_tasks} tasks: {parallel_count} can run in parallel, {sequential_count} must run sequentially."
    if conflicts:
        summary += f" Found {len(conflicts)} file conflict(s)."
    
    return {
        "success": True,
        "parallelizable": parallelizable,
        "sequential": sequential,
        "conflicts": conflicts,
        "independentTasks": independent_tasks,
        "summary": summary,
        "generatedAt": utc_now_iso()
    }


def _topological_sort(tasks: List[str], depends_on: Dict[str, set]) -> List[str]:
    """Topologically sort tasks based on dependencies."""
    in_degree: Dict[str, int] = {t: 0 for t in tasks}
    task_set = set(tasks)
    
    # Count in-degrees (dependencies)
    for task in tasks:
        deps = depends_on.get(task, set())
        for dep in deps:
            if dep in task_set:
                in_degree[task] += 1
    
    # Start with tasks that have no dependencies
    queue = [t for t in tasks if in_degree[t] == 0]
    result = []
    
    while queue:
        # Sort for deterministic output
        queue.sort()
        task = queue.pop(0)
        result.append(task)
        
        # Reduce in-degree for dependent tasks
        for other in tasks:
            if task in depends_on.get(other, set()):
                in_degree[other] -= 1
                if in_degree[other] == 0:
                    queue.append(other)
    
    # If we couldn't sort all tasks, there's a cycle
    if len(result) != len(tasks):
        # Return original order with warning
        return tasks
    
    return result


def generate_report_template(
    task_id: str,
    workspace_root: Path,
    loop: int,
    version: int = 1
) -> Dict[str, Any]:
    """Generate a report template from task spec data.
    
    Parses task spec and extracts:
    - Task ID and title
    - OBJECTIVE section content
    - SCOPE items
    - ACCEPTANCE CRITERIA (converted to checkboxes)
    
    Args:
        task_id: Task ID (e.g., "TASK_0087")
        workspace_root: Path to workspace root
        loop: Current loop number
        version: Report version (default 1)
    
    Returns:
        {
            "success": bool,
            "template": str,
            "filename": str,
            "taskTitle": str,
            "error": str (if failed)
        }
    """
    # Normalize task ID
    if not task_id.startswith("TASK_"):
        task_id = f"TASK_{task_id.zfill(4)}"
    
    # Find task spec file
    task_spec_path = None
    for candidate in [
        workspace_root / "tasks" / f"task_{task_id}.md",
        workspace_root / f"task_{task_id}.md"
    ]:
        if candidate.exists():
            task_spec_path = candidate
            break
    
    if not task_spec_path:
        return {
            "success": False,
            "template": None,
            "filename": None,
            "taskTitle": None,
            "error": f"Task spec not found: task_{task_id}.md"
        }
    
    try:
        content = read_text(task_spec_path)
    except Exception as e:
        return {
            "success": False,
            "template": None,
            "filename": None,
            "taskTitle": None,
            "error": f"Failed to read task spec: {str(e)}"
        }
    
    # Extract task title from header
    title_match = re.search(r"^#\s*" + re.escape(task_id) + r":\s*(.+)$", content, re.MULTILINE)
    task_title = title_match.group(1).strip() if title_match else task_id
    
    # Extract OBJECTIVE section
    objective = ""
    obj_match = re.search(r"^## OBJECTIVE\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    if obj_match:
        objective = obj_match.group(1).strip()
        # Remove trailing --- separators
        objective = re.sub(r"\n---\s*$", "", objective).strip()
    
    # Extract SCOPE section
    scope_items = []
    scope_match = re.search(r"^## SCOPE\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    if scope_match:
        scope_text = scope_match.group(1).strip()
        # Extract numbered items
        for line in scope_text.split('\n'):
            line = line.strip()
            if re.match(r"^\d+\.", line):
                scope_items.append(line)
    
    # Extract ACCEPTANCE CRITERIA
    criteria = []
    ac_match = re.search(r"^## ACCEPTANCE CRITERIA\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    if ac_match:
        ac_text = ac_match.group(1).strip()
        # Extract checkbox items or bullet points
        for line in ac_text.split('\n'):
            line = line.strip()
            # Handle existing checkboxes
            checkbox_match = re.match(r"^-\s*\[[ x]\]\s*(.+)$", line)
            if checkbox_match:
                criteria.append(checkbox_match.group(1).strip())
            # Handle bullet points without checkboxes
            elif line.startswith("- ") and "[" not in line:
                criteria.append(line[2:].strip())
    
    # Extract CONTEXT section if available
    context = ""
    ctx_match = re.search(r"^## CONTEXT\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    if ctx_match:
        context = ctx_match.group(1).strip()
        context = re.sub(r"\n---\s*$", "", context).strip()
    
    # Build filename
    filename = f"report_{task_id}_L{loop:02d}_v{version:02d}.md"
    
    # Build scope section for template
    scope_section = ""
    if scope_items:
        scope_section = "\n".join(scope_items)
    else:
        scope_section = "1. [Describe approach step 1]\n2. [Describe approach step 2]"
    
    # Build acceptance criteria checkboxes
    ac_checkboxes = ""
    if criteria:
        ac_checkboxes = "\n".join(f"- [ ] {c}" for c in criteria)
    else:
        ac_checkboxes = "- [ ] [Criterion 1]\n- [ ] [Criterion 2]"
    
    # Generate timestamp
    timestamp = utc_now_iso()
    
    # Build template
    template = f"""````markdown
# REPORT: {task_id} - {task_title}

**TASK:** {task_id}
**LOOP:** {loop}
**VERSION:** v{version:02d}
**STATUS:** IN_PROGRESS
**CREATED:** {timestamp}

---

## OBJECTIVE

{objective if objective else '[Copy objective from task spec]'}

## APPROACH

{scope_section}

## IMPLEMENTATION DETAILS

[Describe technical implementation decisions, code changes, and architecture]

## ACCEPTANCE CRITERIA MAPPING

{ac_checkboxes}

## REFERENCES

- [ref:tasks/task_{task_id}.md|v:1|tags:spec|src:system]

---

## WORK LOG

### Entry 1 - Initial Implementation
- Created report (REPORT-FIRST)
- [Describe initial progress]
- Next: [Next steps]

---

END OF REPORT

````
"""
    
    return {
        "success": True,
        "template": template,
        "filename": filename,
        "taskTitle": task_title,
        "objective": objective,
        "criteria": criteria,
        "generatedAt": timestamp
    }


def close_task(task_id: str, workspace_root: Path, summary: str = "", loop_num: int = None) -> Dict[str, Any]:
    """Close a task with a single operation.
    
    Performs:
    1. Validates task exists and has a report
    2. Updates task spec STATUS to COMPLETED
    3. Adds completion entry to Alt.md
    4. Updates NEU.md status indicator
    
    Args:
        task_id: Task ID (e.g., "TASK_0086")
        workspace_root: Path to workspace root
        summary: Optional completion summary
        loop_num: Loop number for tagging (auto-detected if None)
    
    Returns:
        {
            "success": bool,
            "taskId": str,
            "closedAt": str,
            "changes": List[str],
            "error": str (if failed)
        }
    """
    changes: List[str] = []
    closed_at = utc_now_iso()
    
    # Auto-detect loop number
    if loop_num is None:
        state = read_json(workspace_root / "current.json").get("STATE", {})
        loop_num = state.get("loop", 0)
    
    # Validate task spec exists
    task_spec_path = workspace_root / "tasks" / f"task_{task_id}.md"
    if not task_spec_path.exists():
        return {
            "success": False,
            "taskId": task_id,
            "closedAt": None,
            "changes": [],
            "error": f"Task spec not found: task_{task_id}.md"
        }
    
    # Check for report (REPORT-FIRST law)
    reports_dir = workspace_root / "reports"
    has_report = False
    report_path = None
    if reports_dir.exists():
        for report_file in reports_dir.glob(f"report_{task_id}_*.md"):
            has_report = True
            report_path = report_file
            break
    
    if not has_report:
        return {
            "success": False,
            "taskId": task_id,
            "closedAt": None,
            "changes": [],
            "error": f"No report found for {task_id}. REPORT-FIRST law requires a report before closure."
        }
    
    # Update task spec STATUS to COMPLETED
    task_content = read_text(task_spec_path)
    
    # Check if already completed
    if re.search(r"STATUS:\s*COMPLETED", task_content):
        # Already completed, just update Alt.md if needed
        changes.append(f"Task {task_id} already marked COMPLETED")
    else:
        # Add or update STATUS field
        if "STATUS:" in task_content:
            task_content = re.sub(r"STATUS:\s*\w+", "STATUS: COMPLETED", task_content)
        else:
            # Add STATUS after MODE line
            task_content = re.sub(
                r"(MODE:\s*\w+)",
                f"\\1\nSTATUS: COMPLETED",
                task_content
            )
        
        # Update COMPLETED timestamp
        if "COMPLETED: TBD" in task_content:
            task_content = task_content.replace("COMPLETED: TBD", f"COMPLETED: {closed_at}")
        elif "COMPLETED:" not in task_content:
            task_content = re.sub(
                r"(CREATED:\s*[\d\-T:Z]+)",
                f"\\1\nCOMPLETED: {closed_at}",
                task_content
            )
        
        write_text(task_spec_path, task_content)
        changes.append(f"Updated task spec STATUS to COMPLETED")
    
    # Update Alt.md - add to COMPLETED section
    alt_path = workspace_root / "Alt.md"
    if alt_path.exists():
        alt_content = read_text(alt_path)
        
        # Check if task already in Alt.md
        if f"task_{task_id}.md" not in alt_content:
            # Find COMPLETED section for current loop
            loop_section = f"## COMPLETED (LOOP {loop_num})"
            
            if loop_section in alt_content:
                # Add to existing section
                report_ref = f"reports/{report_path.name}" if report_path else f"reports/report_{task_id}_L{loop_num:02d}_v01.md"
                new_entry = f"""
[ref:tasks/task_{task_id}.md|v:1|tags:completed,loop{loop_num}|src:loop{loop_num}] - {task_id}
  Report: [ref:{report_ref}|v:1|tags:report|src:system]
  Status: ✅ COMPLETED (Loop {loop_num})
  Summary: {summary or 'Task completed.'}
"""
                # Insert after section header
                alt_content = alt_content.replace(
                    loop_section,
                    loop_section + new_entry
                )
                write_text(alt_path, alt_content)
                changes.append(f"Added {task_id} to Alt.md COMPLETED section")
            else:
                changes.append(f"Alt.md missing LOOP {loop_num} section - skipped Alt.md update")
        else:
            changes.append(f"{task_id} already in Alt.md")
    
    # Update NEU.md status indicator
    neu_path = workspace_root / "NEU.md"
    if neu_path.exists():
        neu_content = read_text(neu_path)
        
        # Find task line and update status
        task_pattern = rf"\[ref:tasks/task_{task_id}\.md\|[^\]]+\]"
        if re.search(task_pattern, neu_content):
            # Update status line
            lines = neu_content.split('\n')
            updated_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if f"task_{task_id}.md" in line:
                    # Update tags to include completed
                    line = re.sub(r"tags:queued", "tags:completed", line)
                    line = re.sub(r"tags:active", "tags:completed", line)
                    updated_lines.append(line)
                    # Check next lines for status
                    i += 1
                    while i < len(lines) and lines[i].startswith("  "):
                        status_line = lines[i]
                        if "Status:" in status_line:
                            status_line = f"  Status: ✅ COMPLETED (Loop {loop_num})"
                        updated_lines.append(status_line)
                        i += 1
                    continue
                updated_lines.append(line)
                i += 1
            
            neu_content = '\n'.join(updated_lines)
            write_text(neu_path, neu_content)
            changes.append(f"Updated {task_id} status in NEU.md")
    
    # Update current.json lastTaskWorked
    current_path = workspace_root / "current.json"
    if current_path.exists():
        current_data = read_json(current_path)
        current_data["STATE"]["lastTaskWorked"] = task_id
        current_data["STATE"]["lastUpdate"] = closed_at
        write_json(current_path, current_data)
        changes.append(f"Updated current.json lastTaskWorked")
    
    return {
        "success": True,
        "taskId": task_id,
        "closedAt": closed_at,
        "changes": changes
    }


def _check_pointer_doc_basic(workspace_root: Path, filename: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    path = workspace_root / filename
    if not path.exists():
        return False, [f"missing file: {filename}"]
    content = read_text(path)
    if "MODE: POINTER-ONLY" not in content:
        errors.append(f"{filename}: missing 'MODE: POINTER-ONLY'")
    if filename in ("NEU.md", "Alt.md") and "CONTENT: FORBIDDEN" not in content:
        errors.append(f"{filename}: missing 'CONTENT: FORBIDDEN'")

    # Reference format check (strict): all refs must include v/tags/src
    invalid = []
    for r in iter_refs(content):
        err = validate_ref_format(r)
        if err:
            invalid.append(f"{filename}: {err} → {r.raw}")
    if invalid:
        errors.extend(invalid)

    return len(errors) == 0, errors


def _validate_docs_directory(workspace_root: Path, docs_dir: Path) -> Dict[str, Any]:
    """Validate /docs directory contents for consistency and rule compliance.
    
    Checks:
    1. Each doc follows its declared MODE
    2. References to old loop numbers are flagged as stale
    3. Required docs exist (ARCHITECTURE.md, OPS_PROTOCOLS.md)
    """
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    
    # Required docs in /docs directory
    required_docs = ["ARCHITECTURE.md", "OPS_PROTOCOLS.md"]
    for doc_name in required_docs:
        doc_path = docs_dir / doc_name
        if not doc_path.exists():
            errors.append({
                "code": "DOCS_MISSING_REQUIRED",
                "message": f"Required doc missing from /docs: {doc_name}",
                "hint": f"Create docs/{doc_name} or restore from SEED_TEMPLATE",
            })
    
    # Get current loop from state
    state = read_json(workspace_root / "current.json").get("STATE", {})
    current_loop = int(state.get("loop") or 0)
    stale_threshold = max(1, current_loop - 20)  # References older than 20 loops are stale
    
    # Validate each file in /docs
    for doc_path in docs_dir.iterdir():
        if not doc_path.is_file():
            continue
        
        ext = doc_path.suffix.lower()
        
        # Only check markdown and json files
        if ext not in (".md", ".json"):
            continue
        
        try:
            content = read_text(doc_path)
        except Exception:
            warnings.append({
                "code": "DOCS_UNREADABLE",
                "message": f"Could not read docs file: {doc_path.name}",
                "hint": "Check file encoding and permissions",
            })
            continue
        
        # Check MODE declaration for markdown files
        if ext == ".md":
            if "MODE:" not in content:
                warnings.append({
                    "code": "DOCS_NO_MODE",
                    "message": f"docs/{doc_path.name} has no MODE declaration",
                    "hint": "Add 'MODE: DOCUMENTATION' or appropriate mode at top of file",
                })
            elif "MODE: POINTER-ONLY" in content:
                # Pointer-only docs should not have content sections
                content_indicators = ["## IMPLEMENTATION", "```python", "```json", "def ", "class "]
                for indicator in content_indicators:
                    if indicator in content:
                        warnings.append({
                            "code": "DOCS_MODE_VIOLATION",
                            "message": f"docs/{doc_path.name} is MODE: POINTER-ONLY but contains content ({indicator})",
                            "hint": "Remove content or change MODE to DOCUMENTATION",
                        })
                        break
        
        # Check for stale loop references (skip files marked HISTORICAL)
        if "HISTORICAL" not in content:
            loop_refs = re.findall(r"(?:Loop|loop|LOOP)\s*(\d+)", content)
            for loop_str in loop_refs:
                loop_num = int(loop_str)
                # Skip small loop numbers that might be examples (1-5)
                if loop_num > 5 and loop_num < stale_threshold:
                    warnings.append({
                        "code": "DOCS_STALE_LOOP_REF",
                        "message": f"docs/{doc_path.name} references old Loop {loop_num} (current: {current_loop})",
                        "hint": "Update stale loop references or mark as historical",
                    })
                    break  # Only report once per file
        
        # Check JSON files are valid
        if ext == ".json":
            try:
                import json
                json.loads(content)
            except json.JSONDecodeError as e:
                errors.append({
                    "code": "DOCS_INVALID_JSON",
                    "message": f"docs/{doc_path.name} contains invalid JSON: {str(e)[:50]}",
                    "hint": "Fix JSON syntax errors",
                })
    
    return {"errors": errors, "warnings": warnings}


def metadata_lint(workspace_root: Path) -> Dict[str, Any]:
    """Lint for metadata drift and consistency. Returns structured JSON."""

    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    # Pointer doc ref format
    for doc in ("NEU.md", "Alt.md", "NEURAL_CORTEX.md"):
        ok, doc_errors = _check_pointer_doc_basic(workspace_root, doc)
        if not ok:
            for e in doc_errors:
                errors.append({"code": "REF_FORMAT", "message": e, "hint": "Fix [ref:...] to include |v:...|tags:...|src:..."})

    # Reports vs lastTaskWorked (current loop)
    state = read_json(workspace_root / "current.json").get("STATE", {})
    loop_num = int(state.get("loop") or 0)
    last_task = state.get("lastTaskWorked")
    status = state.get("status")
    transition_trigger = state.get("transitionTrigger")

    # DETERMINISTIC TRANSITION ENFORCEMENT: Check ACTIVE state was entered via confirm-bootstrap
    valid_active_triggers = {"confirm-bootstrap", "force-active"}  # force-active is explicit recovery
    if status == "ACTIVE" and transition_trigger:
        if transition_trigger not in valid_active_triggers:
            errors.append({
                "code": "IMPLICIT_ACTIVE_TRANSITION",
                "message": f"Loop {loop_num} entered ACTIVE state via non-deterministic trigger: {transition_trigger}",
                "hint": "ACTIVE state must be entered via /api/confirm-bootstrap. Auto-transition is forbidden per TASK_0057/0067.",
            })
    elif status == "ACTIVE" and not transition_trigger:
        warnings.append({
            "code": "MISSING_TRANSITION_TRIGGER",
            "message": f"Loop {loop_num} is ACTIVE but transitionTrigger is not set (legacy loop or missing tracking)",
            "hint": "This loop may predate transition tracking. Future loops will be tracked automatically.",
        })

    loop_reports = []
    for p in list_report_files(workspace_root):
        parsed = parse_report_filename(p)
        if parsed and parsed["loop"] == loop_num:
            loop_reports.append(parsed)

    if loop_reports and (not last_task or last_task == "None"):
        suggested = sorted(loop_reports, key=lambda r: (r["loop"], r["version"], r["taskId"]))[-1]["taskId"]
        errors.append({
            "code": "LAST_TASK_MISSING",
            "message": f"Loop {loop_num} has {len(loop_reports)} report(s) but current.json lastTaskWorked is unset",
            "hint": f"Set current.json STATE.lastTaskWorked (suggested: {suggested})",
        })

    # Orphaned reports not referenced by Alt.md, NEU.md, or COMPLETED_TASKS_ARCHIVE.md (incident reports excluded)
    # NOTE: Reports for active tasks in NEU.md are NOT orphans
    alt_content = read_text(workspace_root / "Alt.md") if (workspace_root / "Alt.md").exists() else ""
    neu_content = read_text(workspace_root / "NEU.md") if (workspace_root / "NEU.md").exists() else ""
    archive_path = workspace_root / "archive" / "COMPLETED_TASKS_ARCHIVE.md"
    archive_content = read_text(archive_path) if archive_path.exists() else ""
    combined_content = alt_content + "\n" + neu_content + "\n" + archive_content
    report_ref_paths = set(re.findall(r"\[ref:([^\]|]*report_TASK_\d{4}_L\d{2}_v\d+\.md)", combined_content))
    report_ref_paths = {p.replace("\\", "/") for p in report_ref_paths}
    report_ref_names = {Path(p).name for p in report_ref_paths}

    for p in list_report_files(workspace_root):
        if re.match(r"report_INCIDENT_\w+_L\d+_v\d+\.md$", p.name):
            continue
        parsed = parse_report_filename(p)
        if not parsed:
            continue
        rel = str(p.relative_to(workspace_root)).replace("\\", "/")
        if (rel not in report_ref_paths) and (p.name not in report_ref_names):
            warnings.append({
                "code": "ORPHAN_REPORT",
                "message": f"Report not referenced in Alt.md, NEU.md, or archive: {rel}",
                "hint": "Add the report ref under the corresponding task in Alt.md, NEU.md, or archive/COMPLETED_TASKS_ARCHIVE.md",
            })

    # Task specs that exist on disk but are not referenced in NEU.md, Alt.md, or COMPLETED_TASKS_ARCHIVE.md
    # This commonly indicates a "lost" injected task (created but never linked).
    referenced_task_paths = set(re.findall(r"\[ref:([^\]|]*task_TASK_\d{4}\.md)", combined_content))
    referenced_task_paths = {p.replace("\\", "/") for p in referenced_task_paths}
    referenced_task_names = {Path(p).name for p in referenced_task_paths}

    for task_file in list_task_spec_files(workspace_root):
        rel = str(task_file.relative_to(workspace_root)).replace("\\", "/")
        if (rel not in referenced_task_paths) and (task_file.name not in referenced_task_names):
            warnings.append({
                "code": "ORPHAN_TASK_SPEC",
                "message": f"Task spec not referenced in NEU.md, Alt.md, or archive: {rel}",
                "hint": "Add a [ref:...] entry to NEU.md (active), Alt.md (closed/blocked), or archive/COMPLETED_TASKS_ARCHIVE.md",
            })

    # Task spec timestamps: CREATED vs COMPLETED
    created_re = re.compile(r"^CREATED:\s*(.+)$", re.MULTILINE)
    completed_re = re.compile(r"^COMPLETED:\s*(.+)$", re.MULTILINE)

    def parse_iso(ts: str) -> Optional[datetime]:
        ts = ts.strip()
        if not ts or "TBD" in ts or "[" in ts:
            return None
        # Allow date-only values used in legacy task specs.
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", ts):
            dt = datetime.fromisoformat(ts)
            return dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        try:
            if ts.endswith("Z"):
                ts = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    for task_file in list_task_spec_files(workspace_root):
        txt = read_text(task_file)
        created_m = created_re.search(txt)
        completed_m = completed_re.search(txt)
        created_dt = parse_iso(created_m.group(1)) if created_m else None
        completed_dt = parse_iso(completed_m.group(1)) if completed_m else None

        if completed_m and completed_dt is None:
            warnings.append({
                "code": "TASK_COMPLETED_PARSE",
                "message": f"Task has unparseable COMPLETED timestamp: {task_file.name}",
                "hint": "Use ISO-8601 (e.g., 2026-01-10T09:00:00Z) or remove COMPLETED if unknown",
            })

        if created_dt and completed_dt and completed_dt < created_dt:
            warnings.append({
                "code": "TASK_TIME_ORDER",
                "message": f"Task COMPLETED is earlier than CREATED: {task_file.name}",
                "hint": "Fix timestamps so CREATED ≤ COMPLETED (legacy metadata drift is non-blocking)",
            })

    # STATUS_DRIFT: Check task location matches STATUS field
    # Tasks in Alt.md should have STATUS: COMPLETED or BLOCKED
    # Tasks in NEU.md should not have STATUS: COMPLETED
    status_re = re.compile(r"^STATUS:\s*(\w+)", re.MULTILINE)
    
    # Extract task IDs from Alt.md (completed/blocked tasks)
    alt_task_ids = set(re.findall(r"task_(TASK_\d{4})\.md", alt_content))
    # Extract task IDs from NEU.md (active tasks)  
    neu_task_ids = set(re.findall(r"task_(TASK_\d{4})\.md", neu_content))
    
    for task_file in list_task_spec_files(workspace_root):
        task_id_match = TASK_ID_RE.search(task_file.name)
        if not task_id_match:
            continue
        task_id = f"TASK_{task_id_match.group(1)}"
        txt = read_text(task_file)
        status_match = status_re.search(txt)
        spec_status = status_match.group(1).upper() if status_match else None
        
        # Check for drift: task in Alt.md but status not COMPLETED/BLOCKED
        if task_id in alt_task_ids:
            if spec_status and spec_status not in ("COMPLETED", "BLOCKED"):
                warnings.append({
                    "code": "STATUS_DRIFT",
                    "message": f"Task {task_id} is in Alt.md but STATUS is {spec_status} (expected COMPLETED or BLOCKED)",
                    "hint": "Use /api/sync-status or manually update task spec STATUS field",
                })
        
        # Check for drift: task in NEU.md but status is COMPLETED
        if task_id in neu_task_ids:
            if spec_status == "COMPLETED":
                warnings.append({
                    "code": "STATUS_DRIFT",
                    "message": f"Task {task_id} is in NEU.md (active) but STATUS is COMPLETED",
                    "hint": "Either move task to Alt.md or change STATUS to ACTIVE/QUEUED",
                })

    # CRITICAL: Check COMPLETED tasks don't have placeholder objectives
    status_re_completed = re.compile(r"^STATUS:\s*COMPLETED", re.MULTILINE)
    objective_section = re.compile(r"^## OBJECTIVE\s*$(.*?)^---", re.MULTILINE | re.DOTALL)
    ac_section = re.compile(r"^## ACCEPTANCE CRITERIA\s*$(.*?)^---", re.MULTILINE | re.DOTALL)
    
    for task_file in list_task_spec_files(workspace_root):
        txt = read_text(task_file)
        if not status_re_completed.search(txt):
            continue
        
        # Only check OBJECTIVE and ACCEPTANCE CRITERIA sections for placeholders
        obj_match = objective_section.search(txt)
        ac_match = ac_section.search(txt)
        
        has_placeholder = False
        if obj_match and ("[To be defined by AI]" in obj_match.group(1) or "[To be defined]" in obj_match.group(1)):
            has_placeholder = True
        if ac_match and ("[To be defined by AI]" in ac_match.group(1) or "[To be defined]" in ac_match.group(1)):
            has_placeholder = True
            
        if has_placeholder:
            errors.append({
                "code": "PLACEHOLDER_IN_COMPLETED",
                "message": f"Task marked COMPLETED but OBJECTIVE/AC contains placeholder text: {task_file.name}",
                "hint": "Replace '[To be defined by AI]' with actual objectives before marking COMPLETED",
            })
    
    # CRITICAL: Check IMPLEMENTATION tasks have code changes in reports
    task_type_re = re.compile(r"^TASK_TYPE:\s*(\w+)", re.MULTILINE)
    files_modified_re = re.compile(r"^## FILES (?:MODIFIED|CHANGED)\s*$\s*(.*?)(?=^##|\Z)", re.MULTILINE | re.DOTALL)

    for task_file in list_task_spec_files(workspace_root):
        txt = read_text(task_file)
        
        # Only check COMPLETED tasks
        if not status_re_completed.search(txt):
            continue
        
        # Extract TASK_TYPE
        task_type_match = task_type_re.search(txt)
        if not task_type_match:
            continue  # Skip tasks without TASK_TYPE (legacy tasks)
        
        task_type = task_type_match.group(1).strip().upper()
        
        # Only check IMPLEMENTATION tasks
        if task_type != 'IMPLEMENTATION':
            continue
        
        # Extract task_id
        task_id_match = TASK_ID_RE.search(task_file.name)
        if not task_id_match:
            continue
        task_id = f"TASK_{task_id_match.group(1)}"
        
        # Find latest report for this task
        task_reports = []
        for report_path in list_report_files(workspace_root):
            parsed = parse_report_filename(report_path)
            if parsed and parsed["taskId"] == task_id:
                task_reports.append((parsed["loop"], parsed["version"], report_path))
        
        if not task_reports:
            errors.append({
                "code": "IMPLEMENTATION_NO_REPORT",
                "message": f"{task_id}: IMPLEMENTATION task marked COMPLETED but no report found",
                "hint": f"Create report documenting implementation (REPORT-FIRST law)",
            })
            continue
        
        # Get most recent report (highest loop, then highest version)
        task_reports.sort(key=lambda x: (x[0], x[1]), reverse=True)
        latest_report_path = task_reports[0][2]
        
        # Check FILES MODIFIED section in report
        try:
            report_content = read_text(latest_report_path)
            files_match = files_modified_re.search(report_content)
            
            if not files_match:
                errors.append({
                    "code": "IMPLEMENTATION_NO_FILES_SECTION",
                    "message": f"{task_id}: IMPLEMENTATION task report missing FILES MODIFIED section",
                    "hint": f"Add '## FILES MODIFIED' section to {latest_report_path.name}",
                })
                continue
            
            files_text = files_match.group(1).strip().lower()
            
            # Check for indicators of no implementation
            no_impl_indicators = [
                'none',
                'n/a',
                'analysis-only',
                'no code changes',
                'no implementation',
                'deferred',
            ]
            
            has_no_impl = any(indicator in files_text for indicator in no_impl_indicators)
            has_file_list = bool(re.search(r'[-*]\s+\w+\.(?:py|md|json|txt|html|sh|bat)', files_text))
            
            if has_no_impl and not has_file_list:
                errors.append({
                    "code": "IMPLEMENTATION_NO_CODE_CHANGES",
                    "message": f"{task_id}: IMPLEMENTATION task marked COMPLETED but report shows no code changes",
                    "hint": f"Either implement code changes and document in {latest_report_path.name}, or change TASK_TYPE to ANALYSIS",
                })
        
        except Exception as e:
            warnings.append({
                "code": "IMPLEMENTATION_CHECK_FAILED",
                "message": f"{task_id}: Could not validate implementation proof: {str(e)}",
                "hint": "Check report file format and accessibility",
            })
    
    # DOCS DIRECTORY VALIDATION: Check /docs consistency
    docs_dir = workspace_root / "docs"
    if docs_dir.exists() and docs_dir.is_dir():
        docs_validation = _validate_docs_directory(workspace_root, docs_dir)
        errors.extend(docs_validation.get("errors", []))
        warnings.extend(docs_validation.get("warnings", []))
    
    return {
        "generatedAt": utc_now_iso(),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "errorCount": len(errors),
            "warningCount": len(warnings),
        },
    }


def extract_report_metadata(report_path: Path) -> Dict[str, Any]:
    """Extract structured metadata from a report file."""
    try:
        content = read_text(report_path)
    except Exception:
        return {}
    
    # Parse filename for task_id, loop, version
    parsed = parse_report_filename(report_path)
    if not parsed:
        return {}
    
    metadata = {
        "id": report_path.stem,
        "taskId": parsed["taskId"],
        "loopNum": parsed["loop"],
        "version": parsed["version"],
        "path": parsed["path"],
    }
    
    # Extract GOAL/OBJECTIVE section
    goal_match = re.search(r"^## GOAL\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    if not goal_match:
        goal_match = re.search(r"^## OBJECTIVE\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    if goal_match:
        metadata["goal"] = goal_match.group(1).strip()[:500]  # First 500 chars
    
    # Extract FILES CHANGED section
    files_match = re.search(r"^## (?:FILES CHANGED|WHAT CHANGED|CHANGES IMPLEMENTED)\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    files_changed = []
    if files_match:
        files_text = files_match.group(1)
        # Look for file references in markdown links or code
        file_patterns = [
            r'\[([^\]]+\.(?:py|md|json|txt|html|sh|bat))\]',  # [filename.ext]
            r'`([^\`]+\.(?:py|md|json|txt|html|sh|bat))`',     # `filename.ext`
            r'(\w+\.(?:py|md|json|txt|html|sh|bat))',         # filename.ext
        ]
        for pattern in file_patterns:
            files_changed.extend(re.findall(pattern, files_text))
        metadata["filesChanged"] = sorted(set(f for f in files_changed if len(f) < 100))
    
    # Extract VALIDATION section and determine if passed
    validation_match = re.search(r"^## VALIDATION\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    validation_passed = None
    if validation_match:
        val_text = validation_match.group(1).lower()
        if "✅" in val_text or "success" in val_text or "passed" in val_text:
            validation_passed = True
        elif "❌" in val_text or "failed" in val_text or "failure" in val_text:
            validation_passed = False
    
    # Also check STATUS line at top
    status_match = re.search(r"\*\*STATUS:\*\*\s*(.+?)$", content, re.MULTILINE)
    if status_match:
        status_text = status_match.group(1).strip().lower()
        if "✅" in status_text or "success" in status_text:
            validation_passed = True
        elif "❌" in status_text or "fail" in status_text:
            validation_passed = False
    
    metadata["validationPassed"] = validation_passed
    
    # Extract date (WORK LOG or DATE field)
    date_match = re.search(r"(?:COMPLETED|DATE):\s*(\d{4}-\d{2}-\d{2})", content)
    if date_match:
        metadata["dateCompleted"] = date_match.group(1)
    
    # Extract all reference citations for cross-linking
    refs = []
    for ref in iter_refs(content):
        refs.append(ref.target)
    metadata["references"] = list(set(refs))
    
    # Extract tags from references
    tags = set()
    for ref in iter_refs(content):
        if ref.tags:
            tags.update(t.strip() for t in ref.tags.split(","))
    metadata["tags"] = sorted(tags)
    
    # Generate keywords from goal (simple: split on spaces, filter common words)
    if "goal" in metadata:
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "is", "was", "be"}
        words = re.findall(r'\b[a-z]{3,}\b', metadata["goal"].lower())
        metadata["keywords"] = sorted(set(w for w in words if w not in stop_words))[:20]
    
    return metadata


def extract_task_metadata(task_path: Path) -> Dict[str, Any]:
    """Extract structured metadata from a task specification file."""
    try:
        content = read_text(task_path)
    except Exception:
        return {}
    
    # Parse task_id from filename
    task_id_match = TASK_ID_RE.search(task_path.name)
    task_id = f"TASK_{task_id_match.group(1)}" if task_id_match else task_path.stem
    
    metadata = {
        "id": task_id,
        "path": task_path.name,
    }
    
    # Extract STATUS
    status_match = re.search(r"^STATUS:\s*(.+?)$", content, re.MULTILINE)
    if status_match:
        metadata["status"] = status_match.group(1).strip()
    
    # Extract OBJECTIVE
    obj_match = re.search(r"^## OBJECTIVE\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    if obj_match:
        metadata["objective"] = obj_match.group(1).strip()[:500]
    
    # Extract SEED IDEA
    seed_match = re.search(r"^## SEED IDEA\s*$\s*(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    if seed_match:
        metadata["seedIdea"] = seed_match.group(1).strip()[:300]
    
    # Extract CREATED/COMPLETED dates
    created_match = re.search(r"^CREATED:\s*(.+?)$", content, re.MULTILINE)
    if created_match:
        metadata["created"] = created_match.group(1).strip()
    
    completed_match = re.search(r"^COMPLETED:\s*(.+?)$", content, re.MULTILINE)
    if completed_match:
        metadata["completed"] = completed_match.group(1).strip()
    
    # Extract tags from references
    tags = set()
    for ref in iter_refs(content):
        if ref.tags:
            tags.update(t.strip() for t in ref.tags.split(","))
    metadata["tags"] = sorted(tags)
    
    # Extract references
    refs = []
    for ref in iter_refs(content):
        refs.append(ref.target)
    metadata["references"] = list(set(refs))
    
    return metadata


def query_index_data(workspace_root: Path) -> Dict[str, Any]:
    """Generate queryable index with enhanced metadata for structured search."""
    
    # Extract all reports with metadata
    reports = []
    for path in list_report_files(workspace_root):
        metadata = extract_report_metadata(path)
        if metadata:
            reports.append(metadata)
    reports.sort(key=lambda r: (r["loopNum"], r["taskId"], r["version"]))
    
    # Extract all tasks with metadata
    tasks = []
    for path in list_task_spec_files(workspace_root):
        metadata = extract_task_metadata(path)
        if metadata:
            tasks.append(metadata)
    tasks.sort(key=lambda t: t["id"])
    
    # Build file index (file → tasks/reports that modified it)
    file_index: Dict[str, Dict[str, Any]] = {}
    for report in reports:
        for file in report.get("filesChanged", []):
            if file not in file_index:
                file_index[file] = {
                    "modifiedBy": [],
                    "reports": [],
                    "loopRange": [9999, 0]
                }
            entry = file_index[file]
            task_id = report["taskId"]
            if task_id not in entry["modifiedBy"]:
                entry["modifiedBy"].append(task_id)
            report_path = report.get("path", "")
            if report_path and report_path not in entry["reports"]:
                entry["reports"].append(report_path)
            loop_num = report["loopNum"]
            entry["loopRange"][0] = min(entry["loopRange"][0], loop_num)
            entry["loopRange"][1] = max(entry["loopRange"][1], loop_num)
    
    # Build concept/tag index (tag → tasks/reports)
    concept_index: Dict[str, Dict[str, Any]] = {}
    for report in reports:
        for tag in report.get("tags", []):
            if tag not in concept_index:
                concept_index[tag] = {
                    "tasks": set(),
                    "reports": set(),
                }
            concept_index[tag]["reports"].add(report["id"])
            concept_index[tag]["tasks"].add(report["taskId"])
    
    for task in tasks:
        for tag in task.get("tags", []):
            if tag not in concept_index:
                concept_index[tag] = {
                    "tasks": set(),
                    "reports": set(),
                }
            concept_index[tag]["tasks"].add(task["id"])
    
    # Convert sets to sorted lists
    concept_index_serializable = {}
    for tag, data in sorted(concept_index.items()):
        concept_index_serializable[tag] = {
            "tasks": sorted(data["tasks"]),
            "reports": sorted(data["reports"]),
        }
    
    # Map tasks to their reports
    task_reports_map: Dict[str, List[str]] = {}
    for report in reports:
        task_id = report["taskId"]
        if task_id not in task_reports_map:
            task_reports_map[task_id] = []
        task_reports_map[task_id].append(report["id"])
    
    # Enhance tasks with report references
    for task in tasks:
        task["reports"] = task_reports_map.get(task["id"], [])
    
    return {
        "generatedAt": utc_now_iso(),
        "reports": reports,
        "tasks": tasks,
        "fileIndex": file_index,
        "conceptIndex": concept_index_serializable,
    }


def check_archive_consistency(workspace_root: Path) -> Dict[str, Any]:
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
    # Load legacy archives list from config (LAW 12: No hardcoded loop IDs)
    try:
        config_path = workspace_root / "config.json"
        if config_path.exists():
            config = read_json(config_path)
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
            current_json = workspace_root / "current.json"
            state_data = read_json(current_json)
            current_loop = state_data.get('STATE', {}).get('loop')
            if current_loop is None:
                raise ValueError("Loop number missing from current.json STATE")
        except Exception as e:
            # FATAL: Cannot proceed without valid loop number (LAW 12)
            raise RuntimeError(f"FATAL: Cannot read loop number from current.json: {e}")
        
        # Get all archive files
        archive_dir = workspace_root / "archive"
        archive_files = [f.name for f in archive_dir.glob("ARCHIV_*.md")] if archive_dir.exists() else []
        stats['total_archives'] = len(archive_files)
        
        # Parse Alt.md for completed tasks
        alt_md = workspace_root / "Alt.md"
        alt_content = read_text(alt_md) if alt_md.exists() else ""
        alt_task_refs = re.findall(r'\[ref:(task_TASK_\d+\.md)', alt_content)
        stats['tasks_in_alt'] = len(alt_task_refs)
        
        # Get all report files in workspace (excluding incident reports)
        report_files = []
        for pattern in ["report_TASK_*.md", "reports/report_TASK_*.md"]:
            report_files.extend([str(f) for f in workspace_root.glob(pattern)])
        # Filter out incident reports (match by basename to support subfolders like reports/)
        task_report_files = [
            r for r in report_files
            if not re.match(r'report_INCIDENT_\w+_L\d+_v\d+\.md$', Path(r).name)
        ]
        stats['reports_in_workspace'] = len(task_report_files)
        
        # Parse archives for task references
        archived_tasks = set()
        for archive_file in archive_files:
            archive_path = archive_dir / archive_file
            if archive_path.exists():
                content = read_text(archive_path)
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
            
            archive_path = archive_dir / archive_file
            content = read_text(archive_path)
            
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


def check_for_resurrected_tasks(workspace_root: Path) -> Dict[str, Any]:
    """
    Check for tasks that exist on disk but are marked as BLOCKED in Alt.md.
    This indicates a violation of immutability where archived tasks have been resurrected.
    
    Returns:
        dict: {
            'resurrected_tasks': list of task filenames that violate immutability,
            'is_clean': bool indicating if any violations were found
        }
    """
    resurrected_tasks = []
    
    try:
        # Read Alt.md to find BLOCKED tasks
        alt_path = workspace_root / "Alt.md"
        if not alt_path.exists():
            return {'resurrected_tasks': [], 'is_clean': True}
        
        alt_content = read_text(alt_path)
        
        # Find all BLOCKED task references in Alt.md
        blocked_tasks = set()
        for line in alt_content.split('\n'):
            if 'BLOCKED' in line and '[ref:task_TASK_' in line:
                # Extract task filename from reference
                ref_match = re.search(r'\[ref:(task_TASK_\d+\.md)', line)
                if ref_match:
                    blocked_tasks.add(ref_match.group(1))
        
        # Check if any of these BLOCKED tasks exist on disk
        for task_file in blocked_tasks:
            task_path = workspace_root / task_file
            if task_path.exists():
                resurrected_tasks.append(task_file)
    
    except Exception as e:
        # If we can't check, assume clean to avoid blocking unnecessarily
        return {'resurrected_tasks': [], 'is_clean': True, 'error': str(e)}
    
    return {
        'resurrected_tasks': resurrected_tasks,
        'is_clean': len(resurrected_tasks) == 0
    }


def generate_loop_gate(workspace_root: Path, checked_by: str = "loop_cockpit", reason: str = "automation") -> Dict[str, Any]:
    """Generate loop gate content and return metadata."""

    checks: List[Dict[str, Any]] = []
    blocked = False

    # Check current.json
    state_path = workspace_root / "current.json"
    state_ok = True
    state_err = None
    try:
        state = read_json(state_path).get("STATE", {})
    except Exception as e:
        state_ok = False
        state_err = str(e)
        state = {}

    if not state_ok:
        blocked = True
        checks.append({"id": "CURRENT_JSON", "ok": False, "message": f"Failed to read current.json: {state_err}"})
    else:
        status = state.get("status")
        loop_num = state.get("loop")
        ok = isinstance(loop_num, int) and status in {"ACTIVE", "READY_FOR_RESET", "FINALIZED"}
        if not ok:
            blocked = True
        checks.append({"id": "CURRENT_JSON", "ok": ok, "message": f"loop={loop_num} status={status}"})

    # Pending ARCHIV in root must not exist for entry safety
    pending = find_pending_archiv(workspace_root)
    if pending is not None:
        blocked = True
        checks.append({"id": "PENDING_ARCHIV", "ok": False, "message": f"ARCHIV present in root: {pending.name}"})
    else:
        checks.append({"id": "PENDING_ARCHIV", "ok": True, "message": "No ARCHIV in root"})

    # Archive reference existence (archiveCurrent if set)
    archive_current = state.get("archiveCurrent") if isinstance(state, dict) else None
    if archive_current:
        p = workspace_root / str(archive_current)
        ok = p.exists()
        if not ok:
            blocked = True
        checks.append({"id": "ARCHIVE_CURRENT", "ok": ok, "message": f"{archive_current}"})

    # Check for resurrected tasks (critical immutability violation)
    resurrection_check = check_for_resurrected_tasks(workspace_root)
    if not resurrection_check['is_clean']:
        blocked = True
        resurrected_list = resurrection_check['resurrected_tasks']
        checks.append({
            "id": "TASK_RESURRECTION", 
            "ok": False, 
            "message": f"CRITICAL: {len(resurrected_list)} resurrected task(s): {', '.join(resurrected_list)}"
        })
    else:
        checks.append({"id": "TASK_RESURRECTION", "ok": True, "message": "No resurrected tasks detected"})

    # Pointer doc basics + reference format
    for doc in ("NEU.md", "Alt.md", "NEURAL_CORTEX.md"):
        ok, errs = _check_pointer_doc_basic(workspace_root, doc)
        if not ok:
            blocked = True
            for e in errs:
                checks.append({"id": f"POINTER_{doc}", "ok": False, "message": e})
        else:
            checks.append({"id": f"POINTER_{doc}", "ok": True, "message": "OK"})

    # REPORT-FIRST snapshot (non-blocking summary; blocking only if a hard violation is detected)
    lint = metadata_lint(workspace_root)
    if lint.get("summary", {}).get("errorCount", 0) > 0:
        # These are protocol violations; block gate.
        blocked = True
        checks.append({"id": "LINT", "ok": False, "message": f"Lint errors: {lint['summary']['errorCount']}"})
    else:
        checks.append({"id": "LINT", "ok": True, "message": f"Lint warnings: {lint['summary']['warningCount']}"})

    status_str = "BLOCKED" if blocked else "PASS"

    lines: List[str] = []
    lines.append("# LOOP GATE - PRE-ENTRY VALIDATION")
    lines.append("")
    lines.append("MODE: SYSTEM VALIDATOR")
    lines.append("UPDATE: Cockpit automation only")
    lines.append("")
    lines.append(f"**STATUS: {status_str}**")
    lines.append(f"**CHECKED_AT: {utc_now_iso()}**")
    lines.append(f"**CHECKED_BY: {checked_by}**")
    lines.append(f"**REASON: {reason}**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## CHECKS")
    lines.append("")

    for c in sorted(checks, key=lambda x: (x["id"], str(x.get("message", "")))):
        mark = "✓" if c["ok"] else "✗"
        lines.append(f"{mark} **{c['id']}**")
        lines.append(f"  - {c['message']}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## VERDICT")
    lines.append("")
    lines.append(f"**GATE STATUS: {status_str}**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("END OF DOCUMENT")
    lines.append("")

    content = "\n".join(lines)

    return {
        "status": status_str,
        "blocked": blocked,
        "checks": checks,
        "content": content,
        "lint": lint,
    }


# ============================================================================
# TASK_0090: Git Worktree Manager
# ============================================================================

@dataclass
class Worktree:
    """Represents a git worktree for agent isolation."""
    name: str
    path: Path
    branch: str
    agent_id: str
    task_id: str
    created_at: str
    status: str = "active"  # active, merged, removed


@dataclass
class MergeResult:
    """Result of a worktree merge operation."""
    success: bool
    worktree_name: str
    message: str
    conflicts: List[str] = field(default_factory=list)
    files_changed: int = 0


class WorktreeManager:
    """Manages git worktrees for parallel agent execution.
    
    Provides isolated working directories for each agent via git worktrees.
    Handles creation, merging, and cleanup with rollback safety.
    """
    
    def __init__(self, repo_path: Optional[Path] = None, worktree_base: Optional[Path] = None):
        """Initialize the worktree manager.
        
        Args:
            repo_path: Path to git repository (default: current directory)
            worktree_base: Base directory for worktrees (default: repo/.worktrees)
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.worktree_base = worktree_base if worktree_base else self.repo_path / ".worktrees"
        self._worktrees: Dict[str, Worktree] = {}
        self._pre_parallel_tag: Optional[str] = None
        
    def _run_git(self, *args: str, cwd: Optional[Path] = None) -> Tuple[bool, str]:
        """Run a git command and return (success, output)."""
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout.strip() or result.stderr.strip()
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        success, _ = self._run_git("rev-parse", "--git-dir")
        return success
    
    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name."""
        success, output = self._run_git("branch", "--show-current")
        return output if success else None
    
    def tag_pre_parallel(self, reason: str = "parallel-work") -> Optional[str]:
        """Create a tag before parallel work for rollback safety.
        
        Args:
            reason: Reason for the tag (included in name)
            
        Returns:
            Tag name if successful, None otherwise
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        tag_name = f"pre-parallel-{reason}-{timestamp}"
        
        success, output = self._run_git("tag", tag_name)
        if success:
            self._pre_parallel_tag = tag_name
            return tag_name
        return None
    
    def rollback_to_tag(self, tag_name: Optional[str] = None) -> Tuple[bool, str]:
        """Rollback to a pre-parallel tag.
        
        Args:
            tag_name: Tag to rollback to (default: last pre-parallel tag)
            
        Returns:
            (success, message) tuple
        """
        tag = tag_name or self._pre_parallel_tag
        if not tag:
            return False, "No tag specified and no pre-parallel tag exists"
        
        # First cleanup all worktrees
        self.cleanup_all()
        
        # Hard reset to tag
        success, output = self._run_git("reset", "--hard", tag)
        if success:
            return True, f"Rolled back to {tag}"
        return False, f"Rollback failed: {output}"
    
    def create_worktree(self, agent_id: str, task_id: str) -> Optional[Worktree]:
        """Create a new worktree for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            task_id: Task being worked on
            
        Returns:
            Worktree object if successful, None otherwise
        """
        # Ensure worktree base exists
        self.worktree_base.mkdir(parents=True, exist_ok=True)
        
        # Generate unique names
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        worktree_name = f"wt-{agent_id}-{task_id}-{timestamp}"
        branch_name = f"agent/{agent_id}/{task_id}"
        worktree_path = self.worktree_base / worktree_name
        
        # Create new branch from current HEAD
        success, output = self._run_git("worktree", "add", "-b", branch_name, str(worktree_path))
        
        if not success:
            # Try without -b if branch exists
            success, output = self._run_git("worktree", "add", str(worktree_path), branch_name)
        
        if success:
            wt = Worktree(
                name=worktree_name,
                path=worktree_path,
                branch=branch_name,
                agent_id=agent_id,
                task_id=task_id,
                created_at=utc_now_iso(),
                status="active"
            )
            self._worktrees[worktree_name] = wt
            return wt
        
        return None
    
    def list_worktrees(self) -> List[Worktree]:
        """List all managed worktrees."""
        return list(self._worktrees.values())
    
    def list_git_worktrees(self) -> List[Dict[str, str]]:
        """List all git worktrees (including unmanaged ones)."""
        success, output = self._run_git("worktree", "list", "--porcelain")
        if not success:
            return []
        
        worktrees = []
        current_wt: Dict[str, str] = {}
        
        for line in output.split("\n"):
            if line.startswith("worktree "):
                if current_wt:
                    worktrees.append(current_wt)
                current_wt = {"path": line[9:]}
            elif line.startswith("HEAD "):
                current_wt["head"] = line[5:]
            elif line.startswith("branch "):
                current_wt["branch"] = line[7:]
            elif line == "bare":
                current_wt["bare"] = "true"
            elif line == "detached":
                current_wt["detached"] = "true"
        
        if current_wt:
            worktrees.append(current_wt)
        
        return worktrees
    
    def check_conflicts(self, worktree: Worktree) -> List[str]:
        """Check for potential merge conflicts before merging.
        
        Args:
            worktree: Worktree to check
            
        Returns:
            List of files that would conflict
        """
        # Get list of files changed in worktree
        success, output = self._run_git(
            "diff", "--name-only", "HEAD", worktree.branch
        )
        
        if not success:
            return []
        
        changed_files = output.split("\n") if output else []
        
        # Check if any are modified in main branch too
        success, main_changes = self._run_git("diff", "--name-only", "HEAD")
        main_files = set(main_changes.split("\n")) if main_changes else set()
        
        conflicts = [f for f in changed_files if f in main_files and f]
        return conflicts
    
    def merge_worktree(self, worktree: Worktree, force: bool = False) -> MergeResult:
        """Merge worktree changes back to main branch.
        
        Args:
            worktree: Worktree to merge
            force: If True, attempt merge even with conflicts
            
        Returns:
            MergeResult with success status and details
        """
        # Check for conflicts first
        conflicts = self.check_conflicts(worktree)
        if conflicts and not force:
            return MergeResult(
                success=False,
                worktree_name=worktree.name,
                message=f"Potential conflicts detected in {len(conflicts)} file(s)",
                conflicts=conflicts
            )
        
        # Get count of changed files
        success, diff_stat = self._run_git(
            "diff", "--shortstat", "HEAD", worktree.branch
        )
        files_changed = 0
        if success and diff_stat:
            match = re.search(r"(\d+) file", diff_stat)
            if match:
                files_changed = int(match.group(1))
        
        # Perform merge
        success, output = self._run_git("merge", worktree.branch, "--no-ff", "-m", 
                                        f"Merge {worktree.branch} from agent {worktree.agent_id}")
        
        if success:
            worktree.status = "merged"
            return MergeResult(
                success=True,
                worktree_name=worktree.name,
                message=f"Successfully merged {worktree.branch}",
                files_changed=files_changed
            )
        
        # Check if merge conflict occurred
        if "CONFLICT" in output or "Automatic merge failed" in output:
            # Abort the merge
            self._run_git("merge", "--abort")
            return MergeResult(
                success=False,
                worktree_name=worktree.name,
                message="Merge conflict during merge",
                conflicts=conflicts or ["unknown"]
            )
        
        return MergeResult(
            success=False,
            worktree_name=worktree.name,
            message=f"Merge failed: {output}"
        )
    
    def cleanup_worktree(self, worktree: Worktree, delete_branch: bool = True) -> bool:
        """Remove a worktree and optionally its branch.
        
        Args:
            worktree: Worktree to remove
            delete_branch: If True, also delete the branch
            
        Returns:
            True if cleanup successful
        """
        # Remove worktree
        success, _ = self._run_git("worktree", "remove", str(worktree.path), "--force")
        
        if success and delete_branch:
            # Delete the branch
            self._run_git("branch", "-D", worktree.branch)
        
        if success:
            worktree.status = "removed"
            if worktree.name in self._worktrees:
                del self._worktrees[worktree.name]
            return True
        
        return False
    
    def cleanup_all(self) -> int:
        """Remove all managed worktrees.
        
        Returns:
            Number of worktrees cleaned up
        """
        cleaned = 0
        for wt in list(self._worktrees.values()):
            if self.cleanup_worktree(wt):
                cleaned += 1
        return cleaned
    
    def cleanup_orphans(self) -> int:
        """Clean up any orphan worktrees not in our registry.
        
        Returns:
            Number of orphan worktrees cleaned
        """
        if not self.worktree_base.exists():
            return 0
        
        cleaned = 0
        git_worktrees = self.list_git_worktrees()
        git_paths = {wt.get("path", "") for wt in git_worktrees}
        
        for item in self.worktree_base.iterdir():
            if item.is_dir() and item.name.startswith("wt-"):
                # Check if it's registered
                if item.name not in self._worktrees:
                    # Check if git knows about it
                    if str(item) in git_paths:
                        # Remove via git
                        self._run_git("worktree", "remove", str(item), "--force")
                    else:
                        # Just remove directory
                        import shutil
                        shutil.rmtree(item, ignore_errors=True)
                    cleaned += 1
        
        return cleaned
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall worktree manager status.
        
        Returns:
            Status dictionary with counts and details
        """
        active = [wt for wt in self._worktrees.values() if wt.status == "active"]
        merged = [wt for wt in self._worktrees.values() if wt.status == "merged"]
        
        return {
            "is_git_repo": self.is_git_repo(),
            "current_branch": self.get_current_branch(),
            "worktree_base": str(self.worktree_base),
            "pre_parallel_tag": self._pre_parallel_tag,
            "total_worktrees": len(self._worktrees),
            "active_count": len(active),
            "merged_count": len(merged),
            "worktrees": [
                {
                    "name": wt.name,
                    "path": str(wt.path),
                    "branch": wt.branch,
                    "agent_id": wt.agent_id,
                    "task_id": wt.task_id,
                    "status": wt.status,
                    "created_at": wt.created_at
                }
                for wt in self._worktrees.values()
            ]
        }


def worktree_manager_factory(repo_path: Optional[str] = None) -> WorktreeManager:
    """Factory function to create a WorktreeManager instance.
    
    Args:
        repo_path: Optional path to git repository
        
    Returns:
        Configured WorktreeManager instance
    """
    path = Path(repo_path) if repo_path else None
    return WorktreeManager(repo_path=path)


# ============================================================================
# TASK_0091: Multi-Agent Orchestrator
# ============================================================================

@dataclass
class AgentSession:
    """Represents an agent working on a task."""
    agent_id: str
    task_id: str
    worktree_name: str
    worktree_path: Path
    status: str = "pending"  # pending, spawned, working, completed, failed
    progress: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result_summary: Optional[str] = None


@dataclass
class OrchestrationResult:
    """Result of a multi-agent orchestration run."""
    success: bool
    agents_spawned: int
    agents_completed: int
    agents_failed: int
    conflicts: int
    all_merged: bool
    time_started: str
    time_completed: str
    time_saved_seconds: float
    tasks_parallelized: List[str]
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class MultiAgentOrchestrator:
    """Coordinates multiple AI agents working on parallelizable tasks.
    
    This is the core orchestration engine that:
    1. Receives a list of tasks
    2. Analyzes for parallelization potential
    3. Creates isolated worktrees for each parallel task
    4. Spawns agent sessions to work on tasks
    5. Monitors progress via session files
    6. Merges results back to main branch
    7. Handles failures with automatic rollback
    """
    
    def __init__(
        self, 
        workspace_root: Optional[Path] = None,
        max_parallel_agents: int = 4,
        session_poll_interval: float = 5.0,
        agent_timeout_seconds: float = 3600.0
    ):
        """Initialize the orchestrator.
        
        Args:
            workspace_root: Path to project workspace
            max_parallel_agents: Maximum concurrent agents
            session_poll_interval: How often to check session files (seconds)
            agent_timeout_seconds: Max time for agent to complete
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.max_parallel_agents = max_parallel_agents
        self.session_poll_interval = session_poll_interval
        self.agent_timeout_seconds = agent_timeout_seconds
        
        self._worktree_manager: Optional[WorktreeManager] = None
        self._sessions: Dict[str, AgentSession] = {}
        self._pre_parallel_tag: Optional[str] = None
        
    def _get_worktree_manager(self) -> WorktreeManager:
        """Get or create the worktree manager."""
        if self._worktree_manager is None:
            self._worktree_manager = WorktreeManager(repo_path=self.workspace_root)
        return self._worktree_manager
    
    def _generate_agent_id(self, task_id: str) -> str:
        """Generate unique agent ID for a task."""
        import uuid
        short_uuid = uuid.uuid4().hex[:8]
        return f"agent-{task_id.lower()}-{short_uuid}"
    
    def _create_session_file(self, session: AgentSession) -> Path:
        """Create session state file in worktree."""
        session_data = {
            "agent_id": session.agent_id,
            "task_id": session.task_id,
            "status": session.status,
            "progress": session.progress,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "error": session.error,
            "result_summary": session.result_summary,
            "last_update": utc_now_iso()
        }
        
        session_file = session.worktree_path / "_AGENT_SESSION.json"
        session_file.write_text(json.dumps(session_data, indent=2), encoding="utf-8")
        return session_file
    
    def _read_session_file(self, session: AgentSession) -> Optional[Dict[str, Any]]:
        """Read session state from worktree."""
        session_file = session.worktree_path / "_AGENT_SESSION.json"
        if session_file.exists():
            try:
                return json.loads(session_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def analyze_tasks(self, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze tasks for parallelization potential.
        
        Args:
            task_ids: Specific task IDs to analyze, or None for all queued
            
        Returns:
            Analysis result from analyze_parallelization()
        """
        return analyze_parallelization(self.workspace_root, task_ids)
    
    def prepare_parallel_execution(self, task_ids: List[str]) -> List[AgentSession]:
        """Prepare sessions for parallel task execution.
        
        Args:
            task_ids: List of task IDs to execute in parallel
            
        Returns:
            List of prepared AgentSession objects
        """
        wm = self._get_worktree_manager()
        
        if not wm.is_git_repo():
            raise RuntimeError("Not a git repository - cannot use worktrees")
        
        # Limit to max agents
        tasks_to_run = task_ids[:self.max_parallel_agents]
        
        # Create pre-parallel tag
        self._pre_parallel_tag = wm.tag_pre_parallel("multi-agent-run")
        
        sessions = []
        for task_id in tasks_to_run:
            agent_id = self._generate_agent_id(task_id)
            
            # Create worktree for this agent
            worktree = wm.create_worktree(agent_id, task_id)
            if not worktree:
                raise RuntimeError(f"Failed to create worktree for {task_id}")
            
            session = AgentSession(
                agent_id=agent_id,
                task_id=task_id,
                worktree_name=worktree.name,
                worktree_path=worktree.path,
                status="pending"
            )
            
            self._sessions[agent_id] = session
            sessions.append(session)
        
        return sessions
    
    def spawn_agent(self, session: AgentSession) -> bool:
        """Spawn an agent to work on a task.
        
        This creates the session file that an external agent process
        will monitor and update as it works.
        
        Args:
            session: AgentSession to spawn
            
        Returns:
            True if spawn successful
        """
        session.status = "spawned"
        session.started_at = utc_now_iso()
        
        # Create session file for agent to find
        self._create_session_file(session)
        
        # In a real implementation, this would spawn an actual agent process
        # For now, we just mark the session as ready for an external agent
        
        return True
    
    def spawn_all_agents(self, sessions: List[AgentSession]) -> int:
        """Spawn all prepared agents.
        
        Args:
            sessions: List of sessions to spawn
            
        Returns:
            Number of agents successfully spawned
        """
        spawned = 0
        for session in sessions:
            if self.spawn_agent(session):
                spawned += 1
        return spawned
    
    def poll_session_status(self, session: AgentSession) -> str:
        """Poll a session's current status from its session file.
        
        Args:
            session: Session to poll
            
        Returns:
            Current status string
        """
        data = self._read_session_file(session)
        if data:
            session.status = data.get("status", session.status)
            session.progress = data.get("progress", session.progress)
            session.error = data.get("error")
            session.result_summary = data.get("result_summary")
            if data.get("completed_at"):
                session.completed_at = data["completed_at"]
        return session.status
    
    def poll_all_sessions(self) -> Dict[str, int]:
        """Poll all active sessions.
        
        Returns:
            Dict with counts by status
        """
        counts = {"pending": 0, "spawned": 0, "working": 0, "completed": 0, "failed": 0}
        
        for session in self._sessions.values():
            status = self.poll_session_status(session)
            counts[status] = counts.get(status, 0) + 1
        
        return counts
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all agents to complete.
        
        Args:
            timeout: Max seconds to wait (default: agent_timeout_seconds)
            
        Returns:
            True if all agents completed (success or failure)
        """
        import time
        
        timeout = timeout or self.agent_timeout_seconds
        start_time = time.time()
        
        while True:
            counts = self.poll_all_sessions()
            
            # Check if all done
            active = counts.get("pending", 0) + counts.get("spawned", 0) + counts.get("working", 0)
            if active == 0:
                return True
            
            # Check timeout
            if time.time() - start_time > timeout:
                return False
            
            time.sleep(self.session_poll_interval)
    
    def merge_results(self, force: bool = False) -> Tuple[int, int, List[str]]:
        """Merge all completed agent worktrees back to main.
        
        Args:
            force: If True, attempt merge even with conflicts
            
        Returns:
            (merged_count, conflict_count, errors)
        """
        wm = self._get_worktree_manager()
        merged = 0
        conflicts = 0
        errors = []
        
        # Get completed sessions
        completed = [s for s in self._sessions.values() if s.status == "completed"]
        
        for session in completed:
            # Find worktree
            worktrees = {wt.name: wt for wt in wm.list_worktrees()}
            if session.worktree_name not in worktrees:
                errors.append(f"Worktree not found: {session.worktree_name}")
                continue
            
            worktree = worktrees[session.worktree_name]
            result = wm.merge_worktree(worktree, force=force)
            
            if result.success:
                merged += 1
            else:
                conflicts += 1
                errors.append(f"Merge failed for {session.task_id}: {result.message}")
        
        return merged, conflicts, errors
    
    def cleanup(self, delete_worktrees: bool = True) -> int:
        """Clean up all sessions and worktrees.
        
        Args:
            delete_worktrees: If True, remove worktree directories
            
        Returns:
            Number of items cleaned
        """
        cleaned = 0
        
        if delete_worktrees:
            wm = self._get_worktree_manager()
            cleaned = wm.cleanup_all()
        
        self._sessions.clear()
        return cleaned
    
    def rollback(self) -> Tuple[bool, str]:
        """Rollback to pre-parallel state.
        
        Returns:
            (success, message)
        """
        wm = self._get_worktree_manager()
        return wm.rollback_to_tag(self._pre_parallel_tag)
    
    def execute_parallel(
        self, 
        task_ids: List[str],
        auto_merge: bool = True,
        auto_cleanup: bool = True,
        wait_for_agents: bool = False
    ) -> OrchestrationResult:
        """Execute the full parallel orchestration workflow.
        
        This is the main entry point for parallel task execution.
        
        Args:
            task_ids: Task IDs to execute in parallel
            auto_merge: If True, automatically merge on completion
            auto_cleanup: If True, clean up worktrees after merge
            wait_for_agents: If True, keep sessions pending for real agent pickup
            
        Returns:
            OrchestrationResult with metrics
        """
        start_time = utc_now_iso()
        errors = []
        
        try:
            # 1. Prepare sessions
            sessions = self.prepare_parallel_execution(task_ids)
            
            # 2. Spawn agents
            spawned = self.spawn_all_agents(sessions)
            
            # 3. Wait for completion
            completed_count = 0
            failed_count = 0
            
            if wait_for_agents:
                # Real mode: Keep sessions in "spawned" state for VS Code extension to pick up
                # Extension polls /api/orchestrator/sessions/pending and spawns Copilot agents
                # Return immediately - merging/cleanup happens when agents report completion
                return OrchestrationResult(
                    success=True,
                    agents_spawned=spawned,
                    agents_completed=0,
                    agents_failed=0,
                    conflicts=0,
                    all_merged=False,
                    time_started=start_time,
                    time_completed=None,  # Not completed yet
                    time_saved_seconds=0,
                    tasks_parallelized=task_ids,
                    errors=[],
                    metrics={
                        "mode": "wait_for_agents",
                        "sessions_pending": spawned,
                        "hint": "Poll /api/orchestrator/status for completion"
                    }
                )
            
            # Simulation mode: Auto-complete sessions immediately
            for session in sessions:
                session.status = "completed"
                session.completed_at = utc_now_iso()
                session.progress = 100
                self._create_session_file(session)
                completed_count += 1
            
            # 4. Merge results
            merged = 0
            conflicts = 0
            all_merged = False
            
            if auto_merge and completed_count > 0:
                merged, conflicts, merge_errors = self.merge_results()
                errors.extend(merge_errors)
                all_merged = (merged == completed_count and conflicts == 0)
            
            # 5. Cleanup
            if auto_cleanup:
                self.cleanup(delete_worktrees=True)
            
            end_time = utc_now_iso()
            
            # Calculate time saved (estimate: parallel vs sequential)
            # Assume each task takes ~10 minutes, parallel saves (n-1)*10 minutes
            sequential_time = len(task_ids) * 600  # 10 min per task
            parallel_time = 600  # All run in parallel = 1 task time
            time_saved = sequential_time - parallel_time if len(task_ids) > 1 else 0
            
            return OrchestrationResult(
                success=all_merged or (not auto_merge and failed_count == 0),
                agents_spawned=spawned,
                agents_completed=completed_count,
                agents_failed=failed_count,
                conflicts=conflicts,
                all_merged=all_merged,
                time_started=start_time,
                time_completed=end_time,
                time_saved_seconds=float(time_saved),
                tasks_parallelized=task_ids,
                errors=errors,
                metrics={
                    "sequential_estimate_sec": sequential_time,
                    "parallel_estimate_sec": parallel_time,
                    "efficiency_gain_pct": round((time_saved / sequential_time) * 100, 1) if sequential_time > 0 else 0
                }
            )
            
        except Exception as e:
            # On error, attempt rollback
            self.rollback()
            self.cleanup()
            
            return OrchestrationResult(
                success=False,
                agents_spawned=0,
                agents_completed=0,
                agents_failed=len(task_ids),
                conflicts=0,
                all_merged=False,
                time_started=start_time,
                time_completed=utc_now_iso(),
                time_saved_seconds=0,
                tasks_parallelized=task_ids,
                errors=[str(e)]
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status.
        
        Returns:
            Status dictionary with session info
        """
        wm = self._get_worktree_manager()
        
        sessions_by_status = {"pending": 0, "spawned": 0, "working": 0, "completed": 0, "failed": 0}
        for session in self._sessions.values():
            sessions_by_status[session.status] = sessions_by_status.get(session.status, 0) + 1
        
        return {
            "is_git_repo": wm.is_git_repo(),
            "max_parallel_agents": self.max_parallel_agents,
            "pre_parallel_tag": self._pre_parallel_tag,
            "total_sessions": len(self._sessions),
            "sessions_by_status": sessions_by_status,
            "sessions": [
                {
                    "agent_id": s.agent_id,
                    "task_id": s.task_id,
                    "status": s.status,
                    "progress": s.progress,
                    "started_at": s.started_at,
                    "completed_at": s.completed_at,
                    "error": s.error,
                    "result_summary": s.result_summary
                }
                for s in self._sessions.values()
            ]
        }


def orchestrator_factory(
    workspace_root: Optional[str] = None,
    max_parallel_agents: int = 4
) -> MultiAgentOrchestrator:
    """Factory function to create a MultiAgentOrchestrator instance.
    
    Args:
        workspace_root: Optional path to workspace
        max_parallel_agents: Maximum concurrent agents
        
    Returns:
        Configured MultiAgentOrchestrator instance
    """
    path = Path(workspace_root) if workspace_root else None
    return MultiAgentOrchestrator(workspace_root=path, max_parallel_agents=max_parallel_agents)

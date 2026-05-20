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
from dataclasses import dataclass
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
        reports.append(parsed)
    reports.sort(key=lambda r: (r["loop"], r["taskId"], r["version"], r["path"]))

    # Group reports per task
    reports_by_task: Dict[str, List[Dict[str, Any]]] = {}
    for r in reports:
        reports_by_task.setdefault(r["taskId"], []).append(r)

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

    # Orphaned reports not referenced by Alt.md (incident reports excluded)
    alt_content = read_text(workspace_root / "Alt.md") if (workspace_root / "Alt.md").exists() else ""
    neu_content = read_text(workspace_root / "NEU.md") if (workspace_root / "NEU.md").exists() else ""
    alt_report_ref_paths = set(re.findall(r"\[ref:([^\]|]*report_TASK_\d{4}_L\d{2}_v\d+\.md)", alt_content))
    alt_report_ref_paths = {p.replace("\\", "/") for p in alt_report_ref_paths}
    alt_report_ref_names = {Path(p).name for p in alt_report_ref_paths}

    for p in list_report_files(workspace_root):
        if re.match(r"report_INCIDENT_\w+_L\d+_v\d+\.md$", p.name):
            continue
        parsed = parse_report_filename(p)
        if not parsed:
            continue
        rel = str(p.relative_to(workspace_root)).replace("\\", "/")
        if (rel not in alt_report_ref_paths) and (p.name not in alt_report_ref_names):
            warnings.append({
                "code": "ORPHAN_REPORT",
                "message": f"Report not referenced in Alt.md: {rel}",
                "hint": "Add the report ref under the corresponding task in Alt.md (or confirm it is intentional)",
            })

    # Task specs that exist on disk but are not referenced in NEU.md or Alt.md
    # This commonly indicates a "lost" injected task (created but never linked).
    referenced_task_paths = set(re.findall(r"\[ref:([^\]|]*task_TASK_\d{4}\.md)", alt_content + "\n" + neu_content))
    referenced_task_paths = {p.replace("\\", "/") for p in referenced_task_paths}
    referenced_task_names = {Path(p).name for p in referenced_task_paths}

    for task_file in list_task_spec_files(workspace_root):
        rel = str(task_file.relative_to(workspace_root)).replace("\\", "/")
        if (rel not in referenced_task_paths) and (task_file.name not in referenced_task_names):
            warnings.append({
                "code": "ORPHAN_TASK_SPEC",
                "message": f"Task spec not referenced in NEU.md or Alt.md: {rel}",
                "hint": "Add a [ref:...] entry to NEU.md (active) or Alt.md (closed/blocked), or delete if it was created by mistake",
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

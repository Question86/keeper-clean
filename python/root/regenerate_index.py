# MODE: SCRIPT\n\n#!/usr/bin/env python3
"""
regenerate_index.py - Archive Index Regeneration Tool

Scans all archives and generates:
1. Updated HISTORY_INDEX.md with epoch metadata
2. HISTORY_INDEX.json for programmatic queries

Part of TASK_0133: Archive Index Foundation & Epoch Boundaries (C3-Phase1)
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Constants
EPOCH_SIZE = 50
ARCHIVE_DIR = "archive"
TASKS_DIR = "tasks"
REPORTS_DIR = "reports"
DOCS_DIR = "docs"

# Epoch definitions
EPOCH_NAMES = {
    1: "Foundation Era",
    2: "Automation Era",
    3: "Scaling Era",
}


def get_epoch(loop_number: int) -> int:
    """Calculate epoch number from loop number (1-indexed)."""
    return ((loop_number - 1) // EPOCH_SIZE) + 1


def get_epoch_range(epoch: int) -> Tuple[int, int]:
    """Get loop range for an epoch (inclusive)."""
    start = (epoch - 1) * EPOCH_SIZE + 1
    end = epoch * EPOCH_SIZE
    return (start, end)


def get_epoch_name(epoch: int) -> str:
    """Get human-readable epoch name."""
    return EPOCH_NAMES.get(epoch, f"Epoch {epoch}")


def scan_archives(workspace: Path) -> List[Dict[str, Any]]:
    """Scan all archive files and extract metadata."""
    archive_dir = workspace / ARCHIVE_DIR
    archives = []
    
    if not archive_dir.exists():
        return archives
    
    archive_pattern = re.compile(r"ARCHIV_(\d{4})\.md")
    
    for file in sorted(archive_dir.iterdir()):
        if not file.is_file():
            continue
        match = archive_pattern.match(file.name)
        if not match:
            continue
        
        loop_num = int(match.group(1))
        archive_data = {
            "loop": loop_num,
            "filename": file.name,
            "path": str(file.relative_to(workspace)),
            "epoch": get_epoch(loop_num),
            "finalized": None,
            "lastTask": None,
            "tasks": [],
        }
        
        # Parse archive content
        try:
            content = file.read_text(encoding="utf-8")
            
            # Extract finalized date (multiple formats, case-insensitive)
            # Format 1: FINALIZED: 2026-01-10T12:30:00Z
            # Format 2: **ARCHIVED:** 2026-01-10T12:30:00Z
            # Format 3: CREATED: 2026-01-10T09:17:14Z (for loops that use CREATED instead)
            # Format 4: **Finalized:** 2026-01-12T19:48:00Z (mixed case with bold)
            # Format 5: **COMPLETED:** 2026-01-10T17:20:00Z
            # Format 6: **FINALIZED_AT:** 2026-01-11T03:27:56Z
            finalized_match = re.search(
                r"\*?\*?(?:FINALIZED|ARCHIVED|CREATED|Finalized|COMPLETED|FINALIZED_AT):\*?\*?\s*(\d{4}-\d{2}-\d{2}T[\d:]+Z?)",
                content, re.IGNORECASE
            )
            if finalized_match:
                archive_data["finalized"] = finalized_match.group(1)
            
            # Extract last task worked (multiple formats)
            # Format 1: **Last Task Worked:** TASK_XXXX (bold, most common)
            # Format 2: Last Task Worked: TASK_XXXX (no bold)
            # Format 3: - Last Task Worked: TASK_XXXX (list item)
            task_match = re.search(r"\*?\*?Last Task Worked:\*?\*?\s*(TASK_\d{4})", content)
            if task_match:
                archive_data["lastTask"] = task_match.group(1)
            
            # Extract all task references
            task_refs = re.findall(r"(TASK_\d{4})", content)
            archive_data["tasks"] = sorted(list(set(task_refs)))
            
        except Exception as e:
            print(f"Warning: Error parsing {file.name}: {e}")
    
        archives.append(archive_data)
    
    return archives


def scan_tasks(workspace: Path) -> List[Dict[str, Any]]:
    """Scan task files from both root and tasks directory."""
    tasks = []
    task_pattern = re.compile(r"task_(TASK_\d{4})\.md")
    status_pattern = re.compile(r"STATUS:\s*(\w+)")
    
    # Check root directory
    for file in workspace.iterdir():
        if file.is_file():
            match = task_pattern.match(file.name)
            if match:
                tasks.append(_parse_task_file(file, workspace, match.group(1)))
    
    # Check tasks subdirectory
    tasks_dir = workspace / TASKS_DIR
    if tasks_dir.exists():
        for file in tasks_dir.iterdir():
            if file.is_file():
                match = task_pattern.match(file.name)
                if match:
                    tasks.append(_parse_task_file(file, workspace, match.group(1)))
    
    return sorted(tasks, key=lambda x: x["id"])


def _parse_task_file(file: Path, workspace: Path, task_id: str) -> Dict[str, Any]:
    """Parse a task file and extract metadata."""
    task_data = {
        "id": task_id,
        "filename": file.name,
        "path": str(file.relative_to(workspace)),
        "status": "UNKNOWN",
        "reports": [],
    }
    
    try:
        content = file.read_text(encoding="utf-8")
        status_match = re.search(r"STATUS:\s*(\w+)", content)
        if status_match:
            task_data["status"] = status_match.group(1)
    except Exception as e:
        print(f"Warning: Error parsing {file.name}: {e}")
    
    return task_data


def scan_reports(workspace: Path) -> List[Dict[str, Any]]:
    """Scan report files from both root and reports directory."""
    reports = []
    report_pattern = re.compile(r"report_(TASK_\d{4}|INCIDENT)_L(\d+)_v(\d+)\.md")
    
    # Check root directory
    for file in workspace.iterdir():
        if file.is_file():
            match = report_pattern.match(file.name)
            if match:
                reports.append(_parse_report_file(file, workspace, match))
    
    # Check reports subdirectory
    reports_dir = workspace / REPORTS_DIR
    if reports_dir.exists():
        for file in reports_dir.iterdir():
            if file.is_file():
                match = report_pattern.match(file.name)
                if match:
                    reports.append(_parse_report_file(file, workspace, match))
    
    return sorted(reports, key=lambda x: (x["taskId"], x["loop"], x["version"]))


def _parse_report_file(file: Path, workspace: Path, match: re.Match) -> Dict[str, Any]:
    """Parse a report file and extract metadata."""
    return {
        "taskId": match.group(1),
        "loop": int(match.group(2)),
        "version": int(match.group(3)),
        "filename": file.name,
        "path": str(file.relative_to(workspace)),
        "epoch": get_epoch(int(match.group(2))),
    }


def build_epoch_summaries(archives: List[Dict], tasks: List[Dict], reports: List[Dict]) -> Dict[int, Dict]:
    """Build summary statistics for each epoch."""
    epochs = {}
    
    # Group archives by epoch
    for archive in archives:
        epoch = archive["epoch"]
        if epoch not in epochs:
            start, end = get_epoch_range(epoch)
            epochs[epoch] = {
                "epoch": epoch,
                "name": get_epoch_name(epoch),
                "loopRange": [start, end],
                "status": "PLANNED",
                "archiveCount": 0,
                "taskCount": 0,
                "reportCount": 0,
                "archives": [],
                "tasks": set(),
            }
        epochs[epoch]["archiveCount"] += 1
        epochs[epoch]["archives"].append(archive["loop"])
        epochs[epoch]["tasks"].update(archive.get("tasks", []))
    
    # Count reports by epoch
    for report in reports:
        epoch = report["epoch"]
        if epoch in epochs:
            epochs[epoch]["reportCount"] += 1
    
    # Finalize status and convert sets
    for epoch_num, epoch_data in epochs.items():
        start, end = epoch_data["loopRange"]
        if epoch_data["archiveCount"] >= EPOCH_SIZE:
            epoch_data["status"] = "COMPLETE"
        elif epoch_data["archiveCount"] > 0:
            epoch_data["status"] = "IN_PROGRESS"
        
        epoch_data["taskCount"] = len(epoch_data["tasks"])
        epoch_data["tasks"] = sorted(list(epoch_data["tasks"]))
    
    return epochs


def build_task_index(tasks: List[Dict], reports: List[Dict], archives: List[Dict]) -> Dict[str, Dict]:
    """Build task → archives/reports cross-reference."""
    task_index = {}
    
    for task in tasks:
        task_id = task["id"]
        task_index[task_id] = {
            "id": task_id,
            "path": task["path"],
            "status": task["status"],
            "reports": [],
            "archives": [],
        }
    
    # Map reports to tasks
    for report in reports:
        task_id = report["taskId"]
        if task_id not in task_index:
            task_index[task_id] = {
                "id": task_id,
                "path": None,
                "status": "UNKNOWN",
                "reports": [],
                "archives": [],
            }
        task_index[task_id]["reports"].append({
            "path": report["path"],
            "loop": report["loop"],
            "version": report["version"],
        })
    
    # Map archives to tasks
    for archive in archives:
        for task_id in archive.get("tasks", []):
            if task_id not in task_index:
                task_index[task_id] = {
                    "id": task_id,
                    "path": None,
                    "status": "UNKNOWN",
                    "reports": [],
                    "archives": [],
                }
            if archive["loop"] not in task_index[task_id]["archives"]:
                task_index[task_id]["archives"].append(archive["loop"])
    
    # Sort archives
    for task_data in task_index.values():
        task_data["archives"] = sorted(task_data["archives"])
    
    return task_index


def generate_json_index(
    archives: List[Dict],
    tasks: List[Dict],
    reports: List[Dict],
    epochs: Dict[int, Dict],
    task_index: Dict[str, Dict],
) -> Dict[str, Any]:
    """Generate complete JSON index."""
    from datetime import timezone
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": 1,
        "schema": "history_index_v1",
        "summary": {
            "totalArchives": len(archives),
            "totalTasks": len(tasks),
            "totalReports": len(reports),
            "totalEpochs": len(epochs),
            "latestLoop": max([a["loop"] for a in archives]) if archives else 0,
        },
        "epochs": {str(k): {
            "epoch": v["epoch"],
            "name": v["name"],
            "loopRange": v["loopRange"],
            "status": v["status"],
            "archiveCount": v["archiveCount"],
            "taskCount": v["taskCount"],
            "reportCount": v["reportCount"],
        } for k, v in epochs.items()},
        "archives": {str(a["loop"]): {
            "path": a["path"],
            "epoch": a["epoch"],
            "finalized": a["finalized"],
            "lastTask": a["lastTask"],
        } for a in archives},
        "tasks": task_index,
    }


def generate_markdown_index(
    archives: List[Dict],
    tasks: List[Dict],
    reports: List[Dict],
    epochs: Dict[int, Dict],
    task_index: Dict[str, Dict],
) -> str:
    """Generate HISTORY_INDEX.md with epoch metadata."""
    from datetime import timezone
    lines = [
        "# HISTORY INDEX",
        "",
        "MODE: GENERATED",
        "HISTORICAL: true (contains references to all archived loops by design)",
        f"GENERATED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "VERSION: 2 (with epochs)",
        "",
        "---",
        "",
        "## EPOCH SUMMARY",
        "",
    ]
    
    # Epoch summaries
    for epoch_num in sorted(epochs.keys()):
        epoch = epochs[epoch_num]
        status_icon = "✅" if epoch["status"] == "COMPLETE" else "🔄" if epoch["status"] == "IN_PROGRESS" else "📋"
        lines.append(f"### Epoch {epoch_num}: {epoch['name']} (Loops {epoch['loopRange'][0]}-{epoch['loopRange'][1]})")
        lines.append(f"- **Status:** {status_icon} {epoch['status']}")
        lines.append(f"- **Archives:** {epoch['archiveCount']}/{EPOCH_SIZE}")
        lines.append(f"- **Tasks Referenced:** {epoch['taskCount']}")
        lines.append(f"- **Reports:** {epoch['reportCount']}")
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "## TASKS → REPORTS",
        "",
    ])
    
    # Task index
    for task_id in sorted(task_index.keys()):
        task = task_index[task_id]
        task_path = task["path"] if task["path"] else f"(no file)"
        lines.append(f"- {task_id}: [ref:{task_path}|v:1|tags:task|src:system]")
        for report in task["reports"]:
            lines.append(f"  - Report L{report['loop']:02d} v{report['version']:02d}: [ref:{report['path']}|v:{report['version']}|tags:report|src:system]")
    
    lines.extend([
        "",
        "---",
        "",
        "## ARCHIVES BY EPOCH",
        "",
    ])
    
    # Archives grouped by epoch
    for epoch_num in sorted(epochs.keys()):
        epoch = epochs[epoch_num]
        lines.append(f"### Epoch {epoch_num}: {epoch['name']}")
        lines.append("")
        for archive in archives:
            if archive["epoch"] == epoch_num:
                lines.append(f"- Loop {archive['loop']}: [ref:{archive['path']}|v:immutable|tags:archive|src:system]")
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "## PROGRAMMATIC ACCESS",
        "",
        "For machine-readable queries, see: [ref:docs/HISTORY_INDEX.json|v:dynamic|tags:index,json|src:system]",
        "",
        "### Quick Lookups",
        "",
        "```python",
        "import json",
        "with open('docs/HISTORY_INDEX.json') as f:",
        "    index = json.load(f)",
        "",
        "# Find all archives in Epoch 1",
        "epoch1_archives = [a for a in index['archives'].values() if a['epoch'] == 1]",
        "",
        "# Find reports for a task",
        "task_reports = index['tasks']['TASK_0001']['reports']",
        "",
        "# Get epoch status",
        "epoch_status = index['epochs']['1']['status']",
        "```",
        "",
        "---",
        "",
        "END OF DOCUMENT",
    ])
    
    return "\n".join(lines)


def regenerate_index(workspace_path: str = ".") -> Dict[str, Any]:
    """Main entry point for index regeneration."""
    workspace = Path(workspace_path).resolve()
    
    print(f"Scanning workspace: {workspace}")
    
    # Scan all artifacts
    print("Scanning archives...")
    archives = scan_archives(workspace)
    print(f"  Found {len(archives)} archives")
    
    print("Scanning tasks...")
    tasks = scan_tasks(workspace)
    print(f"  Found {len(tasks)} tasks")
    
    print("Scanning reports...")
    reports = scan_reports(workspace)
    print(f"  Found {len(reports)} reports")
    
    # Build indices
    print("Building epoch summaries...")
    epochs = build_epoch_summaries(archives, tasks, reports)
    
    print("Building task cross-references...")
    task_index = build_task_index(tasks, reports, archives)
    
    # Generate outputs
    print("Generating JSON index...")
    json_index = generate_json_index(archives, tasks, reports, epochs, task_index)
    
    print("Generating Markdown index...")
    md_index = generate_markdown_index(archives, tasks, reports, epochs, task_index)
    
    # Write outputs
    docs_dir = workspace / DOCS_DIR
    docs_dir.mkdir(exist_ok=True)
    
    json_path = docs_dir / "HISTORY_INDEX.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_index, f, indent=2)
    print(f"Wrote: {json_path}")
    
    md_path = docs_dir / "HISTORY_INDEX.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_index)
    print(f"Wrote: {md_path}")
    
    return {
        "success": True,
        "archives": len(archives),
        "tasks": len(tasks),
        "reports": len(reports),
        "epochs": len(epochs),
        "outputs": [str(json_path), str(md_path)],
    }


if __name__ == "__main__":
    import sys
    workspace = sys.argv[1] if len(sys.argv) > 1 else "."
    result = regenerate_index(workspace)
    print(f"\nIndex regeneration complete!")
    print(f"  Archives: {result['archives']}")
    print(f"  Tasks: {result['tasks']}")
    print(f"  Reports: {result['reports']}")
    print(f"  Epochs: {result['epochs']}")

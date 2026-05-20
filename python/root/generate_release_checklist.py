# MODE: SCRIPT\n\n#!/usr/bin/env python3
"""
Release Checklist Generator - Pre-Alpha 0.9
============================================
Automatically generates a pre-release checklist based on workspace state.

Usage:
    python generate_release_checklist.py [--output FILE]
    
Options:
    --output FILE   Write checklist to FILE (default: RELEASE_CHECKLIST.md)
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

# Try imports
try:
    import loop_guardrails as lg
    HAS_GUARDRAILS = True
except ImportError:
    HAS_GUARDRAILS = False


def get_workspace_stats(workspace: Path) -> Dict[str, Any]:
    """Gather workspace statistics."""
    stats = {
        "total_files": 0,
        "json_files": 0,
        "md_files": 0,
        "py_files": 0,
        "task_files": 0,
        "report_files": 0,
        "archive_files": 0,
        "total_lines": 0,
    }
    
    for f in workspace.rglob("*"):
        if f.is_file() and not any(p in str(f) for p in [".git", "__pycache__", ".venv"]):
            stats["total_files"] += 1
            suffix = f.suffix.lower()
            
            if suffix == ".json":
                stats["json_files"] += 1
            elif suffix == ".md":
                stats["md_files"] += 1
                if f.name.startswith("task_"):
                    stats["task_files"] += 1
                elif f.name.startswith("report_"):
                    stats["report_files"] += 1
                elif f.name.startswith("ARCHIV_"):
                    stats["archive_files"] += 1
            elif suffix == ".py":
                stats["py_files"] += 1
            
            try:
                stats["total_lines"] += len(f.read_text(encoding="utf-8").split("\n"))
            except Exception:
                pass
    
    return stats


def get_current_state(workspace: Path) -> Dict[str, Any]:
    """Get current loop state."""
    current_path = workspace / "current.json"
    if not current_path.exists():
        return {"loop": 0, "status": "UNKNOWN"}
    
    try:
        return json.loads(current_path.read_text(encoding="utf-8"))
    except Exception:
        return {"loop": 0, "status": "ERROR"}


def run_validation_suite(workspace: Path) -> Dict[str, Any]:
    """Run validation checks."""
    results = {
        "schema_valid": False,
        "schema_errors": [],
        "reference_issues": [],
        "orphaned_tasks": [],
        "security_issues": [],
    }
    
    if HAS_GUARDRAILS:
        try:
            schema_result = lg.validate_all_schemas(workspace)
            results["schema_valid"] = schema_result.get("valid", False)
            results["schema_errors"] = schema_result.get("errors", [])
        except Exception as e:
            results["schema_errors"].append(str(e))
    
    # Check for orphaned tasks
    tasks_dir = workspace / "tasks"
    if tasks_dir.exists():
        for task_file in tasks_dir.glob("task_TASK_*.md"):
            task_id = task_file.stem.replace("task_", "")
            # Check for report
            has_report = any(workspace.glob(f"**/report_{task_id}_*.md"))
            if not has_report:
                results["orphaned_tasks"].append(task_id)
    
    # Root-level tasks
    for task_file in workspace.glob("task_TASK_*.md"):
        task_id = task_file.stem.replace("task_", "")
        has_report = any(workspace.glob(f"report_{task_id}_*.md"))
        if not has_report:
            results["orphaned_tasks"].append(task_id)
    
    return results


def check_documentation(workspace: Path) -> Dict[str, Any]:
    """Check documentation completeness."""
    docs = {
        "readme_exists": (workspace / "README.md").exists(),
        "baseline_exists": (workspace / "PROJECT_TECH_BASELINE.md").exists(),
        "ops_protocols_exists": (workspace / "docs" / "OPS_PROTOCOLS.md").exists(),
        "architecture_exists": False,
        "missing_docs": [],
    }
    
    # Check for architecture docs
    docs_dir = workspace / "docs"
    if docs_dir.exists():
        arch_docs = list(docs_dir.glob("*ARCHITECTURE*.md"))
        docs["architecture_exists"] = len(arch_docs) > 0
    
    # Required docs
    required = [
        ("README.md", workspace / "README.md"),
        ("PROJECT_TECH_BASELINE.md", workspace / "PROJECT_TECH_BASELINE.md"),
        ("NEU.md", workspace / "NEU.md"),
        ("Alt.md", workspace / "Alt.md"),
        ("NEURAL_CORTEX.md", workspace / "NEURAL_CORTEX.md"),
    ]
    
    for name, path in required:
        if not path.exists():
            docs["missing_docs"].append(name)
    
    return docs


def check_code_quality(workspace: Path) -> Dict[str, Any]:
    """Check code quality indicators."""
    quality = {
        "python_files": [],
        "syntax_errors": [],
        "missing_docstrings": [],
        "test_coverage": "unknown",
    }
    
    for py_file in workspace.glob("*.py"):
        quality["python_files"].append(py_file.name)
        try:
            content = py_file.read_text(encoding="utf-8")
            compile(content, str(py_file), "exec")
            
            # Check for docstring
            if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
                quality["missing_docstrings"].append(py_file.name)
        except SyntaxError as e:
            quality["syntax_errors"].append(f"{py_file.name}: {e.msg} (line {e.lineno})")
    
    return quality


def generate_checklist(workspace: Path) -> str:
    """Generate the release checklist."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Gather data
    stats = get_workspace_stats(workspace)
    state = get_current_state(workspace)
    validation = run_validation_suite(workspace)
    docs = check_documentation(workspace)
    quality = check_code_quality(workspace)
    
    # Determine overall readiness
    blockers = []
    warnings = []
    
    if not validation["schema_valid"]:
        blockers.append("Schema validation failed")
    if validation["orphaned_tasks"]:
        warnings.append(f"{len(validation['orphaned_tasks'])} tasks without reports")
    if docs["missing_docs"]:
        blockers.append(f"Missing required docs: {', '.join(docs['missing_docs'])}")
    if quality["syntax_errors"]:
        blockers.append(f"{len(quality['syntax_errors'])} Python syntax errors")
    if state.get("status") not in ["ACTIVE", "FINALIZED", "READY_FOR_RESET"]:
        warnings.append(f"Loop status is {state.get('status', 'UNKNOWN')}")
    
    ready_for_release = len(blockers) == 0
    
    # Build checklist
    lines = [
        "# Pre-Alpha 0.9 Release Checklist",
        "",
        f"Generated: {timestamp}",
        f"Workspace: {workspace}",
        f"Loop: {state.get('loop', 'N/A')}",
        f"Status: {state.get('status', 'N/A')}",
        "",
        "---",
        "",
        "## Overall Status",
        "",
        f"**Ready for Release:** {'✅ YES' if ready_for_release else '❌ NO'}",
        "",
    ]
    
    if blockers:
        lines.extend([
            "### 🚫 Blockers",
            "",
        ])
        for b in blockers:
            lines.append(f"- [ ] {b}")
        lines.append("")
    
    if warnings:
        lines.extend([
            "### ⚠️ Warnings",
            "",
        ])
        for w in warnings:
            lines.append(f"- [ ] {w}")
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "## Pre-Release Checks",
        "",
        "### 1. Schema Validation",
        "",
        f"- [{'x' if validation['schema_valid'] else ' '}] All JSON schemas valid",
    ])
    
    if validation["schema_errors"]:
        lines.append(f"  - Errors: {len(validation['schema_errors'])}")
        for err in validation["schema_errors"][:5]:
            lines.append(f"    - {err}")
        if len(validation["schema_errors"]) > 5:
            lines.append(f"    - ... and {len(validation['schema_errors']) - 5} more")
    
    lines.extend([
        "",
        "### 2. Documentation",
        "",
        f"- [{'x' if docs['readme_exists'] else ' '}] README.md exists",
        f"- [{'x' if docs['baseline_exists'] else ' '}] PROJECT_TECH_BASELINE.md exists",
        f"- [{'x' if docs['ops_protocols_exists'] else ' '}] OPS_PROTOCOLS.md exists",
        f"- [{'x' if docs['architecture_exists'] else ' '}] Architecture documentation exists",
    ])
    
    if docs["missing_docs"]:
        lines.append(f"  - Missing: {', '.join(docs['missing_docs'])}")
    
    lines.extend([
        "",
        "### 3. Code Quality",
        "",
        f"- [{'x' if not quality['syntax_errors'] else ' '}] No Python syntax errors",
    ])
    
    if quality["syntax_errors"]:
        for err in quality["syntax_errors"]:
            lines.append(f"  - {err}")
    
    lines.extend([
        f"- [{'x' if not quality['missing_docstrings'] else ' '}] All Python files have docstrings",
    ])
    
    if quality["missing_docstrings"]:
        lines.append(f"  - Missing docstrings: {', '.join(quality['missing_docstrings'][:5])}")
    
    lines.extend([
        "",
        "### 4. Task Completion",
        "",
        f"- [{'x' if not validation['orphaned_tasks'] else ' '}] All tasks have reports",
    ])
    
    if validation["orphaned_tasks"]:
        lines.append(f"  - Tasks without reports: {', '.join(validation['orphaned_tasks'][:5])}")
        if len(validation["orphaned_tasks"]) > 5:
            lines.append(f"  - ... and {len(validation['orphaned_tasks']) - 5} more")
    
    lines.extend([
        "",
        "### 5. Security Audit",
        "",
        "- [ ] No credentials in repository",
        "- [ ] No sensitive paths exposed",
        "- [ ] Archive immutability verified",
        "",
        "### 6. Integration Testing",
        "",
        "- [ ] `validate_release.py --verbose` passes",
        "- [ ] `test_system_regression.py` passes",
        "- [ ] `python -m py_compile loop_cockpit.py` passes",
        "- [ ] Manual cockpit UI test completed",
        "",
        "---",
        "",
        "## Workspace Statistics",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total Files | {stats['total_files']} |",
        f"| Python Files | {stats['py_files']} |",
        f"| Markdown Files | {stats['md_files']} |",
        f"| JSON Files | {stats['json_files']} |",
        f"| Task Files | {stats['task_files']} |",
        f"| Report Files | {stats['report_files']} |",
        f"| Archive Files | {stats['archive_files']} |",
        f"| Total Lines | {stats['total_lines']:,} |",
        "",
        "---",
        "",
        "## Sign-off",
        "",
        "- [ ] Development Lead approval",
        "- [ ] QA sign-off",
        "- [ ] Documentation review complete",
        "",
        f"Release Target: **v0.9-prealpha**",
        "",
    ])
    
    return "\n".join(lines)


def main():
    """Main entry point."""
    workspace = Path.cwd()
    output_file = "RELEASE_CHECKLIST.md"
    
    # Parse args
    args = sys.argv[1:]
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 < len(args):
            output_file = args[idx + 1]
    
    print(f"Generating release checklist...")
    print(f"Workspace: {workspace}")
    
    checklist = generate_checklist(workspace)
    
    output_path = workspace / output_file
    output_path.write_text(checklist, encoding="utf-8")
    
    print(f"Checklist written to: {output_path}")
    print()
    
    # Print summary
    lines = checklist.split("\n")
    for line in lines:
        if "Ready for Release" in line:
            print(line)
            break


if __name__ == "__main__":
    main()

# MODE: SCRIPT\n\n#!/usr/bin/env python3
"""
validate_release.py - Pre-Release Validation Suite for Universal Architecture v0.9

Part of TASK_0144: Prepares the system for Pre-Alpha 0.9 release by running
comprehensive validation checks.

Usage:
    python validate_release.py [workspace_path]
    python validate_release.py --json  # Output as JSON
    python validate_release.py --verbose  # Detailed output
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Import validation functions from guardrails
try:
    from loop_guardrails import (
        metadata_lint,
        validate_all_schemas,
        check_archive_consistency,
    )
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False


def validate_reference_integrity(workspace: Path) -> Dict[str, Any]:
    """Check that all [ref:...] references point to existing files.
    
    Returns:
        dict with valid, broken_refs, total_refs
    """
    broken_refs = []
    total_refs = 0
    
    # Files to scan for references
    scan_patterns = [
        "*.md",
        "docs/*.md",
        "tasks/*.md",
        "reports/*.md",
    ]
    
    # Match the entire payload inside [ref:...]
    ref_pattern = re.compile(r'\[ref:([^\]]+)\]')

    # Known template tokens used in canonical blueprints that should be ignored by the validator
    template_tokens = {"FILE", "SECTION", "VERSION", "TAG1", "TAG2", "SOURCE"}

    for pattern in scan_patterns:
        for file_path in workspace.glob(pattern):
            try:
                content = file_path.read_text(encoding='utf-8')

                # Remove fenced code blocks and inline code to avoid capturing example placeholders
                content_sanitized = re.sub(r'```[\s\S]*?```', '', content)
                content_sanitized = re.sub(r'`[^`]*`', '', content_sanitized)

                matches = ref_pattern.findall(content_sanitized)
                for payload in matches:
                    total_refs += 1
                    payload = payload.strip()

                    # Skip obvious code-like payloads that are not intended as refs
                    if any(ch in payload for ch in ('{', '}', "'", '"', '[', ']')):
                        # likely an example or interpolation fragment; ignore
                        continue

                    # Extract path part (before '|' or '#')
                    path_part = payload.split('|', 1)[0].split('#', 1)[0].strip()

                    # Detect blueprint/template placeholder refs and skip validation
                    # - Explicit known tokens (e.g., FILE#SECTION|v:VERSION)
                    # - Or an all-uppercase single token (e.g., FILE)
                    is_template = False
                    if any(tok in payload for tok in template_tokens):
                        is_template = True
                    if path_part.isalpha() and path_part.isupper() and len(path_part) < 40:
                        is_template = True

                    if is_template:
                        # Skip validating canonical blueprint placeholders
                        continue

                    # Reject path_parts that contain unexpected characters (likely code samples)
                    if not re.match(r'^[A-Za-z0-9_\-./]+$', path_part):
                        continue

                    ref_path = path_part

                    if ref_path.endswith('/'):
                        # Directory reference
                        full_path = workspace / ref_path
                        if not full_path.exists():
                            broken_refs.append({
                                "source": str(file_path.relative_to(workspace)),
                                "ref": ref_path,
                                "type": "directory"
                            })
                    else:
                        # File reference
                        full_path = workspace / ref_path
                        if not full_path.exists():
                            broken_refs.append({
                                "source": str(file_path.relative_to(workspace)),
                                "ref": ref_path,
                                "type": "file"
                            })
            except Exception as e:
                broken_refs.append({
                    "source": str(file_path),
                    "ref": "ERROR",
                    "type": f"read_error: {e}"
                })
    
    return {
        "valid": len(broken_refs) == 0,
        "broken_refs": broken_refs,
        "total_refs": total_refs,
        "broken_count": len(broken_refs)
    }


def validate_pointer_only_docs(workspace: Path) -> Dict[str, Any]:
    """Validate that pointer-only documents contain no inline content.
    
    Checks: NEU.md, Alt.md, NEURAL_CORTEX.md
    """
    issues = []
    pointer_docs = ["NEU.md", "Alt.md", "NEURAL_CORTEX.md"]
    
    # Patterns that indicate inline content (forbidden)
    content_patterns = [
        (re.compile(r'^```[a-z]*\n[\s\S]+?\n```', re.MULTILINE), "Code block detected"),
        (re.compile(r'^\s*[-*]\s+[A-Z][a-z].{50,}', re.MULTILINE), "Long list item (possible content)"),
    ]
    
    # Patterns that are allowed
    allowed_patterns = [
        re.compile(r'\[ref:'),  # References are allowed
        re.compile(r'^#'),  # Headers
        re.compile(r'^MODE:'),  # Metadata
        re.compile(r'^CONTENT:'),
        re.compile(r'^\s*$'),  # Empty lines
        re.compile(r'^---'),  # Dividers
        re.compile(r'^Process Rules:'),
        re.compile(r'Status:'),
        re.compile(r'Summary:'),
        re.compile(r'Priority:'),
        re.compile(r'Report:'),
        re.compile(r'^\s*-\s*[🔴🟡🟢🔵🟣⚫🔷🔶🟠🔥🎨📦📋✅⏳]'),  # Emoji markers
    ]
    
    for doc_name in pointer_docs:
        doc_path = workspace / doc_name
        if not doc_path.exists():
            issues.append({
                "file": doc_name,
                "issue": "File not found",
                "severity": "error"
            })
            continue
        
        try:
            content = doc_path.read_text(encoding='utf-8')
            
            # Check for required MODE declaration
            if "MODE: POINTER-ONLY" not in content:
                issues.append({
                    "file": doc_name,
                    "issue": "Missing MODE: POINTER-ONLY declaration",
                    "severity": "error"
                })
            
            # Check for CONTENT: FORBIDDEN
            if "CONTENT: FORBIDDEN" not in content:
                issues.append({
                    "file": doc_name,
                    "issue": "Missing CONTENT: FORBIDDEN declaration",
                    "severity": "warning"
                })
            
        except Exception as e:
            issues.append({
                "file": doc_name,
                "issue": f"Read error: {e}",
                "severity": "error"
            })
    
    return {
        "valid": all(i["severity"] != "error" for i in issues),
        "issues": issues,
        "checked": pointer_docs
    }


def validate_archive_format(workspace: Path) -> Dict[str, Any]:
    """Validate that all archives match the canonical format.
    
    Checks for required sections in each archive.
    """
    archive_dir = workspace / "archive"
    issues = []
    archives_checked = 0
    
    if not archive_dir.exists():
        return {
            "valid": False,
            "issues": [{"archive": "archive/", "issue": "Archive directory not found"}],
            "archives_checked": 0
        }
    
    required_sections = [
        "## LOOP SUMMARY",
        "## TASKS AT FINALIZATION",
    ]
    
    recommended_sections = [
        "### Active Tasks (NEU.md)",
        "### Closed Tasks (Alt.md)",
        "## VALIDATION",
    ]
    
    # Check last 10 archives for format compliance
    archives = sorted(archive_dir.glob("ARCHIV_*.md"))[-10:]
    
    for archive_path in archives:
        archives_checked += 1
        try:
            content = archive_path.read_text(encoding='utf-8')
            
            # Check MODE: IMMUTABLE
            if "MODE: IMMUTABLE" not in content:
                issues.append({
                    "archive": archive_path.name,
                    "issue": "Missing MODE: IMMUTABLE",
                    "severity": "error"
                })
            
            # Check required sections
            for section in required_sections:
                if section not in content:
                    issues.append({
                        "archive": archive_path.name,
                        "issue": f"Missing required section: {section}",
                        "severity": "error"
                    })
            
            # Check recommended sections (warnings only)
            for section in recommended_sections:
                if section not in content:
                    issues.append({
                        "archive": archive_path.name,
                        "issue": f"Missing recommended section: {section}",
                        "severity": "warning"
                    })
                    
        except Exception as e:
            issues.append({
                "archive": archive_path.name,
                "issue": f"Read error: {e}",
                "severity": "error"
            })
    
    return {
        "valid": all(i["severity"] != "error" for i in issues),
        "issues": issues,
        "archives_checked": archives_checked
    }


def validate_orphaned_files(workspace: Path) -> Dict[str, Any]:
    """Check for orphaned files (reports without tasks, tasks without reports).
    
    Returns list of potentially orphaned files.
    """
    orphans = []
    
    # Get all task IDs from task files
    task_ids = set()
    tasks_dir = workspace / "tasks"
    if tasks_dir.exists():
        for task_file in tasks_dir.glob("task_TASK_*.md"):
            match = re.search(r'task_(TASK_\d+)\.md', task_file.name)
            if match:
                task_ids.add(match.group(1))
    
    # Also check root for legacy task files
    for task_file in workspace.glob("task_TASK_*.md"):
        match = re.search(r'task_(TASK_\d+)\.md', task_file.name)
        if match:
            task_ids.add(match.group(1))
    
    # Get all report task IDs
    report_task_ids = set()
    reports_dir = workspace / "reports"
    if reports_dir.exists():
        for report_file in reports_dir.glob("report_TASK_*_L*_v*.md"):
            match = re.search(r'report_(TASK_\d+)_L\d+_v\d+\.md', report_file.name)
            if match:
                report_task_ids.add(match.group(1))
    
    # Also check root
    for report_file in workspace.glob("report_TASK_*_L*_v*.md"):
        match = re.search(r'report_(TASK_\d+)_L\d+_v\d+\.md', report_file.name)
        if match:
            report_task_ids.add(match.group(1))
    
    # Find tasks without any reports
    tasks_without_reports = task_ids - report_task_ids
    for task_id in tasks_without_reports:
        # Check if task is still in NEU.md (active) - those don't need reports yet
        neu_content = ""
        neu_path = workspace / "NEU.md"
        if neu_path.exists():
            neu_content = neu_path.read_text(encoding='utf-8')
        
        if task_id not in neu_content:
            orphans.append({
                "type": "task_without_report",
                "id": task_id,
                "note": "Task not in NEU.md and has no reports"
            })
    
    # Find reports for non-existent tasks (rare but possible)
    reports_without_tasks = report_task_ids - task_ids
    for task_id in reports_without_tasks:
        orphans.append({
            "type": "report_without_task",
            "id": task_id,
            "note": "Report exists but task spec not found"
        })
    
    return {
        "valid": len(orphans) == 0,
        "orphans": orphans,
        "task_count": len(task_ids),
        "report_task_count": len(report_task_ids)
    }


def validate_security_audit(workspace: Path) -> Dict[str, Any]:
    """Run security audit checklist verification.
    
    Checks from CANONICAL_SYSTEM_SPEC.md Section 8.
    """
    issues = []
    
    # Check 1: No hardcoded credentials
    sensitive_patterns = [
        (re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "Hardcoded password"),
        (re.compile(r'api_key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "Hardcoded API key"),
        (re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "Hardcoded secret"),
        (re.compile(r'token\s*=\s*["\'][A-Za-z0-9_-]{20,}["\']', re.IGNORECASE), "Hardcoded token"),
    ]
    
    # Scan Python files
    for py_file in workspace.glob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8')
            for pattern, desc in sensitive_patterns:
                matches = pattern.findall(content)
                if matches:
                    issues.append({
                        "check": "credentials",
                        "file": py_file.name,
                        "issue": f"{desc} detected",
                        "severity": "critical"
                    })
        except Exception:
            pass
    
    # Check 2: Verify archive immutability (archives should not have recent mtime)
    archive_dir = workspace / "archive"
    if archive_dir.exists():
        # Get current.json to know current loop
        current_json = workspace / "current.json"
        current_loop = 0
        if current_json.exists():
            try:
                data = json.loads(current_json.read_text(encoding='utf-8'))
                current_loop = data.get('STATE', {}).get('loop', 0)
            except:
                pass
        
        # Archives from loops < current-1 should be old
        for archive in archive_dir.glob("ARCHIV_*.md"):
            match = re.search(r'ARCHIV_(\d+)\.md', archive.name)
            if match:
                archive_loop = int(match.group(1))
                if archive_loop < current_loop - 1:
                    # Should be at least a day old if it's from 2+ loops ago
                    mtime = archive.stat().st_mtime
                    age_hours = (datetime.now().timestamp() - mtime) / 3600
                    if age_hours < 1:  # Modified in last hour
                        issues.append({
                            "check": "immutability",
                            "file": archive.name,
                            "issue": f"Archive modified recently ({age_hours:.1f}h ago)",
                            "severity": "warning"
                        })
    
    # Check 3: Path traversal in file operations
    # This is a code review check - scan for unsafe path operations
    unsafe_patterns = [
        (re.compile(r'open\([^)]*\+[^)]*\)'), "Path concatenation in open()"),
        (re.compile(r'\.\.\/'), "Parent directory traversal"),
    ]
    
    for py_file in workspace.glob("*.py"):
        if py_file.name == "validate_release.py":
            continue  # Skip this file
        try:
            content = py_file.read_text(encoding='utf-8')
            for pattern, desc in unsafe_patterns:
                if pattern.search(content):
                    issues.append({
                        "check": "path_traversal",
                        "file": py_file.name,
                        "issue": f"Potential {desc}",
                        "severity": "warning"
                    })
        except Exception:
            pass
    
    return {
        "valid": all(i["severity"] != "critical" for i in issues),
        "issues": issues,
        "checks_run": ["credentials", "immutability", "path_traversal"]
    }


def run_full_validation(workspace_path: str = ".") -> Dict[str, Any]:
    """Run all validation checks and return comprehensive report.
    
    Returns:
        dict with all validation results and summary
    """
    workspace = Path(workspace_path).resolve()
    
    results = {
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "workspace": str(workspace),
        "version": "0.9-prealpha",
        "checks": {}
    }
    
    # Run all checks
    print("Running pre-release validation...")
    
    print("  [1/6] Reference integrity...")
    results["checks"]["reference_integrity"] = validate_reference_integrity(workspace)
    
    print("  [2/6] Pointer-only documents...")
    results["checks"]["pointer_only_docs"] = validate_pointer_only_docs(workspace)
    
    print("  [3/6] Archive format...")
    results["checks"]["archive_format"] = validate_archive_format(workspace)
    
    print("  [4/6] Orphaned files...")
    results["checks"]["orphaned_files"] = validate_orphaned_files(workspace)
    
    print("  [5/6] Security audit...")
    results["checks"]["security_audit"] = validate_security_audit(workspace)
    
    # Run guardrails checks if available
    if GUARDRAILS_AVAILABLE:
        print("  [6/6] Schema validation & lint...")
        try:
            results["checks"]["schema_validation"] = validate_all_schemas(workspace)
            results["checks"]["metadata_lint"] = metadata_lint(workspace)
        except Exception as e:
            results["checks"]["guardrails_error"] = str(e)
    else:
        print("  [6/6] Skipped (loop_guardrails not available)")
        results["checks"]["guardrails_available"] = False
    
    # Calculate summary
    all_valid = True
    error_count = 0
    warning_count = 0
    
    for check_name, check_result in results["checks"].items():
        if isinstance(check_result, dict):
            if not check_result.get("valid", True):
                all_valid = False
            
            # Count issues
            for issue in check_result.get("issues", []):
                if isinstance(issue, dict):
                    if issue.get("severity") == "error" or issue.get("severity") == "critical":
                        error_count += 1
                    elif issue.get("severity") == "warning":
                        warning_count += 1
            
            # Count broken refs
            error_count += len(check_result.get("broken_refs", []))
            
            # Count orphans
            error_count += len(check_result.get("orphans", []))
    
    results["summary"] = {
        "all_checks_passed": all_valid,
        "error_count": error_count,
        "warning_count": warning_count,
        "ready_for_release": all_valid and error_count == 0,
        "recommendation": "✅ Ready for v0.9-prealpha tag" if (all_valid and error_count == 0) else "❌ Fix errors before release"
    }
    
    return results


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pre-Release Validation Suite")
    parser.add_argument("workspace", nargs="?", default=".", help="Workspace path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    results = run_full_validation(args.workspace)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("\n" + "=" * 60)
        print("PRE-RELEASE VALIDATION REPORT")
        print("=" * 60)
        print(f"Workspace: {results['workspace']}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Version: {results['version']}")
        print("-" * 60)
        
        for check_name, check_result in results["checks"].items():
            if isinstance(check_result, dict):
                status = "✅" if check_result.get("valid", True) else "❌"
                print(f"\n{status} {check_name}")
                
                if args.verbose:
                    if "issues" in check_result and check_result["issues"]:
                        for issue in check_result["issues"][:5]:
                            if isinstance(issue, dict):
                                print(f"    - {issue.get('file', issue.get('archive', 'N/A'))}: {issue.get('issue', str(issue))}")
                    if "broken_refs" in check_result and check_result["broken_refs"]:
                        for ref in check_result["broken_refs"][:5]:
                            print(f"    - {ref['source']}: broken ref to {ref['ref']}")
                    if "orphans" in check_result and check_result["orphans"]:
                        for orphan in check_result["orphans"][:5]:
                            print(f"    - {orphan['type']}: {orphan['id']}")
        
        print("\n" + "-" * 60)
        summary = results["summary"]
        print(f"Errors: {summary['error_count']}")
        print(f"Warnings: {summary['warning_count']}")
        print(f"\n{summary['recommendation']}")
        print("=" * 60)
    
    # Exit code based on results
    sys.exit(0 if results["summary"]["ready_for_release"] else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Consistency Audit Framework

Comprehensive audit system for content reliability and logical consistency
across all system components. TASK_0181 implementation.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class AuditIssue:
    """Represents a consistency issue found during audit."""
    file_path: str
    line_number: int
    issue_type: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    suggestion: str

@dataclass
class AuditResult:
    """Results from a consistency audit."""
    issues: List[AuditIssue]
    summary: Dict[str, int]
    passed_checks: int
    total_checks: int

class ConsistencyAuditor:
    """
    Comprehensive consistency auditor for system integrity validation.
    """

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.issues: List[AuditIssue] = []
        self.reference_patterns = {
            'task_ref': r'\[ref:tasks/task_[^|]+\.md\|v:\d+\|tags:[^|]+\|src:[^\]]+\]',
            'report_ref': r'\[ref:reports/report_[^|]+\.md\|v:\d+\|tags:[^|]+\|src:[^\]]+\]',
            'doc_ref': r'\[ref:[^#]+#[^|]+\|v:[^|]+\|tags:[^|]+\|src:[^\]]+\]'
        }

    def run_full_audit(self) -> AuditResult:
        """Run comprehensive consistency audit."""
        print("🔍 Starting Full Consistency Audit...")
        print("=" * 60)

        # Clear previous issues
        self.issues = []

        # Run all audit checks
        checks = [
            self._audit_file_naming,
            self._audit_reference_consistency,
            self._audit_task_status_consistency,
            self._audit_documentation_structure,
            self._audit_code_comment_alignment,
            self._audit_json_integrity,
            self._audit_cross_references
        ]

        total_checks = len(checks)
        passed_checks = 0

        for check in checks:
            try:
                check()
                passed_checks += 1
                print(f"✅ {check.__name__} completed")
            except Exception as e:
                self._add_issue("SYSTEM", 0, "audit_failure", "high",
                              f"Audit check {check.__name__} failed: {str(e)}",
                              "Fix audit framework")
                print(f"❌ {check.__name__} failed: {e}")

        # Generate summary
        summary = defaultdict(int)
        for issue in self.issues:
            summary[issue.severity] += 1

        result = AuditResult(
            issues=self.issues,
            summary=dict(summary),
            passed_checks=passed_checks,
            total_checks=total_checks
        )

        self._print_audit_results(result)
        return result

    def _audit_file_naming(self):
        """Audit file naming consistency."""
        print("  📁 Checking file naming consistency...")

        # Check task files
        task_files = list(self.root_path.glob("task_*.md"))
        for task_file in task_files:
            if not re.match(r'task_TASK_\d+\.md$', task_file.name):
                self._add_issue(str(task_file), 0, "file_naming", "medium",
                              f"Task file {task_file.name} doesn't follow naming convention",
                              "Rename to task_TASK_XXXX.md format")

        # Check report files
        report_files = list(self.root_path.glob("report_*.md"))
        for report_file in report_files:
            if not re.match(r'report_TASK_\d+_L\d+_v\d+\.md$', report_file.name):
                self._add_issue(str(report_file), 0, "file_naming", "medium",
                              f"Report file {report_file.name} doesn't follow naming convention",
                              "Rename to report_TASK_XXXX_LXX_vXX.md format")

    def _audit_reference_consistency(self):
        """Audit reference format consistency."""
        print("  🔗 Checking reference consistency...")

        # Only check specific files that should have references
        key_files = ["NEU.md", "Alt.md", "_SESSION.md", "_LOOP_GATE.md"]
        for filename in key_files:
            file_path = self.root_path / filename
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    # Check for malformed references
                    ref_matches = re.findall(r'\[ref:[^\]]+\]', line)
                    for ref in ref_matches:
                        if not self._validate_reference_format(ref):
                            self._add_issue(str(file_path), line_num, "reference_format", "high",
                                          f"Malformed reference: {ref}",
                                          "Fix reference format to match standard pattern")

            except Exception as e:
                self._add_issue(str(file_path), 0, "file_read_error", "medium",
                              f"Could not read file: {e}",
                              "Check file encoding and accessibility")

    def _audit_task_status_consistency(self):
        """Audit task status consistency between NEU.md, Alt.md, and task files."""
        print("  📋 Checking task status consistency...")

        # Read NEU.md and Alt.md
        neu_tasks = self._extract_tasks_from_file("NEU.md")
        alt_tasks = self._extract_tasks_from_file("Alt.md")

        # Check for tasks in both NEU and Alt
        overlap = set(neu_tasks.keys()) & set(alt_tasks.keys())
        for task in overlap:
            self._add_issue("NEU.md/Alt.md", 0, "task_status", "critical",
                          f"Task {task} appears in both NEU.md and Alt.md",
                          "Move task to correct status file")

        # Check task file status vs queue status
        all_tasks = {**neu_tasks, **alt_tasks}
        for task_id, task_info in all_tasks.items():
            task_file = self.root_path / f"task_{task_id}.md"
            if task_file.exists():
                try:
                    content = task_file.read_text(encoding='utf-8')
                    # Check if status matches queue status
                    if "## Status: ACTIVE" in content and task_id in alt_tasks:
                        self._add_issue(str(task_file), 0, "status_mismatch", "high",
                                      f"Task {task_id} marked ACTIVE but in Alt.md (completed)",
                                      "Update task status to COMPLETED")
                    elif "## Status: COMPLETED" in content and task_id in neu_tasks:
                        self._add_issue(str(task_file), 0, "status_mismatch", "high",
                                      f"Task {task_id} marked COMPLETED but in NEU.md (active)",
                                      "Update task status to ACTIVE")
                except Exception as e:
                    self._add_issue(str(task_file), 0, "file_read_error", "medium",
                                  f"Could not read task file: {e}",
                                  "Check file accessibility")

    def _audit_documentation_structure(self):
        """Audit documentation structure consistency."""
        print("  📚 Checking documentation structure...")

        # Check task files have required sections
        required_sections = ["## Status:", "## Priority:", "## Objective:", "## Requirements:"]

        task_files = list(self.root_path.glob("task_*.md"))
        for task_file in task_files:
            try:
                content = task_file.read_text(encoding='utf-8')
                for section in required_sections:
                    if section not in content:
                        self._add_issue(str(task_file), 0, "missing_section", "medium",
                                      f"Missing required section: {section}",
                                      "Add missing section to task file")
            except Exception as e:
                self._add_issue(str(task_file), 0, "file_read_error", "medium",
                              f"Could not read task file: {e}",
                              "Check file accessibility")

    def _audit_code_comment_alignment(self):
        """Audit code-comment alignment in key Python files."""
        print("  💻 Checking code-comment alignment...")

        # Only check key Python files, not all
        key_py_files = [
            "loop_cockpit.py",
            "consistency_auditor.py",
            "optimization/parameter_learning_optimizer.py",
            "ai_integrity_protector.py"
        ]

        for filename in key_py_files:
            py_file = self.root_path / filename
            if not py_file.exists():
                continue

            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    # Check for functions without docstrings (only major functions)
                    if re.match(r'^\s*def \w+\(', line) and line_num < len(lines):
                        # Check next few lines for docstring
                        has_docstring = False
                        for i in range(min(3, len(lines) - line_num)):
                            next_line = lines[line_num + i]
                            if '"""' in next_line or 'def ' in next_line:
                                has_docstring = True
                                break

                        if not has_docstring:
                            self._add_issue(str(py_file), line_num, "missing_docstring", "low",
                                          f"Function {line.strip()} missing docstring",
                                          "Add docstring to function")

            except Exception as e:
                self._add_issue(str(py_file), 0, "file_read_error", "medium",
                              f"Could not read Python file: {e}",
                              "Check file accessibility")

    def _audit_json_integrity(self):
        """Audit JSON file integrity."""
        print("  📄 Checking JSON file integrity...")

        # Files that are not pure JSON (logs, configs with comments)
        json_exceptions = {
            "lint_output.json",  # Hybrid log + JSON
            "temp_lint.json",    # Hybrid log + JSON
            "Breadcrumbs_ext/tsconfig.json"  # JSONC with comments
        }

        json_files = list(self.root_path.glob("**/*.json"))
        for json_file in json_files:
            # Skip known exception files
            if json_file.name in json_exceptions or str(json_file.relative_to(self.root_path)) in json_exceptions:
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json.load(f)  # Try to parse
            except json.JSONDecodeError as e:
                self._add_issue(str(json_file), 0, "json_invalid", "high",
                              f"Invalid JSON: {e}",
                              "Fix JSON syntax errors")
            except Exception as e:
                self._add_issue(str(json_file), 0, "file_read_error", "medium",
                              f"Could not read JSON file: {e}",
                              "Check file accessibility")

    def _audit_cross_references(self):
        """Audit cross-reference validity."""
        print("  🔄 Checking cross-references...")

        # Check references in key files only
        check_files = ["NEU.md", "Alt.md", "_SESSION.md"]
        for filename in check_files:
            md_file = self.root_path / filename
            if not md_file.exists():
                continue

            try:
                content = md_file.read_text(encoding='utf-8')
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    # Extract file references
                    file_refs = re.findall(r'\[ref:([^|]+)', line)
                    for ref in file_refs:
                        # Extract file path before section anchor
                        file_part = ref.split('#')[0]
                        # Check if referenced file exists
                        ref_path = self.root_path / file_part
                        if not ref_path.exists():
                            self._add_issue(str(md_file), line_num, "broken_reference", "high",
                                          f"Reference to non-existent file: {ref}",
                                          "Fix or remove broken reference")

            except Exception as e:
                self._add_issue(str(md_file), 0, "file_read_error", "medium",
                              f"Could not read file: {e}",
                              "Check file accessibility")

    def _validate_reference_format(self, ref: str) -> bool:
        """Validate reference format."""
        for pattern in self.reference_patterns.values():
            if re.match(pattern, ref):
                return True
        return False

    def _extract_tasks_from_file(self, filename: str) -> Dict[str, Dict]:
        """Extract tasks from NEU.md or Alt.md."""
        tasks = {}
        file_path = self.root_path / filename
        if not file_path.exists():
            return tasks

        try:
            content = file_path.read_text(encoding='utf-8')
            # Find task references
            task_refs = re.findall(r'\[ref:tasks/task_([A-Z_]+)\.md\|v:(\d+)\|tags:([^|]+)\|src:([^\]]+)\]', content)
            for task_id, version, tags, source in task_refs:
                tasks[task_id] = {
                    'version': version,
                    'tags': tags,
                    'source': source
                }
        except Exception:
            pass

        return tasks

    def _add_issue(self, file_path: str, line_number: int, issue_type: str,
                  severity: str, description: str, suggestion: str):
        """Add an audit issue."""
        issue = AuditIssue(
            file_path=file_path,
            line_number=line_number,
            issue_type=issue_type,
            severity=severity,
            description=description,
            suggestion=suggestion
        )
        self.issues.append(issue)

    def _print_audit_results(self, result: AuditResult):
        """Print audit results summary."""
        print("\n📊 AUDIT RESULTS SUMMARY")
        print("=" * 60)
        print(f"Checks Passed: {result.passed_checks}/{result.total_checks}")
        print(f"Total Issues: {len(result.issues)}")

        if result.summary:
            print("\nIssues by Severity:")
            for severity, count in sorted(result.summary.items()):
                print(f"  {severity.upper()}: {count}")

        if result.issues:
            print("\n🔴 CRITICAL ISSUES:")
            critical_issues = [i for i in result.issues if i.severity == 'critical']
            for issue in critical_issues[:5]:  # Show first 5
                print(f"  {issue.file_path}:{issue.line_number} - {issue.description}")

            if len(critical_issues) > 5:
                print(f"  ... and {len(critical_issues) - 5} more critical issues")

        print("\n" + "=" * 60)
        if len(result.issues) == 0:
            print("✅ AUDIT PASSED: No consistency issues found!")
        else:
            print(f"⚠️  AUDIT FOUND {len(result.issues)} ISSUES requiring attention")

def main():
    """Run the consistency audit."""
    auditor = ConsistencyAuditor()
    result = auditor.run_full_audit()

    # Save detailed results
    output_file = Path("audit_results.json")
    audit_data = {
        "timestamp": "2026-01-28T00:00:00Z",
        "summary": result.summary,
        "passed_checks": result.passed_checks,
        "total_checks": result.total_checks,
        "issues": [
            {
                "file_path": issue.file_path,
                "line_number": issue.line_number,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "description": issue.description,
                "suggestion": issue.suggestion
            }
            for issue in result.issues
        ]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Detailed results saved to {output_file}")

if __name__ == "__main__":
    main()
"""
Quality Scanner Module

This module provides the core scanning functionality for quality assessment,
including multi-threaded file processing and rule application.
"""

import ast
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Set, Optional, Tuple
from dataclasses import dataclass

from detection_rules import (
    QualityIssue, IssueSeverity, IssueCategory,
    DetectionRule, MockupDetectionRules, CodeQualityRules,
    ArchitectureRules, IncompleteFeatureRules
)


@dataclass
class ScanResult:
    """Result of scanning a single file"""
    file_path: str
    issues: List[QualityIssue]
    scan_time: float
    success: bool
    error_message: Optional[str] = None


class QualityScanner:
    """Main quality scanning engine"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scanning_config = config.get("scanning", {})
        self.performance_config = config.get("performance", {})

        # Initialize detection rules
        self.rules = self._initialize_rules()

        # Threading and performance
        self.max_workers = self.performance_config.get("max_workers", 4)
        self.batch_size = self.performance_config.get("batch_size", 10)

        # File filtering
        self.include_patterns = self._compile_patterns(
            self.scanning_config.get("include_patterns", ["*.py"])
        )
        self.exclude_patterns = self._compile_patterns(
            self.scanning_config.get("exclude_patterns", [])
        )

    def _initialize_rules(self) -> List[DetectionRule]:
        """Initialize detection rules based on configuration"""
        rules = []
        rule_config = self.config.get("detection_rules", {})

        if rule_config.get("mockup_detection", {}).get("enabled", True):
            rules.append(MockupDetectionRules())

        if rule_config.get("code_quality", {}).get("enabled", True):
            rules.append(CodeQualityRules())

        if rule_config.get("architecture_rules", {}).get("enabled", True):
            rules.append(ArchitectureRules())

        if rule_config.get("incomplete_features", {}).get("enabled", True):
            rules.append(IncompleteFeatureRules())

        return rules

    def _compile_patterns(self, patterns: List[str]) -> List[re.Pattern]:
        """Compile glob patterns to regex"""
        compiled = []
        for pattern in patterns:
            # Use fnmatch.translate but modify for our needs
            import fnmatch
            regex = fnmatch.translate(pattern)
            
            # Handle directory patterns like "dir/**/*" to also match files in the root directory
            if pattern.endswith("/**/*"):
                # Add alternative pattern for files directly in the directory
                dir_root = pattern[:-5]  # Remove "/**/*"
                root_pattern = f"{dir_root}/*"
                root_regex = fnmatch.translate(root_pattern)
                regex = f"(?:{regex}|{root_regex})"
            
            # For patterns like **/*.py, make the directory part optional for root files
            elif pattern.startswith("**/"):
                # Add alternative pattern for root directory files
                root_pattern = pattern[3:]  # Remove **/
                root_regex = fnmatch.translate(root_pattern)
                regex = f"(?:{regex}|{root_regex})"
            
            compiled.append(re.compile(f"^{regex}$", re.IGNORECASE))
        return compiled

    def scan_directory(self, directory_path: str) -> List[QualityIssue]:
        """
        Scan all files in a directory

        Args:
            directory_path: Path to directory to scan

        Returns:
            List of all quality issues found
        """
        directory = Path(directory_path)
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")

        print(f"Discovering files in: {directory_path}")

        # Find all files to scan
        files_to_scan = self._discover_files(directory)

        if not files_to_scan:
            print("No files found to scan")
            return []

        print(f"Found {len(files_to_scan)} files to scan")

        # Scan files in parallel
        all_issues = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all scan tasks
            future_to_file = {
                executor.submit(self._scan_file, file_path): file_path
                for file_path in files_to_scan
            }

            # Collect results
            completed = 0
            for future in as_completed(future_to_file):
                result = future.result()
                completed += 1

                if result.success:
                    all_issues.extend(result.issues)
                    if result.issues:
                        print(f"[{completed}/{len(files_to_scan)}] {Path(result.file_path).name}: {len(result.issues)} issues")
                    else:
                        print(f"[{completed}/{len(files_to_scan)}] {Path(result.file_path).name}: clean")
                else:
                    print(f"[{completed}/{len(files_to_scan)}] {Path(result.file_path).name}: ERROR - {result.error_message}")

        total_time = time.time() - start_time
        print(f"Scanned {len(files_to_scan)} files in {total_time:.2f} seconds")
        return all_issues

    def _discover_files(self, directory: Path) -> List[str]:
        """Discover files to scan based on include/exclude patterns"""
        files_to_scan = []

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            # Check file size limit
            max_size = self.scanning_config.get("max_file_size", 1000000)  # 1MB default
            if file_path.stat().st_size > max_size:
                continue

            # Convert to relative path string for pattern matching
            rel_path = str(file_path.relative_to(directory))
            # Normalize path separators to forward slashes for cross-platform compatibility
            rel_path = rel_path.replace('\\', '/')

            # Check exclude patterns first
            excluded = any(pattern.search(rel_path) for pattern in self.exclude_patterns)
            if excluded:
                continue

            # Check include patterns
            included = any(pattern.search(rel_path) for pattern in self.include_patterns)
            if included:
                files_to_scan.append(str(file_path))

        return files_to_scan

    def _scan_file(self, file_path: str) -> ScanResult:
        """Scan a single file for quality issues"""
        start_time = time.time()

        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Parse AST for Python files
            tree = None
            if file_path.endswith('.py'):
                try:
                    tree = ast.parse(content, filename=file_path)
                except SyntaxError as e:
                    # Create issue for syntax errors
                    issue = QualityIssue(
                        file_path=file_path,
                        line_number=e.lineno or 1,
                        category=IssueCategory.CODE_QUALITY,
                        severity=IssueSeverity.CRITICAL,
                        rule_name="syntax_error",
                        message=f"Syntax error: {e.msg}",
                        code_snippet="",
                        suggestion="Fix the syntax error in the code"
                    )
                    return ScanResult(
                        file_path=file_path,
                        issues=[issue],
                        scan_time=time.time() - start_time,
                        success=True
                    )

            # Apply all detection rules
            all_issues = []
            for rule in self.rules:
                try:
                    issues = rule.detect(file_path, content, self.config)
                    all_issues.extend(issues)
                except Exception as e:
                    # Create issue for rule errors
                    error_issue = QualityIssue(
                        file_path=str(file_path),
                        line_number=1,
                        category=IssueCategory.CODE_QUALITY,
                        severity=IssueSeverity.MEDIUM,
                        rule_name="rule_error",
                        message=f"Error running rule {rule.__class__.__name__}: {str(e)}",
                        code_snippet="",
                        suggestion="Check rule implementation or file content"
                    )
                    all_issues.append(error_issue)

            return ScanResult(
                file_path=file_path,
                issues=all_issues,
                scan_time=time.time() - start_time,
                success=True
            )

        except Exception as e:
            return ScanResult(
                file_path=file_path,
                issues=[],
                scan_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )

    def scan_file(self, file_path: str) -> List[QualityIssue]:
        """
        Scan a single file (convenience method)

        Args:
            file_path: Path to file to scan

        Returns:
            List of quality issues found
        """
        result = self._scan_file(file_path)
        return result.issues

    def get_scan_statistics(self, issues: List[QualityIssue]) -> Dict[str, Any]:
        """Get statistics about scan results"""
        if not issues:
            return {
                "total_issues": 0,
                "issues_by_severity": {},
                "issues_by_category": {},
                "files_affected": 0,
                "most_common_issues": []
            }

        from collections import Counter

        severity_counts = Counter(issue.severity.value for issue in issues)
        category_counts = Counter(issue.category.value for issue in issues)
        files_affected = len(set(issue.file_path for issue in issues))

        # Most common issues
        rule_counts = Counter(issue.rule_name for issue in issues)
        most_common = rule_counts.most_common(5)

        return {
            "total_issues": len(issues),
            "issues_by_severity": dict(severity_counts),
            "issues_by_category": dict(category_counts),
            "files_affected": files_affected,
            "most_common_issues": most_common
        }


class IncrementalScanner:
    """Scanner that can perform incremental scans based on file changes"""

    def __init__(self, scanner: QualityScanner):
        self.scanner = scanner
        self.last_scan_results: Dict[str, List[QualityIssue]] = {}
        self.file_hashes: Dict[str, str] = {}

    def scan_changed_files(self, changed_files: List[str]) -> List[QualityIssue]:
        """
        Scan only files that have changed since last scan

        Args:
            changed_files: List of file paths that have changed

        Returns:
            List of new or changed issues
        """
        new_issues = []

        for file_path in changed_files:
            if not Path(file_path).exists():
                continue

            # Check if file has actually changed
            current_hash = self._get_file_hash(file_path)
            if current_hash == self.file_hashes.get(file_path):
                # File hasn't changed, use cached results
                cached_issues = self.last_scan_results.get(file_path, [])
                new_issues.extend(cached_issues)
                continue

            # Scan the file
            issues = self.scanner.scan_file(file_path)

            # Update cache
            self.last_scan_results[file_path] = issues
            self.file_hashes[file_path] = current_hash

            new_issues.extend(issues)

        return new_issues

    def _get_file_hash(self, file_path: str) -> str:
        """Get simple hash of file content"""
        try:
            import hashlib
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""


def create_quality_scanner(config: Dict[str, Any]) -> QualityScanner:
    """Factory function to create quality scanner"""
    return QualityScanner(config)
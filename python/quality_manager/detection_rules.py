"""
Quality Detection Rules for Codebase Analysis

This module contains pluggable detection rules for identifying quality issues
in the codebase including mockups, incomplete features, and code quality problems.
"""

import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class IssueSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(Enum):
    MOCKUP = "mockup"
    CODE_QUALITY = "code_quality"
    INCOMPLETE = "incomplete"
    ARCHITECTURE = "architecture"
    SECURITY = "security"


@dataclass
class QualityIssue:
    file_path: str
    line_number: int
    category: IssueCategory
    severity: IssueSeverity
    rule_name: str
    message: str
    code_snippet: str
    suggestion: str
    metadata: Dict[str, Any] = None


class DetectionRule:
    """Base class for detection rules"""

    def __init__(self, name: str, category: IssueCategory, severity: IssueSeverity):
        self.name = name
        self.category = category
        self.default_severity = severity

    def detect(self, file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        """Detect issues in the given file content"""
        raise NotImplementedError

    def is_enabled(self, config: Dict) -> bool:
        """Check if this rule is enabled in config"""
        return config.get("detection_rules", {}).get(self.category.value, {}).get("enabled", True)


class MockupDetectionRules(DetectionRule):
    """Rules for detecting mockup code and incomplete implementations"""

    def __init__(self):
        super().__init__("MockupDetectionRules", IssueCategory.MOCKUP, IssueSeverity.MEDIUM)

    def detect(self, file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        """Detect mockup and incomplete implementation issues"""
        issues = []

        # Run all mockup detection methods
        issues.extend(self.placeholder_functions(file_path, content, config))
        issues.extend(self.todo_comments(file_path, content, config))
        issues.extend(self.placeholder_variables(file_path, content, config))

        return issues

    @staticmethod
    def placeholder_functions(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # Detect functions with only 'pass'
            if re.search(r'def\s+\w+\s*\([^)]*\)\s*:\s*pass\s*$', line.strip()):
                issues.append(QualityIssue(
                    file_path=str(file_path),
                    line_number=i,
                    category=IssueCategory.MOCKUP,
                    severity=IssueSeverity.MEDIUM,
                    rule_name="placeholder_function",
                    message="Function contains only 'pass' - likely a placeholder",
                    code_snippet=line.strip(),
                    suggestion="Implement the function or add TODO comment explaining why it's empty"
                ))

            # Detect functions with minimal implementation
            func_match = re.search(r'def\s+(\w+)\s*\([^)]*\)\s*:\s*$', line.strip())
            if func_match:
                func_name = func_match.group(1)
                # Check next few lines for minimal implementation
                for j in range(min(3, len(lines) - i)):
                    next_line = lines[i + j].strip()
                    if next_line and not next_line.startswith('#') and not next_line.startswith('"""'):
                        if next_line in ['pass', 'return None', 'return', '...', 'raise NotImplementedError']:
                            issues.append(QualityIssue(
                                file_path=str(file_path),
                                line_number=i,
                                category=IssueCategory.MOCKUP,
                                severity=IssueSeverity.LOW,
                                rule_name="minimal_function",
                                message=f"Function '{func_name}' has minimal implementation",
                                code_snippet=line.strip(),
                                suggestion="Review if this is intentional or needs full implementation"
                            ))
                        break

        return issues

    @staticmethod
    def todo_comments(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        issues = []
        lines = content.split('\n')

        todo_patterns = [
            r'#\s*TODO[:\s]',
            r'#\s*FIXME[:\s]',
            r'#\s*XXX[:\s]',
            r'#\s*HACK[:\s]',
            r'#\s*NOTE[:\s]*implement',
            r'#\s*NOTE[:\s]*add',
            r'#\s*NOTE[:\s]*create'
        ]

        for i, line in enumerate(lines, 1):
            for pattern in todo_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(QualityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        category=IssueCategory.MOCKUP,
                        severity=IssueSeverity.LOW,
                        rule_name="todo_comment",
                        message="TODO/FIXME comment found - indicates incomplete work",
                        code_snippet=line.strip(),
                        suggestion="Address the TODO item or convert to proper task tracking"
                    ))
                    break

        return issues

    @staticmethod
    def placeholder_variables(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        issues = []
        lines = content.split('\n')

        placeholder_names = [
            'foo', 'bar', 'baz', 'dummy', 'temp', 'test', 'example',
            'placeholder', 'mock', 'stub', 'fake'
        ]

        for i, line in enumerate(lines, 1):
            line_content = line.strip()
            if '=' in line_content and not line_content.startswith('#'):
                # Check variable assignments
                for placeholder in placeholder_names:
                    if re.search(rf'\b{placeholder}\b\s*=', line_content):
                        issues.append(QualityIssue(
                            file_path=str(file_path),
                            line_number=i,
                            category=IssueCategory.MOCKUP,
                            severity=IssueSeverity.LOW,
                            rule_name="placeholder_variable",
                            message=f"Placeholder variable name '{placeholder}' detected",
                            code_snippet=line_content,
                            suggestion="Use meaningful variable names"
                        ))
                        break

        return issues


class CodeQualityRules(DetectionRule):
    """Rules for detecting code quality issues"""

    def __init__(self):
        super().__init__("CodeQualityRules", IssueCategory.CODE_QUALITY, IssueSeverity.MEDIUM)

    def detect(self, file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        """Detect code quality issues"""
        issues = []

        # Run all code quality detection methods
        issues.extend(self.complexity_check(file_path, content, config))
        issues.extend(self.unused_imports(file_path, content, config))
        issues.extend(self.naming_conventions(file_path, content, config))

        return issues

    @staticmethod
    def complexity_check(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        issues = []
        thresholds = config.get("quality_thresholds", {}).get("function_complexity", {})

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Count lines in function
                    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                        line_count = node.end_lineno - node.lineno + 1
                        if line_count > thresholds.get("max_lines", 50):
                            issues.append(QualityIssue(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                category=IssueCategory.CODE_QUALITY,
                                severity=IssueSeverity.MEDIUM,
                                rule_name="function_too_long",
                                message=f"Function '{node.name}' is too long ({line_count} lines)",
                                code_snippet=f"def {node.name}(...):",
                                suggestion=f"Break down into smaller functions (max {thresholds.get('max_lines', 50)} lines)"
                            ))

                    # Count parameters
                    param_count = len(node.args.args)
                    if param_count > thresholds.get("max_parameters", 7):
                        issues.append(QualityIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            category=IssueCategory.CODE_QUALITY,
                            severity=IssueSeverity.MEDIUM,
                            rule_name="too_many_parameters",
                            message=f"Function '{node.name}' has too many parameters ({param_count})",
                            code_snippet=f"def {node.name}({', '.join(arg.arg for arg in node.args.args)}):",
                            suggestion="Consider using a configuration object or breaking into smaller functions"
                        ))

        except SyntaxError:
            # Skip files with syntax errors
            pass

        return issues

    @staticmethod
    def unused_imports(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        issues = []

        try:
            tree = ast.parse(content)

            # Get all imports
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
                    for alias in node.names:
                        imports.add(alias.name)

            # Get all used names
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)

            # Find unused imports
            unused = imports - used_names
            for unused_import in unused:
                issues.append(QualityIssue(
                    file_path=str(file_path),
                    line_number=1,  # Import lines are usually at top
                    category=IssueCategory.CODE_QUALITY,
                    severity=IssueSeverity.LOW,
                    rule_name="unused_import",
                    message=f"Unused import: {unused_import}",
                    code_snippet=f"import {unused_import}",
                    suggestion="Remove unused import to clean up code"
                ))

        except SyntaxError:
            pass

        return issues

    @staticmethod
    def naming_conventions(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        issues = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                        issues.append(QualityIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            category=IssueCategory.CODE_QUALITY,
                            severity=IssueSeverity.LOW,
                            rule_name="function_naming",
                            message=f"Function name '{node.name}' doesn't follow snake_case convention",
                            code_snippet=f"def {node.name}(",
                            suggestion="Use snake_case for function names"
                        ))

                elif isinstance(node, ast.ClassDef):
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                        issues.append(QualityIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            category=IssueCategory.CODE_QUALITY,
                            severity=IssueSeverity.LOW,
                            rule_name="class_naming",
                            message=f"Class name '{node.name}' doesn't follow PascalCase convention",
                            code_snippet=f"class {node.name}:",
                            suggestion="Use PascalCase for class names"
                        ))

        except SyntaxError:
            pass

        return issues


class IncompleteFeatureRules(DetectionRule):
    """Rules for detecting incomplete features"""

    def __init__(self):
        super().__init__("IncompleteFeatureRules", IssueCategory.INCOMPLETE, IssueSeverity.MEDIUM)

    def detect(self, file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        """Detect incomplete feature issues"""
        issues = []

        # Run all incomplete feature detection methods
        issues.extend(self.broken_imports(file_path, content, config))
        issues.extend(self.dead_code(file_path, content, config))

        return issues

    @staticmethod
    def broken_imports(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                # This is a basic check - in a real implementation, we'd try to import
                # For now, just flag suspicious import patterns
                if 'import *' in line and 'from' in line:
                    issues.append(QualityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        category=IssueCategory.INCOMPLETE,
                        severity=IssueSeverity.MEDIUM,
                        rule_name="wildcard_import",
                        message="Wildcard import detected - may hide missing dependencies",
                        code_snippet=line.strip(),
                        suggestion="Use explicit imports instead of 'from module import *'"
                    ))

        return issues

    @staticmethod
    def dead_code(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            line_content = line.strip()

            # Detect unreachable code after return
            if line_content.startswith('return ') or line_content == 'return':
                # Check next few lines for unreachable code
                for j in range(1, min(5, len(lines) - i)):
                    next_line = lines[i + j].strip()
                    if next_line and not next_line.startswith('#') and not next_line.startswith('"""'):
                        if not next_line.startswith(' ') and not next_line.startswith('\t'):
                            # Next line is not indented, so it's not part of the function
                            break
                        issues.append(QualityIssue(
                            file_path=str(file_path),
                            line_number=i + j,
                            category=IssueCategory.INCOMPLETE,
                            severity=IssueSeverity.LOW,
                            rule_name="unreachable_code",
                            message="Code after return statement is unreachable",
                            code_snippet=next_line,
                            suggestion="Remove unreachable code or fix control flow"
                        ))
                        break

        return issues


class ArchitectureRules(DetectionRule):
    """Rules for detecting architecture issues"""

    def __init__(self):
        super().__init__("ArchitectureRules", IssueCategory.ARCHITECTURE, IssueSeverity.HIGH)

    def detect(self, file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        """Detect architecture issues"""
        issues = []

        # Run all architecture detection methods
        issues.extend(self.circular_dependencies(file_path, content, config))

        return issues

    @staticmethod
    def circular_dependencies(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
        issues = []

        # This is a simplified check - real circular dependency detection
        # would require analyzing the entire codebase
        try:
            tree = ast.parse(content)

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)

            # Simple heuristic: if a file imports from a module with similar name
            file_stem = file_path.stem
            for imp in imports:
                if file_stem in imp and imp != file_stem:
                    issues.append(QualityIssue(
                        file_path=str(file_path),
                        line_number=1,
                        category=IssueCategory.ARCHITECTURE,
                        severity=IssueSeverity.HIGH,
                        rule_name="potential_circular_import",
                        message=f"Potential circular dependency: {file_stem} imports from {imp}",
                        code_snippet=f"from {imp} import ...",
                        suggestion="Review import structure to avoid circular dependencies"
                    ))

        except SyntaxError:
            pass

        return issues


# Registry of all detection rules
DETECTION_RULES = {
    # Mockup detection
    "placeholder_functions": MockupDetectionRules.placeholder_functions,
    "todo_comments": MockupDetectionRules.todo_comments,
    "placeholder_variables": MockupDetectionRules.placeholder_variables,

    # Code quality
    "complexity_check": CodeQualityRules.complexity_check,
    "unused_imports": CodeQualityRules.unused_imports,
    "naming_conventions": CodeQualityRules.naming_conventions,

    # Incomplete features
    "broken_imports": IncompleteFeatureRules.broken_imports,
    "dead_code": IncompleteFeatureRules.dead_code,

    # Architecture
    "circular_dependencies": ArchitectureRules.circular_dependencies,
}


def run_detection_rules(file_path: Path, content: str, config: Dict) -> List[QualityIssue]:
    """
    Run all enabled detection rules on a file

    Args:
        file_path: Path to the file being analyzed
        content: File content as string
        config: Quality configuration dictionary

    Returns:
        List of detected quality issues
    """
    all_issues = []

    for rule_name, rule_func in DETECTION_RULES.items():
        try:
            # Check if rule is enabled
            rule_config = config.get("detection_rules", {})
            category_enabled = False

            # Map rule to category
            if rule_name in ["placeholder_functions", "todo_comments", "placeholder_variables"]:
                category_enabled = rule_config.get("mockup_detection", {}).get("enabled", True)
                specific_enabled = rule_config.get("mockup_detection", {}).get(rule_name, True)
            elif rule_name in ["complexity_check", "unused_imports", "naming_conventions"]:
                category_enabled = rule_config.get("code_quality", {}).get("enabled", True)
                specific_enabled = rule_config.get("code_quality", {}).get(rule_name, True)
            elif rule_name in ["broken_imports", "dead_code"]:
                category_enabled = rule_config.get("incomplete_features", {}).get("enabled", True)
                specific_enabled = rule_config.get("incomplete_features", {}).get(rule_name, True)
            elif rule_name in ["circular_dependencies"]:
                category_enabled = rule_config.get("architecture", {}).get("enabled", True)
                specific_enabled = rule_config.get("architecture", {}).get(rule_name, True)
            else:
                specific_enabled = True

            if category_enabled and specific_enabled:
                issues = rule_func(file_path, content, config)
                all_issues.extend(issues)

        except Exception as e:
            # Log rule execution errors but don't fail the scan
            print(f"Error running rule {rule_name} on {file_path}: {e}")

    return all_issues
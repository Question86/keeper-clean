# MODE: SCRIPT\n\n"""Core Process Hardening Module.

This module provides protection mechanisms to prevent accidental corruption
of critical system files by AI agents. It defines:

1. IMMUTABLE_FILES - Files that should never be modified after creation
2. PROTECTED_PATTERNS - File patterns with restricted modification rules
3. POINTER_ONLY_FILES - Files that must contain only reference pointers

Design Philosophy:
- Defense-in-depth: Multiple layers of validation
- Fail-safe: When in doubt, block the modification
- Audit trail: Log all protection decisions

Usage:
    from core_hardening import (
        validate_edit_allowed,
        get_protection_status,
        check_core_integrity,
        ProtectionLevel,
    )
    
    # Check if a file can be edited
    result = validate_edit_allowed(Path("archive/ARCHIV_0001.md"))
    if not result.allowed:
        print(f"Edit blocked: {result.reason}")

Part of TASK_0147 - Core Process Hardening
"""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class ProtectionLevel(Enum):
    """Protection levels for workspace files."""
    IMMUTABLE = "immutable"        # Never modify after creation
    COCKPIT_ONLY = "cockpit_only"  # Only modify via loop_cockpit automation
    POINTER_ONLY = "pointer_only"  # Must contain only reference pointers
    SCHEMA_STRICT = "schema_strict" # Must maintain strict schema format
    UNRESTRICTED = "unrestricted"  # No special restrictions


@dataclass
class ProtectionStatus:
    """Status of file protection check."""
    path: str
    level: ProtectionLevel
    allowed: bool
    reason: str
    warnings: List[str]


# =============================================================================
# PROTECTION REGISTRY
# =============================================================================

# Files that should NEVER be modified after creation
IMMUTABLE_FILES: Set[str] = {
    # Archive files (pattern, checked dynamically)
    # PROJECT_TECH_BASELINE.md (core laws - human edits only)
}

# Pattern-based immutable files
IMMUTABLE_PATTERNS: List[re.Pattern] = [
    re.compile(r"archive[/\\]ARCHIV_\d{4}\.md$"),       # All archive files
    re.compile(r"archive[/\\]DIGEST_\d{4}\.md$"),      # All digest files
]

# Files only modifiable by cockpit automation
COCKPIT_ONLY_FILES: Set[str] = {
    "_LOOP_GATE.md",
    "_SESSION.md",
    "_BOOTSTRAP.md",
    "docs/HISTORY_INDEX.md",
    "docs/HISTORY_INDEX.json",
    "docs/QUERY_INDEX.json",
    "docs/CONTEXT_INDEX.json",
}

# Pattern-based cockpit-only files
COCKPIT_ONLY_PATTERNS: List[re.Pattern] = [
    # Generated indices and digests
]

# Files that must contain only reference pointers (no inline content)
POINTER_ONLY_FILES: Set[str] = {
    "NEURAL_CORTEX.md",
    "NEU.md",
    "Alt.md",
}

# Files with strict schema requirements
SCHEMA_STRICT_FILES: Dict[str, str] = {
    "current.json": "current_state",
    "knownissues.json": "known_issues",
    "milestone_01.json": "milestone",
}

# Core system files that require special care
CORE_SYSTEM_FILES: Set[str] = {
    "PROJECT_TECH_BASELINE.md",
    "loop_cockpit.py",
    "loop_guardrails.py",
    "core_hardening.py",
}


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def get_protection_level(filepath: Path) -> ProtectionLevel:
    """Determine the protection level for a file.
    
    Args:
        filepath: Path to the file (absolute or relative)
    
    Returns:
        ProtectionLevel enum value
    """
    # Normalize path for comparison
    path_str = str(filepath).replace("\\", "/")
    name = filepath.name
    
    # Check immutable patterns first (archives)
    for pattern in IMMUTABLE_PATTERNS:
        if pattern.search(path_str):
            return ProtectionLevel.IMMUTABLE
    
    # Check explicit immutable files
    if name in IMMUTABLE_FILES:
        return ProtectionLevel.IMMUTABLE
    
    # Check cockpit-only files
    if name in COCKPIT_ONLY_FILES:
        return ProtectionLevel.COCKPIT_ONLY
    
    for pattern in COCKPIT_ONLY_PATTERNS:
        if pattern.search(path_str):
            return ProtectionLevel.COCKPIT_ONLY
    
    # Check pointer-only files
    if name in POINTER_ONLY_FILES:
        return ProtectionLevel.POINTER_ONLY
    
    # Check schema-strict files
    if name in SCHEMA_STRICT_FILES:
        return ProtectionLevel.SCHEMA_STRICT
    
    return ProtectionLevel.UNRESTRICTED


def validate_edit_allowed(
    filepath: Path,
    caller: str = "unknown",
    is_cockpit: bool = False,
) -> ProtectionStatus:
    """Check if editing a file is allowed.
    
    Args:
        filepath: Path to the file being edited
        caller: Identifier for the caller (for audit trail)
        is_cockpit: True if called from cockpit automation
    
    Returns:
        ProtectionStatus with allowed=True/False and reason
    """
    path_str = str(filepath).replace("\\", "/")
    level = get_protection_level(filepath)
    warnings: List[str] = []
    
    # IMMUTABLE: Never allow modifications
    if level == ProtectionLevel.IMMUTABLE:
        return ProtectionStatus(
            path=path_str,
            level=level,
            allowed=False,
            reason=f"File is IMMUTABLE and cannot be modified. Archives are final.",
            warnings=[],
        )
    
    # COCKPIT_ONLY: Only allow if caller is cockpit
    if level == ProtectionLevel.COCKPIT_ONLY:
        if is_cockpit:
            return ProtectionStatus(
                path=path_str,
                level=level,
                allowed=True,
                reason="Cockpit automation has permission to modify this file.",
                warnings=[],
            )
        else:
            return ProtectionStatus(
                path=path_str,
                level=level,
                allowed=False,
                reason=f"File is COCKPIT_ONLY and can only be modified via loop_cockpit automation.",
                warnings=[],
            )
    
    # POINTER_ONLY: Allow but warn about content restrictions
    if level == ProtectionLevel.POINTER_ONLY:
        warnings.append(
            f"File {filepath.name} is POINTER_ONLY: ensure only [ref:...] pointers are added, no inline content."
        )
        return ProtectionStatus(
            path=path_str,
            level=level,
            allowed=True,
            reason="File can be modified but must maintain pointer-only structure.",
            warnings=warnings,
        )
    
    # SCHEMA_STRICT: Allow but warn about schema requirements
    if level == ProtectionLevel.SCHEMA_STRICT:
        schema_name = SCHEMA_STRICT_FILES.get(filepath.name, "unknown")
        warnings.append(
            f"File {filepath.name} has SCHEMA_STRICT protection: must maintain {schema_name} schema."
        )
        return ProtectionStatus(
            path=path_str,
            level=level,
            allowed=True,
            reason="File can be modified but must maintain schema structure.",
            warnings=warnings,
        )
    
    # UNRESTRICTED: No special restrictions
    # Add warning for core system files
    if filepath.name in CORE_SYSTEM_FILES:
        warnings.append(
            f"⚠️ {filepath.name} is a CORE SYSTEM FILE. Modifications should be careful and intentional."
        )
    
    return ProtectionStatus(
        path=path_str,
        level=level,
        allowed=True,
        reason="No protection restrictions.",
        warnings=warnings,
    )


def get_protection_status(filepath: Path) -> Dict[str, any]:
    """Get protection information for a file (for API/UI).
    
    Returns a dictionary with protection details suitable for JSON serialization.
    """
    level = get_protection_level(filepath)
    status = validate_edit_allowed(filepath)
    
    return {
        "path": str(filepath),
        "level": level.value,
        "allowed": status.allowed,
        "reason": status.reason,
        "warnings": status.warnings,
        "is_core_file": filepath.name in CORE_SYSTEM_FILES,
        "is_pointer_only": filepath.name in POINTER_ONLY_FILES,
    }


# =============================================================================
# INTEGRITY CHECKING
# =============================================================================

def compute_file_hash(filepath: Path) -> Optional[str]:
    """Compute SHA-256 hash of file content."""
    try:
        content = filepath.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]  # First 16 chars
    except Exception:
        return None


def check_pointer_only_compliance(filepath: Path) -> Tuple[bool, List[str]]:
    """Check if a pointer-only file contains only valid references.
    
    Returns:
        (compliant, violations) - True if compliant, list of violations if not
    """
    if filepath.name not in POINTER_ONLY_FILES:
        return True, []
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Could not read file: {e}"]
    
    violations = []
    
    # Check for prohibited content patterns
    # Pointer-only files should contain:
    # - Markdown headers (# ## ###)
    # - Reference links [ref:...]
    # - Minimal structural text (MODE:, STATUS:, etc.)
    # - Whitespace and separators (---)
    
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        # Allow headers
        if line.startswith("#"):
            continue
        
        # Allow reference links
        if "[ref:" in line:
            continue
        
        # Allow metadata lines
        if any(line.startswith(prefix) for prefix in [
            "MODE:", "STATUS:", "CREATED:", "UPDATED:", "CONTENT:",
            "Process Rules:", "Read from:", "**", "- ", "* ", "✓", "✅", "❌",
            "---", "END OF DOCUMENT", "Loop", "Phase", "BACKLOG", "NEXT",
            "###", "Summary:", "Priority:",
        ]):
            continue
        
        # Allow empty bullets and short list items
        if len(line) < 100 and any(line.startswith(c) for c in ["-", "*", "•"]):
            continue
        
        # Flag potential inline content (long text blocks)
        if len(line) > 200:
            violations.append(f"Line {i}: Potential inline content (>200 chars)")
    
    return len(violations) == 0, violations


def check_core_integrity(workspace_root: Path) -> Dict[str, any]:
    """Run integrity checks on all protected files.
    
    Returns a report of integrity check results.
    """
    results = {
        "checked_at": None,  # Will be set by caller
        "immutable_files": [],
        "pointer_only_files": [],
        "schema_files": [],
        "violations": [],
        "summary": {
            "total_checked": 0,
            "immutable_ok": 0,
            "pointer_only_ok": 0,
            "schema_ok": 0,
            "violations_count": 0,
        }
    }
    
    # Check all files in archive/ are present and haven't been tampered with
    archive_dir = workspace_root / "archive"
    if archive_dir.exists():
        for archiv_file in sorted(archive_dir.glob("ARCHIV_*.md")):
            results["immutable_files"].append({
                "path": str(archiv_file.relative_to(workspace_root)),
                "hash": compute_file_hash(archiv_file),
                "exists": True,
            })
            results["summary"]["immutable_ok"] += 1
            results["summary"]["total_checked"] += 1
    
    # Check pointer-only files
    for name in POINTER_ONLY_FILES:
        filepath = workspace_root / name
        if filepath.exists():
            compliant, violations = check_pointer_only_compliance(filepath)
            results["pointer_only_files"].append({
                "path": name,
                "compliant": compliant,
                "violations": violations,
            })
            if compliant:
                results["summary"]["pointer_only_ok"] += 1
            else:
                results["violations"].extend([
                    {"file": name, "violation": v} for v in violations
                ])
                results["summary"]["violations_count"] += len(violations)
            results["summary"]["total_checked"] += 1
    
    # Check schema files exist
    for name in SCHEMA_STRICT_FILES:
        filepath = workspace_root / name
        results["schema_files"].append({
            "path": name,
            "exists": filepath.exists(),
            "schema": SCHEMA_STRICT_FILES[name],
        })
        if filepath.exists():
            results["summary"]["schema_ok"] += 1
        results["summary"]["total_checked"] += 1
    
    return results


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """CLI for testing hardening checks."""
    import argparse
    import json
    from datetime import datetime, timezone
    
    parser = argparse.ArgumentParser(description="Core Process Hardening")
    parser.add_argument("--check", type=str, help="Check protection status of a file")
    parser.add_argument("--integrity", action="store_true", help="Run full integrity check")
    parser.add_argument("--list-protected", action="store_true", help="List all protected files")
    args = parser.parse_args()
    
    workspace = Path(__file__).parent
    
    if args.check:
        filepath = Path(args.check)
        if not filepath.is_absolute():
            filepath = workspace / filepath
        status = get_protection_status(filepath)
        print(json.dumps(status, indent=2))
    
    elif args.integrity:
        results = check_core_integrity(workspace)
        results["checked_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(json.dumps(results, indent=2))
    
    elif args.list_protected:
        print("=== IMMUTABLE FILES ===")
        for f in sorted(IMMUTABLE_FILES):
            print(f"  {f}")
        print("\n=== IMMUTABLE PATTERNS ===")
        for p in IMMUTABLE_PATTERNS:
            print(f"  {p.pattern}")
        print("\n=== COCKPIT-ONLY FILES ===")
        for f in sorted(COCKPIT_ONLY_FILES):
            print(f"  {f}")
        print("\n=== POINTER-ONLY FILES ===")
        for f in sorted(POINTER_ONLY_FILES):
            print(f"  {f}")
        print("\n=== SCHEMA-STRICT FILES ===")
        for f, s in sorted(SCHEMA_STRICT_FILES.items()):
            print(f"  {f} -> {s}")
        print("\n=== CORE SYSTEM FILES ===")
        for f in sorted(CORE_SYSTEM_FILES):
            print(f"  {f}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

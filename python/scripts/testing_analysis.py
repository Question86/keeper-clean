#!/usr/bin/env python3
"""
Testing Coverage Analysis (TASK_0221)

Analyzes test-to-module coverage and generates a concrete testing expansion plan.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set


EXCLUDE_DIRS = {".git", ".venv", "venv", "venv310", "venv311", "venv312", "__pycache__", ".pytest_cache"}


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def discover_modules(workspace: Path) -> List[Path]:
    modules: List[Path] = []
    for p in workspace.rglob("*.py"):
        if _is_excluded(p):
            continue
        rel = p.relative_to(workspace)
        if rel.parts and rel.parts[0] == "tests":
            continue
        if p.name.startswith("test_"):
            continue
        modules.append(rel)
    return sorted(modules)


def discover_tests(workspace: Path) -> List[Path]:
    tests: List[Path] = []
    for p in workspace.rglob("test_*.py"):
        if _is_excluded(p):
            continue
        rel = p.relative_to(workspace)
        tests.append(rel)
    return sorted(tests)


def module_stem(path: Path) -> str:
    return path.stem.lower()


def analyze_testing_coverage(workspace: Path, target: float = 0.60) -> Dict:
    modules = discover_modules(workspace)
    tests = discover_tests(workspace)

    test_stems: Set[str] = {module_stem(t).removeprefix("test_") for t in tests}
    covered = [m for m in modules if module_stem(m) in test_stems]
    uncovered = [m for m in modules if module_stem(m) not in test_stems]

    total = len(modules)
    covered_count = len(covered)
    coverage_ratio = (covered_count / total) if total else 1.0

    critical_prefixes = ("scripts", "api", "ui")
    critical_uncovered = [str(p) for p in uncovered if p.parts and p.parts[0] in critical_prefixes][:30]

    required_content = []
    if coverage_ratio < target:
        required_content.append(
            {
                "area": "module_test_coverage",
                "current": round(coverage_ratio, 4),
                "target": target,
                "gap": round(target - coverage_ratio, 4),
                "recommended_new_tests": max(1, int((target * total) - covered_count + 0.9999)),
            }
        )

    implementation_plan = [
        "Generate tests for uncovered critical modules under scripts/api/ui first.",
        "Add deterministic smoke tests for orchestration and maintenance scripts.",
        "Enforce minimum test coverage gate in CI for newly added modules.",
        "Re-run testing analysis after each batch to track progress to target.",
    ]

    cross_references = []
    for module in uncovered[:10]:
        suggested = f"tests/test_{module.stem}.py"
        cross_references.append(
            {
                "module": str(module),
                "suggested_test": suggested,
                "reason": "Missing direct test mapping for module stem",
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workspace": str(workspace),
        "target_coverage": target,
        "module_count": total,
        "test_file_count": len(tests),
        "covered_modules": covered_count,
        "coverage_ratio": round(coverage_ratio, 4),
        "under_target": coverage_ratio < target,
        "required_content": required_content,
        "implementation_plan": implementation_plan,
        "critical_uncovered": critical_uncovered,
        "cross_references": cross_references,
    }


def render_plan_markdown(result: Dict) -> str:
    lines: List[str] = []
    lines.append("# Testing Expansion Plan")
    lines.append("")
    lines.append("## Coverage Snapshot")
    lines.append(f"- Generated: {result['generated_at']}")
    lines.append(f"- Target module coverage: {result['target_coverage']:.0%}")
    lines.append(f"- Current module coverage: {result['coverage_ratio']:.2%}")
    lines.append(f"- Covered modules: {result['covered_modules']} / {result['module_count']}")
    lines.append("")
    lines.append("## Required Content")
    if result["required_content"]:
        for item in result["required_content"]:
            lines.append(
                f"- {item['area']}: current {item['current']:.2%}, target {item['target']:.0%}, "
                f"recommended new tests {item['recommended_new_tests']}"
            )
    else:
        lines.append("- Target currently met; continue incremental improvements.")
    lines.append("")
    lines.append("## Implementation Plan")
    for step in result["implementation_plan"]:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Cross-Reference Actions")
    for ref in result["cross_references"][:10]:
        lines.append(f"- {ref['module']} -> {ref['suggested_test']} ({ref['reason']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze testing coverage and generate expansion plan")
    parser.add_argument("--workspace", default=".", help="Workspace root")
    parser.add_argument("--target", type=float, default=0.60, help="Target module coverage ratio")
    parser.add_argument("--output", default="", help="Output JSON report path")
    parser.add_argument("--plan-doc", default="docs/testing_expansion_plan.md", help="Output markdown plan path")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    result = analyze_testing_coverage(workspace=workspace, target=args.target)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    output = (
        Path(args.output)
        if args.output
        else reports_dir / f"testing_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    plan = Path(args.plan_doc)
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(render_plan_markdown(result), encoding="utf-8")

    print(f"coverage={result['coverage_ratio']}")
    print(f"under_target={result['under_target']}")
    print(f"report={output}")
    print(f"plan={plan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

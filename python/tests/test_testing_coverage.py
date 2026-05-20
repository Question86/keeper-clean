#!/usr/bin/env python3
"""Tests for TASK_0221 testing coverage analysis."""

from __future__ import annotations

from pathlib import Path

from scripts.testing_analysis import analyze_testing_coverage, render_plan_markdown


def test_analyze_testing_coverage_detects_uncovered(tmp_path: Path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()

    (tmp_path / "scripts" / "alpha.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "scripts" / "beta.py").write_text("print('b')\n", encoding="utf-8")
    (tmp_path / "tests" / "test_alpha.py").write_text("def test_alpha():\n    assert True\n", encoding="utf-8")

    result = analyze_testing_coverage(tmp_path, target=0.80)
    assert result["module_count"] == 2
    assert result["covered_modules"] == 1
    assert result["under_target"] is True
    assert result["required_content"]
    assert result["cross_references"]


def test_render_plan_markdown_has_required_sections():
    sample = {
        "generated_at": "2026-02-16T00:00:00Z",
        "target_coverage": 0.60,
        "coverage_ratio": 0.25,
        "covered_modules": 5,
        "module_count": 20,
        "required_content": [
            {
                "area": "module_test_coverage",
                "current": 0.25,
                "target": 0.60,
                "recommended_new_tests": 7,
            }
        ],
        "implementation_plan": ["a", "b"],
        "cross_references": [{"module": "scripts/x.py", "suggested_test": "tests/test_x.py", "reason": "mapping"}],
    }
    md = render_plan_markdown(sample)
    assert "# Testing Expansion Plan" in md
    assert "## Coverage Snapshot" in md
    assert "## Required Content" in md
    assert "## Implementation Plan" in md
    assert "## Cross-Reference Actions" in md

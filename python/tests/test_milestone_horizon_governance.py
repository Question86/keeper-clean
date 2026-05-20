#!/usr/bin/env python3
"""Tests for TASK_0135 milestone horizon governance enrichment."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.milestone_horizon_governance import enrich_milestone


def test_enrich_milestone_adds_required_blocks(tmp_path: Path):
    p = tmp_path / "milestone_99.json"
    p.write_text(
        json.dumps(
            {
                "MILESTONE": {"id": "99", "name": "Test", "status": "PLANNING"},
                "GOALS": [{"id": "G001", "description": "Test goal", "status": "NOT_STARTED"}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    out = enrich_milestone(p)
    assert out["changed"] is True
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "PLANNING_HORIZONS" in data
    assert "TOKEN_GOVERNANCE" in data
    assert set(data["PLANNING_HORIZONS"].keys()) == {"short_term", "mid_term", "long_term"}

#!/usr/bin/env python3
"""Add planning-horizon and token-governance blocks to milestone files (TASK_0135)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


DEFAULT_HORIZONS = {
    "short_term": {"loop_range": [1, 5], "priority_weight": 0.6, "focus": "immediate_execution"},
    "mid_term": {"loop_range": [5, 20], "priority_weight": 0.3, "focus": "milestone_progress"},
    "long_term": {"loop_range": [20, 50], "priority_weight": 0.1, "focus": "strategic_scaling"},
}

DEFAULT_TOKEN_GOVERNANCE = {
    "budget_policy": {
        "safe_zone_pct": 50,
        "caution_zone_pct": 75,
        "conservation_zone_pct": 85,
        "emergency_zone_pct": 95,
    },
    "allocation": {"short_term": 0.30, "mid_term": 0.50, "long_term": 0.20},
    "rules": [
        "Prioritize short_term goals in conservation/emergency zones.",
        "Defer long_term acquisition when token zone is emergency or abort.",
        "Require milestone-aware relevance for external knowledge imports.",
    ],
}


def enrich_milestone(path: Path) -> Dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    if "PLANNING_HORIZONS" not in data:
        data["PLANNING_HORIZONS"] = DEFAULT_HORIZONS
        changed = True
    if "TOKEN_GOVERNANCE" not in data:
        data["TOKEN_GOVERNANCE"] = DEFAULT_TOKEN_GOVERNANCE
        changed = True
    if changed:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"path": str(path), "changed": changed}


def find_milestones(workspace: Path) -> List[Path]:
    return sorted(p for p in workspace.glob("milestone_*.json") if p.stem[10:].isdigit())


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich milestone json files with planning horizons and token governance")
    parser.add_argument("--workspace", default=".", help="Workspace root")
    args = parser.parse_args()

    ws = Path(args.workspace).resolve()
    milestones = find_milestones(ws)
    results = [enrich_milestone(m) for m in milestones]
    changed = sum(1 for r in results if r["changed"])
    print(json.dumps({"milestones": len(results), "changed": changed, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Autostart-safe wrapper for external_knowledge_importer.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _find_milestone_id(gaps_path: Path) -> str | None:
    try:
        data = json.loads(gaps_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    milestones = data.get("milestones")
    if not isinstance(milestones, list) or not milestones:
        return None
    for item in milestones:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
            return item["id"].strip()
    return None


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    gaps_path = root / "milestone_knowledge_gaps.json"
    if not gaps_path.exists():
        print("autostart_external_knowledge_importer: skipping (milestone_knowledge_gaps.json missing)")
        return 0

    milestone_id = _find_milestone_id(gaps_path)
    if not milestone_id:
        print("autostart_external_knowledge_importer: skipping (no milestone id in gaps file)")
        return 0

    cmd = [
        sys.executable,
        str(root / "scripts" / "external_knowledge_importer.py"),
        "--milestone",
        milestone_id,
    ]
    completed = subprocess.run(cmd, cwd=str(root))
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

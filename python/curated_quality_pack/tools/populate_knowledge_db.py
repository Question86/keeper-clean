"""Rebuild keeper_knowledge.db and emit deterministic quality summary.

Usage:
    python tools/populate_knowledge_db.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

# Ensure workspace root is on sys.path so local modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from knowledge_db import KnowledgeDB
from policy_gate import enforce_db_write_policy

WORKSPACE = Path(__file__).resolve().parent.parent
SUMMARY_PATH = WORKSPACE / "logs" / "knowledge_db_rebuild_summary.json"

CRITICAL_ERROR_PATTERNS = (
    "database is locked",
    "not null constraint failed: lessons.source_id",
)


def _classify_errors(errors: List[str]) -> Dict[str, List[str]]:
    critical = []
    non_critical = []
    for err in errors:
        text = err.lower()
        if any(pat in text for pat in CRITICAL_ERROR_PATTERNS):
            critical.append(err)
        else:
            non_critical.append(err)
    return {"critical": critical, "non_critical": non_critical}


def _is_hard_fail(stats: Dict[str, object], critical_errors: List[str]) -> bool:
    if critical_errors:
        return True
    # Require basic population to be non-zero for primary tables.
    for key in ("reports_indexed", "archives_indexed", "tasks_indexed"):
        if int(stats.get(key, 0) or 0) <= 0:
            return True
    return False


def main() -> int:
    decision = enforce_db_write_policy(
        WORKSPACE,
        operation="knowledge.rebuild",
        actor="system",
    )
    if not decision.allowed:
        print(json.dumps({
            "ok": False,
            "hard_fail": True,
            "error": decision.reason,
            "policy": decision.policy_path,
        }, indent=2, ensure_ascii=False))
        return 2

    db = KnowledgeDB(WORKSPACE)
    print("Starting knowledge DB rebuild...")
    stats = db.rebuild_with_write_guard()
    db.close()

    errors = list(stats.get("errors", []) or [])
    classified = _classify_errors(errors)
    hard_fail = _is_hard_fail(stats, classified["critical"])

    summary = {
        "ok": not hard_fail,
        "hard_fail": hard_fail,
        "stats": stats,
        "error_summary": {
            "total": len(errors),
            "critical_count": len(classified["critical"]),
            "non_critical_count": len(classified["non_critical"]),
            "critical_examples": classified["critical"][:25],
        },
    }

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Summary written to: {SUMMARY_PATH}")

    return 2 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

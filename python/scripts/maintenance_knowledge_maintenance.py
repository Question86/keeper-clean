#!/usr/bin/env python3
"""
Knowledge Maintenance Audit (TASK_0226)

Audits freshness across core knowledge tables, emits maintenance scope, quality
checks, and actionable automation opportunities.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional


TABLES = {
    "docs": "docs",
    "reports": "reports",
    "tasks": "tasks",
    "archives": "archives",
    "bugs": "bugs",
    "code": "code",
}


@dataclass
class TableFreshness:
    total: int
    fresh: int
    stale: int
    missing_indexed_at: int
    missing_paths: int

    @property
    def freshness_score(self) -> float:
        if self.total <= 0:
            return 1.0
        return self.fresh / self.total


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows]


def audit_table(
    conn: sqlite3.Connection,
    workspace_root: Path,
    table: str,
    cutoff: datetime,
) -> TableFreshness:
    cols = set(table_columns(conn, table))
    if "indexed_at" not in cols:
        return TableFreshness(total=0, fresh=0, stale=0, missing_indexed_at=0, missing_paths=0)

    has_path = "path" in cols
    query = "SELECT indexed_at" + (", path" if has_path else "") + f" FROM {table}"
    rows = conn.execute(query).fetchall()

    total = len(rows)
    fresh = 0
    stale = 0
    missing_indexed = 0
    missing_paths = 0

    for row in rows:
        indexed = parse_iso(row[0])
        if indexed is None:
            missing_indexed += 1
            stale += 1
        elif indexed >= cutoff:
            fresh += 1
        else:
            stale += 1

        if has_path:
            rel = row[1] or ""
            if rel:
                p = Path(rel)
                if not p.is_absolute():
                    p = (workspace_root / p).resolve()
                if not p.exists():
                    missing_paths += 1

    return TableFreshness(
        total=total,
        fresh=fresh,
        stale=stale,
        missing_indexed_at=missing_indexed,
        missing_paths=missing_paths,
    )


def build_result(
    db_path: Path,
    workspace_root: Path,
    days: int,
    min_freshness_score: float,
) -> Dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    conn = sqlite3.connect(str(db_path))
    by_table: Dict[str, Dict] = {}
    try:
        for _, table in TABLES.items():
            stats = audit_table(conn, workspace_root, table, cutoff)
            by_table[table] = {
                "total": stats.total,
                "fresh": stats.fresh,
                "stale": stats.stale,
                "missing_indexed_at": stats.missing_indexed_at,
                "missing_paths": stats.missing_paths,
                "freshness_score": round(stats.freshness_score, 4),
            }
    finally:
        conn.close()

    total_items = sum(v["total"] for v in by_table.values())
    total_fresh = sum(v["fresh"] for v in by_table.values())
    overall_freshness = (total_fresh / total_items) if total_items else 1.0

    maintenance_scope: List[Dict] = []
    for table, stats in by_table.items():
        if stats["total"] == 0:
            continue
        if stats["freshness_score"] < min_freshness_score or stats["stale"] > 0 or stats["missing_paths"] > 0:
            maintenance_scope.append(
                {
                    "table": table,
                    "reason": "freshness_below_target_or_stale_or_missing",
                    "freshness_score": stats["freshness_score"],
                    "stale": stats["stale"],
                    "missing_paths": stats["missing_paths"],
                }
            )

    quality_checks = {
        "indexed_at_present": all(v["missing_indexed_at"] == 0 for v in by_table.values()),
        "path_integrity": all(v["missing_paths"] == 0 for v in by_table.values()),
        "table_coverage": {k: v["total"] for k, v in by_table.items()},
    }

    automation_opportunities: List[Dict[str, str]] = []
    for table, stats in by_table.items():
        if stats["stale"] > 0:
            automation_opportunities.append(
                {
                    "table": table,
                    "opportunity": "schedule_incremental_reindex",
                    "value": f"{stats['stale']} stale rows can be refreshed via automated indexing pipeline",
                }
            )
        if stats["missing_paths"] > 0:
            automation_opportunities.append(
                {
                    "table": table,
                    "opportunity": "orphan_path_cleaner",
                    "value": f"{stats['missing_paths']} missing paths can be auto-flagged for cleanup",
                }
            )

    process_improvements = [
        "Run maintenance audit weekly with threshold-based action gates.",
        "Trigger targeted re-index jobs only for tables below freshness target.",
        "Track stale counts and path integrity drift in loop reports.",
    ]

    return {
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "db_path": str(db_path),
        "workspace_root": str(workspace_root),
        "params": {
            "days_threshold": days,
            "min_freshness_score": min_freshness_score,
        },
        "summary": {
            "overall_freshness_score": round(overall_freshness, 4),
            "total_items": total_items,
            "total_fresh": total_fresh,
            "maintenance_tables": len(maintenance_scope),
        },
        "maintenance_scope": maintenance_scope,
        "per_table": by_table,
        "update_procedures": [
            "Identify stale/missing-path rows by table.",
            "Run incremental index for impacted files/tables.",
            "Re-run audit and confirm freshness target compliance.",
        ],
        "quality_checks": quality_checks,
        "automation_opportunities": automation_opportunities,
        "process_improvements": process_improvements,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit knowledge freshness and emit maintenance plan")
    parser.add_argument("--db", default="keeper_knowledge.db", help="Path to SQLite knowledge DB")
    parser.add_argument("--workspace", default=".", help="Workspace root path")
    parser.add_argument("--days", type=int, default=90, help="Freshness threshold in days")
    parser.add_argument("--min-freshness", type=float, default=0.60, help="Minimum acceptable freshness score")
    parser.add_argument(
        "--output",
        default="",
        help="Output JSON path (default: reports/maintenance_knowledge_maintenance_<timestamp>.json)",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 1

    workspace_root = Path(args.workspace).resolve()
    result = build_result(db_path=db_path, workspace_root=workspace_root, days=args.days, min_freshness_score=args.min_freshness)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    output = (
        Path(args.output)
        if args.output
        else reports_dir / f"maintenance_knowledge_maintenance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"overall_freshness={result['summary']['overall_freshness_score']}")
    print(f"maintenance_tables={result['summary']['maintenance_tables']}")
    print(f"automation_opportunities={len(result['automation_opportunities'])}")
    print(f"report={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

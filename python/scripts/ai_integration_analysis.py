#!/usr/bin/env python3
"""
AI Integration Coverage Analysis (TASK_0225)

Measures AI-integration coverage across core knowledge tables and generates an
expansion plan with prioritized content and cross-reference actions.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


DEFAULT_KEYWORDS = [
    "ai",
    "agent",
    "llm",
    "model",
    "embedding",
    "openai",
    "anthropic",
    "mistral",
    "copilot",
    "prompt",
    "semantic",
    "inference",
    "vector",
]

TABLE_FIELDS = {
    "docs": ["id", "title", "path", "category", "tags", "content_full"],
    "reports": ["id", "task_id", "path", "goal", "tags", "keywords", "content_full"],
    "tasks": ["id", "path", "objective", "seed_idea", "tags"],
    "archives": ["id", "path", "summary", "lessons_learned", "content_full"],
    "bugs": ["id", "title", "path", "tags", "content_full"],
    "code": ["id", "title", "path", "category", "tags", "content_full"],
}


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _coverage_for_table(
    conn: sqlite3.Connection,
    table: str,
    fields: Sequence[str],
    keywords: Sequence[str],
) -> Dict:
    cols = set(_table_columns(conn, table))
    valid_fields = [f for f in fields if f in cols]
    if not valid_fields:
        return {"table": table, "total": 0, "ai_related": 0, "coverage": 0.0, "examples": []}

    id_field = "id" if "id" in cols else valid_fields[0]
    select_fields = [id_field] + [f for f in valid_fields if f != id_field]
    rows = conn.execute(f"SELECT {', '.join(select_fields)} FROM {table}").fetchall()
    total = len(rows)
    if total <= 0:
        return {"table": table, "total": 0, "ai_related": 0, "coverage": 0.0, "examples": []}

    patterns = [re.compile(rf"\b{re.escape(kw.lower())}\b") for kw in keywords]
    ai_related = 0
    examples: List[str] = []
    for row in rows:
        row_id = row[0]
        haystack = " ".join(str(x or "").lower() for x in row[1:])
        if any(p.search(haystack) for p in patterns):
            ai_related += 1
            if row_id and len(examples) < 5:
                examples.append(str(row_id))

    return {
        "table": table,
        "total": total,
        "ai_related": ai_related,
        "coverage": round(ai_related / total, 4),
        "examples": examples,
    }


def analyze_ai_coverage(
    db_path: Path,
    target_coverage: float = 0.15,
    keywords: Sequence[str] = DEFAULT_KEYWORDS,
) -> Dict:
    conn = sqlite3.connect(str(db_path))
    try:
        per_table = [
            _coverage_for_table(conn, table, fields, keywords)
            for table, fields in TABLE_FIELDS.items()
        ]
    finally:
        conn.close()

    total_items = sum(x["total"] for x in per_table)
    total_ai = sum(x["ai_related"] for x in per_table)
    overall = round((total_ai / total_items), 4) if total_items else 0.0
    underrepresented = [x for x in per_table if x["total"] > 0 and x["coverage"] < target_coverage]

    required_content = []
    for row in underrepresented:
        required_content.append(
            {
                "table": row["table"],
                "current_coverage": row["coverage"],
                "target_coverage": target_coverage,
                "gap": round(target_coverage - row["coverage"], 4),
                "recommended_new_items": max(1, int((target_coverage * row["total"]) - row["ai_related"] + 0.9999)),
            }
        )

    implementation_plan = [
        "Create targeted AI integration docs for underrepresented tables.",
        "Link new AI docs to related tasks/reports to improve retrieval graph connectivity.",
        "Index all created artifacts and re-run coverage analysis.",
        "Gate closure on achieving or trending toward target coverage per table.",
    ]

    cross_refs = []
    seeds = [x for x in per_table if x["examples"]]
    if len(seeds) >= 2:
        for left in seeds[:3]:
            for right in seeds[1:4]:
                if left["table"] == right["table"]:
                    continue
                cross_refs.append(
                    {
                        "from_table": left["table"],
                        "from_id": left["examples"][0],
                        "to_table": right["table"],
                        "to_id": right["examples"][0],
                        "reason": "Establish cross-domain AI integration traceability",
                    }
                )
                if len(cross_refs) >= 10:
                    break
            if len(cross_refs) >= 10:
                break

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "db_path": str(db_path),
        "target_coverage": target_coverage,
        "keywords": list(keywords),
        "overall_coverage": overall,
        "total_items": total_items,
        "total_ai_related": total_ai,
        "per_table": per_table,
        "underrepresented_tables": [x["table"] for x in underrepresented],
        "required_content": required_content,
        "implementation_plan": implementation_plan,
        "cross_references": cross_refs,
    }


def render_markdown_plan(result: Dict) -> str:
    lines: List[str] = []
    lines.append("# AI Integration Expansion Plan")
    lines.append("")
    lines.append("## Coverage Snapshot")
    lines.append(f"- Generated: {result['generated_at']}")
    lines.append(f"- Target coverage: {result['target_coverage']:.0%}")
    lines.append(f"- Overall AI coverage: {result['overall_coverage']:.2%}")
    lines.append(f"- Total AI-related entries: {result['total_ai_related']} / {result['total_items']}")
    lines.append("")
    lines.append("## Underrepresented Tables")
    if result["required_content"]:
        for item in result["required_content"]:
            lines.append(
                f"- {item['table']}: current {item['current_coverage']:.2%}, target {item['target_coverage']:.0%}, "
                f"recommended new items {item['recommended_new_items']}"
            )
    else:
        lines.append("- None; target met across all measured tables.")
    lines.append("")
    lines.append("## Implementation Plan")
    for step in result["implementation_plan"]:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Cross-Reference Actions")
    if result["cross_references"]:
        for ref in result["cross_references"][:10]:
            lines.append(
                f"- Link {ref['from_table']}:{ref['from_id']} -> {ref['to_table']}:{ref['to_id']} ({ref['reason']})"
            )
    else:
        lines.append("- No cross-reference recommendations available from current sample set.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze AI integration coverage and generate expansion plan")
    parser.add_argument("--db", default="keeper_knowledge.db", help="SQLite DB path")
    parser.add_argument("--target", type=float, default=0.15, help="Target AI coverage ratio")
    parser.add_argument("--output", default="", help="Output JSON report path")
    parser.add_argument("--plan-doc", default="docs/ai_integration_expansion_plan.md", help="Markdown plan path")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 1

    result = analyze_ai_coverage(db_path=db_path, target_coverage=args.target)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    output = (
        Path(args.output)
        if args.output
        else reports_dir / f"ai_integration_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    plan_path = Path(args.plan_doc)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(render_markdown_plan(result), encoding="utf-8")

    print(f"overall_coverage={result['overall_coverage']}")
    print(f"underrepresented={len(result['underrepresented_tables'])}")
    print(f"report={output}")
    print(f"plan={plan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

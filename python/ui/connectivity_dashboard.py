#!/usr/bin/env python3
"""
Connectivity Dashboard (CLI)

Reads a connectivity analysis JSON report and prints a concise operator view.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def latest_report() -> Path | None:
    reports = sorted(Path("reports").glob("connectivity_improvements_*.json"))
    return reports[-1] if reports else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Display connectivity analysis report summary.")
    parser.add_argument("--report", default="", help="Report JSON path (defaults to latest connectivity report).")
    parser.add_argument("--limit", type=int, default=10, help="Max suggestions to print.")
    args = parser.parse_args()

    report_path = Path(args.report) if args.report else latest_report()
    if not report_path or not report_path.exists():
        print("No connectivity report found. Run scripts/connectivity_improvements.py first.")
        return 0

    data = json.loads(report_path.read_text(encoding="utf-8"))
    print("CONNECTIVITY DASHBOARD")
    print("======================")
    print(f"report: {report_path}")
    print(f"generated_at: {data.get('generated_at')}")
    print(f"nodes: {data.get('nodes')}")
    print(f"components: {data.get('components')}")
    print(f"small_components: {data.get('small_components')}")
    print(f"density: {data.get('density'):.4f}")
    print(f"largest_component_size: {data.get('largest_component_size')}")
    print()
    print("Top suggestions:")
    suggestions = data.get("suggestions", [])
    for i, rec in enumerate(suggestions[: max(0, args.limit)], 1):
        print(f"{i}. {rec.get('source')} -> {rec.get('target')} | {rec.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Unified API test framework runner.

Modes:
- unit:        fast endpoint tests
- integration: broader API inventory tests
- performance: benchmark-oriented API tests
- all:         unit + integration (+performance if enabled)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]

UNIT_CORE_SUITES = [
    "tests/test_api_inventory_framework.py",
    "tests/test_api_autostart.py",
    "tests/test_api_error_handling.py",
]

LEGACY_UNIT_SUITES = [
    "tests/test_api_status.py",
    "tests/test_api_tasks.py",
    "tests/test_api_validation.py",
    "tests/test_api_knowledge.py",
]
INTEGRATION_SUITES = [
    "tests/test_api_inventory_framework.py",
]
PERFORMANCE_SUITES = [
    "tests/test_performance.py",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_pytest(paths: List[str], extra_args: List[str] | None = None) -> Dict[str, object]:
    cmd = [sys.executable, "-m", "pytest", "-q", *paths]
    if extra_args:
        cmd.extend(extra_args)

    started = utc_now_iso()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    ended = utc_now_iso()

    return {
        "command": cmd,
        "start": started,
        "end": ended,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-12000:],
        "stderr": proc.stderr[-12000:],
        "success": proc.returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run API test framework suites.")
    parser.add_argument(
        "--mode",
        default="unit",
        choices=["unit", "integration", "performance", "all"],
        help="Test scope to run.",
    )
    parser.add_argument(
        "--include-performance",
        action="store_true",
        help="When --mode=all, include performance benchmarks.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output JSON path. Defaults to reports/api_test_framework_<ts>.json",
    )
    parser.add_argument(
        "--strict-legacy",
        action="store_true",
        help="Include legacy unit suites with older endpoint assumptions.",
    )
    args = parser.parse_args()

    suites: Dict[str, Dict[str, object]] = {}
    overall_success = True

    if args.mode in ("unit", "all"):
        unit_paths = list(UNIT_CORE_SUITES)
        if args.strict_legacy:
            unit_paths.extend(LEGACY_UNIT_SUITES)
        suites["unit"] = run_pytest(unit_paths)
        overall_success = overall_success and bool(suites["unit"]["success"])

    if args.mode in ("integration", "all"):
        suites["integration"] = run_pytest(INTEGRATION_SUITES)
        overall_success = overall_success and bool(suites["integration"]["success"])

    if args.mode == "performance" or (args.mode == "all" and args.include_performance):
        # Performance tests may require pytest-benchmark plugin and are optional by default.
        suites["performance"] = run_pytest(PERFORMANCE_SUITES, extra_args=["-m", "benchmark"])
        overall_success = overall_success and bool(suites["performance"]["success"])

    payload = {
        "generated_at": utc_now_iso(),
        "mode": args.mode,
        "include_performance": bool(args.include_performance),
        "strict_legacy": bool(args.strict_legacy),
        "success": overall_success,
        "suites": suites,
    }

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    output_path = Path(args.output) if args.output else reports_dir / f"api_test_framework_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for name, result in suites.items():
        status = "PASS" if result["success"] else "FAIL"
        print(f"{name}: {status} (rc={result['returncode']})")

    print(f"report: {output_path}")
    return 0 if overall_success else 1


if __name__ == "__main__":
    raise SystemExit(main())

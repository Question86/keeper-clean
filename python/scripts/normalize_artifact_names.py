#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from artifact_naming_contract import normalize_legacy_artifacts
from output_safety import safe_print


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize legacy bootstrap/finalization artifact names to canonical contract."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply renames. Without this flag, runs in dry-run mode.",
    )
    args = parser.parse_args()

    workspace_root = Path.cwd()
    result = normalize_legacy_artifacts(workspace_root, apply_changes=args.apply)
    mode = "APPLY" if args.apply else "DRY-RUN"
    safe_print(f"[{mode}] planned moves: {len(result['actions'])}")
    for src, dst in result["actions"]:
        safe_print(f"  MOVE {src} -> {dst}")

    safe_print(f"[{mode}] skipped: {len(result['skipped'])}")
    for src, reason in result["skipped"]:
        safe_print(f"  SKIP {src} ({reason})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

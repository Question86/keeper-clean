#!/usr/bin/env python3
"""Synchronize canonical files into SEED_TEMPLATE.

This script copies the deterministic architecture and automation files from the
active project into the SEED_TEMPLATE directory so new projects inherit the
latest loop cockpit, guardrails, documentation, and search tooling.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
TEMPLATE_ROOT = ROOT / "SEED_TEMPLATE"

# Relative paths (from repo root) that should always match between the live
# project and the seed template. Keep this list focused on deterministic
# architecture + tooling files (no stateful artifacts like current.json).
SYNC_ITEMS = (
    "README.md",
    "PROJECT_TECH_BASELINE.md",
    "DEPLOYMENT_GUIDE.md",
    "requirements_cockpit.txt",
    "loop_cockpit.py",
    "loop_guardrails.py",
    "docs/ARCHITECTURE.md",
    "docs/OPS_PROTOCOLS.md",
    "docs/SEARCH_IMPROVEMENT_PLAN.md",
    "docs/PROJECT_EVOLUTION_ROADMAP.md",
    "docs/HISTORY_INDEX.md",
    "docs/QUERY_INDEX.json",
    "templates/cockpit.html",
    "START_COCKPIT.bat",
    "START_COCKPIT.sh",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy canonical loop architecture files into SEED_TEMPLATE so "
            "future projects start from the current prototype."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print copying actions without writing to disk",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="RELATIVE_PATH",
        help="Limit syncing to a subset of entries (paths relative to repo root)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the managed paths and exit",
    )
    return parser.parse_args()


def iter_items(only: Iterable[str] | None) -> Iterable[Path]:
    items = SYNC_ITEMS if not only else tuple(only)
    for entry in items:
        rel_path = Path(entry)
        source = ROOT / rel_path
        if not source.exists():
            raise FileNotFoundError(f"Source missing: {rel_path}")
        yield rel_path


def copy_into_template(rel_path: Path, *, dry_run: bool) -> None:
    source = ROOT / rel_path
    destination = TEMPLATE_ROOT / rel_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        print(f"[DRY-RUN] {rel_path} -> {destination.relative_to(ROOT)}")
        return
    shutil.copy2(source, destination)
    print(f"Copied {rel_path} -> {destination.relative_to(ROOT)}")


def main() -> int:
    args = parse_args()

    if not TEMPLATE_ROOT.exists():
        print("SEED_TEMPLATE directory not found. Nothing to sync.", file=sys.stderr)
        return 1

    if args.list:
        print("Managed seed template paths:\n")
        for rel in SYNC_ITEMS:
            print(f" - {rel}")
        return 0

    try:
        items = tuple(iter_items(args.only))
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        print(str(exc), file=sys.stderr)
        return 1

    for rel_path in items:
        copy_into_template(rel_path, dry_run=args.dry_run)

    if args.dry_run:
        print("Dry-run complete. No files were copied.")
    else:
        print("Seed template synced successfully.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

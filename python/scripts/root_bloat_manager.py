#!/usr/bin/env python3
"""
Root Bloat Manager

Policy-driven, batch-safe relocation planner for root-level file bloat.
Default mode is dry-run planning only.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class MoveCandidate:
    source: Path
    destination_dir: Path
    rule: str
    size_bytes: int
    mtime: float


class RootBloatManager:
    def __init__(self, workspace_root: Path, policy_path: Optional[Path] = None):
        self.workspace_root = workspace_root
        self.policy_path = policy_path or (workspace_root / "config" / "root_cleanup_policy.json")
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        if not self.policy_path.exists():
            raise FileNotFoundError(f"Root cleanup policy not found: {self.policy_path}")
        return json.loads(self.policy_path.read_text(encoding="utf-8"))

    def _is_protected(self, file_name: str) -> bool:
        protected_files = set(self.policy.get("protected_files", []))
        if file_name in protected_files:
            return True
        for glob_pattern in self.policy.get("protected_globs", []):
            if fnmatch.fnmatch(file_name, glob_pattern):
                return True
        return False

    def _resolve_destination(self, file_name: str) -> Optional[tuple[str, Path]]:
        for rule in self.policy.get("move_rules", []):
            pattern = rule.get("glob")
            if pattern and fnmatch.fnmatch(file_name, pattern):
                destination = self.workspace_root / rule["destination"]
                return rule.get("name", "unnamed_rule"), destination
        return None

    def scan_root_candidates(self) -> Dict[str, Any]:
        all_root_files = [p for p in self.workspace_root.iterdir() if p.is_file()]
        candidates: List[MoveCandidate] = []
        skipped_protected = 0
        unmatched = 0

        for file_path in all_root_files:
            name = file_path.name
            if self._is_protected(name):
                skipped_protected += 1
                continue

            resolved = self._resolve_destination(name)
            if not resolved:
                unmatched += 1
                continue

            rule_name, destination = resolved
            stat = file_path.stat()
            candidates.append(
                MoveCandidate(
                    source=file_path,
                    destination_dir=destination,
                    rule=rule_name,
                    size_bytes=stat.st_size,
                    mtime=stat.st_mtime,
                )
            )

        return {
            "generated_at": utc_now_iso(),
            "workspace_root": str(self.workspace_root),
            "total_root_files": len(all_root_files),
            "protected_skipped": skipped_protected,
            "unmatched_files": unmatched,
            "candidates": candidates,
        }

    def build_plan(
        self,
        max_files: int = 25,
        max_bytes: int = 50 * 1024 * 1024,
    ) -> Dict[str, Any]:
        scan = self.scan_root_candidates()
        candidates: List[MoveCandidate] = scan["candidates"]
        candidates.sort(key=lambda c: c.mtime)

        selected: List[MoveCandidate] = []
        bytes_selected = 0
        for candidate in candidates:
            if len(selected) >= max_files:
                break
            if bytes_selected + candidate.size_bytes > max_bytes:
                continue
            selected.append(candidate)
            bytes_selected += candidate.size_bytes

        return {
            "generated_at": utc_now_iso(),
            "workspace_root": str(self.workspace_root),
            "policy_path": str(self.policy_path),
            "limits": {
                "max_files": max_files,
                "max_bytes": max_bytes,
            },
            "scan_summary": {
                "total_root_files": scan["total_root_files"],
                "protected_skipped": scan["protected_skipped"],
                "unmatched_files": scan["unmatched_files"],
                "candidate_count": len(candidates),
                "selected_count": len(selected),
                "selected_bytes": bytes_selected,
            },
            "moves": [
                {
                    "source": str(c.source.relative_to(self.workspace_root)),
                    "destination_dir": str(c.destination_dir.relative_to(self.workspace_root)),
                    "rule": c.rule,
                    "size_bytes": c.size_bytes,
                    "mtime": c.mtime,
                }
                for c in selected
            ],
        }

    def apply_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        move_records = []
        moved = 0
        skipped = 0
        errors = 0
        journal = self.workspace_root / "logs" / "root_cleanup_moves.jsonl"
        journal.parent.mkdir(parents=True, exist_ok=True)

        for item in plan.get("moves", []):
            src = self.workspace_root / item["source"]
            dst_dir = self.workspace_root / item["destination_dir"]
            dst_dir.mkdir(parents=True, exist_ok=True)

            if not src.exists():
                skipped += 1
                record = {
                    "timestamp": utc_now_iso(),
                    "source": item["source"],
                    "destination_dir": item["destination_dir"],
                    "status": "skipped_missing",
                }
                move_records.append(record)
                journal.write_text("", encoding="utf-8") if not journal.exists() else None
                with journal.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record) + "\n")
                continue

            dst = dst_dir / src.name
            if dst.exists():
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                dst = dst_dir / f"{src.stem}_{stamp}{src.suffix}"

            try:
                shutil.move(str(src), str(dst))
                moved += 1
                record = {
                    "timestamp": utc_now_iso(),
                    "source": item["source"],
                    "destination": str(dst.relative_to(self.workspace_root)),
                    "status": "moved",
                }
            except Exception as error:
                errors += 1
                record = {
                    "timestamp": utc_now_iso(),
                    "source": item["source"],
                    "destination_dir": item["destination_dir"],
                    "status": "error",
                    "error": str(error),
                }

            move_records.append(record)
            with journal.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")

        return {
            "applied_at": utc_now_iso(),
            "moved": moved,
            "skipped": skipped,
            "errors": errors,
            "records": move_records,
            "journal": str(journal),
        }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan and apply safe root cleanup moves.")
    parser.add_argument("--workspace", default=".", help="Workspace root")
    parser.add_argument("--policy", default="config/root_cleanup_policy.json", help="Policy file path")
    parser.add_argument("--max-files", type=int, default=25, help="Maximum files per plan")
    parser.add_argument("--max-bytes", type=int, default=50 * 1024 * 1024, help="Maximum bytes per plan")
    parser.add_argument(
        "--plan-out",
        default=None,
        help="Optional plan output path (default: reports/root_cleanup_plan_<ts>.json)",
    )
    parser.add_argument("--apply", action="store_true", help="Apply selected moves from generated plan")
    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = workspace_root / policy_path

    manager = RootBloatManager(workspace_root=workspace_root, policy_path=policy_path)
    plan = manager.build_plan(max_files=max(1, args.max_files), max_bytes=max(1, args.max_bytes))

    if args.plan_out:
        plan_path = Path(args.plan_out)
        if not plan_path.is_absolute():
            plan_path = workspace_root / plan_path
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        plan_path = workspace_root / "reports" / f"root_cleanup_plan_{stamp}.json"

    _write_json(plan_path, plan)
    print(f"plan written: {plan_path}")
    print(
        f"selected: {plan['scan_summary']['selected_count']} file(s), "
        f"{plan['scan_summary']['selected_bytes']} bytes"
    )

    if not args.apply:
        return 0

    result = manager.apply_plan(plan)
    print(
        f"apply result: moved={result['moved']} skipped={result['skipped']} "
        f"errors={result['errors']}"
    )
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

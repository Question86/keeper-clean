#!/usr/bin/env python3
"""
General Knowledge Maintenance Script.

Reviews and updates outdated knowledge items across maintenance categories and
reports DB-vs-filesystem coverage drift.
"""

import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

class KnowledgeMaintenance:
    """
    Handles maintenance operations for knowledge base freshness.
    """

    def __init__(self, db_path: str = "keeper_knowledge.db", workspace_root: str = "."):
        self.db_path = db_path
        self.workspace_root = Path(workspace_root)
        self.logger = logging.getLogger(__name__)
        self.categories = [
            "operations",
            "documentation",
            "implementation",
            "planning",
            "ui_design",
            "architecture",
            "audit",
            "multiagent",
            "search",
            "reports",
            "tasks",
            "archives",
            "observation",
            "success",
            "warning",
            "failure",
        ]
        self.coverage_targets = {
            "reports": ("reports", self.workspace_root / "reports", "report_*.md"),
            "tasks": ("tasks", self.workspace_root / "tasks", "task_TASK_*.md"),
            "archives": ("archives", self.workspace_root / "archive", "ARCHIV_*.md"),
            "docs": ("docs", self.workspace_root / "docs", "*.md"),
            "bugs": ("bugs", self.workspace_root / "bugs", "BUG_*.md"),
            "code": ("code", self.workspace_root / "code", "CODE_*.md"),
        }

    def _parse_tags(self, raw_tags: str) -> List[str]:
        """Parse tags from JSON, CSV, or empty values."""
        if not raw_tags:
            return []
        try:
            parsed = json.loads(raw_tags)
            if isinstance(parsed, list):
                return [str(t) for t in parsed]
        except Exception:
            pass
        return [part.strip() for part in raw_tags.split(",") if part.strip()]

    def get_outdated_items(self, days_threshold: int = 90) -> List[Dict]:
        """
        Get items older than threshold days.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_threshold)).isoformat()

            cursor.execute("""
                SELECT id, title, path, category, tags, indexed_at
                FROM docs
                WHERE indexed_at < ?
                ORDER BY indexed_at ASC
            """, (cutoff_date,))

            items = []
            for row in cursor.fetchall():
                items.append({
                    'id': row[0],
                    'title': row[1] or row[2],
                    'path': row[2],
                    'category': row[3],
                    'tags': self._parse_tags(row[4]),
                    'indexed_at': row[5]
                })

            conn.close()
            return items

        except Exception as e:
            self.logger.error(f"Error getting outdated items: {e}")
            return []

    def update_item_freshness(self, item_id: int) -> bool:
        """
        Update an item's indexed_at to current time.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            current_time = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                UPDATE docs
                SET indexed_at = ?
                WHERE id = ?
            """, (current_time, item_id))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            self.logger.error(f"Error updating item {item_id}: {e}")
            return False

    def validate_item_exists(self, path: str) -> bool:
        """
        Check if the file still exists on disk.
        """
        return os.path.exists(path)

    def get_coverage_drift(self) -> Dict[str, Dict[str, float]]:
        """Compare DB table counts to filesystem artifact counts."""
        result: Dict[str, Dict[str, float]] = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for key, (table, folder, pattern) in self.coverage_targets.items():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    db_count = int(cursor.fetchone()[0])
                except Exception:
                    db_count = 0
                fs_count = sum(1 for p in folder.glob(pattern) if p.is_file()) if folder.exists() else 0
                missing = max(fs_count - db_count, 0)
                extra = max(db_count - fs_count, 0)
                drift_ratio = (missing / fs_count) if fs_count else 0.0
                result[key] = {
                    "db": db_count,
                    "fs": fs_count,
                    "missing": missing,
                    "extra": extra,
                    "drift_ratio": round(drift_ratio, 4),
                }
            conn.close()
        except Exception as e:
            self.logger.error(f"Error computing coverage drift: {e}")
        return result

    def perform_maintenance(self, dry_run: bool = True, days_threshold: int = 90) -> Dict:
        """
        Perform maintenance on outdated items.
        """
        outdated = self.get_outdated_items(days_threshold=days_threshold)
        coverage_drift = self.get_coverage_drift()
        results = {
            'total_outdated': len(outdated),
            'updated': 0,
            'skipped_missing': 0,
            'errors': 0,
            'categories_updated': {},
            'days_threshold': days_threshold,
            'dry_run': dry_run,
            'coverage_drift': coverage_drift,
        }

        for item in outdated:
            category = item['category']
            if category not in results['categories_updated']:
                results['categories_updated'][category] = 0

            # Check if file exists
            if not self.validate_item_exists(item['path']):
                results['skipped_missing'] += 1
                continue

            # Update freshness
            if not dry_run:
                if self.update_item_freshness(item['id']):
                    results['updated'] += 1
                    results['categories_updated'][category] += 1
                else:
                    results['errors'] += 1
            else:
                results['updated'] += 1
                results['categories_updated'][category] += 1

        return results

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Knowledge maintenance runner")
    parser.add_argument("--db", default="keeper_knowledge.db", help="Path to sqlite database")
    parser.add_argument("--workspace", default=".", help="Workspace root path")
    parser.add_argument("--days", type=int, default=90, help="Outdated threshold in days")
    parser.add_argument(
        "--mode",
        choices=["dry-run", "apply", "both"],
        default="both",
        help="Execution mode",
    )
    return parser

def main() -> None:
    """Main maintenance execution."""
    logging.basicConfig(level=logging.INFO)
    args = _build_arg_parser().parse_args()
    maintainer = KnowledgeMaintenance(db_path=args.db, workspace_root=args.workspace)

    print("Knowledge Maintenance Starting...")
    print(f"DB: {args.db}")
    print(f"Workspace: {Path(args.workspace).resolve()}")
    print(f"Outdated threshold: {args.days} days")

    if args.mode in ("dry-run", "both"):
        print("Performing dry run...")
        dry_results = maintainer.perform_maintenance(dry_run=True, days_threshold=args.days)
        print(f"Dry run results: {dry_results}")

    if args.mode in ("apply", "both"):
        print("Proceeding with actual maintenance...")
        results = maintainer.perform_maintenance(dry_run=False, days_threshold=args.days)
        print(f"Maintenance completed: {results}")

        print("\nSUMMARY:")
        print(f"- Total outdated items: {results['total_outdated']}")
        print(f"- Successfully updated: {results['updated']}")
        print(f"- Skipped (missing files): {results['skipped_missing']}")
        print(f"- Errors: {results['errors']}")
        print(f"- Categories updated: {results['categories_updated']}")
        print(f"- Coverage drift: {results['coverage_drift']}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Knowledge Health Monitor

Autonomous system for monitoring knowledge freshness and relevance.
Tracks knowledge lifecycle metrics and identifies items requiring attention.
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

class KnowledgeHealthMonitor:
    """
    Monitors the health and freshness of knowledge in the database.
    """

    def __init__(self, db_path: str = "keeper_knowledge.db", workspace_root: str = "."):
        self.db_path = db_path
        self.workspace_root = Path(workspace_root)
        self.logger = logging.getLogger(__name__)
        self.freshness_thresholds = {
            'critical': 90,  # days
            'warning': 60,   # days
            'info': 30       # days
        }
        self.coverage_targets = {
            "reports": ("reports", self.workspace_root / "reports", "report_*.md"),
            "tasks": ("tasks", self.workspace_root / "tasks", "task_TASK_*.md"),
            "archives": ("archives", self.workspace_root / "archive", "ARCHIV_*.md"),
            "docs": ("docs", self.workspace_root / "docs", "*.md"),
            "bugs": ("bugs", self.workspace_root / "bugs", "BUG_*.md"),
            "code": ("code", self.workspace_root / "code", "CODE_*.md"),
        }

    def get_db_counts(self) -> Dict[str, int]:
        """Get row counts for key DB tables."""
        counts: Dict[str, int] = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for key, (table, _, _) in self.coverage_targets.items():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[key] = int(cursor.fetchone()[0])
                except Exception:
                    counts[key] = 0
            conn.close()
        except Exception as e:
            self.logger.error(f"Error reading DB counts: {e}")
        return counts

    def get_fs_counts(self) -> Dict[str, int]:
        """Get filesystem counts for canonical artifact groups."""
        counts: Dict[str, int] = {}
        for key, (_, folder, pattern) in self.coverage_targets.items():
            try:
                if folder.exists():
                    counts[key] = sum(1 for p in folder.glob(pattern) if p.is_file())
                else:
                    counts[key] = 0
            except Exception:
                counts[key] = 0
        return counts

    def assess_db_drift(self) -> Dict[str, Dict[str, float]]:
        """Compare DB coverage vs filesystem coverage."""
        db_counts = self.get_db_counts()
        fs_counts = self.get_fs_counts()
        drift: Dict[str, Dict[str, float]] = {}
        for key in self.coverage_targets.keys():
            db_count = int(db_counts.get(key, 0))
            fs_count = int(fs_counts.get(key, 0))
            missing = max(fs_count - db_count, 0)
            extra = max(db_count - fs_count, 0)
            drift_ratio = (missing / fs_count) if fs_count > 0 else 0.0
            drift[key] = {
                "db": db_count,
                "fs": fs_count,
                "missing": missing,
                "extra": extra,
                "drift_ratio": round(drift_ratio, 4),
            }
        return drift

    def get_knowledge_items(self) -> List[Dict]:
        """
        Retrieve all knowledge items with their metadata.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, path, category, tags, indexed_at
                FROM docs
                ORDER BY indexed_at DESC
            """)

            items = []
            for row in cursor.fetchall():
                items.append({
                    'id': row[0],
                    'title': row[1] or row[2],  # title or path
                    'path': row[2],
                    'category': row[3],
                    'tags': row[4].split(',') if row[4] else [],
                    'updated_at': row[5]  # indexed_at as updated_at
                })

            conn.close()
            return items

        except Exception as e:
            self.logger.error(f"Error retrieving knowledge items: {e}")
            return []

    def calculate_freshness_score(self, updated_at: str) -> Tuple[str, int]:
        """
        Calculate freshness score based on last update time.

        Returns: (status, days_since_update)
        """
        try:
            update_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            days_since = (datetime.now(update_time.tzinfo) - update_time).days

            if days_since >= self.freshness_thresholds['critical']:
                return 'critical', days_since
            elif days_since >= self.freshness_thresholds['warning']:
                return 'warning', days_since
            elif days_since >= self.freshness_thresholds['info']:
                return 'info', days_since
            else:
                return 'fresh', days_since

        except Exception as e:
            self.logger.error(f"Error calculating freshness: {e}")
            return 'unknown', -1

    def assess_knowledge_health(self) -> Dict:
        """
        Perform comprehensive health assessment of knowledge base.
        """
        items = self.get_knowledge_items()
        assessment = {
            'total_items': len(items),
            'freshness_distribution': {
                'fresh': 0,
                'info': 0,
                'warning': 0,
                'critical': 0,
                'unknown': 0
            },
            'items_needing_attention': [],
            'categories': {},
            'tags': {},
            'health_score': 0.0
        }

        for item in items:
            status, days = self.calculate_freshness_score(item['updated_at'])
            assessment['freshness_distribution'][status] += 1

            if status in ['warning', 'critical']:
                assessment['items_needing_attention'].append({
                    'id': item['id'],
                    'title': item['title'],
                    'status': status,
                    'days_since_update': days,
                    'category': item['category']
                })

            # Category tracking
            cat = item['category'] or 'uncategorized'
            if cat not in assessment['categories']:
                assessment['categories'][cat] = {'count': 0, 'stale': 0}
            assessment['categories'][cat]['count'] += 1
            if status in ['warning', 'critical']:
                assessment['categories'][cat]['stale'] += 1

            # Tag tracking
            for tag in item['tags']:
                if tag not in assessment['tags']:
                    assessment['tags'][tag] = {'count': 0, 'stale': 0}
                assessment['tags'][tag]['count'] += 1
                if status in ['warning', 'critical']:
                    assessment['tags'][tag]['stale'] += 1

        # Calculate overall health score (0-100)
        total_items = assessment['total_items']
        if total_items > 0:
            fresh_count = assessment['freshness_distribution']['fresh']
            assessment['health_score'] = (fresh_count / total_items) * 100

        # Add DB coverage drift analysis
        assessment["db_drift"] = self.assess_db_drift()
        assessment["db_drift_summary"] = {
            "max_drift_ratio": max(
                (v["drift_ratio"] for v in assessment["db_drift"].values()),
                default=0.0
            ),
            "tables_with_drift": sum(1 for v in assessment["db_drift"].values() if v["missing"] > 0),
        }

        return assessment

    def generate_health_report(self) -> str:
        """
        Generate a human-readable health report.
        """
        assessment = self.assess_knowledge_health()

        report = f"""
# Knowledge Health Report
Generated: {datetime.now().isoformat()}

## Overview
- Total Knowledge Items: {assessment['total_items']}
- Overall Health Score: {assessment['health_score']:.1f}/100

## Freshness Distribution
- Fresh (< 30 days): {assessment['freshness_distribution']['fresh']}
- Info (30-60 days): {assessment['freshness_distribution']['info']}
- Warning (60-90 days): {assessment['freshness_distribution']['warning']}
- Critical (> 90 days): {assessment['freshness_distribution']['critical']}

## Items Needing Attention ({len(assessment['items_needing_attention'])})
"""

        for item in assessment['items_needing_attention'][:10]:  # Top 10
            report += f"- **{item['status'].upper()}**: {item['title']} ({item['days_since_update']} days old)\n"

        if len(assessment['items_needing_attention']) > 10:
            report += f"- ... and {len(assessment['items_needing_attention']) - 10} more\n"

        report += "\n## Category Health\n"
        for cat, stats in assessment['categories'].items():
            stale_ratio = (stats['stale'] / stats['count']) * 100 if stats['count'] > 0 else 0
            report += f"- {cat}: {stats['count']} items, {stale_ratio:.1f}% stale\n"

        report += "\n## DB Coverage Drift\n"
        for key, info in assessment.get("db_drift", {}).items():
            report += (
                f"- {key}: db={info['db']} fs={info['fs']} "
                f"missing={info['missing']} extra={info['extra']} "
                f"drift={info['drift_ratio'] * 100:.1f}%\n"
            )

        summary = assessment.get("db_drift_summary", {})
        report += (
            f"\nDrift Summary: max_drift={summary.get('max_drift_ratio', 0.0) * 100:.1f}% "
            f"tables_with_drift={summary.get('tables_with_drift', 0)}\n"
        )

        return report

    def get_update_recommendations(self) -> List[Dict]:
        """
        Generate recommendations for knowledge updates.
        """
        assessment = self.assess_knowledge_health()
        recommendations = []

        # Critical items first
        critical_items = [item for item in assessment['items_needing_attention']
                         if item['status'] == 'critical']
        if critical_items:
            recommendations.append({
                'priority': 'high',
                'type': 'update',
                'description': f"Update {len(critical_items)} critical knowledge items (>90 days old)",
                'items': critical_items
            })

        # Category-wide issues
        for cat, stats in assessment['categories'].items():
            if stats['count'] > 5:  # Only for categories with multiple items
                stale_ratio = (stats['stale'] / stats['count']) * 100
                if stale_ratio > 50:
                    recommendations.append({
                        'priority': 'medium',
                        'type': 'category_audit',
                        'description': f"Audit category '{cat}' ({stale_ratio:.1f}% stale)",
                        'category': cat
                    })

        return recommendations


if __name__ == "__main__":
    # Example usage
    monitor = KnowledgeHealthMonitor()
    report = monitor.generate_health_report()
    print(report)

    recommendations = monitor.get_update_recommendations()
    print("\n## Recommendations")
    for rec in recommendations:
        print(f"- {rec['priority'].upper()}: {rec['description']}")

#!/usr/bin/env python3
"""
Update Reminder Engine

Generates automated reminders for knowledge updates based on health monitoring.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from knowledge_health_monitor import KnowledgeHealthMonitor

class UpdateReminderEngine:
    """
    Engine for generating update reminders based on knowledge health.
    """

    def __init__(self, db_path: str = "keeper_knowledge.db"):
        self.db_path = db_path
        self.monitor = KnowledgeHealthMonitor(db_path)
        self.logger = logging.getLogger(__name__)

    def generate_reminders(self) -> List[Dict]:
        """
        Generate update reminders based on current knowledge health.
        """
        assessment = self.monitor.assess_knowledge_health()
        reminders = []

        # Critical items reminders
        critical_items = [item for item in assessment['items_needing_attention']
                         if item['status'] == 'critical']
        for item in critical_items:
            reminders.append({
                'type': 'update_required',
                'priority': 'high',
                'title': f"Critical: Update '{item['title']}'",
                'description': f"This knowledge item is {item['days_since_update']} days old and requires immediate attention.",
                'item_id': item['id'],
                'days_overdue': item['days_since_update'] - 90,
                'due_date': (datetime.now() + timedelta(days=7)).isoformat(),
                'category': item['category']
            })

        # Warning items reminders
        warning_items = [item for item in assessment['items_needing_attention']
                        if item['status'] == 'warning']
        for item in warning_items:
            reminders.append({
                'type': 'update_suggested',
                'priority': 'medium',
                'title': f"Review '{item['title']}'",
                'description': f"This knowledge item is {item['days_since_update']} days old. Consider updating if information has changed.",
                'item_id': item['id'],
                'days_overdue': item['days_since_update'] - 60,
                'due_date': (datetime.now() + timedelta(days=30)).isoformat(),
                'category': item['category']
            })

        # Category-wide reminders
        for cat, stats in assessment['categories'].items():
            if stats['count'] > 5:  # Only for categories with multiple items
                stale_ratio = (stats['stale'] / stats['count']) * 100
                if stale_ratio > 30:
                    reminders.append({
                        'type': 'category_review',
                        'priority': 'medium' if stale_ratio > 50 else 'low',
                        'title': f"Review Category: {cat}",
                        'description': f"Category '{cat}' has {stale_ratio:.1f}% stale items ({stats['stale']}/{stats['count']}). Consider a category-wide review.",
                        'category': cat,
                        'stale_ratio': stale_ratio,
                        'due_date': (datetime.now() + timedelta(days=14 if stale_ratio > 50 else 60)).isoformat()
                    })

        # Overall health reminders
        health_score = assessment['health_score']
        if health_score < 80:
            reminders.append({
                'type': 'health_check',
                'priority': 'high' if health_score < 50 else 'medium',
                'title': f"Knowledge Base Health: {health_score:.1f}/100",
                'description': f"Overall knowledge health is {health_score:.1f}%. Review and update stale items to maintain quality.",
                'health_score': health_score,
                'due_date': (datetime.now() + timedelta(days=7)).isoformat()
            })

        return sorted(reminders, key=lambda x: self._get_priority_weight(x['priority']), reverse=True)

    def _get_priority_weight(self, priority: str) -> int:
        """Get numerical weight for priority sorting."""
        weights = {'high': 3, 'medium': 2, 'low': 1}
        return weights.get(priority, 0)

    def schedule_reminders(self, reminders: List[Dict]) -> Dict:
        """
        Schedule reminders for future delivery.
        """
        # For now, just return the reminders with scheduling info
        # In a real implementation, this would integrate with a scheduling system
        scheduled = {
            'immediate': [r for r in reminders if r['priority'] == 'high'],
            'weekly': [r for r in reminders if r['priority'] == 'medium'],
            'monthly': [r for r in reminders if r['priority'] == 'low']
        }

        return scheduled

    def export_reminders(self, reminders: List[Dict], format: str = 'json') -> str:
        """
        Export reminders in specified format.
        """
        if format == 'json':
            return json.dumps(reminders, indent=2, default=str)
        elif format == 'markdown':
            return self._format_reminders_markdown(reminders)
        else:
            return str(reminders)

    def _format_reminders_markdown(self, reminders: List[Dict]) -> str:
        """Format reminders as markdown."""
        md = "# Knowledge Update Reminders\n"
        md += f"Generated: {datetime.now().isoformat()}\n\n"

        for reminder in reminders:
            md += f"## {reminder['title']}\n"
            md += f"**Priority:** {reminder['priority'].upper()}\n"
            md += f"**Type:** {reminder['type']}\n"
            md += f"**Due:** {reminder.get('due_date', 'ASAP')}\n"
            md += f"{reminder['description']}\n\n"

        return md

    def get_reminder_summary(self) -> Dict:
        """
        Get a summary of current reminders.
        """
        reminders = self.generate_reminders()
        scheduled = self.schedule_reminders(reminders)

        return {
            'total_reminders': len(reminders),
            'by_priority': {
                'high': len([r for r in reminders if r['priority'] == 'high']),
                'medium': len([r for r in reminders if r['priority'] == 'medium']),
                'low': len([r for r in reminders if r['priority'] == 'low'])
            },
            'by_type': {
                'update_required': len([r for r in reminders if r['type'] == 'update_required']),
                'update_suggested': len([r for r in reminders if r['type'] == 'update_suggested']),
                'category_review': len([r for r in reminders if r['type'] == 'category_review']),
                'health_check': len([r for r in reminders if r['type'] == 'health_check'])
            },
            'scheduled': scheduled
        }


if __name__ == "__main__":
    # Example usage
    engine = UpdateReminderEngine()
    reminders = engine.generate_reminders()

    print("Generated reminders:")
    for reminder in reminders[:5]:  # Show first 5
        print(f"- {reminder['priority'].upper()}: {reminder['title']}")

    summary = engine.get_reminder_summary()
    print(f"\nTotal reminders: {summary['total_reminders']}")

    # Export to markdown
    md_report = engine.export_reminders(reminders, 'markdown')
    print("\nMarkdown report preview:")
    print(md_report[:500] + "..." if len(md_report) > 500 else md_report)
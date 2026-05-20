#!/usr/bin/env python3
"""
Passive Notifier

Non-intrusive suggestion system for loop retrospective insights.
Part of the Loop Retrospective Automation Framework (TASK_0190).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from analysis.loop_insight_extractor import LoopInsightExtractor

class PassiveNotifier:
    """Provides passive, non-intrusive notifications for improvement suggestions."""

    def __init__(self, notification_file: str = "passive_notifications.jsonl"):
        self.notification_file = Path(notification_file)
        self.notification_file.parent.mkdir(exist_ok=True)

    def generate_notifications(self, loop_number: int) -> List[Dict[str, Any]]:
        """
        Generate passive notifications based on loop insights.

        Returns list of notification dictionaries with:
        - id: unique notification ID
        - type: notification type (suggestion, warning, info)
        - title: brief title
        - message: detailed message
        - actionable: whether user can take action
        - dismissible: whether user can dismiss
        - timestamp: when generated
        """
        extractor = LoopInsightExtractor()
        insights = extractor.extract_insights_for_loop(loop_number)

        notifications = []

        for insight in insights:
            notification = self._insight_to_notification(insight, loop_number)
            if notification:
                notifications.append(notification)

        # Limit to 3 notifications max to avoid overload
        return notifications[:3]

    def _insight_to_notification(self, insight: Dict[str, Any], loop_number: int) -> Optional[Dict[str, Any]]:
        """Convert an insight to a passive notification."""
        insight_type = insight.get('type', 'general')
        title = insight.get('title', 'Insight')
        description = insight.get('description', '')
        impact = insight.get('impact', '')
        confidence = insight.get('confidence', 0.5)

        # Only create notifications for high-confidence insights
        if confidence < 0.6:
            return None

        # Create notification based on insight type
        if insight_type == 'productivity':
            if 'Low Task Completion' in title:
                return {
                    'id': f"loop_{loop_number}_productivity_{int(datetime.now().timestamp())}",
                    'type': 'suggestion',
                    'title': 'Task Completion Opportunity',
                    'message': f"{description} {impact}",
                    'actionable': True,
                    'dismissible': True,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'category': 'productivity'
                }
            elif 'High Productivity' in title:
                return {
                    'id': f"loop_{loop_number}_success_{int(datetime.now().timestamp())}",
                    'type': 'info',
                    'title': 'Productivity Success',
                    'message': f"{description} {impact}",
                    'actionable': False,
                    'dismissible': True,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'category': 'success'
                }

        elif insight_type == 'behavioral':
            if 'Frequent Incidents' in title:
                return {
                    'id': f"loop_{loop_number}_incidents_{int(datetime.now().timestamp())}",
                    'type': 'warning',
                    'title': 'Incident Pattern Detected',
                    'message': f"{description} {impact}",
                    'actionable': True,
                    'dismissible': True,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'category': 'safety'
                }
            elif 'High Documentation' in title:
                return {
                    'id': f"loop_{loop_number}_docs_{int(datetime.now().timestamp())}",
                    'type': 'suggestion',
                    'title': 'Documentation Efficiency',
                    'message': f"{description} {impact}",
                    'actionable': True,
                    'dismissible': True,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'category': 'efficiency'
                }

        elif insight_type == 'complexity':
            return {
                'id': f"loop_{loop_number}_complexity_{int(datetime.now().timestamp())}",
                'type': 'suggestion',
                'title': 'Complexity Consideration',
                'message': f"{description} {impact}",
                'actionable': True,
                'dismissible': True,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'category': 'complexity'
            }

        return None

    def store_notifications(self, notifications: List[Dict[str, Any]]):
        """Store notifications to file for later retrieval."""
        with open(self.notification_file, 'a', encoding='utf-8') as f:
            for notification in notifications:
                f.write(json.dumps(notification) + '\n')

    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Retrieve notifications that haven't been dismissed."""
        if not self.notification_file.exists():
            return []

        notifications = []
        try:
            with open(self.notification_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            notification = json.loads(line)
                            # Only return non-dismissed notifications
                            if not notification.get('dismissed', False):
                                notifications.append(notification)
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return notifications

    def dismiss_notification(self, notification_id: str):
        """Mark a notification as dismissed."""
        if not self.notification_file.exists():
            return

        # Read all notifications
        notifications = []
        try:
            with open(self.notification_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            notification = json.loads(line)
                            if notification.get('id') == notification_id:
                                notification['dismissed'] = True
                                notification['dismissed_at'] = datetime.now(timezone.utc).isoformat()
                            notifications.append(notification)
                        except json.JSONDecodeError:
                            continue
        except Exception:
            return

        # Write back
        with open(self.notification_file, 'w', encoding='utf-8') as f:
            for notification in notifications:
                f.write(json.dumps(notification) + '\n')

def main():
    """Command line interface for passive notifications."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate passive notifications')
    parser.add_argument('loop_number', type=int, help='Loop number to analyze')
    parser.add_argument('--generate', action='store_true', help='Generate new notifications')
    parser.add_argument('--list', action='store_true', help='List pending notifications')
    parser.add_argument('--dismiss', type=str, help='Dismiss notification by ID')

    args = parser.parse_args()

    notifier = PassiveNotifier()

    if args.generate:
        notifications = notifier.generate_notifications(args.loop_number)
        notifier.store_notifications(notifications)
        print(f"Generated {len(notifications)} notifications for loop {args.loop_number}")

    elif args.list:
        pending = notifier.get_pending_notifications()
        print(f"Pending notifications: {len(pending)}")
        for notification in pending:
            print(f"- {notification['title']}: {notification['message']}")

    elif args.dismiss:
        notifier.dismiss_notification(args.dismiss)
        print(f"Dismissed notification {args.dismiss}")

if __name__ == "__main__":
    main()
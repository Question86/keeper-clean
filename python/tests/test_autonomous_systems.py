#!/usr/bin/env python3
"""
Tests for Autonomous Knowledge Systems

Comprehensive tests for knowledge health monitoring, reminders, audits, and dashboard.
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ui'))

from knowledge_health_monitor import KnowledgeHealthMonitor
from update_reminder_engine import UpdateReminderEngine
from autonomous_audit_system import AutonomousAuditSystem
from knowledge_dashboard import KnowledgeDashboard


class TestKnowledgeHealthMonitor(unittest.TestCase):
    """Test cases for KnowledgeHealthMonitor."""

    def setUp(self):
        self.monitor = KnowledgeHealthMonitor()

    def test_get_knowledge_items(self):
        """Test retrieving knowledge items."""
        items = self.monitor.get_knowledge_items()
        self.assertIsInstance(items, list)
        if items:
            item = items[0]
            self.assertIn('id', item)
            self.assertIn('title', item)
            self.assertIn('updated_at', item)

    def test_calculate_freshness_score(self):
        """Test freshness score calculation."""
        # Test with current timestamp (should be fresh)
        current_time = datetime.now().isoformat()
        status, days = self.monitor.calculate_freshness_score(current_time)
        self.assertEqual(status, 'fresh')
        self.assertLessEqual(days, 1)

    def test_assess_knowledge_health(self):
        """Test health assessment."""
        assessment = self.monitor.assess_knowledge_health()
        required_keys = ['total_items', 'freshness_distribution', 'items_needing_attention', 'health_score']
        for key in required_keys:
            self.assertIn(key, assessment)

    def test_generate_health_report(self):
        """Test health report generation."""
        report = self.monitor.generate_health_report()
        self.assertIsInstance(report, str)
        self.assertIn('Knowledge Health Report', report)
        self.assertIn('Overview', report)


class TestUpdateReminderEngine(unittest.TestCase):
    """Test cases for UpdateReminderEngine."""

    def setUp(self):
        self.engine = UpdateReminderEngine()

    def test_generate_reminders(self):
        """Test reminder generation."""
        reminders = self.engine.generate_reminders()
        self.assertIsInstance(reminders, list)
        for reminder in reminders:
            required_keys = ['type', 'priority', 'title', 'description']
            for key in required_keys:
                self.assertIn(key, reminder)

    def test_get_reminder_summary(self):
        """Test reminder summary."""
        summary = self.engine.get_reminder_summary()
        required_keys = ['total_reminders', 'by_priority', 'by_type', 'scheduled']
        for key in required_keys:
            self.assertIn(key, summary)

    def test_export_reminders(self):
        """Test reminder export."""
        reminders = self.engine.generate_reminders()

        # Test JSON export
        json_export = self.engine.export_reminders(reminders, 'json')
        self.assertIsInstance(json_export, str)

        # Test Markdown export
        md_export = self.engine.export_reminders(reminders, 'markdown')
        self.assertIsInstance(md_export, str)
        self.assertIn('# Knowledge Update Reminders', md_export)


class TestAutonomousAuditSystem(unittest.TestCase):
    """Test cases for AutonomousAuditSystem."""

    def setUp(self):
        self.auditor = AutonomousAuditSystem()

    def test_perform_full_audit(self):
        """Test full audit performance."""
        results = self.auditor.perform_full_audit()
        required_keys = ['total_items', 'audit_timestamp', 'quality_scores', 'gaps_identified', 'recommendations']
        for key in required_keys:
            self.assertIn(key, results)

    def test_audit_item_quality(self):
        """Test individual item quality audit."""
        # Get a sample item
        items = self.auditor.monitor.get_knowledge_items()
        if items:
            item = items[0]
            content = self.auditor._get_item_content(item['id'])
            if content:
                scores = self.auditor._audit_item_quality(item, content)
                required_checks = ['completeness', 'accuracy', 'consistency', 'relevance', 'structure', 'overall']
                for check in required_checks:
                    self.assertIn(check, scores)
                    self.assertIsInstance(scores[check], float)
                    self.assertGreaterEqual(scores[check], 0.0)
                    self.assertLessEqual(scores[check], 1.0)

    def test_quality_checks(self):
        """Test individual quality check functions."""
        test_item = {
            'id': 'test',
            'title': 'Test Item',
            'category': 'test',
            'tags': ['test']
        }
        test_content = """
        # Test Document

        This is a test document with some content.
        It includes references [ref:test|v:1] and dates 2024-01-01.

        ## Implementation

        Here is some code:
        ```python
        def test():
            return True
        ```

        ## References

        - Reference 1
        - Reference 2
        """

        # Test each check
        checks = [
            self.auditor._check_completeness,
            self.auditor._check_accuracy_indicators,
            self.auditor._check_consistency,
            self.auditor._check_relevance,
            self.auditor._check_structure
        ]

        for check_func in checks:
            score = check_func(test_item, test_content)
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_analyze_cross_references(self):
        """Test cross-reference analysis."""
        items = self.auditor.monitor.get_knowledge_items()
        references = self.auditor._analyze_cross_references(items)
        required_keys = ['references', 'referenced_by', 'orphaned_items', 'highly_referenced']
        for key in required_keys:
            self.assertIn(key, references)

    def test_export_audit_report(self):
        """Test audit report export."""
        results = self.auditor.perform_full_audit()

        # Test JSON export
        json_export = self.auditor.export_audit_report(results, 'json')
        self.assertIsInstance(json_export, str)

        # Test Markdown export
        md_export = self.auditor.export_audit_report(results, 'markdown')
        self.assertIsInstance(md_export, str)
        self.assertIn('# Knowledge Audit Report', md_export)


class TestKnowledgeDashboard(unittest.TestCase):
    """Test cases for KnowledgeDashboard."""

    def setUp(self):
        self.dashboard = KnowledgeDashboard()

    def test_generate_dashboard_html(self):
        """Test dashboard HTML generation."""
        html = self.dashboard.generate_dashboard_html()
        self.assertIsInstance(html, str)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('Knowledge Health Dashboard', html)

    def test_export_dashboard_data(self):
        """Test dashboard data export."""
        data = self.dashboard.export_dashboard_data()
        required_keys = ['health_report', 'reminders', 'audit_results', 'generated_at']
        for key in required_keys:
            self.assertIn(key, data)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""

    def setUp(self):
        self.monitor = KnowledgeHealthMonitor()
        self.reminder_engine = UpdateReminderEngine()
        self.auditor = AutonomousAuditSystem()
        self.dashboard = KnowledgeDashboard()

    def test_end_to_end_workflow(self):
        """Test complete workflow from monitoring to dashboard."""
        # 1. Monitor health
        health = self.monitor.assess_knowledge_health()
        self.assertIn('health_score', health)

        # 2. Generate reminders
        reminders = self.reminder_engine.generate_reminders()
        self.assertIsInstance(reminders, list)

        # 3. Perform audit
        audit = self.auditor.perform_full_audit()
        self.assertIn('quality_scores', audit)

        # 4. Generate dashboard
        html = self.dashboard.generate_dashboard_html()
        self.assertIn('Knowledge Health Dashboard', html)

    def test_data_consistency(self):
        """Test that all components work with the same data."""
        # Get item count from different components
        monitor_count = len(self.monitor.get_knowledge_items())
        audit_count = self.auditor.perform_full_audit()['total_items']
        dashboard_data = self.dashboard.export_dashboard_data()

        # All should report the same total
        self.assertEqual(monitor_count, audit_count)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
#!/usr/bin/env python3
"""
Test Retrospective System

Validation and performance testing for the Loop Retrospective Automation Framework.
Part of TASK_0190 implementation.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the modules to test
from analysis.loop_insight_extractor import LoopInsightExtractor
from ui.passive_notifier import PassiveNotifier
from analysis.trend_analyzer import TrendAnalyzer
from ui.deep_analysis_interface import DeepAnalysisInterface
from monitoring.complexity_tracker import ComplexityTracker

class TestRetrospectiveSystem(unittest.TestCase):
    """Test suite for the retrospective automation framework."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create mock archive directory
        self.archive_dir = self.temp_dir / "archive"
        self.archive_dir.mkdir()

        # Create mock archive file
        self.archive_file = self.archive_dir / "ARCHIV_0095.md"
        self.archive_content = """
# ARCHIV_0095

## Completed Tasks
[ref:tasks/task_TASK_0189.md|v:1|tags:completed,behavioral-analysis,breadcrumb-mapping,performance-optimization,arousal-functionality|src:loop95]
[ref:reports/report_TASK_0189_L95_v01.md|v:1|tags:report|src:system]

[ref:tasks/task_TASK_0194.md|v:1|tags:completed,confidence-matrix,life-coordinates,ai-monitoring,trustworthiness|src:loop95]
[ref:reports/report_TASK_0194_L95_v01.md|v:1|tags:report|src:system]

## INCIDENT
INCIDENT: Test incident for validation

## Summary
This is a test archive with some completed tasks and an incident.
"""
        self.archive_file.write_text(self.archive_content)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_loop_insight_extractor(self):
        """Test insight extraction from archive."""
        extractor = LoopInsightExtractor(str(self.archive_dir))

        insights = extractor.extract_insights_for_loop(95)

        self.assertIsInstance(insights, list)
        self.assertGreater(len(insights), 0)

        # Check insight structure
        for insight in insights:
            self.assertIn('type', insight)
            self.assertIn('title', insight)
            self.assertIn('description', insight)
            self.assertIn('impact', insight)
            self.assertIn('confidence', insight)

    def test_passive_notifier(self):
        """Test passive notification system."""
        notifier = PassiveNotifier(str(self.temp_dir / "notifications.jsonl"))

        notifications = notifier.generate_notifications(95)

        self.assertIsInstance(notifications, list)
        self.assertLessEqual(len(notifications), 3)  # Limited to 3

        # Store and retrieve
        notifier.store_notifications(notifications)
        pending = notifier.get_pending_notifications()

        self.assertEqual(len(pending), len(notifications))

    def test_trend_analyzer(self):
        """Test trend analysis."""
        analyzer = TrendAnalyzer(str(self.archive_dir))

        trends = analyzer.analyze_trends(loops_to_analyze=1)

        self.assertIsInstance(trends, dict)
        self.assertIn('productivity_trends', trends)
        self.assertIn('complexity_trends', trends)
        self.assertIn('behavioral_trends', trends)

    def test_deep_analysis_interface(self):
        """Test deep analysis interface."""
        interface = DeepAnalysisInterface(str(self.archive_dir))

        results = interface.perform_deep_analysis(95, 'productivity')

        self.assertIsInstance(results, dict)
        self.assertIn('loop_number', results)
        self.assertIn('sections', results)
        self.assertIn('productivity_analysis', results['sections'])

    def test_complexity_tracker(self):
        """Test complexity tracking."""
        tracker = ComplexityTracker(str(self.temp_dir / "complexity.jsonl"))

        # Test burden assessment
        metrics = {
            'added_files': 2,
            'added_lines': 150,
            'new_dependencies': 1,
            'api_endpoints': 1
        }

        assessment = tracker.assess_burden_impact('test_feature', metrics)

        self.assertIsInstance(assessment, dict)
        self.assertIn('burden_level', assessment)
        self.assertIn('impact_score', assessment)

    def test_integration_workflow(self):
        """Test the complete retrospective workflow."""
        # This test simulates the full workflow

        # 1. Extract insights
        extractor = LoopInsightExtractor(str(self.archive_dir))
        insights = extractor.extract_insights_for_loop(95)

        # 2. Generate notifications
        notifier = PassiveNotifier(str(self.temp_dir / "notifications.jsonl"))
        notifications = notifier.generate_notifications(95)
        notifier.store_notifications(notifications)

        # 3. Perform deep analysis
        interface = DeepAnalysisInterface(str(self.archive_dir))
        deep_results = interface.perform_deep_analysis(95, 'comprehensive')

        # 4. Track complexity
        tracker = ComplexityTracker(str(self.temp_dir / "complexity.jsonl"))
        burden = tracker.assess_burden_impact('retrospective_system', {
            'added_files': 5,
            'added_lines': 1000,
            'new_dependencies': 0,
            'api_endpoints': 0
        })

        # Assertions
        self.assertGreater(len(insights), 0)
        self.assertIsInstance(notifications, list)
        self.assertIn('sections', deep_results)
        self.assertIn('burden_level', burden)

    def test_performance_constraints(self):
        """Test that the system meets performance constraints."""
        import time

        extractor = LoopInsightExtractor(str(self.archive_dir))

        # Test insight extraction performance
        start_time = time.time()
        insights = extractor.extract_insights_for_loop(95)
        extraction_time = time.time() - start_time

        # Should complete in reasonable time (< 1 second for this test data)
        self.assertLess(extraction_time, 1.0, "Insight extraction too slow")

        # Test notification generation performance
        notifier = PassiveNotifier(str(self.temp_dir / "notifications.jsonl"))

        start_time = time.time()
        notifications = notifier.generate_notifications(95)
        notification_time = time.time() - start_time

        self.assertLess(notification_time, 0.5, "Notification generation too slow")

    def test_error_handling(self):
        """Test error handling in edge cases."""
        # Test with non-existent loop
        extractor = LoopInsightExtractor(str(self.archive_dir))
        insights = extractor.extract_insights_for_loop(999)

        self.assertEqual(insights, [])

        # Test trend analysis with insufficient data
        analyzer = TrendAnalyzer(str(self.archive_dir))
        trends = analyzer.analyze_trends(loops_to_analyze=100)

        # Should handle gracefully
        self.assertIsInstance(trends, dict)

def run_performance_benchmark():
    """Run performance benchmarks for the retrospective system."""
    print("Running Retrospective System Performance Benchmarks")
    print("=" * 60)

    temp_dir = Path(tempfile.mkdtemp())
    archive_dir = temp_dir / "archive"
    archive_dir.mkdir()

    # Create larger test archive
    archive_content = "# ARCHIV_0095\n\n" + "\n".join([
        f"[ref:tasks/task_TASK_{i:04d}.md|v:1|tags:completed,test|src:loop95]"
        for i in range(100)
    ])

    (archive_dir / "ARCHIV_0095.md").write_text(archive_content)

    # Benchmark insight extraction
    extractor = LoopInsightExtractor(str(archive_dir))

    import time
    start_time = time.time()
    insights = extractor.extract_insights_for_loop(95)
    extraction_time = time.time() - start_time

    print(".3f")
    print(f"Insights extracted: {len(insights)}")

    # Benchmark notification generation
    notifier = PassiveNotifier(str(temp_dir / "notifications.jsonl"))

    start_time = time.time()
    notifications = notifier.generate_notifications(95)
    notification_time = time.time() - start_time

    print(".3f")
    print(f"Notifications generated: {len(notifications)}")

    # Clean up
    import shutil
    shutil.rmtree(temp_dir)

    print("Benchmarks completed successfully")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--benchmark":
        run_performance_benchmark()
    else:
        unittest.main()
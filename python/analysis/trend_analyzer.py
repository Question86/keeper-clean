#!/usr/bin/env python3
"""
Trend Analyzer

Historical pattern visualization for loop retrospectives.
Part of the Loop Retrospective Automation Framework (TASK_0190).
"""

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from analysis.loop_insight_extractor import LoopInsightExtractor

class TrendAnalyzer:
    """Analyzes historical trends across multiple loops."""

    def __init__(self, archive_dir: str = "archive"):
        self.archive_dir = Path(archive_dir)
        self.extractor = LoopInsightExtractor(archive_dir)

    def analyze_trends(self, loops_to_analyze: int = 10) -> Dict[str, Any]:
        """
        Analyze trends across recent loops.

        Returns trend analysis with:
        - productivity_trends: task completion rates over time
        - complexity_trends: archive size and detail levels
        - behavioral_trends: incident and activity patterns
        - insights: key trend observations
        """
        # Get available archive files
        archive_files = list(self.archive_dir.glob("ARCHIV_*.md"))
        archive_files.sort(reverse=True)  # Most recent first

        # Extract loop numbers
        loop_data = []
        for archive_file in archive_files[:loops_to_analyze]:
            try:
                # Extract loop number from filename (ARCHIV_0094.md -> 94)
                loop_num = int(archive_file.stem.split('_')[1])
                data = self.extractor._load_archive_data(loop_num)
                if data:
                    loop_data.append((loop_num, data))
            except (ValueError, IndexError):
                continue

        # Sort by loop number
        loop_data.sort(key=lambda x: x[0])

        if not loop_data:
            return {"error": "No archive data available for trend analysis"}

        # Analyze different trend categories
        trends = {
            'productivity_trends': self._analyze_productivity_trends(loop_data),
            'complexity_trends': self._analyze_complexity_trends(loop_data),
            'behavioral_trends': self._analyze_behavioral_trends(loop_data),
            'insights': self._generate_trend_insights(loop_data),
            'analyzed_loops': len(loop_data),
            'date_range': self._get_date_range(loop_data)
        }

        return trends

    def _analyze_productivity_trends(self, loop_data: List[Tuple[int, Dict]]) -> Dict[str, Any]:
        """Analyze productivity trends over time."""
        productivity_metrics = []

        for loop_num, data in loop_data:
            content = data.get('content', '')

            # Task completion metrics
            task_count = content.count('[ref:tasks/task_')
            completed_count = content.count('tags:completed')

            completion_rate = completed_count / task_count if task_count > 0 else 0

            # Transaction volume (if available)
            transactions = self.extractor._load_transaction_data(loop_num)
            transaction_count = len(transactions)

            productivity_metrics.append({
                'loop': loop_num,
                'completion_rate': completion_rate,
                'task_count': task_count,
                'transaction_count': transaction_count
            })

        # Calculate trends
        completion_rates = [m['completion_rate'] for m in productivity_metrics]

        return {
            'completion_rates': productivity_metrics,
            'average_completion_rate': statistics.mean(completion_rates) if completion_rates else 0,
            'completion_trend': self._calculate_trend(completion_rates),
            'highest_completion_loop': max(productivity_metrics, key=lambda x: x['completion_rate'])['loop'] if productivity_metrics else None,
            'lowest_completion_loop': min(productivity_metrics, key=lambda x: x['completion_rate'])['loop'] if productivity_metrics else None
        }

    def _analyze_complexity_trends(self, loop_data: List[Tuple[int, Dict]]) -> Dict[str, Any]:
        """Analyze complexity trends over time."""
        complexity_metrics = []

        for loop_num, data in loop_data:
            complexity_metrics.append({
                'loop': loop_num,
                'word_count': data.get('word_count', 0),
                'line_count': data.get('line_count', 0),
                'has_reports': data.get('has_reports', False),
                'has_tasks': data.get('has_tasks', False),
                'has_incidents': data.get('has_incidents', False)
            })

        # Calculate trends
        word_counts = [m['word_count'] for m in complexity_metrics]
        line_counts = [m['line_count'] for m in complexity_metrics]

        return {
            'complexity_metrics': complexity_metrics,
            'average_word_count': statistics.mean(word_counts) if word_counts else 0,
            'word_count_trend': self._calculate_trend(word_counts),
            'average_line_count': statistics.mean(line_counts) if line_counts else 0,
            'line_count_trend': self._calculate_trend(line_counts),
            'most_complex_loop': max(complexity_metrics, key=lambda x: x['word_count'])['loop'] if complexity_metrics else None
        }

    def _analyze_behavioral_trends(self, loop_data: List[Tuple[int, Dict]]) -> Dict[str, Any]:
        """Analyze behavioral trends over time."""
        behavioral_metrics = []

        for loop_num, data in loop_data:
            content = data.get('content', '')

            # Incident and activity metrics
            incident_count = content.count('INCIDENT')
            report_count = content.count('[ref:reports/report_')

            behavioral_metrics.append({
                'loop': loop_num,
                'incident_count': incident_count,
                'report_count': report_count,
                'has_incidents': incident_count > 0
            })

        # Calculate trends
        incident_counts = [m['incident_count'] for m in behavioral_metrics]

        return {
            'behavioral_metrics': behavioral_metrics,
            'average_incidents': statistics.mean(incident_counts) if incident_counts else 0,
            'incident_trend': self._calculate_trend(incident_counts),
            'loops_with_incidents': sum(1 for m in behavioral_metrics if m['has_incidents']),
            'most_incident_loop': max(behavioral_metrics, key=lambda x: x['incident_count'])['loop'] if behavioral_metrics else None
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values."""
        if len(values) < 2:
            return 'insufficient_data'

        # Simple linear trend
        if len(values) >= 2:
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]

            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)

            if second_avg > first_avg * 1.1:
                return 'increasing'
            elif second_avg < first_avg * 0.9:
                return 'decreasing'
            else:
                return 'stable'

        return 'unknown'

    def _generate_trend_insights(self, loop_data: List[Tuple[int, Dict]]) -> List[Dict[str, Any]]:
        """Generate key insights from trend analysis."""
        insights = []

        # Compute trends directly to avoid recursion
        prod_trends = self._analyze_productivity_trends(loop_data)
        comp_trends = self._analyze_complexity_trends(loop_data)
        beh_trends = self._analyze_behavioral_trends(loop_data)

        # Productivity insights
        if prod_trends.get('completion_trend') == 'decreasing':
            insights.append({
                'type': 'productivity',
                'title': 'Declining Completion Rates',
                'description': 'Task completion rates have been decreasing over recent loops.',
                'recommendation': 'Review task sizing and workload distribution.'
            })

        # Complexity insights
        if comp_trends.get('word_count_trend') == 'increasing':
            insights.append({
                'type': 'complexity',
                'title': 'Growing Complexity',
                'description': 'Archive sizes are increasing, indicating growing complexity.',
                'recommendation': 'Consider breaking work into smaller loops or consolidating documentation.'
            })

        # Behavioral insights
        if beh_trends.get('incident_trend') == 'increasing':
            insights.append({
                'type': 'behavioral',
                'title': 'Rising Incident Rate',
                'description': 'Incidents are increasing across loops.',
                'recommendation': 'Investigate root causes and implement preventive measures.'
            })

        return insights

    def _get_date_range(self, loop_data: List[Tuple[int, Dict]]) -> Dict[str, str]:
        """Get date range for the analyzed loops."""
        if not loop_data:
            return {'start': None, 'end': None}

        # This is a simplification - in reality would need to extract dates from archives
        return {
            'start': f"Loop {loop_data[0][0]}",
            'end': f"Loop {loop_data[-1][0]}",
            'count': len(loop_data)
        }

def main():
    """Command line interface for trend analysis."""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze loop trends')
    parser.add_argument('--loops', type=int, default=10, help='Number of recent loops to analyze')
    parser.add_argument('--archive-dir', default='archive', help='Archive directory')

    args = parser.parse_args()

    analyzer = TrendAnalyzer(args.archive_dir)
    trends = analyzer.analyze_trends(args.loops)

    print("Loop Trend Analysis")
    print("=" * 50)

    if 'error' in trends:
        print(f"Error: {trends['error']}")
        return

    print(f"Analyzed {trends['analyzed_loops']} loops")
    print(f"Date range: {trends['date_range']['start']} to {trends['date_range']['end']}")
    print()

    # Productivity trends
    prod = trends.get('productivity_trends', {})
    print("Productivity Trends:")
    print(f"  Average completion rate: {prod.get('average_completion_rate', 0):.1%}")
    print(f"  Trend: {prod.get('completion_trend', 'unknown')}")
    print()

    # Complexity trends
    comp = trends.get('complexity_trends', {})
    print("Complexity Trends:")
    print(f"  Average word count: {comp.get('average_word_count', 0):,.0f}")
    print(f"  Word count trend: {comp.get('word_count_trend', 'unknown')}")
    print()

    # Behavioral trends
    beh = trends.get('behavioral_trends', {})
    print("Behavioral Trends:")
    print(f"  Average incidents: {beh.get('average_incidents', 0):.1f}")
    print(f"  Incident trend: {beh.get('incident_trend', 'unknown')}")
    print(f"  Loops with incidents: {beh.get('loops_with_incidents', 0)}")
    print()

    # Key insights
    insights = trends.get('insights', [])
    if insights:
        print("Key Insights:")
        for insight in insights:
            print(f"  {insight['title']}: {insight['description']}")
            print(f"    Recommendation: {insight['recommendation']}")
            print()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Complexity Tracker

Automated assessment of finalization burden and feature impact.
Part of the Loop Retrospective Automation Framework (TASK_0190).
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict

class ComplexityTracker:
    """Tracks and monitors finalization complexity and burden."""

    def __init__(self, metrics_file: str = "monitoring/complexity_metrics.jsonl"):
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(exist_ok=True)

    def track_finalization_start(self, loop_number: int) -> str:
        """
        Start tracking a finalization process.

        Returns a tracking ID for this finalization session.
        """
        tracking_id = f"finalization_{loop_number}_{int(time.time())}"

        metric = {
            'tracking_id': tracking_id,
            'loop_number': loop_number,
            'event': 'finalization_start',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics': {
                'start_time': time.time(),
                'initial_complexity': self._assess_current_complexity()
            }
        }

        self._append_metric(metric)
        return tracking_id

    def track_finalization_end(self, tracking_id: str, success: bool = True) -> Dict[str, Any]:
        """
        End tracking of a finalization process.

        Returns finalization metrics.
        """
        end_time = time.time()

        # Find the start metric
        start_metric = None
        for metric in self._read_all_metrics():
            if (metric.get('tracking_id') == tracking_id and
                metric.get('event') == 'finalization_start'):
                start_metric = metric
                break

        if not start_metric:
            return {'error': 'Start metric not found'}

        start_time = start_metric['metrics']['start_time']
        duration = end_time - start_time

        final_metric = {
            'tracking_id': tracking_id,
            'loop_number': start_metric['loop_number'],
            'event': 'finalization_end',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': success,
            'metrics': {
                'duration_seconds': duration,
                'final_complexity': self._assess_current_complexity(),
                'complexity_delta': self._assess_current_complexity() - start_metric['metrics']['initial_complexity']
            }
        }

        self._append_metric(final_metric)

        return {
            'tracking_id': tracking_id,
            'duration': duration,
            'success': success,
            'complexity_increase': final_metric['metrics']['complexity_delta']
        }

    def assess_burden_impact(self, feature_name: str, feature_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the burden impact of a new feature or change.

        feature_metrics should include:
        - added_files: number of new files
        - added_lines: lines of code/docs added
        - new_dependencies: new external dependencies
        - api_endpoints: new API endpoints added
        """
        current_complexity = self._assess_current_complexity()

        # Calculate impact score
        impact_score = 0
        impact_factors = []

        added_files = feature_metrics.get('added_files', 0)
        if added_files > 0:
            impact_score += added_files * 2
            impact_factors.append(f"{added_files} new files")

        added_lines = feature_metrics.get('added_lines', 0)
        if added_lines > 1000:
            impact_score += 3
            impact_factors.append(f"{added_lines} lines added")
        elif added_lines > 100:
            impact_score += 1
            impact_factors.append(f"{added_lines} lines added")

        new_deps = feature_metrics.get('new_dependencies', 0)
        if new_deps > 0:
            impact_score += new_deps * 3
            impact_factors.append(f"{new_deps} new dependencies")

        api_endpoints = feature_metrics.get('api_endpoints', 0)
        if api_endpoints > 0:
            impact_score += api_endpoints * 2
            impact_factors.append(f"{api_endpoints} new API endpoints")

        # Determine burden level
        if impact_score >= 10:
            burden_level = 'high'
            recommendation = 'Consider breaking into smaller features or phases'
        elif impact_score >= 5:
            burden_level = 'medium'
            recommendation = 'Monitor impact during next finalization'
        else:
            burden_level = 'low'
            recommendation = 'Minimal impact expected'

        assessment = {
            'feature_name': feature_name,
            'impact_score': impact_score,
            'burden_level': burden_level,
            'impact_factors': impact_factors,
            'recommendation': recommendation,
            'current_complexity': current_complexity,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Store assessment
        metric = {
            'event': 'burden_assessment',
            'feature_name': feature_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'assessment': assessment
        }
        self._append_metric(metric)

        return assessment

    def get_complexity_trends(self, loops: int = 10) -> Dict[str, Any]:
        """Get complexity trends over recent loops."""
        metrics = self._read_all_metrics()

        # Group by loop
        loop_complexity = defaultdict(list)

        for metric in metrics:
            if metric.get('event') == 'finalization_end':
                loop_num = metric.get('loop_number')
                complexity = metric.get('metrics', {}).get('final_complexity', 0)
                if loop_num and complexity:
                    loop_complexity[loop_num].append(complexity)

        # Get average complexity per loop
        complexity_by_loop = {}
        for loop_num, complexities in loop_complexity.items():
            complexity_by_loop[loop_num] = sum(complexities) / len(complexities)

        # Sort by loop number
        sorted_loops = sorted(complexity_by_loop.items(), key=lambda x: x[0], reverse=True)
        recent_loops = sorted_loops[:loops]

        if len(recent_loops) < 2:
            return {'error': 'Insufficient data for trend analysis'}

        # Calculate trend
        values = [complexity for _, complexity in recent_loops]
        trend = self._calculate_trend(values)

        return {
            'recent_complexity': dict(recent_loops),
            'trend': trend,
            'average_complexity': sum(values) / len(values),
            'complexity_range': max(values) - min(values)
        }

    def get_finalization_efficiency(self, loops: int = 10) -> Dict[str, Any]:
        """Get finalization efficiency metrics."""
        metrics = self._read_all_metrics()

        finalizations = [m for m in metrics if m.get('event') == 'finalization_end']

        if not finalizations:
            return {'error': 'No finalization data available'}

        # Sort by timestamp, get recent ones
        finalizations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        recent_finalizations = finalizations[:loops]

        durations = []
        success_count = 0

        for f in recent_finalizations:
            duration = f.get('metrics', {}).get('duration_seconds', 0)
            if duration > 0:
                durations.append(duration)

            if f.get('success', False):
                success_count += 1

        if not durations:
            return {'error': 'No duration data available'}

        return {
            'average_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'success_rate': success_count / len(recent_finalizations),
            'total_finalizations': len(recent_finalizations)
        }

    def _assess_current_complexity(self) -> float:
        """Assess current system complexity."""
        complexity = 0

        # Count Python files
        py_files = list(Path('.').rglob('*.py'))
        complexity += len(py_files) * 0.1

        # Count lines of code (rough estimate)
        total_lines = 0
        for py_file in py_files[:50]:  # Limit to avoid slow scans
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    total_lines += len(f.readlines())
            except:
                pass

        complexity += total_lines * 0.001

        # Count documentation files
        doc_files = list(Path('.').rglob('*.md'))
        complexity += len(doc_files) * 0.05

        # Count API endpoints (rough estimate from loop_cockpit.py)
        try:
            with open('loop_cockpit.py', 'r', encoding='utf-8') as f:
                content = f.read()
                api_count = content.count('@app.route')
                complexity += api_count * 0.2
        except:
            pass

        return complexity

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction."""
        if len(values) < 2:
            return 'insufficient_data'

        # Simple linear trend
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        if second_avg > first_avg * 1.1:
            return 'increasing'
        elif second_avg < first_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'

    def _read_all_metrics(self) -> List[Dict[str, Any]]:
        """Read all stored metrics."""
        metrics = []

        if not self.metrics_file.exists():
            return metrics

        try:
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            metrics.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return metrics

    def _append_metric(self, metric: Dict[str, Any]):
        """Append a metric to the file."""
        with open(self.metrics_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(metric) + '\n')

def main():
    """Command line interface for complexity tracking."""
    import argparse

    parser = argparse.ArgumentParser(description='Track finalization complexity')
    parser.add_argument('--assess-burden', nargs='*', help='Assess burden of features (format: name files=N lines=N deps=N apis=N)')
    parser.add_argument('--start-finalization', type=int, help='Start tracking finalization for loop number')
    parser.add_argument('--end-finalization', type=str, help='End tracking finalization (tracking_id)')
    parser.add_argument('--trends', action='store_true', help='Show complexity trends')
    parser.add_argument('--efficiency', action='store_true', help='Show finalization efficiency')

    args = parser.parse_args()

    tracker = ComplexityTracker()

    if args.assess_burden:
        # Parse burden assessment
        if len(args.assess_burden) >= 5:
            feature_name = args.assess_burden[0]
            metrics = {}
            for item in args.assess_burden[1:]:
                if '=' in item:
                    key, value = item.split('=', 1)
                    try:
                        metrics[key] = int(value)
                    except ValueError:
                        metrics[key] = value

            assessment = tracker.assess_burden_impact(feature_name, metrics)
            print(f"Burden Assessment for {feature_name}:")
            print(f"  Impact Score: {assessment['impact_score']}")
            print(f"  Burden Level: {assessment['burden_level']}")
            print(f"  Recommendation: {assessment['recommendation']}")

    elif args.start_finalization:
        tracking_id = tracker.track_finalization_start(args.start_finalization)
        print(f"Started tracking finalization for loop {args.start_finalization}")
        print(f"Tracking ID: {tracking_id}")

    elif args.end_finalization:
        result = tracker.track_finalization_end(args.end_finalization)
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Finalization completed in {result['duration']:.1f} seconds")
            print(f"Complexity increase: {result['complexity_increase']:.2f}")

    elif args.trends:
        trends = tracker.get_complexity_trends()
        if 'error' in trends:
            print(f"Error: {trends['error']}")
        else:
            print("Complexity Trends:")
            print(f"  Average: {trends['average_complexity']:.2f}")
            print(f"  Trend: {trends['trend']}")
            print(f"  Range: {trends['complexity_range']:.2f}")

    elif args.efficiency:
        efficiency = tracker.get_finalization_efficiency()
        if 'error' in efficiency:
            print(f"Error: {efficiency['error']}")
        else:
            print("Finalization Efficiency:")
            print(f"  Average duration: {efficiency['average_duration']:.1f}s")
            print(f"  Success rate: {efficiency['success_rate']:.1%}")
            print(f"  Total finalizations: {efficiency['total_finalizations']}")

if __name__ == "__main__":
    main()
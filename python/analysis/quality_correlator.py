#!/usr/bin/env python3
"""
Quality Correlator

Correlates AI behavioral patterns with task outcome quality scores.
Links activity metrics to performance results for predictive analytics.

TASK_0189: AI Behavioral Telemetry and Performance Correlation System
"""

import json
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict
import math

@dataclass
class QualityCorrelation:
    """Correlation between behavioral patterns and quality outcomes."""
    activity_metric: str
    quality_metric: str
    correlation_coefficient: float
    confidence_level: float
    sample_size: int
    trend_direction: str  # 'positive', 'negative', 'neutral'

@dataclass
class TaskOutcome:
    """Task completion outcome with quality metrics."""
    task_id: str
    completion_time: str
    quality_score: float
    behavioral_metrics: Dict[str, Any]
    success: bool

class QualityCorrelator:
    """Correlates behavioral patterns with task quality outcomes."""

    def __init__(self, breadcrumb_file: str = "breadcrumb_trail.jsonl",
                 task_reports_dir: str = "reports"):
        self.breadcrumb_file = Path(breadcrumb_file)
        self.task_reports_dir = Path(task_reports_dir)
        self.correlations = {}
        self.task_outcomes = []
        self._load_task_outcomes()

    def _load_task_outcomes(self):
        """Load task outcomes from report files."""
        if not self.task_reports_dir.exists():
            return

        for report_file in self.task_reports_dir.glob("report_TASK_*.md"):
            try:
                outcome = self._parse_task_report(report_file)
                if outcome:
                    self.task_outcomes.append(outcome)
            except Exception as e:
                print(f"Error parsing {report_file}: {e}")

    def _parse_task_report(self, report_path: Path) -> Optional[TaskOutcome]:
        """Parse task report to extract outcome metrics."""
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract task ID from filename
        filename = report_path.name
        if not filename.startswith("report_TASK_"):
            return None

        task_id = filename.split("_")[2]  # TASK_XXXX

        # Extract status
        status_line = None
        for line in content.split('\n'):
            if line.startswith("STATUS:"):
                status_line = line
                break

        if not status_line:
            return None

        success = "SUCCESS" in status_line.upper()

        # Extract timestamp
        timestamp = None
        for line in content.split('\n'):
            if line.startswith("TIMESTAMP:"):
                timestamp = line.split(":", 1)[1].strip()
                break

        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        # Placeholder quality score (would need actual quality assessment)
        quality_score = 85.0 if success else 45.0

        return TaskOutcome(
            task_id=task_id,
            completion_time=timestamp,
            quality_score=quality_score,
            behavioral_metrics={},  # Would be populated from breadcrumbs
            success=success
        )

    def correlate_activity_with_quality(self, activity_window_hours: int = 24) -> List[QualityCorrelation]:
        """Correlate activity patterns with quality outcomes."""
        correlations = []

        # Activity metrics to analyze
        activity_metrics = [
            'total_activities',
            'unique_files_accessed',
            'file_modification_rate',
            'context_switching_frequency',
            'guardrail_file_ratio'
        ]

        # Quality metrics to correlate with
        quality_metrics = [
            'task_success_rate',
            'quality_score',
            'completion_efficiency'
        ]

        for activity_metric in activity_metrics:
            for quality_metric in quality_metrics:
                correlation = self._calculate_correlation(
                    activity_metric, quality_metric, activity_window_hours
                )
                if correlation:
                    correlations.append(correlation)

        self.correlations = {f"{c.activity_metric}_{c.quality_metric}": c for c in correlations}
        return correlations

    def _calculate_correlation(self, activity_metric: str, quality_metric: str,
                             window_hours: int) -> Optional[QualityCorrelation]:
        """Calculate correlation between specific metrics."""
        if len(self.task_outcomes) < 3:
            return None  # Need minimum sample size

        activity_values = []
        quality_values = []

        for outcome in self.task_outcomes:
            # Get activity metrics for the window before task completion
            activity_value = self._get_activity_metric_for_task(
                outcome, activity_metric, window_hours
            )
            quality_value = self._get_quality_metric_value(outcome, quality_metric)

            if activity_value is not None and quality_value is not None:
                activity_values.append(activity_value)
                quality_values.append(quality_value)

        if len(activity_values) < 3:
            return None

        try:
            # Calculate Pearson correlation coefficient
            correlation = self._pearson_correlation(activity_values, quality_values)

            # Determine trend direction
            if correlation > 0.3:
                trend = 'positive'
            elif correlation < -0.3:
                trend = 'negative'
            else:
                trend = 'neutral'

            # Calculate confidence based on sample size and correlation strength
            confidence = min(abs(correlation) * math.sqrt(len(activity_values) - 2) / 2, 1.0)

            return QualityCorrelation(
                activity_metric=activity_metric,
                quality_metric=quality_metric,
                correlation_coefficient=correlation,
                confidence_level=confidence,
                sample_size=len(activity_values),
                trend_direction=trend
            )
        except Exception:
            return None

    def _get_activity_metric_for_task(self, outcome: TaskOutcome,
                                    metric: str, window_hours: int) -> Optional[float]:
        """Get activity metric value for time window before task completion."""
        try:
            completion_time = datetime.fromisoformat(outcome.completion_time.replace('Z', '+00:00'))
            window_start = completion_time - timedelta(hours=window_hours)

            # Load breadcrumbs for the window
            breadcrumbs = self._load_breadcrumbs_in_window(window_start, completion_time)

            if metric == 'total_activities':
                return len(breadcrumbs)
            elif metric == 'unique_files_accessed':
                return len(set(c.get('target_file', '') for c in breadcrumbs))
            elif metric == 'file_modification_rate':
                modifications = sum(1 for c in breadcrumbs if c.get('operation') == 'modify')
                hours = window_hours or 1
                return modifications / hours
            elif metric == 'context_switching_frequency':
                contexts = [c.get('source_context', '') for c in breadcrumbs]
                switches = sum(1 for i in range(1, len(contexts)) if contexts[i] != contexts[i-1])
                return switches / max(len(breadcrumbs), 1)
            elif metric == 'guardrail_file_ratio':
                guardrail_files = sum(1 for c in breadcrumbs
                                    if self._is_guardrail_file(c.get('target_file', '')))
                return guardrail_files / max(len(breadcrumbs), 1)

        except Exception:
            pass

        return None

    def _get_quality_metric_value(self, outcome: TaskOutcome, metric: str) -> Optional[float]:
        """Get quality metric value for task outcome."""
        if metric == 'task_success_rate':
            return 1.0 if outcome.success else 0.0
        elif metric == 'quality_score':
            return outcome.quality_score
        elif metric == 'completion_efficiency':
            # Placeholder: would need actual time-to-complete data
            return outcome.quality_score / 100.0

        return None

    def _load_breadcrumbs_in_window(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Load breadcrumbs within a time window."""
        breadcrumbs = []

        if not self.breadcrumb_file.exists():
            return breadcrumbs

        with open(self.breadcrumb_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    crumb = json.loads(line)
                    ts_str = crumb.get('timestamp', '')
                    if ts_str:
                        crumb_time = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        if start_time <= crumb_time <= end_time:
                            breadcrumbs.append(crumb)
                except (json.JSONDecodeError, ValueError):
                    continue

        return breadcrumbs

    def _is_guardrail_file(self, file_path: str) -> bool:
        """Check if file is a guardrail/system file."""
        if not file_path:
            return False

        file_name = Path(file_path).name.lower()
        guardrail_patterns = [
            '_guardrails.py', '_protocols.py', '_rules.py', 'critical_',
            'audit_', 'security_', 'validation_', 'compliance_',
            'bootstrap', 'loop_gate', 'session_checkpoint'
        ]

        return any(pattern in file_name for pattern in guardrail_patterns)

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)
        sum_y2 = sum(yi ** 2 for yi in y)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = math.sqrt((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2))

        return numerator / denominator if denominator != 0 else 0.0

    def get_top_correlations(self, min_confidence: float = 0.5) -> List[QualityCorrelation]:
        """Get correlations with highest confidence levels."""
        valid_correlations = [c for c in self.correlations.values()
                            if c.confidence_level >= min_confidence]

        return sorted(valid_correlations,
                     key=lambda c: abs(c.correlation_coefficient),
                     reverse=True)

    def predict_quality_from_activity(self, activity_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Predict quality outcomes based on current activity patterns."""
        predictions = {}

        for correlation_key, correlation in self.correlations.items():
            if correlation.confidence_level < 0.5:
                continue

            activity_value = activity_metrics.get(correlation.activity_metric)
            if activity_value is None:
                continue

            # Simple linear prediction based on correlation
            # In practice, this would use trained models
            predicted_quality = self._predict_from_correlation(
                correlation, activity_value
            )

            predictions[correlation.quality_metric] = {
                'predicted_value': predicted_quality,
                'confidence': correlation.confidence_level,
                'correlation_strength': correlation.correlation_coefficient
            }

        return predictions

    def _predict_from_correlation(self, correlation: QualityCorrelation,
                                activity_value: float) -> float:
        """Predict quality value using correlation (simplified linear model)."""
        # This is a placeholder - real implementation would use trained regression models
        # For now, use correlation coefficient as a simple predictor

        # Get baseline quality from historical data
        quality_values = [self._get_quality_metric_value(outcome, correlation.quality_metric)
                         for outcome in self.task_outcomes]
        quality_values = [v for v in quality_values if v is not None]

        if not quality_values:
            return 50.0  # Neutral

        baseline_quality = statistics.mean(quality_values)

        # Adjust based on correlation and activity level
        # This is highly simplified - real ML models would be used
        adjustment = correlation.correlation_coefficient * (activity_value - 5.0) * 10.0

        predicted = max(0.0, min(100.0, baseline_quality + adjustment))
        return predicted
<parameter name="filePath">d:\Keeper-Clean-Loop1\analysis\quality_correlator.py
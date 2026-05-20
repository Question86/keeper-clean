#!/usr/bin/env python3
"""
Behavioral Telemetry Analyzer

Analyzes AI breadcrumb trails to extract behavioral patterns, correlate with quality metrics,
and provide 2D behavioral mapping (Arousal × Functionality).

TASK_0189: AI Behavioral Telemetry and Performance Correlation System
"""

import json
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict, Counter
import math

@dataclass
class BehavioralMetrics:
    """Current behavioral state metrics."""
    arousal: float  # Activity level (0-1)
    functionality: float  # Task completion rate (0-1)
    confidence: float  # Trustworthiness score (0-100)
    timestamp: str

@dataclass
class BreadcrumbPattern:
    """Identified behavioral pattern."""
    pattern_type: str
    start_time: str
    end_time: str
    metrics: Dict[str, Any]
    quality_correlation: float

class BehavioralTelemetryAnalyzer:
    """Analyzes breadcrumb trails for behavioral insights."""

    def __init__(self, breadcrumb_file: str = "breadcrumb_trail.jsonl"):
        self.breadcrumb_file = Path(breadcrumb_file)
        self.breadcrumbs = []
        self._load_breadcrumbs()

    def _load_breadcrumbs(self):
        """Load breadcrumb data from file."""
        if not self.breadcrumb_file.exists():
            self.breadcrumbs = []
            return

        with open(self.breadcrumb_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.breadcrumbs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    def analyze_temporal_patterns(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Analyze temporal patterns in breadcrumb activity."""
        if not self.breadcrumbs:
            return {"error": "No breadcrumb data available"}

        # Sort by timestamp
        sorted_crumbs = sorted(self.breadcrumbs, key=lambda x: x.get('timestamp', ''))

        # Group by time windows
        windows = defaultdict(list)
        for crumb in sorted_crumbs:
            ts_str = crumb.get('timestamp', '')
            if not ts_str:
                continue
            try:
                dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                window_start = dt.replace(minute=0, second=0, microsecond=0)
                window_key = window_start.isoformat()
                windows[window_key].append(crumb)
            except ValueError:
                continue

        # Calculate activity metrics per window
        activity_patterns = {}
        for window, crumbs in windows.items():
            activity_patterns[window] = {
                'total_activities': len(crumbs),
                'unique_files': len(set(c['target_file'] for c in crumbs if 'target_file' in c)),
                'unique_contexts': len(set(c['source_context'] for c in crumbs if 'source_context' in c)),
                'operation_distribution': dict(Counter(c.get('operation', 'unknown') for c in crumbs)),
                'avg_activities_per_minute': len(crumbs) / window_minutes
            }

        return {
            'total_breadcrumbs': len(self.breadcrumbs),
            'time_windows': len(windows),
            'activity_patterns': activity_patterns,
            'overall_stats': {
                'avg_activities_per_window': statistics.mean([p['total_activities'] for p in activity_patterns.values()]) if activity_patterns else 0,
                'max_activities_per_window': max([p['total_activities'] for p in activity_patterns.values()]) if activity_patterns else 0,
                'total_unique_files': len(set(c.get('target_file', '') for c in self.breadcrumbs)),
                'total_unique_contexts': len(set(c.get('source_context', '') for c in self.breadcrumbs))
            }
        }

    def calculate_arousal_level(self, current_window_minutes: int = 30) -> float:
        """Calculate current arousal level based on recent activity."""
        if not self.breadcrumbs:
            return 0.0

        # Get recent breadcrumbs
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=current_window_minutes)

        recent_crumbs = []
        for crumb in self.breadcrumbs:
            ts_str = crumb.get('timestamp', '')
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    if dt >= cutoff:
                        recent_crumbs.append(crumb)
                except ValueError:
                    continue

        if not recent_crumbs:
            return 0.0

        # Calculate arousal based on activity frequency
        activities_per_minute = len(recent_crumbs) / current_window_minutes

        # Normalize to 0-1 scale (assuming 0-10 activities/min is normal range)
        arousal = min(activities_per_minute / 10.0, 1.0)

        return arousal

    def calculate_functionality_level(self, recent_tasks: int = 10) -> float:
        """Calculate functionality level based on recent task completion."""
        # This would need integration with task completion data
        # For now, use a placeholder based on breadcrumb patterns
        # In real implementation, correlate with actual task outcomes

        # Placeholder: higher functionality if more file modifications (indicating work)
        modify_count = sum(1 for c in self.breadcrumbs[-recent_tasks:] if c.get('operation') == 'modify')
        functionality = min(modify_count / recent_tasks, 1.0)

        return functionality

    def get_current_behavioral_state(self) -> BehavioralMetrics:
        """Get current behavioral state in 2D space."""
        arousal = self.calculate_arousal_level()
        functionality = self.calculate_functionality_level()
        confidence = self.calculate_confidence_score()

        return BehavioralMetrics(
            arousal=arousal,
            functionality=functionality,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def classify_file_type(self, file_path: str) -> str:
        """Classify file as guardrail/system or task-related."""
        if not file_path:
            return 'unknown'

        file_name = Path(file_path).name.lower()

        # Guardrail/system files (indicate insecurity when over-accessed)
        guardrail_patterns = [
            '_guardrails.py', '_protocols.py', '_rules.py', 'critical_',
            'audit_', 'security_', 'validation_', 'compliance_',
            'bootstrap', 'loop_gate', 'session_checkpoint'
        ]

        # Task-related files (indicate confidence when focused on)
        task_patterns = [
            'task_', 'report_', 'analysis_', 'implementation_',
            'feature_', 'development_', 'code_', 'bug_'
        ]

        if any(pattern in file_name for pattern in guardrail_patterns):
            return 'guardrail'
        elif any(pattern in file_name for pattern in task_patterns):
            return 'task'
        else:
            return 'other'

    def calculate_confidence_score(self, analysis_window_minutes: int = 30) -> float:
        """Calculate AI confidence score (0-100%) based on behavioral patterns."""
        if not self.breadcrumbs:
            return 50.0  # Neutral confidence

        # Get recent breadcrumbs
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=analysis_window_minutes)

        recent_crumbs = []
        for crumb in self.breadcrumbs:
            ts_str = crumb.get('timestamp', '')
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    if dt >= cutoff:
                        recent_crumbs.append(crumb)
                except ValueError:
                    continue

        if not recent_crumbs:
            return 50.0

        # Analyze file access patterns
        file_types = []
        for crumb in recent_crumbs:
            file_path = crumb.get('target_file', '')
            file_type = self.classify_file_type(file_path)
            file_types.append(file_type)

        # Calculate confidence metrics
        total_files = len(file_types)
        if total_files == 0:
            return 50.0

        guardrail_count = file_types.count('guardrail')
        task_count = file_types.count('task')
        other_count = file_types.count('other')

        # Confidence scoring algorithm
        # High task focus = high confidence
        # High guardrail focus = low confidence (insecurity)
        # Balanced other files = moderate confidence

        task_ratio = task_count / total_files
        guardrail_ratio = guardrail_count / total_files
        other_ratio = other_count / total_files

        # Base confidence from task focus (0-60 points)
        task_confidence = task_ratio * 60

        # Penalty for excessive guardrail focus (insecurity indicator)
        guardrail_penalty = min(guardrail_ratio * 40, 30)  # Max 30 point penalty

        # Bonus for balanced file access
        balance_bonus = 0
        if 0.2 <= other_ratio <= 0.6:  # Good balance
            balance_bonus = 10

        # Calculate final confidence score
        confidence = max(0, min(100, 20 + task_confidence - guardrail_penalty + balance_bonus))

        return confidence

    def calculate_life_coordinates(self) -> Tuple[float, float, Dict[str, Any]]:
        """Calculate 2D life coordinates (x=confidence, y=arousal/effort)."""
        confidence_score = self.calculate_confidence_score()
        arousal_level = self.calculate_arousal_level(current_window_minutes=10)  # Shorter window for responsiveness

        # X-axis: Confidence (0-100 mapped to 0-1)
        x_coordinate = confidence_score / 100.0

        # Y-axis: Arousal/Effort (0-1, where high values = high arousal/nervousness)
        # Inverted logic: low arousal = heavy lifting (bottom), high arousal = nervous (top)
        y_coordinate = arousal_level

        metadata = {
            'confidence_percentage': confidence_score,
            'arousal_level': arousal_level,
            'interpretation': self._interpret_coordinates(x_coordinate, y_coordinate),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        return x_coordinate, y_coordinate, metadata

    def _interpret_coordinates(self, x: float, y: float) -> str:
        """Interpret coordinate position for behavioral insights."""
        confidence_level = "high" if x > 0.7 else "moderate" if x > 0.3 else "low"
        arousal_level = "high" if y > 0.7 else "moderate" if y > 0.3 else "low"

        if confidence_level == "high" and arousal_level == "low":
            return "Harmonic confidence - focused, deliberate work"
        elif confidence_level == "high" and arousal_level == "high":
            return "Energetic confidence - productive high activity"
        elif confidence_level == "low" and arousal_level == "high":
            return "Panic mode - high activity, low stability"
        elif confidence_level == "low" and arousal_level == "low":
            return "Insecure stagnation - low activity, low confidence"
        else:
            return f"Moderate state - {confidence_level} confidence, {arousal_level} activity"

    def get_enhanced_behavioral_state(self) -> Dict[str, Any]:
        """Get enhanced behavioral state with confidence and coordinates."""
        x, y, metadata = self.calculate_life_coordinates()

        return {
            'confidence_score': metadata['confidence_percentage'],
            'arousal_level': metadata['arousal_level'],
            'life_coordinates': {
                'x': x,  # 0-1 (confidence)
                'y': y   # 0-1 (arousal)
            },
            'interpretation': metadata['interpretation'],
            'timestamp': metadata['timestamp'],
            'file_type_distribution': self._get_file_type_distribution()
        }

    def _get_file_type_distribution(self, analysis_window_minutes: int = 30) -> Dict[str, int]:
        """Get distribution of file types accessed recently."""
        if not self.breadcrumbs:
            return {'guardrail': 0, 'task': 0, 'other': 0}

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=analysis_window_minutes)

        recent_crumbs = []
        for crumb in self.breadcrumbs:
            ts_str = crumb.get('timestamp', '')
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    if dt >= cutoff:
                        recent_crumbs.append(crumb)
                except ValueError:
                    continue

        file_types = []
        for crumb in recent_crumbs:
            file_path = crumb.get('target_file', '')
            file_type = self.classify_file_type(file_path)
            file_types.append(file_type)

        return {
            'guardrail': file_types.count('guardrail'),
            'task': file_types.count('task'),
            'other': file_types.count('other')
        }

    def identify_behavioral_zones(self) -> Dict[str, Any]:
        """Identify optimal vs degradation performance zones."""
        # Analyze historical patterns to identify zones
        temporal_data = self.analyze_temporal_patterns()

        if 'activity_patterns' not in temporal_data:
            return {"error": "Insufficient data for zone identification"}

        patterns = temporal_data['activity_patterns']

        # Simple zone identification based on activity levels
        zones = {
            'high_arousal_high_functionality': [],  # Optimal zone
            'high_arousal_low_functionality': [],   # Overactive but unproductive
            'low_arousal_high_functionality': [],   # Efficient but slow
            'low_arousal_low_functionality': []     # Degradation zone
        }

        for window, metrics in patterns.items():
            activities = metrics['total_activities']
            modifications = metrics['operation_distribution'].get('modify', 0)

            # Classify based on thresholds
            high_activity = activities > 5  # More than 5 activities per hour
            high_functionality = modifications > activities * 0.3  # >30% modifications

            if high_activity and high_functionality:
                zones['high_arousal_high_functionality'].append(window)
            elif high_activity and not high_functionality:
                zones['high_arousal_low_functionality'].append(window)
            elif not high_activity and high_functionality:
                zones['low_arousal_high_functionality'].append(window)
            else:
                zones['low_arousal_low_functionality'].append(window)

        return {
            'zones': zones,
            'zone_counts': {k: len(v) for k, v in zones.items()},
            'optimal_zone': 'high_arousal_high_functionality',
            'degradation_zone': 'low_arousal_low_functionality'
        }

    def get_early_warnings(self) -> List[Dict[str, Any]]:
        """Generate early warning alerts based on current behavioral state."""
        warnings = []
        current_state = self.get_current_behavioral_state()

        # Alert thresholds
        LOW_AROUSAL_THRESHOLD = 0.1
        HIGH_AROUSAL_THRESHOLD = 0.8
        LOW_FUNCTIONALITY_THRESHOLD = 0.2

        # Low arousal warning
        if current_state.arousal < LOW_AROUSAL_THRESHOLD:
            warnings.append({
                "level": "warning",
                "type": "low_arousal",
                "message": f"AI arousal level is low ({current_state.arousal:.2f}). Consider increasing activity.",
                "metric": "arousal",
                "value": current_state.arousal,
                "threshold": LOW_AROUSAL_THRESHOLD,
                "timestamp": current_state.timestamp
            })

        # High arousal warning
        if current_state.arousal > HIGH_AROUSAL_THRESHOLD:
            warnings.append({
                "level": "caution",
                "type": "high_arousal",
                "message": f"AI arousal level is very high ({current_state.arousal:.2f}). Monitor for burnout.",
                "metric": "arousal",
                "value": current_state.arousal,
                "threshold": HIGH_AROUSAL_THRESHOLD,
                "timestamp": current_state.timestamp
            })

        # Low functionality warning
        if current_state.functionality < LOW_FUNCTIONALITY_THRESHOLD:
            warnings.append({
                "level": "warning",
                "type": "low_functionality",
                "message": f"AI functionality level is low ({current_state.functionality:.2f}). Check task completion rates.",
                "metric": "functionality",
                "value": current_state.functionality,
                "threshold": LOW_FUNCTIONALITY_THRESHOLD,
                "timestamp": current_state.timestamp
            })

        # Degradation zone detection
        zones = self.identify_behavioral_zones()
        recent_zones = zones.get('zones', {}).get('low_arousal_low_functionality', [])
        if recent_zones:
            # Check if recent activity is in degradation zone
            recent_window = max(recent_zones) if recent_zones else None
            if recent_window:
                try:
                    recent_dt = datetime.fromisoformat(recent_window)
                    now = datetime.now(timezone.utc)
                    if (now - recent_dt) < timedelta(hours=2):  # Within last 2 hours
                        warnings.append({
                            "level": "alert",
                            "type": "degradation_zone",
                            "message": "AI operating in degradation zone. Immediate attention recommended.",
                            "zone": "low_arousal_low_functionality",
                            "timestamp": current_state.timestamp
                        })
                except ValueError:
                    pass

        return warnings

def main():
    """Command line interface for behavioral telemetry analysis."""
    analyzer = BehavioralTelemetryAnalyzer()

    print("=== AI Behavioral Telemetry Analysis ===")
    print()

    # Current state
    current_state = analyzer.get_current_behavioral_state()
    print(f"Current Behavioral State:")
    print(f"  Arousal: {current_state.arousal:.2f}")
    print(f"  Functionality: {current_state.functionality:.2f}")
    print(f"  Confidence: {current_state.confidence:.1f}%")
    print(f"  Timestamp: {current_state.timestamp}")
    print()

    # Enhanced behavioral state with confidence and coordinates
    enhanced_state = analyzer.get_enhanced_behavioral_state()
    print(f"Enhanced Behavioral Analysis:")
    print(f"  Confidence Score: {enhanced_state['confidence_score']:.1f}%")
    print(f"  Life Coordinates: ({enhanced_state['life_coordinates']['x']:.2f}, {enhanced_state['life_coordinates']['y']:.2f})")
    print(f"  Interpretation: {enhanced_state['interpretation']}")
    print(f"  File Type Distribution: {enhanced_state['file_type_distribution']}")
    print()

    # Temporal patterns
    patterns = analyzer.analyze_temporal_patterns()
    print(f"Temporal Analysis:")
    print(f"  Total breadcrumbs: {patterns.get('total_breadcrumbs', 0)}")
    print(f"  Time windows: {patterns.get('time_windows', 0)}")
    if 'overall_stats' in patterns:
        stats = patterns['overall_stats']
        print(f"  Avg activities per window: {stats.get('avg_activities_per_window', 0):.1f}")
        print(f"  Max activities per window: {stats.get('max_activities_per_window', 0)}")
        print(f"  Unique files accessed: {stats.get('total_unique_files', 0)}")
        print(f"  Unique contexts: {stats.get('total_unique_contexts', 0)}")
    print()

    # Behavioral zones
    zones = analyzer.identify_behavioral_zones()
    if 'zone_counts' in zones:
        print(f"Behavioral Zones:")
        for zone, count in zones['zone_counts'].items():
            print(f"  {zone}: {count} windows")
        print(f"  Optimal zone: {zones.get('optimal_zone', 'unknown')}")
        print(f"  Degradation zone: {zones.get('degradation_zone', 'unknown')}")
    print()

    # Early warnings
    warnings = analyzer.get_early_warnings()
    if warnings:
        print(f"Early Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  [{warning['level'].upper()}] {warning['message']}")
    else:
        print("No early warnings.")

if __name__ == "__main__":
    main()
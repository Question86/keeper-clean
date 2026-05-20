#!/usr/bin/env python3
"""
Dimensional Mapper

Implements 2D behavioral mapping (Arousal × Functionality) with real-time positioning.
Provides visualization and analysis of AI behavioral state space.

TASK_0189: AI Behavioral Telemetry and Performance Correlation System
"""

import json
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import statistics

@dataclass
class BehavioralPoint:
    """A point in 2D behavioral space."""
    arousal: float  # X-axis: 0-1 (activity intensity)
    functionality: float  # Y-axis: 0-1 (task completion quality)
    timestamp: str
    confidence: float
    metadata: Dict[str, Any]

@dataclass
class BehavioralZone:
    """Defined zone in behavioral space."""
    name: str
    arousal_range: Tuple[float, float]
    functionality_range: Tuple[float, float]
    description: str
    risk_level: str  # 'optimal', 'warning', 'critical'
    recommendations: List[str]

@dataclass
class BehavioralTrajectory:
    """Trajectory through behavioral space over time."""
    points: List[BehavioralPoint]
    start_time: str
    end_time: str
    trend_analysis: Dict[str, Any]

class DimensionalMapper:
    """Maps AI behavior to 2D arousal-functionality space."""

    def __init__(self):
        self.behavioral_zones = self._define_behavioral_zones()
        self.trajectory_history = []
        self.current_trajectory = BehavioralTrajectory(
            points=[], start_time="", end_time="", trend_analysis={}
        )

    def _define_behavioral_zones(self) -> Dict[str, BehavioralZone]:
        """Define the behavioral zones in 2D space."""
        return {
            'optimal_performance': BehavioralZone(
                name='Optimal Performance',
                arousal_range=(0.4, 0.8),
                functionality_range=(0.7, 1.0),
                description='Balanced activity with high task completion quality',
                risk_level='optimal',
                recommendations=[
                    'Maintain current behavioral patterns',
                    'Monitor for gradual changes',
                    'Document successful strategies'
                ]
            ),
            'high_focus': BehavioralZone(
                name='High Focus',
                arousal_range=(0.6, 1.0),
                functionality_range=(0.4, 0.8),
                description='High activity but moderate task quality - may indicate rushing',
                risk_level='warning',
                recommendations=[
                    'Consider pacing adjustments',
                    'Review task prioritization',
                    'Check for quality vs speed trade-offs'
                ]
            ),
            'burnout_risk': BehavioralZone(
                name='Burnout Risk',
                arousal_range=(0.8, 1.0),
                functionality_range=(0.0, 0.4),
                description='Very high activity with poor quality - potential exhaustion',
                risk_level='critical',
                recommendations=[
                    'Immediate rest period recommended',
                    'Reduce workload temporarily',
                    'Review task complexity and deadlines'
                ]
            ),
            'low_engagement': BehavioralZone(
                name='Low Engagement',
                arousal_range=(0.0, 0.3),
                functionality_range=(0.0, 0.6),
                description='Low activity with variable quality - may indicate disengagement',
                risk_level='warning',
                recommendations=[
                    'Increase task engagement',
                    'Review motivation factors',
                    'Consider task reassignment'
                ]
            ),
            'inefficient_focus': BehavioralZone(
                name='Inefficient Focus',
                arousal_range=(0.0, 0.4),
                functionality_range=(0.0, 0.3),
                description='Low activity and poor quality - ineffective work patterns',
                risk_level='critical',
                recommendations=[
                    'Immediate intervention required',
                    'Review work methods and tools',
                    'Consider additional training or support'
                ]
            ),
            'recovery_mode': BehavioralZone(
                name='Recovery Mode',
                arousal_range=(0.0, 0.2),
                functionality_range=(0.7, 1.0),
                description='Low activity but high quality - likely strategic pausing',
                risk_level='optimal',
                recommendations=[
                    'Allow recovery time',
                    'Monitor transition back to active work',
                    'Document recovery strategies'
                ]
            )
        }

    def add_behavioral_point(self, arousal: float, functionality: float,
                           confidence: float = 1.0, metadata: Dict[str, Any] = None) -> BehavioralPoint:
        """Add a new point to the current behavioral trajectory."""
        if metadata is None:
            metadata = {}

        point = BehavioralPoint(
            arousal=max(0.0, min(1.0, arousal)),
            functionality=max(0.0, min(1.0, functionality)),
            timestamp=datetime.now(timezone.utc).isoformat(),
            confidence=confidence,
            metadata=metadata
        )

        self.current_trajectory.points.append(point)

        # Update trajectory times
        if not self.current_trajectory.start_time:
            self.current_trajectory.start_time = point.timestamp
        self.current_trajectory.end_time = point.timestamp

        return point

    def get_current_zone(self) -> Tuple[str, BehavioralZone]:
        """Get the current behavioral zone based on latest point."""
        if not self.current_trajectory.points:
            return 'unknown', BehavioralZone(
                name='Unknown',
                arousal_range=(0.0, 1.0),
                functionality_range=(0.0, 1.0),
                description='Insufficient data for zone classification',
                risk_level='warning',
                recommendations=['Gather more behavioral data']
            )

        latest_point = self.current_trajectory.points[-1]

        for zone_name, zone in self.behavioral_zones.items():
            if (zone.arousal_range[0] <= latest_point.arousal <= zone.arousal_range[1] and
                zone.functionality_range[0] <= latest_point.functionality <= zone.functionality_range[1]):
                return zone_name, zone

        # If no zone matches, find closest
        return self._find_closest_zone(latest_point)

    def _find_closest_zone(self, point: BehavioralPoint) -> Tuple[str, BehavioralZone]:
        """Find the closest behavioral zone to a point."""
        min_distance = float('inf')
        closest_zone = None

        for zone_name, zone in self.behavioral_zones.items():
            # Calculate distance to zone center
            zone_center_arousal = (zone.arousal_range[0] + zone.arousal_range[1]) / 2
            zone_center_functionality = (zone.functionality_range[0] + zone.functionality_range[1]) / 2

            distance = math.sqrt(
                (point.arousal - zone_center_arousal) ** 2 +
                (point.functionality - zone_center_functionality) ** 2
            )

            if distance < min_distance:
                min_distance = distance
                closest_zone = (zone_name, zone)

        return closest_zone if closest_zone else ('unknown', self.behavioral_zones['optimal_performance'])

    def analyze_trajectory_trends(self, trajectory: BehavioralTrajectory = None) -> Dict[str, Any]:
        """Analyze trends in behavioral trajectory."""
        if trajectory is None:
            trajectory = self.current_trajectory

        if len(trajectory.points) < 2:
            return {
                'trend': 'insufficient_data',
                'description': 'Need at least 2 data points for trend analysis'
            }

        points = trajectory.points

        # Calculate trend directions
        arousal_trend = self._calculate_trend([p.arousal for p in points])
        functionality_trend = self._calculate_trend([p.functionality for p in points])

        # Calculate volatility
        arousal_volatility = statistics.stdev([p.arousal for p in points]) if len(points) > 1 else 0
        functionality_volatility = statistics.stdev([p.functionality for p in points]) if len(points) > 1 else 0

        # Identify pattern type
        pattern = self._classify_trajectory_pattern(arousal_trend, functionality_trend,
                                                   arousal_volatility, functionality_volatility)

        # Calculate zone transitions
        zone_transitions = self._analyze_zone_transitions(points)

        return {
            'arousal_trend': arousal_trend,
            'functionality_trend': functionality_trend,
            'arousal_volatility': arousal_volatility,
            'functionality_volatility': functionality_volatility,
            'pattern_type': pattern,
            'zone_transitions': zone_transitions,
            'overall_stability': 1.0 - (arousal_volatility + functionality_volatility) / 2,
            'data_points': len(points)
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from value series."""
        if len(values) < 2:
            return 'stable'

        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        y = values

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0

        if slope > 0.01:
            return 'increasing'
        elif slope < -0.01:
            return 'decreasing'
        else:
            return 'stable'

    def _classify_trajectory_pattern(self, arousal_trend: str, functionality_trend: str,
                                   arousal_vol: float, func_vol: float) -> str:
        """Classify the overall trajectory pattern."""
        high_volatility = (arousal_vol + func_vol) / 2 > 0.3

        if high_volatility:
            return 'erratic'
        elif arousal_trend == 'increasing' and functionality_trend == 'increasing':
            return 'improving'
        elif arousal_trend == 'decreasing' and functionality_trend == 'decreasing':
            return 'declining'
        elif arousal_trend == 'increasing' and functionality_trend == 'decreasing':
            return 'overextending'
        elif arousal_trend == 'decreasing' and functionality_trend == 'increasing':
            return 'optimizing'
        else:
            return 'stable'

    def _analyze_zone_transitions(self, points: List[BehavioralPoint]) -> List[Dict[str, Any]]:
        """Analyze transitions between behavioral zones."""
        transitions = []

        for i in range(1, len(points)):
            prev_zone, _ = self._find_closest_zone(points[i-1])
            curr_zone, _ = self._find_closest_zone(points[i])

            if prev_zone != curr_zone:
                transitions.append({
                    'from_zone': prev_zone,
                    'to_zone': curr_zone,
                    'timestamp': points[i].timestamp,
                    'arousal_change': points[i].arousal - points[i-1].arousal,
                    'functionality_change': points[i].functionality - points[i-1].functionality
                })

        return transitions

    def get_zone_statistics(self) -> Dict[str, Any]:
        """Get statistics about time spent in each zone."""
        if not self.current_trajectory.points:
            return {}

        zone_counts = defaultdict(int)
        zone_durations = defaultdict(float)

        prev_point = None
        prev_zone = None

        for point in self.current_trajectory.points:
            curr_zone, _ = self._find_closest_zone(point)
            zone_counts[curr_zone] += 1

            if prev_point and prev_zone == curr_zone:
                # Calculate time spent in zone
                try:
                    prev_time = datetime.fromisoformat(prev_point.timestamp.replace('Z', '+00:00'))
                    curr_time = datetime.fromisoformat(point.timestamp.replace('Z', '+00:00'))
                    duration = (curr_time - prev_time).total_seconds() / 3600  # hours
                    zone_durations[curr_zone] += duration
                except ValueError:
                    pass

            prev_point = point
            prev_zone = curr_zone

        total_points = len(self.current_trajectory.points)

        return {
            'zone_distribution': {
                zone: {
                    'count': count,
                    'percentage': count / total_points * 100,
                    'estimated_hours': zone_durations[zone]
                }
                for zone, count in zone_counts.items()
            },
            'most_common_zone': max(zone_counts.keys(), key=lambda z: zone_counts[z]) if zone_counts else None,
            'zone_stability': len(zone_counts) / total_points if total_points > 0 else 0
        }

    def predict_next_zone(self, recent_points: int = 5) -> Dict[str, Any]:
        """Predict likely next behavioral zone based on recent trajectory."""
        if len(self.current_trajectory.points) < recent_points + 1:
            return {'prediction': 'insufficient_data'}

        recent = self.current_trajectory.points[-recent_points:]

        # Calculate momentum (recent trend)
        arousal_momentum = recent[-1].arousal - recent[0].arousal
        functionality_momentum = recent[-1].functionality - recent[0].functionality

        # Predict next position
        predicted_arousal = max(0.0, min(1.0, recent[-1].arousal + arousal_momentum / recent_points))
        predicted_functionality = max(0.0, min(1.0, recent[-1].functionality + functionality_momentum / recent_points))

        # Find predicted zone
        predicted_point = BehavioralPoint(
            arousal=predicted_arousal,
            functionality=predicted_functionality,
            timestamp=datetime.now(timezone.utc).isoformat(),
            confidence=0.7,  # Lower confidence for predictions
            metadata={'predicted': True}
        )

        predicted_zone_name, predicted_zone = self._find_closest_zone(predicted_point)

        return {
            'predicted_zone': predicted_zone_name,
            'predicted_arousal': predicted_arousal,
            'predicted_functionality': predicted_functionality,
            'confidence': 0.7,
            'momentum_arousal': arousal_momentum,
            'momentum_functionality': functionality_momentum,
            'recommendations': predicted_zone.recommendations
        }

    def export_trajectory_data(self, format: str = 'json') -> str:
        """Export trajectory data for visualization or analysis."""
        data = {
            'trajectory': {
                'start_time': self.current_trajectory.start_time,
                'end_time': self.current_trajectory.end_time,
                'points': [
                    {
                        'arousal': p.arousal,
                        'functionality': p.functionality,
                        'timestamp': p.timestamp,
                        'confidence': p.confidence,
                        'metadata': p.metadata
                    }
                    for p in self.current_trajectory.points
                ]
            },
            'zones': {
                name: {
                    'arousal_range': zone.arousal_range,
                    'functionality_range': zone.functionality_range,
                    'description': zone.description,
                    'risk_level': zone.risk_level,
                    'recommendations': zone.recommendations
                }
                for name, zone in self.behavioral_zones.items()
            },
            'analysis': self.analyze_trajectory_trends()
        }

        if format == 'json':
            return json.dumps(data, indent=2, default=str)
        else:
            return str(data)  # Placeholder for other formats
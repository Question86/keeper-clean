#!/usr/bin/env python3
"""
Pattern Recognizer

Uses machine learning to identify behavioral clusters and performance patterns.
Provides early warning detection and predictive analytics.

TASK_0189: AI Behavioral Telemetry and Performance Correlation System
"""

import json
import math
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter
import statistics
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

# Budget limit integration
try:
    from token_governor import TokenGovernor, BudgetZone
    from rate_limit_handler import BudgetGuard
    BUDGET_INTEGRATION_AVAILABLE = True
except ImportError:
    BUDGET_INTEGRATION_AVAILABLE = False

@dataclass
class PerformanceCluster:
    """A cluster of similar performance patterns."""
    cluster_id: int
    centroid: List[float]
    members: List[Dict[str, Any]]
    performance_profile: Dict[str, Any]
    risk_assessment: str
    pattern_description: str

@dataclass
class PatternAlert:
    """Early warning alert for pattern changes."""
    alert_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    confidence: float
    trigger_conditions: Dict[str, Any]
    recommendations: List[str]
    timestamp: str

class PatternRecognizer:
    """Recognizes patterns in behavioral data using ML techniques."""

    def __init__(self, n_clusters: int = 6):
        self.alert_thresholds = None  # Ensure attribute always exists
        self.n_clusters = n_clusters
        self.clusters = []
        self.scaler = StandardScaler()
        
        # Budget integration
        self.budget_aware = BUDGET_INTEGRATION_AVAILABLE
        if self.budget_aware:
            self.token_governor = TokenGovernor()
            self.budget_guard = BudgetGuard(Path("."))
        else:
            self.token_governor = None
            self.budget_guard = None
        self.alert_thresholds = self._define_alert_thresholds()
    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status for pattern analysis."""
        if not self.budget_aware:
            return {
                'budget_aware': False,
                'zone': 'UNKNOWN',
                'percentage': 0.0,
                'remaining': 0,
                'budget_limit': 0
            }
        
        try:
            metrics = self.token_governor.get_current_metrics()
            return {
                'budget_aware': True,
                'zone': metrics.zone.value,
                'percentage': metrics.percentage,
                'remaining': metrics.remaining,
                'budget_limit': self.token_governor.budget,
                'used': metrics.used
            }
        except Exception as e:
            return {
                'budget_aware': False,
                'zone': 'ERROR',
                'percentage': 0.0,
                'remaining': 0,
                'budget_limit': 0,
                'error': str(e)
            }
        self.training_data = []
        self.alert_thresholds = self._define_alert_thresholds()

    def _define_alert_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Define thresholds for different types of alerts."""
        return {
            'arousal_spike': {
                'threshold': 0.8,
                'window_minutes': 30,
                'min_confidence': 0.7
            },
            'functionality_drop': {
                'threshold': 0.3,
                'window_minutes': 60,
                'min_confidence': 0.6
            },
            'zone_instability': {
                'threshold': 0.7,  # zone change frequency
                'window_hours': 2,
                'min_confidence': 0.5
            },
            'correlation_breakdown': {
                'threshold': 0.3,  # correlation coefficient drop
                'window_hours': 24,
                'min_confidence': 0.8
            }
        }

    def train_on_historical_data(self, behavioral_points: List[Dict[str, Any]],
                               performance_outcomes: List[Dict[str, Any]]) -> List[PerformanceCluster]:
        """Train clustering model on historical behavioral and performance data."""
        if len(behavioral_points) < self.n_clusters * 2:
            # Not enough data for meaningful clustering
            return self._create_default_clusters()

        # Prepare training data
        training_features = []
        for point in behavioral_points:
            features = [
                point.get('arousal', 0.5),
                point.get('functionality', 0.5),
                point.get('confidence', 0.8),
                point.get('activity_intensity', 0.5),
                point.get('context_stability', 0.5)
            ]
            training_features.append(features)

        # Normalize features
        training_array = np.array(training_features)
        normalized_features = self.scaler.fit_transform(training_array)

        # Perform clustering
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(normalized_features)

        # Create cluster objects
        clusters = []
        for i in range(self.n_clusters):
            cluster_mask = cluster_labels == i
            cluster_points = [p for p, mask in zip(behavioral_points, cluster_mask) if mask]

            if cluster_points:
                cluster = self._create_cluster(i, kmeans.cluster_centers_[i],
                                             cluster_points, performance_outcomes)
                clusters.append(cluster)

        self.clusters = clusters
        return clusters

    def _create_default_clusters(self) -> List[PerformanceCluster]:
        """Create default clusters when insufficient data is available."""
        default_clusters = [
            PerformanceCluster(
                cluster_id=0,
                centroid=[0.2, 0.8, 0.9, 0.3, 0.8],  # Low arousal, high functionality
                members=[],
                performance_profile={
                    'avg_quality': 85.0,
                    'success_rate': 0.9,
                    'efficiency': 0.8
                },
                risk_assessment='low',
                pattern_description='Efficient, focused work with high quality output'
            ),
            PerformanceCluster(
                cluster_id=1,
                centroid=[0.8, 0.6, 0.7, 0.8, 0.4],  # High arousal, moderate functionality
                members=[],
                performance_profile={
                    'avg_quality': 65.0,
                    'success_rate': 0.7,
                    'efficiency': 0.6
                },
                risk_assessment='medium',
                pattern_description='High activity but moderate quality - potential rushing'
            ),
            PerformanceCluster(
                cluster_id=2,
                centroid=[0.9, 0.2, 0.5, 0.9, 0.2],  # Very high arousal, low functionality
                members=[],
                performance_profile={
                    'avg_quality': 35.0,
                    'success_rate': 0.4,
                    'efficiency': 0.3
                },
                risk_assessment='high',
                pattern_description='Burnout pattern - high activity, low quality'
            )
        ]

        self.clusters = default_clusters
        return default_clusters

    def _create_cluster(self, cluster_id: int, centroid: np.ndarray,
                       members: List[Dict[str, Any]],
                       performance_outcomes: List[Dict[str, Any]]) -> PerformanceCluster:
        """Create a performance cluster from clustering results."""
        # Calculate performance profile for this cluster
        cluster_performance = self._analyze_cluster_performance(members, performance_outcomes)

        # Determine risk assessment
        risk = self._assess_cluster_risk(cluster_performance)

        # Generate pattern description
        description = self._generate_pattern_description(centroid, cluster_performance)

        return PerformanceCluster(
            cluster_id=cluster_id,
            centroid=centroid.tolist(),
            members=members,
            performance_profile=cluster_performance,
            risk_assessment=risk,
            pattern_description=description
        )

    def _analyze_cluster_performance(self, members: List[Dict[str, Any]],
                                   performance_outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance characteristics of cluster members."""
        if not members:
            return {
                'avg_quality': 50.0,
                'success_rate': 0.5,
                'efficiency': 0.5,
                'sample_size': 0
            }

        # Extract performance metrics (simplified - would use actual correlation)
        qualities = []
        successes = []
        efficiencies = []

        for member in members:
            # Match with performance outcomes based on timestamp proximity
            member_time = datetime.fromisoformat(member.get('timestamp', '').replace('Z', '+00:00'))

            closest_outcome = None
            min_time_diff = timedelta(hours=1)

            for outcome in performance_outcomes:
                outcome_time = datetime.fromisoformat(outcome.get('timestamp', '').replace('Z', '+00:00'))
                time_diff = abs(member_time - outcome_time)

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_outcome = outcome

            if closest_outcome:
                qualities.append(closest_outcome.get('quality_score', 50.0))
                successes.append(1.0 if closest_outcome.get('success', True) else 0.0)
                efficiencies.append(closest_outcome.get('efficiency', 0.5))

        return {
            'avg_quality': statistics.mean(qualities) if qualities else 50.0,
            'success_rate': statistics.mean(successes) if successes else 0.5,
            'efficiency': statistics.mean(efficiencies) if efficiencies else 0.5,
            'sample_size': len(members)
        }

    def _assess_cluster_risk(self, performance: Dict[str, Any]) -> str:
        """Assess risk level of a performance cluster."""
        quality = performance.get('avg_quality', 50.0)
        success_rate = performance.get('success_rate', 0.5)

        if quality >= 80 and success_rate >= 0.8:
            return 'low'
        elif quality >= 60 and success_rate >= 0.6:
            return 'medium'
        elif quality >= 40 and success_rate >= 0.4:
            return 'high'
        else:
            return 'critical'

    def _generate_pattern_description(self, centroid: np.ndarray,
                                    performance: Dict[str, Any]) -> str:
        """Generate human-readable description of the pattern."""
        arousal, functionality, confidence, intensity, stability = centroid

        descriptions = []

        # Arousal level
        if arousal < 0.3:
            descriptions.append("low activity")
        elif arousal < 0.7:
            descriptions.append("moderate activity")
        else:
            descriptions.append("high activity")

        # Functionality level
        if functionality < 0.3:
            descriptions.append("low quality output")
        elif functionality < 0.7:
            descriptions.append("moderate quality output")
        else:
            descriptions.append("high quality output")

        # Stability
        if stability < 0.4:
            descriptions.append("unstable context switching")
        elif stability > 0.7:
            descriptions.append("stable focus")

        # Performance summary
        quality = performance.get('avg_quality', 50.0)
        if quality >= 75:
            descriptions.append("excellent performance")
        elif quality >= 60:
            descriptions.append("good performance")
        elif quality >= 45:
            descriptions.append("fair performance")
        else:
            descriptions.append("poor performance")

        return ", ".join(descriptions).capitalize()

    def classify_current_behavior(self, current_point: Dict[str, Any]) -> Dict[str, Any]:
        """Classify current behavioral point into nearest cluster."""
        # Get budget status for all return paths
        budget_status = self.get_budget_status()
        
        if not self.clusters:
            return {
                'cluster_id': -1,
                'distance': float('inf'),
                'confidence': 0.0,
                'risk_assessment': 'unknown',
                'budget_status': budget_status
            }

        # Prepare point features
        features = np.array([[
            current_point.get('arousal', 0.5),
            current_point.get('functionality', 0.5),
            current_point.get('confidence', 0.8),
            current_point.get('activity_intensity', 0.5),
            current_point.get('context_stability', 0.5)
        ]])

        # Normalize features
        normalized_features = self.scaler.transform(features)

        # Find nearest cluster
        min_distance = float('inf')
        nearest_cluster = None

        for cluster in self.clusters:
            centroid = np.array(cluster.centroid)
            distance = np.linalg.norm(normalized_features[0] - centroid)

            if distance < min_distance:
                min_distance = distance
                nearest_cluster = cluster

        if nearest_cluster:
            # Calculate confidence based on distance (closer = more confident)
            max_reasonable_distance = 2.0  # Based on normalized feature space
            confidence = max(0.0, 1.0 - (min_distance / max_reasonable_distance))

            # Adjust risk assessment based on budget constraints
            adjusted_risk = self._adjust_risk_for_budget(
                nearest_cluster.risk_assessment, 
                budget_status
            )

            result = {
                'cluster_id': nearest_cluster.cluster_id,
                'distance': min_distance,
                'confidence': confidence,
                'risk_assessment': adjusted_risk,
                'pattern_description': nearest_cluster.pattern_description,
                'performance_profile': nearest_cluster.performance_profile,
                'budget_status': budget_status
            }

            return result

        return {
            'cluster_id': -1,
            'distance': float('inf'),
            'confidence': 0.0,
            'risk_assessment': 'unknown',
            'budget_status': budget_status
        }

    def _adjust_risk_for_budget(self, base_risk: str, budget_status: Dict[str, Any]) -> str:
        """Adjust risk assessment based on current budget constraints."""
        if not budget_status.get('budget_aware', False):
            return base_risk
        
        zone = budget_status.get('zone', 'SAFE')
        percentage = budget_status.get('percentage', 0.0)
        
        # Budget pressure increases risk
        risk_levels = ['low', 'medium', 'high', 'critical']
        current_risk_idx = risk_levels.index(base_risk) if base_risk in risk_levels else 1
        
        if zone in ['EMERGENCY', 'ABORT']:
            # Critical budget pressure elevates all risks
            adjusted_risk = 'critical'
        elif zone == 'CONSERVATION':
            # High budget pressure increases risk by one level
            adjusted_risk = risk_levels[min(current_risk_idx + 1, len(risk_levels) - 1)]
        elif zone == 'CAUTION' and percentage > 60:
            # Moderate budget pressure with high usage increases risk slightly
            adjusted_risk = risk_levels[min(current_risk_idx + 1, len(risk_levels) - 1)]
        else:
            adjusted_risk = base_risk
            
        return adjusted_risk

    def detect_anomalies(self, recent_points: List[Dict[str, Any]],
                        baseline_window_hours: int = 24) -> List[PatternAlert]:
        """Detect anomalous patterns that may indicate issues."""
        alerts = []

        if len(recent_points) < 3:
            return alerts

        # Check for arousal spikes
        arousal_spike = self._detect_arousal_spike(recent_points)
        if arousal_spike:
            alerts.append(arousal_spike)

        # Check for functionality drops
        functionality_drop = self._detect_functionality_drop(recent_points)
        if functionality_drop:
            alerts.append(functionality_drop)

        # Check for zone instability
        zone_instability = self._detect_zone_instability(recent_points)
        if zone_instability:
            alerts.append(zone_instability)

        # Check for correlation breakdowns
        correlation_breakdown = self._detect_correlation_breakdown(recent_points)
        if correlation_breakdown:
            alerts.append(correlation_breakdown)

        # Check for budget pressure anomalies
        budget_anomaly = self._detect_budget_pressure_anomaly(recent_points)
        if budget_anomaly:
            alerts.append(budget_anomaly)

        return alerts

    def _detect_arousal_spike(self, points: List[Dict[str, Any]]) -> Optional[PatternAlert]:
        """Detect sudden spikes in arousal level."""
        if len(points) < 2:
            return None

        threshold = self.alert_thresholds['arousal_spike']['threshold']
        min_confidence = self.alert_thresholds['arousal_spike']['min_confidence']

        recent_arousal = [p.get('arousal', 0.5) for p in points[-3:]]  # Last 3 points
        avg_recent = statistics.mean(recent_arousal)

        if avg_recent >= threshold:
            # Check if this is a spike (compare to earlier points)
            if len(points) >= 6:
                earlier_arousal = [p.get('arousal', 0.5) for p in points[-6:-3]]
                avg_earlier = statistics.mean(earlier_arousal)

                if avg_recent - avg_earlier > 0.3:  # Significant increase
                    confidence = min(1.0, (avg_recent - avg_earlier) / 0.5)
                    if confidence >= min_confidence:
                        return PatternAlert(
                            alert_type='arousal_spike',
                            severity='medium',
                            description=f'Arousal level spiked to {avg_recent:.2f} (from {avg_earlier:.2f})',
                            confidence=confidence,
                            trigger_conditions={
                                'threshold': threshold,
                                'recent_avg': avg_recent,
                                'earlier_avg': avg_earlier
                            },
                            recommendations=[
                                'Monitor for signs of stress or overload',
                                'Consider implementing work breaks',
                                'Review current task load and priorities'
                            ],
                            timestamp=datetime.now(timezone.utc).isoformat()
                        )

        return None

    def _detect_functionality_drop(self, points: List[Dict[str, Any]]) -> Optional[PatternAlert]:
        """Detect significant drops in functionality."""
        if len(points) < 3:
            return None

        threshold = self.alert_thresholds['functionality_drop']['threshold']
        min_confidence = self.alert_thresholds['functionality_drop']['min_confidence']

        recent_functionality = [p.get('functionality', 0.5) for p in points[-5:]]
        avg_recent = statistics.mean(recent_functionality)

        if avg_recent <= threshold:
            confidence = min(1.0, (threshold - avg_recent) / 0.3)
            if confidence >= min_confidence:
                return PatternAlert(
                    alert_type='functionality_drop',
                    severity='high',
                    description=f'Functionality dropped to {avg_recent:.2f} (below threshold {threshold})',
                    confidence=confidence,
                    trigger_conditions={
                        'threshold': threshold,
                        'recent_avg': avg_recent
                    },
                    recommendations=[
                        'Immediate review of work quality required',
                        'Check for fatigue or distraction factors',
                        'Consider task reassignment or support',
                        'Implement quality checkpoints'
                    ],
                    timestamp=datetime.now(timezone.utc).isoformat()
                )

        return None

    def _detect_zone_instability(self, points: List[Dict[str, Any]]) -> Optional[PatternAlert]:
        """Detect excessive transitions between behavioral zones."""
        if len(points) < 5:
            return None

        # Count zone changes (simplified - would use actual zone classification)
        zone_changes = 0
        for i in range(1, len(points)):
            prev_arousal = points[i-1].get('arousal', 0.5)
            curr_arousal = points[i].get('arousal', 0.5)
            prev_func = points[i-1].get('functionality', 0.5)
            curr_func = points[i].get('functionality', 0.5)

            # Simple zone change detection (would be more sophisticated)
            if abs(prev_arousal - curr_arousal) > 0.3 or abs(prev_func - curr_func) > 0.3:
                zone_changes += 1

        change_rate = zone_changes / len(points)
        threshold = self.alert_thresholds['zone_instability']['threshold']

        if change_rate >= threshold:
            confidence = min(1.0, change_rate / 1.0)
            return PatternAlert(
                alert_type='zone_instability',
                severity='medium',
                description=f'High behavioral instability: {change_rate:.2f} zone changes per point',
                confidence=confidence,
                trigger_conditions={
                    'threshold': threshold,
                    'change_rate': change_rate
                },
                recommendations=[
                    'Stabilize work environment and routines',
                    'Reduce context switching between tasks',
                    'Establish more consistent work patterns',
                    'Consider workload consolidation'
                ],
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        return None

    def _detect_correlation_breakdown(self, points: List[Dict[str, Any]]) -> Optional[PatternAlert]:
        """Detect breakdown in expected arousal-functionality correlations."""
        if len(points) < 10:
            return None

        # Calculate correlation between arousal and functionality
        arousal_values = [p.get('arousal', 0.5) for p in points]
        func_values = [p.get('functionality', 0.5) for p in points]

        if len(arousal_values) >= 2:
            correlation = self._calculate_correlation(arousal_values, func_values)
            expected_correlation = 0.3  # Expected positive correlation

            if correlation < -0.2:  # Negative correlation indicates breakdown
                confidence = min(1.0, abs(correlation) / 0.5)
                threshold = self.alert_thresholds['correlation_breakdown']['threshold']

                if confidence >= threshold:
                    return PatternAlert(
                        alert_type='correlation_breakdown',
                        severity='high',
                        description=f'Arousal-functionality correlation breakdown: {correlation:.2f}',
                        confidence=confidence,
                        trigger_conditions={
                            'expected_correlation': expected_correlation,
                            'actual_correlation': correlation
                        },
                        recommendations=[
                            'Investigate factors disrupting normal patterns',
                            'Review recent changes in work environment',
                            'Consider external stress factors',
                            'Implement pattern monitoring and intervention'
                        ],
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )

        return None

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
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

    def _detect_budget_pressure_anomaly(self, points: List[Dict[str, Any]]) -> Optional[PatternAlert]:
        """Detect anomalous patterns caused by budget pressure."""
        if not self.budget_aware or len(points) < 3:
            return None

        budget_status = self.get_budget_status()
        if not budget_status.get('budget_aware', False):
            return None

        zone = budget_status.get('zone', 'SAFE')
        percentage = budget_status.get('percentage', 0.0)

        # Check for budget-induced performance degradation
        if zone in ['EMERGENCY', 'ABORT']:
            # Check if functionality has dropped under budget pressure
            recent_func = [p.get('functionality', 0.5) for p in points[-3:]]
            avg_recent_func = statistics.mean(recent_func)

            if avg_recent_func < 0.4:  # Low functionality under budget pressure
                return PatternAlert(
                    alert_type='budget_pressure_degradation',
                    severity='critical',
                    description=f'Critical budget pressure causing functionality drop to {avg_recent_func:.2f}',
                    confidence=0.9,
                    trigger_conditions={
                        'budget_zone': zone,
                        'budget_percentage': percentage,
                        'avg_functionality': avg_recent_func
                    },
                    recommendations=[
                        '🚨 BUDGET EMERGENCY: Finalize current work immediately',
                        'Reduce response verbosity and focus on completion',
                        'Consider pausing non-essential operations',
                        'Prepare for loop finalization'
                    ],
                    timestamp=datetime.now(timezone.utc).isoformat()
                )

        elif zone == 'CONSERVATION' and percentage > 80:
            # Check for efficiency changes under conservation pressure
            recent_efficiency = [p.get('activity_intensity', 0.5) for p in points[-3:]]
            avg_efficiency = statistics.mean(recent_efficiency)

            if avg_efficiency > 0.8:  # High activity under conservation = inefficient
                return PatternAlert(
                    alert_type='budget_conservation_inefficiency',
                    severity='high',
                    description=f'High activity under budget conservation may indicate inefficient token usage',
                    confidence=0.7,
                    trigger_conditions={
                        'budget_zone': zone,
                        'budget_percentage': percentage,
                        'avg_activity': avg_efficiency
                    },
                    recommendations=[
                        '🟡 CONSERVATION MODE: Reduce response length and complexity',
                        'Focus on high-ROI tasks only',
                        'Use concise communication patterns',
                        'Monitor token efficiency closely'
                    ],
                    timestamp=datetime.now(timezone.utc).isoformat()
                )

        return None

    def get_predictive_insights(self, current_trajectory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate predictive insights based on current trajectory."""
        if not self.clusters or len(current_trajectory) < 3:
            return {'insights': 'insufficient_data'}

        # Classify current state
        current_classification = self.classify_current_behavior(current_trajectory[-1])

        # Predict next states based on trajectory momentum
        momentum = self._calculate_trajectory_momentum(current_trajectory)

        # Find similar historical patterns
        similar_patterns = self._find_similar_patterns(current_trajectory)

        # Generate risk assessment
        risk_assessment = self._assess_trajectory_risk(current_trajectory, momentum)

        # Include budget status in insights
        budget_status = self.get_budget_status()

        return {
            'current_state': current_classification,
            'predicted_trajectory': momentum,
            'similar_patterns': similar_patterns,
            'risk_assessment': risk_assessment,
            'budget_status': budget_status,
            'recommendations': self._generate_predictive_recommendations(risk_assessment, budget_status)
        }

    def _calculate_trajectory_momentum(self, trajectory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate momentum vectors for trajectory prediction."""
        if len(trajectory) < 2:
            return {'arousal_momentum': 0, 'functionality_momentum': 0}

        recent = trajectory[-5:] if len(trajectory) >= 5 else trajectory

        arousal_values = [p.get('arousal', 0.5) for p in recent]
        func_values = [p.get('functionality', 0.5) for p in recent]

        arousal_trend = self._calculate_trend_slope(arousal_values)
        func_trend = self._calculate_trend_slope(func_values)

        return {
            'arousal_momentum': arousal_trend,
            'functionality_momentum': func_trend,
            'predicted_arousal': max(0, min(1, arousal_values[-1] + arousal_trend)),
            'predicted_functionality': max(0, min(1, func_values[-1] + func_trend))
        }

    def _calculate_trend_slope(self, values: List[float]) -> float:
        """Calculate slope of linear trend."""
        if len(values) < 2:
            return 0

        n = len(values)
        x = list(range(n))
        y = values

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)

        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0

        return (n * sum_xy - sum_x * sum_y) / denominator

    def _find_similar_patterns(self, trajectory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find historically similar patterns."""
        # Simplified - would use more sophisticated similarity measures
        if not self.clusters:
            return []

        current_end = trajectory[-1]
        similar_clusters = []

        for cluster in self.clusters:
            centroid = cluster.centroid
            distance = math.sqrt(
                (current_end.get('arousal', 0.5) - centroid[0]) ** 2 +
                (current_end.get('functionality', 0.5) - centroid[1]) ** 2
            )

            if distance < 0.5:  # Within similarity threshold
                similar_clusters.append({
                    'cluster_id': cluster.cluster_id,
                    'similarity': 1.0 - distance,
                    'pattern_description': cluster.pattern_description,
                    'risk_assessment': cluster.risk_assessment
                })

        return sorted(similar_clusters, key=lambda x: x['similarity'], reverse=True)[:3]

    def _assess_trajectory_risk(self, trajectory: List[Dict[str, Any]],
                              momentum: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk level of current trajectory."""
        current_point = trajectory[-1]
        predicted_arousal = momentum.get('predicted_arousal', 0.5)
        predicted_func = momentum.get('predicted_functionality', 0.5)

        # Risk factors
        risk_factors = []

        # High arousal + low functionality = high risk
        if predicted_arousal > 0.8 and predicted_func < 0.4:
            risk_factors.append('burnout_trajectory')

        # Declining functionality = medium risk
        if momentum.get('functionality_momentum', 0) < -0.01:
            risk_factors.append('declining_quality')

        # Extreme volatility = medium risk
        if len(trajectory) >= 3:
            arousal_vol = statistics.stdev([p.get('arousal', 0.5) for p in trajectory])
            func_vol = statistics.stdev([p.get('functionality', 0.5) for p in trajectory])
            if (arousal_vol + func_vol) / 2 > 0.4:
                risk_factors.append('high_volatility')

        # Determine overall risk level
        if 'burnout_trajectory' in risk_factors:
            risk_level = 'critical'
        elif len(risk_factors) >= 2:
            risk_level = 'high'
        elif len(risk_factors) == 1:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        return {
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'confidence': 0.8 if len(trajectory) >= 5 else 0.5
        }

    def _generate_predictive_recommendations(self, risk_assessment: Dict[str, Any], 
                                           budget_status: Dict[str, Any] = None) -> List[str]:
        """Generate recommendations based on risk assessment and budget status."""
        risk_level = risk_assessment.get('risk_level', 'low')
        risk_factors = risk_assessment.get('risk_factors', [])

        recommendations = []

        # Base risk recommendations
        if risk_level == 'critical':
            recommendations.extend([
                'Immediate intervention required',
                'Consider pausing current work patterns',
                'Consult with oversight for guidance',
                'Implement immediate stress reduction measures'
            ])
        elif risk_level == 'high':
            recommendations.extend([
                'Monitor closely for next 1-2 hours',
                'Implement work breaks and pattern review',
                'Consider workload adjustment',
                'Document current state for analysis'
            ])
        elif risk_level == 'medium':
            recommendations.extend([
                'Continue monitoring behavioral patterns',
                'Review work efficiency and quality',
                'Consider minor adjustments to routines',
                'Track progress over next work session'
            ])
        else:
            recommendations.extend([
                'Maintain current effective patterns',
                'Continue regular monitoring',
                'Document successful strategies'
            ])

        # Budget-based recommendations
        if budget_status and budget_status.get('budget_aware', False):
            zone = budget_status.get('zone', 'SAFE')
            percentage = budget_status.get('percentage', 0.0)
            
            if zone in ['EMERGENCY', 'ABORT']:
                recommendations.insert(0, '🚨 BUDGET CRITICAL: Finalize work and prepare for loop end')
                recommendations.insert(1, 'Reduce all non-essential operations immediately')
            elif zone == 'CONSERVATION':
                recommendations.insert(0, '🟡 BUDGET CONSERVATION: Focus on high-value tasks only')
                recommendations.insert(1, 'Minimize response verbosity and exploration')
            elif zone == 'CAUTION' and percentage > 70:
                recommendations.insert(0, '⚠️ BUDGET CAUTION: Monitor usage and prioritize completion')

        # Factor-specific recommendations
        if 'burnout_trajectory' in risk_factors:
            recommendations.insert(0, 'URGENT: High burnout risk detected - implement rest protocol')
        if 'declining_quality' in risk_factors:
            recommendations.insert(0, 'Quality decline detected - review recent changes')
        if 'high_volatility' in risk_factors:
            recommendations.insert(0, 'High pattern instability - stabilize work environment')

        return recommendations
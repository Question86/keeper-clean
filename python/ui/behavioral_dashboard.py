#!/usr/bin/env python3
"""
Behavioral Dashboard

Web interface for real-time behavioral monitoring and analytics.
Integrates with loop cockpit for comprehensive AI state visualization.

TASK_0189: AI Behavioral Telemetry and Performance Correlation System
"""

import json
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask, render_template_string, jsonify, request
from pathlib import Path

from behavioral_telemetry_analyzer import BehavioralTelemetryAnalyzer
from analysis.quality_correlator import QualityCorrelator
from analysis.dimensional_mapper import DimensionalMapper
from analysis.pattern_recognizer import PatternRecognizer

class BehavioralDashboard:
    """Web dashboard for behavioral telemetry monitoring."""

    def __init__(self, host: str = 'localhost', port: int = 8082):
        self.host = host
        self.port = port
        self.app = Flask(__name__)

        # Initialize analysis components
        self.telemetry_analyzer = BehavioralTelemetryAnalyzer()
        self.quality_correlator = QualityCorrelator()
        self.dimensional_mapper = DimensionalMapper()
        self.pattern_recognizer = PatternRecognizer()

        # Dashboard state
        self.current_metrics = {}
        self.alert_history = []
        self.update_thread = None
        self.running = False

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes for the dashboard."""

        @self.app.route('/')
        def dashboard():
            return render_template_string(self._get_dashboard_html())

        @self.app.route('/api/behavioral-state')
        def get_behavioral_state():
            """Get current behavioral state."""
            try:
                state = self.telemetry_analyzer.get_current_behavioral_state()
                zone_name, zone = self.dimensional_mapper.get_current_zone()

                return jsonify({
                    'arousal': state.arousal,
                    'functionality': state.functionality,
                    'confidence': state.confidence,
                    'timestamp': state.timestamp,
                    'current_zone': {
                        'name': zone_name,
                        'description': zone.description,
                        'risk_level': zone.risk_level,
                        'recommendations': zone.recommendations
                    }
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/behavioral-history')
        def get_behavioral_history():
            """Get historical behavioral data."""
            try:
                hours = int(request.args.get('hours', 24))
                points = self._get_recent_behavioral_points(hours)

                return jsonify({
                    'points': [
                        {
                            'arousal': p.arousal,
                            'functionality': p.functionality,
                            'timestamp': p.timestamp,
                            'confidence': p.confidence
                        }
                        for p in points
                    ],
                    'trends': self.dimensional_mapper.analyze_trajectory_trends()
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/quality-correlations')
        def get_quality_correlations():
            """Get quality-behavior correlations."""
            try:
                correlations = self.quality_correlator.get_top_correlations()

                return jsonify({
                    'correlations': [
                        {
                            'activity_metric': c.activity_metric,
                            'quality_metric': c.quality_metric,
                            'correlation_coefficient': c.correlation_coefficient,
                            'confidence_level': c.confidence_level,
                            'trend_direction': c.trend_direction
                        }
                        for c in correlations
                    ]
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/pattern-analysis')
        def get_pattern_analysis():
            """Get pattern recognition analysis."""
            try:
                current_state = self.telemetry_analyzer.get_current_behavioral_state()
                classification = self.pattern_recognizer.classify_current_behavior({
                    'arousal': current_state.arousal,
                    'functionality': current_state.functionality,
                    'confidence': current_state.confidence,
                    'timestamp': current_state.timestamp
                })

                recent_points = self._get_recent_behavioral_points(2)
                alerts = self.pattern_recognizer.detect_anomalies([
                    {
                        'arousal': p.arousal,
                        'functionality': p.functionality,
                        'timestamp': p.timestamp
                    }
                    for p in recent_points
                ])

                return jsonify({
                    'current_classification': classification,
                    'active_alerts': [
                        {
                            'type': alert.alert_type,
                            'severity': alert.severity,
                            'description': alert.description,
                            'confidence': alert.confidence,
                            'recommendations': alert.recommendations
                        }
                        for alert in alerts
                    ],
                    'predictive_insights': self.pattern_recognizer.get_predictive_insights([
                        {
                            'arousal': p.arousal,
                            'functionality': p.functionality,
                            'timestamp': p.timestamp
                        }
                        for p in recent_points
                    ])
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/zone-statistics')
        def get_zone_statistics():
            """Get statistics about behavioral zones."""
            try:
                return jsonify(self.dimensional_mapper.get_zone_statistics())
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    def _get_recent_behavioral_points(self, hours: int) -> List[Any]:
        """Get recent behavioral points for analysis."""
        # This would integrate with the dimensional mapper's trajectory
        # For now, return mock data based on current analysis
        points = []

        # Get current state and extrapolate recent history
        current = self.telemetry_analyzer.get_current_behavioral_state()

        # Create synthetic recent points (would be replaced with actual historical data)
        base_time = datetime.fromisoformat(current.timestamp.replace('Z', '+00:00'))

        for i in range(min(hours * 2, 10)):  # Up to 10 points
            point_time = base_time - timedelta(minutes=i * 15)
            # Add some variation for realistic data
            variation = (i % 3 - 1) * 0.1
            point = type('Point', (), {
                'arousal': max(0, min(1, current.arousal + variation)),
                'functionality': max(0, min(1, current.functionality + variation * 0.5)),
                'timestamp': point_time.isoformat(),
                'confidence': current.confidence * (0.9 ** i)  # Decreasing confidence
            })()
            points.append(point)

        return list(reversed(points))  # Most recent first

    def _get_dashboard_html(self) -> str:
        """Get the HTML template for the behavioral dashboard."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Behavioral Telemetry Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #007acc;
            padding-bottom: 20px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #007acc;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #007acc;
        }
        .metric-label {
            color: #666;
            margin-top: 5px;
        }
        .chart-container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .alerts-section {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .alert {
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
            border-left: 4px solid;
        }
        .alert-high { border-left-color: #dc3545; background: #f8d7da; }
        .alert-medium { border-left-color: #ffc107; background: #fff3cd; }
        .alert-low { border-left-color: #17a2b8; background: #d1ecf1; }
        .zone-indicator {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .zone-optimal { background: #d4edda; color: #155724; }
        .zone-warning { background: #fff3cd; color: #856404; }
        .zone-critical { background: #f8d7da; color: #721c24; }
        .recommendations {
            background: #e7f3ff;
            border: 1px solid #b3d7ff;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }
        .recommendations ul {
            margin: 0;
            padding-left: 20px;
        }
        .recommendations li {
            margin: 5px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Behavioral Telemetry Dashboard</h1>
            <p>Real-time monitoring of AI behavioral patterns and performance correlations</p>
            <div id="current-zone" class="zone-indicator zone-optimal">Loading...</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="arousal-value">--</div>
                <div class="metric-label">Arousal Level</div>
                <div style="font-size: 0.8em; color: #888; margin-top: 5px;">Activity Intensity (0-1)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="functionality-value">--</div>
                <div class="metric-label">Functionality Level</div>
                <div style="font-size: 0.8em; color: #888; margin-top: 5px;">Task Completion Quality (0-1)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="confidence-value">--%</div>
                <div class="metric-label">Confidence Score</div>
                <div style="font-size: 0.8em; color: #888; margin-top: 5px;">Analysis Reliability</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="correlation-count">--</div>
                <div class="metric-label">Active Correlations</div>
                <div style="font-size: 0.8em; color: #888; margin-top: 5px;">Quality-Behavior Links</div>
            </div>
        </div>

        <div class="chart-container">
            <h3>Behavioral Trajectory (Last 24 Hours)</h3>
            <canvas id="trajectoryChart" width="400" height="200"></canvas>
        </div>

        <div class="chart-container">
            <h3>Quality Correlations</h3>
            <canvas id="correlationChart" width="400" height="200"></canvas>
        </div>

        <div id="alerts-section" class="alerts-section" style="display: none;">
            <h3>⚠️ Active Alerts</h3>
            <div id="alerts-container"></div>
        </div>

        <div id="recommendations-section" class="recommendations" style="display: none;">
            <h3>💡 Current Recommendations</h3>
            <ul id="recommendations-list"></ul>
        </div>
    </div>

    <script>
        let trajectoryChart = null;
        let correlationChart = null;

        async function updateDashboard() {
            try {
                // Update behavioral state
                const stateResponse = await fetch('/api/behavioral-state');
                const stateData = await stateResponse.json();

                document.getElementById('arousal-value').textContent = stateData.arousal.toFixed(2);
                document.getElementById('functionality-value').textContent = stateData.functionality.toFixed(2);
                document.getElementById('confidence-value').textContent = (stateData.confidence * 100).toFixed(0) + '%';

                // Update zone indicator
                const zoneElement = document.getElementById('current-zone');
                zoneElement.textContent = stateData.current_zone.name;
                zoneElement.className = `zone-indicator zone-${stateData.current_zone.risk_level.toLowerCase()}`;

                // Update recommendations
                if (stateData.current_zone.recommendations && stateData.current_zone.recommendations.length > 0) {
                    const recSection = document.getElementById('recommendations-section');
                    const recList = document.getElementById('recommendations-list');
                    recList.innerHTML = stateData.current_zone.recommendations.map(rec => `<li>${rec}</li>`).join('');
                    recSection.style.display = 'block';
                }

                // Update trajectory chart
                const historyResponse = await fetch('/api/behavioral-history');
                const historyData = await historyResponse.json();

                updateTrajectoryChart(historyData.points);

                // Update correlation chart
                const correlationResponse = await fetch('/api/quality-correlations');
                const correlationData = await correlationResponse.json();

                document.getElementById('correlation-count').textContent = correlationData.correlations.length;
                updateCorrelationChart(correlationData.correlations);

                // Update pattern analysis and alerts
                const patternResponse = await fetch('/api/pattern-analysis');
                const patternData = await patternResponse.json();

                updateAlerts(patternData.active_alerts);

            } catch (error) {
                console.error('Dashboard update error:', error);
            }
        }

        function updateTrajectoryChart(points) {
            const ctx = document.getElementById('trajectoryChart').getContext('2d');

            if (trajectoryChart) {
                trajectoryChart.destroy();
            }

            trajectoryChart = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Behavioral Points',
                        data: points.map(p => ({
                            x: p.arousal,
                            y: p.functionality
                        })),
                        backgroundColor: 'rgba(0, 122, 204, 0.6)',
                        borderColor: 'rgba(0, 122, 204, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            title: { display: true, text: 'Arousal (Activity Level)' },
                            min: 0,
                            max: 1
                        },
                        y: {
                            title: { display: true, text: 'Functionality (Quality)' },
                            min: 0,
                            max: 1
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }

        function updateCorrelationChart(correlations) {
            const ctx = document.getElementById('correlationChart').getContext('2d');

            if (correlationChart) {
                correlationChart.destroy();
            }

            correlationChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: correlations.map(c => `${c.activity_metric} → ${c.quality_metric}`),
                    datasets: [{
                        label: 'Correlation Strength',
                        data: correlations.map(c => c.correlation_coefficient),
                        backgroundColor: correlations.map(c =>
                            c.correlation_coefficient > 0 ? 'rgba(40, 167, 69, 0.6)' : 'rgba(220, 53, 69, 0.6)'
                        ),
                        borderColor: correlations.map(c =>
                            c.correlation_coefficient > 0 ? 'rgba(40, 167, 69, 1)' : 'rgba(220, 53, 69, 1)'
                        ),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            title: { display: true, text: 'Correlation Coefficient' },
                            min: -1,
                            max: 1
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }

        function updateAlerts(alerts) {
            const alertsSection = document.getElementById('alerts-section');
            const alertsContainer = document.getElementById('alerts-container');

            if (alerts && alerts.length > 0) {
                alertsContainer.innerHTML = alerts.map(alert => `
                    <div class="alert alert-${alert.severity.toLowerCase()}">
                        <strong>${alert.type.toUpperCase()}</strong>: ${alert.description}
                        <br><small>Confidence: ${(alert.confidence * 100).toFixed(0)}%</small>
                        ${alert.recommendations ? '<br><em>Recommendations: ' + alert.recommendations.join(', ') + '</em>' : ''}
                    </div>
                `).join('');
                alertsSection.style.display = 'block';
            } else {
                alertsSection.style.display = 'none';
            }
        }

        // Initial load
        updateDashboard();

        // Update every 30 seconds
        setInterval(updateDashboard, 30000);
    </script>
</body>
</html>
        """

    def start(self):
        """Start the behavioral dashboard server."""
        if self.running:
            return

        self.running = True

        # Start background update thread
        self.update_thread = threading.Thread(target=self._background_updates, daemon=True)
        self.update_thread.start()

        # Start Flask app
        print(f"Starting Behavioral Dashboard on http://{self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)

    def stop(self):
        """Stop the behavioral dashboard server."""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)

    def _background_updates(self):
        """Background thread for periodic updates."""
        while self.running:
            try:
                # Update behavioral state
                current_state = self.telemetry_analyzer.get_current_behavioral_state()

                # Add to dimensional mapper
                self.dimensional_mapper.add_behavioral_point(
                    current_state.arousal,
                    current_state.functionality,
                    current_state.confidence
                )

                # Update quality correlations
                self.quality_correlator.correlate_activity_with_quality()

                # Check for pattern alerts
                recent_points = self._get_recent_behavioral_points(2)
                alerts = self.pattern_recognizer.detect_anomalies([
                    {
                        'arousal': p.arousal,
                        'functionality': p.functionality,
                        'timestamp': p.timestamp
                    }
                    for p in recent_points
                ])

                if alerts:
                    self.alert_history.extend(alerts)

                time.sleep(60)  # Update every minute

            except Exception as e:
                print(f"Background update error: {e}")
                time.sleep(60)

if __name__ == '__main__':
    dashboard = BehavioralDashboard()
    dashboard.start()</content>
<parameter name="filePath">d:\Keeper-Clean-Loop1\ui\behavioral_dashboard.py
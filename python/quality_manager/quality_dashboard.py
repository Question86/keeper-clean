"""
Quality Dashboard and UI Integration

This module provides web-based dashboard for quality monitoring
and integrates with the loop cockpit UI.
"""

import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template_string, jsonify, request
from collections import defaultdict

from quality_scorer import QualityScorer, QualityReportGenerator
from detection_rules import QualityIssue, IssueSeverity, IssueCategory


class QualityDashboard:
    """Web-based quality monitoring dashboard"""

    def __init__(self, config: Dict, scorer: QualityScorer, report_generator: QualityReportGenerator):
        self.config = config
        self.scorer = scorer
        self.report_generator = report_generator

        # Dashboard state
        self.current_project_score = {}
        self.current_file_scores = {}
        self.current_issues = []
        self.historical_data = []
        self.last_update = None

        # Threading
        self.update_lock = threading.Lock()
        self.monitoring_active = False
        self.monitor_thread = None

        # Callbacks
        self.update_callbacks: List[Callable] = []

        # Load existing report data on startup
        self.load_from_report()

    def update_data(self, project_score: Dict, file_scores: Dict, issues: List[QualityIssue]):
        """Update dashboard data"""
        with self.update_lock:
            self.current_project_score = project_score
            self.current_file_scores = file_scores
            self.current_issues = issues
            self.last_update = datetime.now(timezone.utc)

            # Store historical data (keep last 50 entries)
            self.historical_data.append({
                "timestamp": self.last_update.isoformat(),
                "project_score": project_score,
                "file_scores": file_scores,
                "issues_count": len(issues)
            })

            if len(self.historical_data) > 50:
                self.historical_data = self.historical_data[-50:]

        # Notify callbacks
        for callback in self.update_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Dashboard callback error: {e}")

    def load_from_report(self):
        """Load data from the latest quality report file"""
        try:
            report_path = Path("reports/quality_report.json")
            if report_path.exists():
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                # Convert JSON issues back to QualityIssue objects
                issues = []
                for issue_data in report_data.get('issues', []):
                    try:
                        issue = QualityIssue(
                            file_path=issue_data['file_path'],
                            line_number=issue_data['line_number'],
                            category=IssueCategory(issue_data['category']),
                            severity=IssueSeverity(issue_data['severity']),
                            rule_name=issue_data['rule_name'],
                            message=issue_data['message'],
                            code_snippet=issue_data.get('code_snippet', ''),  # Default empty if not in JSON
                            suggestion=issue_data.get('suggestion')
                        )
                        issues.append(issue)
                    except Exception as e:
                        print(f"Error loading issue: {e}")
                        continue
                
                # Update dashboard with loaded data
                self.update_data(
                    project_score=report_data.get('project_score', {}),
                    file_scores=report_data.get('file_scores', {}),
                    issues=issues
                )
                
                print(f"Loaded quality report data: {len(issues)} issues, score: {report_data.get('project_score', {}).get('overall_score', 'N/A')}")
            else:
                print("No quality report file found, starting with empty dashboard")
        except Exception as e:
            print(f"Error loading quality report: {e}")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        with self.update_lock:
            data = {
                "project_score": self.current_project_score,
                "file_scores": self.current_file_scores,
                "issues": [
                    {
                        "file_path": issue.file_path,
                        "line_number": issue.line_number,
                        "category": issue.category.value,
                        "severity": issue.severity.value,
                        "rule_name": issue.rule_name,
                        "message": issue.message,
                        "suggestion": issue.suggestion
                    }
                    for issue in self.current_issues
                ],
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "historical_trends": self.historical_data[-10:]  # Last 10 entries
            }
            return data

    def register_update_callback(self, callback: Callable):
        """Register callback for data updates"""
        self.update_callbacks.append(callback)

    def start_monitoring(self, update_interval: int = 300):
        """Start background monitoring thread"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(update_interval,),
            daemon=True
        )
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitoring_loop(self, interval: int):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Trigger quality scan (this would be implemented in quality_scanner)
                # For now, just sleep
                time.sleep(interval)
            except Exception as e:
                print(f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait before retry


class QualityDashboardServer:
    """Flask server for quality dashboard"""

    def __init__(self, dashboard: QualityDashboard, host: str = "127.0.0.1", port: int = 8082):
        self.dashboard = dashboard
        self.host = host
        self.port = port
        
        # Initialize Flask app
        self.app = Flask(__name__)

        # Register routes
        self._register_routes()

        # Add CORS headers
        @self.app.after_request
        def add_cors_headers(response):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response

    def _register_routes(self):
        """Register Flask routes"""

        @self.app.route("/")
        def index():
            """Main dashboard page"""
            return "Hello from Quality Dashboard!"

    def _render_dashboard_page(self) -> str:
        """Render the main dashboard HTML page"""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Quality Dashboard</title>
    <script src="/static/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .score-large { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .grade-excellent { color: #27ae60; }
        .grade-good { color: #3498db; }
        .grade-acceptable { color: #f39c12; }
        .grade-poor { color: #e74c3c; }
        .grade-critical { color: #c0392b; }
        .charts-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .chart-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .issues-table { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: bold; }
        .severity-critical { color: #c0392b; }
        .severity-high { color: #e74c3c; }
        .severity-medium { color: #f39c12; }
        .severity-low { color: #3498db; }
        .severity-info { color: #95a5a6; }
        .last-update { color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Code Quality Dashboard</h1>
            <div class="last-update" id="lastUpdate">Loading...</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Overall Score</h3>
                <div class="score-large grade-excellent" id="overallScore">--</div>
                <div id="overallGrade">--</div>
            </div>
            <div class="stat-card">
                <h3>Files Analyzed</h3>
                <div class="score-large" id="filesAnalyzed">--</div>
            </div>
            <div class="stat-card">
                <h3>Total Issues</h3>
                <div class="score-large" id="totalIssues">--</div>
            </div>
            <div class="stat-card">
                <h3>Critical Issues</h3>
                <div class="score-large severity-critical" id="criticalIssues">--</div>
            </div>
        </div>

        <div class="charts-container">
            <div class="chart-card">
                <h3>Quality Distribution</h3>
                <canvas id="qualityChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Issues by Category</h3>
                <canvas id="categoryChart"></canvas>
            </div>
        </div>

        <div class="issues-table">
            <h3>Recent Issues</h3>
            <table id="issuesTable">
                <thead>
                    <tr>
                        <th>File</th>
                        <th>Line</th>
                        <th>Severity</th>
                        <th>Category</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody id="issuesTableBody">
                    <tr><td colspan="5">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let qualityChart, categoryChart;

        async function updateDashboard() {
            try {
                const response = await fetch('/api/quality');
                const data = await response.json();

                // Update stats
                document.getElementById('overallScore').textContent = data.project_score.overall_score || '--';
                document.getElementById('overallGrade').textContent = (data.project_score.grade || '--').toUpperCase();
                document.getElementById('filesAnalyzed').textContent = data.project_score.files_analyzed || '--';
                document.getElementById('totalIssues').textContent = data.issues.length || '--';

                const criticalIssues = data.issues.filter(i => i.severity === 'critical').length;
                document.getElementById('criticalIssues').textContent = criticalIssues;

                // Update grade color
                const gradeElement = document.getElementById('overallScore');
                gradeElement.className = 'score-large grade-' + (data.project_score.grade || 'excellent');

                // Update last update
                if (data.last_update) {
                    const date = new Date(data.last_update);
                    document.getElementById('lastUpdate').textContent =
                        'Last updated: ' + date.toLocaleString();
                }

                // Update charts
                updateCharts(data);

                // Update issues table
                updateIssuesTable(data.issues.slice(0, 20)); // Show first 20 issues

            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }

        function updateCharts(data) {
            // Quality distribution chart
            const gradeData = data.project_score.files_by_grade || {};
            if (qualityChart) qualityChart.destroy();
            qualityChart = new Chart(document.getElementById('qualityChart'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(gradeData),
                    datasets: [{
                        data: Object.values(gradeData),
                        backgroundColor: ['#27ae60', '#3498db', '#f39c12', '#e74c3c', '#c0392b']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });

            // Issues by category chart
            const categoryCounts = {};
            data.issues.forEach(issue => {
                categoryCounts[issue.category] = (categoryCounts[issue.category] || 0) + 1;
            });

            if (categoryChart) categoryChart.destroy();
            categoryChart = new Chart(document.getElementById('categoryChart'), {
                type: 'bar',
                data: {
                    labels: Object.keys(categoryCounts),
                    datasets: [{
                        label: 'Issues',
                        data: Object.values(categoryCounts),
                        backgroundColor: '#3498db'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }

        function updateIssuesTable(issues) {
            const tbody = document.getElementById('issuesTableBody');
            tbody.innerHTML = '';

            if (issues.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No issues found</td></tr>';
                return;
            }

            issues.forEach(issue => {
                const row = document.createElement('tr');

                const fileCell = document.createElement('td');
                fileCell.textContent = issue.file_path.split('/').pop().split('\\\\').pop();
                row.appendChild(fileCell);

                const lineCell = document.createElement('td');
                lineCell.textContent = issue.line_number;
                row.appendChild(lineCell);

                const severityCell = document.createElement('td');
                severityCell.textContent = issue.severity;
                severityCell.className = 'severity-' + issue.severity;
                row.appendChild(severityCell);

                const categoryCell = document.createElement('td');
                categoryCell.textContent = issue.category.replace(/_/g, ' ');
                row.appendChild(categoryCell);

                const messageCell = document.createElement('td');
                messageCell.textContent = issue.message;
                row.appendChild(messageCell);

                tbody.appendChild(row);
            });
        }

        // Update dashboard every 30 seconds
        updateDashboard();
        setInterval(updateDashboard, 30000);
    </script>
</body>
</html>
        """
        return html_template

    def run(self, debug: bool = False):
        """Start the Flask server"""
        print(f"Starting Quality Dashboard on http://{self.host}:{self.port}")
        try:
            print("DEBUG: About to call app.run()")
            self.app.run(host='127.0.0.1', port=self.port, debug=True, use_reloader=False, threaded=False)
            print("DEBUG: app.run() completed normally")
        except Exception as e:
            print(f"DEBUG: Exception in app.run(): {e}")
            import traceback
            traceback.print_exc()
            raise


def create_quality_dashboard(config: Dict) -> QualityDashboard:
    """Factory function to create quality dashboard"""
    scorer = QualityScorer(config)
    report_generator = QualityReportGenerator(scorer)
    dashboard = QualityDashboard(config, scorer, report_generator)
    return dashboard


def start_dashboard_server(dashboard: QualityDashboard, host: str = "localhost", port: int = 8081):
    """Start the dashboard web server"""
    server = QualityDashboardServer(dashboard, host, port)

    # Start in background thread
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    return server
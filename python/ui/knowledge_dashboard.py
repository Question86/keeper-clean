#!/usr/bin/env python3
"""
Knowledge Dashboard

Web-based dashboard for monitoring knowledge health and audit results.
"""

import json
import webbrowser
import sys
import os
from datetime import datetime
from typing import Dict, List

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from knowledge_health_monitor import KnowledgeHealthMonitor
from update_reminder_engine import UpdateReminderEngine
from autonomous_audit_system import AutonomousAuditSystem

class KnowledgeDashboard:
    """
    Web dashboard for knowledge health monitoring.
    """

    def __init__(self, db_path: str = "keeper_knowledge.db"):
        self.db_path = db_path
        self.monitor = KnowledgeHealthMonitor(db_path)
        self.reminder_engine = UpdateReminderEngine(db_path)
        self.auditor = AutonomousAuditSystem(db_path)

    def generate_dashboard_html(self) -> str:
        """
        Generate HTML dashboard.
        """
        # Get current data
        health_report = self.monitor.generate_health_report()
        reminders = self.reminder_engine.generate_reminders()
        audit_results = self.auditor.perform_full_audit()

        # Create HTML
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Health Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .metric-card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .status-good {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-critical {{ color: #e74c3c; }}
        .chart-container {{ height: 300px; margin: 20px 0; }}
        .reminder-list {{ max-height: 400px; overflow-y: auto; }}
        .reminder-item {{ padding: 10px; margin: 5px 0; border-left: 4px solid; border-radius: 4px; }}
        .reminder-high {{ border-color: #e74c3c; background: #fdf2f2; }}
        .reminder-medium {{ border-color: #f39c12; background: #fdf9f2; }}
        .reminder-low {{ border-color: #27ae60; background: #f2fdf2; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Knowledge Health Dashboard</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        {self._generate_overview_section(health_report, audit_results)}

        {self._generate_health_metrics_section(health_report)}

        {self._generate_reminders_section(reminders)}

        {self._generate_audit_section(audit_results)}

        {self._generate_category_analysis_section(audit_results)}
    </div>

    <script>
        // Simple refresh functionality
        function refreshDashboard() {{
            location.reload();
        }}

        // Auto-refresh every 5 minutes
        setInterval(refreshDashboard, 300000);
    </script>
</body>
</html>
        """

        return html

    def _generate_overview_section(self, health_report: str, audit_results: Dict) -> str:
        """Generate overview section."""
        # Parse health report for key metrics
        lines = health_report.split('\n')
        total_items = "0"
        health_score = "0.0"

        for line in lines:
            if "Total Knowledge Items:" in line:
                total_items = line.split(": ")[1]
            elif "Overall Health Score:" in line:
                health_score = line.split(": ")[1].split("/")[0]

        avg_quality = f"{audit_results.get('quality_scores', {}) and sum(scores['overall'] for scores in audit_results['quality_scores'].values()) / len(audit_results['quality_scores']):.2f}" if audit_results.get('quality_scores') else "0.00"

        return f"""
        <div class="metric-grid">
            <div class="metric-card">
                <h3>📊 Knowledge Overview</h3>
                <p><strong>Total Items:</strong> {total_items}</p>
                <p><strong>Health Score:</strong> <span class="status-{'good' if float(health_score) > 80 else 'warning' if float(health_score) > 60 else 'critical'}">{health_score}/100</span></p>
                <p><strong>Average Quality:</strong> {avg_quality}/1.0</p>
            </div>

            <div class="metric-card">
                <h3>🔍 Audit Summary</h3>
                <p><strong>Gaps Identified:</strong> {len(audit_results.get('gaps_identified', []))}</p>
                <p><strong>Recommendations:</strong> {len(audit_results.get('recommendations', []))}</p>
                <p><strong>Cross-references:</strong> {len(audit_results.get('cross_references', {}).get('references', {}))}</p>
            </div>

            <div class="metric-card">
                <h3>⏰ Active Reminders</h3>
                <p><strong>High Priority:</strong> {len([r for r in self.reminder_engine.generate_reminders() if r['priority'] == 'high'])}</p>
                <p><strong>Medium Priority:</strong> {len([r for r in self.reminder_engine.generate_reminders() if r['priority'] == 'medium'])}</p>
                <p><strong>Low Priority:</strong> {len([r for r in self.reminder_engine.generate_reminders() if r['priority'] == 'low'])}</p>
            </div>
        </div>
        """

    def _generate_health_metrics_section(self, health_report: str) -> str:
        """Generate health metrics section."""
        # Extract freshness distribution from report
        lines = health_report.split('\n')
        freshness_data = {}

        for line in lines:
            if "Fresh (" in line:
                freshness_data['fresh'] = line.split(": ")[1]
            elif "Info (" in line:
                freshness_data['info'] = line.split(": ")[1]
            elif "Warning (" in line:
                freshness_data['warning'] = line.split(": ")[1]
            elif "Critical (" in line:
                freshness_data['critical'] = line.split(": ")[1]

        return f"""
        <div class="metric-card">
            <h3>📈 Knowledge Freshness Distribution</h3>
            <div style="display: flex; justify-content: space-around; margin: 20px 0;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; color: #27ae60;">{freshness_data.get('fresh', '0')}</div>
                    <div>Fresh</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; color: #3498db;">{freshness_data.get('info', '0')}</div>
                    <div>Info</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; color: #f39c12;">{freshness_data.get('warning', '0')}</div>
                    <div>Warning</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; color: #e74c3c;">{freshness_data.get('critical', '0')}</div>
                    <div>Critical</div>
                </div>
            </div>
        </div>
        """

    def _generate_reminders_section(self, reminders: List[Dict]) -> str:
        """Generate reminders section."""
        reminder_html = ""
        for reminder in reminders[:10]:  # Show top 10
            priority_class = f"reminder-{reminder['priority']}"
            reminder_html += f"""
            <div class="reminder-item {priority_class}">
                <strong>{reminder['title']}</strong><br>
                <small>{reminder['description']}</small><br>
                <em>Due: {reminder.get('due_date', 'ASAP')}</em>
            </div>
            """

        return f"""
        <div class="metric-card">
            <h3>🔔 Active Reminders</h3>
            <div class="reminder-list">
                {reminder_html if reminder_html else '<p>No active reminders</p>'}
            </div>
        </div>
        """

    def _generate_audit_section(self, audit_results: Dict) -> str:
        """Generate audit results section."""
        gaps_html = ""
        for gap in audit_results.get('gaps_identified', [])[:5]:
            severity_color = {'high': '#e74c3c', 'medium': '#f39c12', 'low': '#27ae60'}[gap['severity']]
            gaps_html += f"""
            <tr>
                <td style="color: {severity_color};">{gap['severity'].upper()}</td>
                <td>{gap['type'].replace('_', ' ').title()}</td>
                <td>{gap['description']}</td>
            </tr>
            """

        return f"""
        <div class="metric-card">
            <h3>🔍 Audit Findings</h3>
            <table>
                <thead>
                    <tr>
                        <th>Severity</th>
                        <th>Type</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {gaps_html if gaps_html else '<tr><td colspan="3">No gaps identified</td></tr>'}
                </tbody>
            </table>
        </div>
        """

    def _generate_category_analysis_section(self, audit_results: Dict) -> str:
        """Generate category analysis section."""
        category_html = ""
        for cat, analysis in list(audit_results.get('category_analysis', {}).items())[:8]:  # Top 8
            quality_color = '#27ae60' if analysis['avg_quality'] > 0.7 else '#f39c12' if analysis['avg_quality'] > 0.5 else '#e74c3c'
            category_html += f"""
            <tr>
                <td>{cat}</td>
                <td>{analysis['count']}</td>
                <td style="color: {quality_color};">{analysis['avg_quality']:.2f}</td>
                <td>{len(analysis['tags'])}</td>
            </tr>
            """

        return f"""
        <div class="metric-card">
            <h3>📂 Category Analysis</h3>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Items</th>
                        <th>Avg Quality</th>
                        <th>Tags</th>
                    </tr>
                </thead>
                <tbody>
                    {category_html}
                </tbody>
            </table>
        </div>
        """

    def open_dashboard(self):
        """
        Generate and open the dashboard in browser.
        """
        html_content = self.generate_dashboard_html()

        # Save to temporary file
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_file = f.name

        # Open in browser
        webbrowser.open(f'file://{temp_file}')

        print(f"Dashboard opened in browser. Temporary file: {temp_file}")
        return temp_file

    def export_dashboard_data(self) -> Dict:
        """
        Export dashboard data as JSON.
        """
        return {
            'health_report': self.monitor.generate_health_report(),
            'reminders': self.reminder_engine.generate_reminders(),
            'audit_results': self.auditor.perform_full_audit(),
            'generated_at': datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Example usage
    dashboard = KnowledgeDashboard()

    # Export data
    data = dashboard.export_dashboard_data()
    print(f"Dashboard data exported with {len(data['reminders'])} reminders")

    # Generate HTML (without opening browser for testing)
    html = dashboard.generate_dashboard_html()
    print(f"Dashboard HTML generated: {len(html)} characters")

    # Save to file for inspection
    with open('dashboard_test.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Dashboard saved to dashboard_test.html")
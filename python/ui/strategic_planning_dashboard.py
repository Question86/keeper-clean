#!/usr/bin/env python3
"""
Strategic Planning Dashboard

Web-based dashboard for strategic task planning and knowledge analysis.
"""

import json
import webbrowser
import sys
import os
from datetime import datetime
from typing import Dict, List

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from knowledge_dependency_analyzer import KnowledgeDependencyAnalyzer
from strategic_task_planner import StrategicTaskPlanner

class StrategicPlanningDashboard:
    """
    Dashboard for strategic planning insights and task recommendations.
    """

    def __init__(self, db_path: str = "keeper_knowledge.db"):
        self.db_path = db_path
        self.analyzer = KnowledgeDependencyAnalyzer(db_path)
        self.planner = StrategicTaskPlanner(db_path)

    def generate_dashboard_html(self) -> str:
        """
        Generate comprehensive planning dashboard.
        """
        # Get all analysis data
        landscape = self.analyzer.analyze_knowledge_landscape()
        recommendations = self.planner.generate_task_recommendations()
        dependencies = self.planner.analyze_task_dependencies(recommendations)

        # Create HTML dashboard
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strategic Planning Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 2.5em; font-weight: 300; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; font-size: 1.1em; }}
        .dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; padding: 30px; }}
        .metric-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); transition: transform 0.2s; }}
        .metric-card:hover {{ transform: translateY(-2px); }}
        .metric-card h3 {{ margin: 0 0 15px 0; color: #2c3e50; font-size: 1.2em; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #3498db; margin: 10px 0; }}
        .status-good {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-critical {{ color: #e74c3c; }}
        .recommendations-list {{ max-height: 500px; overflow-y: auto; }}
        .recommendation-item {{ padding: 15px; margin: 8px 0; border-left: 4px solid; border-radius: 6px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .rec-high {{ border-color: #e74c3c; background: linear-gradient(90deg, #ffeaea 0%, #ffffff 100%); }}
        .rec-medium {{ border-color: #f39c12; background: linear-gradient(90deg, #fff8e1 0%, #ffffff 100%); }}
        .rec-low {{ border-color: #27ae60; background: linear-gradient(90deg, #e8f5e8 0%, #ffffff 100%); }}
        .rec-title {{ font-weight: bold; margin-bottom: 5px; }}
        .rec-meta {{ font-size: 0.9em; color: #7f8c8d; margin-bottom: 8px; }}
        .progress-bar {{ width: 100%; height: 8px; background: #ecf0f1; border-radius: 4px; overflow: hidden; margin: 10px 0; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #3498db 0%, #2980b9 100%); transition: width 0.3s; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        th, td {{ padding: 12px 15px; text-align: left; }}
        th {{ background: #34495e; color: white; font-weight: 600; }}
        tr:nth-child(even) {{ background: #f8f9fa; }}
        .chart-container {{ height: 300px; margin: 20px 0; position: relative; }}
        .dependency-flow {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .execution-path {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; }}
        .path-step {{ background: #3498db; color: white; padding: 8px 12px; border-radius: 20px; font-size: 0.9em; }}
        .insights-section {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; margin: 20px 0; border-radius: 8px; }}
        .insights-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
        .insight-card {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 6px; backdrop-filter: blur(10px); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Strategic Planning Dashboard</h1>
            <p>Knowledge-Driven Task Planning & Future Readiness Analysis</p>
            <p style="font-size: 0.9em; opacity: 0.8;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        {self._generate_overview_section(landscape, recommendations)}

        {self._generate_knowledge_landscape_section(landscape)}

        {self._generate_recommendations_section(recommendations)}

        {self._generate_dependency_section(dependencies)}

        {self._generate_insights_section(landscape, recommendations)}
    </div>

    <script>
        // Auto-refresh every 5 minutes
        setInterval(() => {{
            if (confirm('Refresh dashboard with latest data?')) {{
                location.reload();
            }}
        }}, 300000);

        // Add some interactivity
        document.addEventListener('DOMContentLoaded', function() {{
            // Animate progress bars
            const progressBars = document.querySelectorAll('.progress-fill');
            progressBars.forEach(bar => {{
                const width = bar.style.width;
                bar.style.width = '0%';
                setTimeout(() => {{
                    bar.style.width = width;
                }}, 500);
            }});
        }});
    </script>
</body>
</html>
        """

        return html

    def _generate_overview_section(self, landscape: Dict, recommendations: List[Dict]) -> str:
        """Generate overview metrics section."""
        total_items = landscape['total_items']
        avg_readiness = sum(score['overall_score'] for score in landscape['readiness_scores'].values()) / len(landscape['readiness_scores']) if landscape['readiness_scores'] else 0

        high_priority = len([r for r in recommendations if r['priority'] == 'high'])
        total_recs = len(recommendations)

        return f"""
        <div class="dashboard-grid">
            <div class="metric-card">
                <h3>📊 Knowledge Base Overview</h3>
                <div class="metric-value">{total_items}</div>
                <p>Total Knowledge Items</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(total_items / 500 * 100, 100)}%"></div>
                </div>
                <p style="font-size: 0.9em; color: #7f8c8d;">{len(landscape['categories'])} categories, {len(landscape['tags'])} unique tags</p>
            </div>

            <div class="metric-card">
                <h3>🎯 Readiness Score</h3>
                <div class="metric-value status-{'good' if avg_readiness > 0.7 else 'warning' if avg_readiness > 0.5 else 'critical'}">{avg_readiness:.2f}</div>
                <p>Overall Knowledge Readiness</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {avg_readiness * 100}%"></div>
                </div>
                <p style="font-size: 0.9em; color: #7f8c8d;">Based on {len(landscape['readiness_scores'])} categories</p>
            </div>

            <div class="metric-card">
                <h3>📋 Task Recommendations</h3>
                <div class="metric-value">{total_recs}</div>
                <p>Strategic Tasks Suggested</p>
                <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                    <span style="color: #e74c3c;">🔴 {high_priority} High</span>
                    <span style="color: #f39c12;">🟡 {len([r for r in recommendations if r['priority'] == 'medium'])} Medium</span>
                    <span style="color: #27ae60;">🟢 {len([r for r in recommendations if r['priority'] == 'low'])} Low</span>
                </div>
            </div>

            <div class="metric-card">
                <h3>🔗 Knowledge Network</h3>
                <div class="metric-value">{landscape['knowledge_graph']['nodes']}</div>
                <p>Connected Knowledge Nodes</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {landscape['knowledge_graph']['density'] * 1000}%"></div>
                </div>
                <p style="font-size: 0.9em; color: #7f8c8d;">Density: {landscape['knowledge_graph']['density']:.3f} | Components: {landscape['knowledge_graph']['connected_components']}</p>
            </div>
        </div>
        """

    def _generate_knowledge_landscape_section(self, landscape: Dict) -> str:
        """Generate knowledge landscape analysis section."""
        # Category analysis table
        category_rows = ""
        for cat, data in list(landscape['categories'].items())[:8]:  # Top 8 categories
            readiness = landscape['readiness_scores'].get(cat, {'overall_score': 0})
            category_rows += f"""
            <tr>
                <td>{cat}</td>
                <td>{data['count']}</td>
                <td>{data['avg_length']:.0f}</td>
                <td style="color: {'#27ae60' if data.get('freshness_score', 1) > 0.7 else '#f39c12' if data.get('freshness_score', 1) > 0.5 else '#e74c3c'}">{data.get('freshness_score', 0):.2f}</td>
                <td>{readiness['overall_score']:.2f}</td>
            </tr>
            """

        # Gaps summary
        gaps_summary = {}
        for gap in landscape['gaps']:
            gap_type = gap['type'].replace('_', ' ').title()
            gaps_summary[gap_type] = gaps_summary.get(gap_type, 0) + 1

        gaps_html = "".join(f"<li>{gap_type}: {count}</li>" for gap_type, count in gaps_summary.items())

        return f"""
        <div style="padding: 30px; background: #f8f9fa;">
            <h2 style="color: #2c3e50; margin-bottom: 20px;">🗺️ Knowledge Landscape Analysis</h2>

            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 30px;">
                <div>
                    <h3>Category Analysis</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Category</th>
                                <th>Items</th>
                                <th>Avg Length</th>
                                <th>Freshness</th>
                                <th>Readiness</th>
                            </tr>
                        </thead>
                        <tbody>
                            {category_rows}
                        </tbody>
                    </table>
                </div>

                <div>
                    <h3>Identified Gaps</h3>
                    <ul style="background: white; padding: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        {gaps_html if gaps_html else '<li>No significant gaps identified</li>'}
                    </ul>

                    <h3 style="margin-top: 30px;">Network Statistics</h3>
                    <div style="background: white; padding: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        <p><strong>Nodes:</strong> {landscape['knowledge_graph']['nodes']}</p>
                        <p><strong>Edges:</strong> {landscape['knowledge_graph']['edges']}</p>
                        <p><strong>Density:</strong> {landscape['knowledge_graph']['density']:.3f}</p>
                        <p><strong>Components:</strong> {landscape['knowledge_graph']['connected_components']}</p>
                        <p><strong>Clustering:</strong> {landscape['knowledge_graph']['average_clustering']:.3f}</p>
                    </div>
                </div>
            </div>
        </div>
        """

    def _generate_recommendations_section(self, recommendations: List[Dict]) -> str:
        """Generate recommendations section."""
        rec_html = ""
        for rec in recommendations[:10]:  # Show top 10
            priority_class = f"rec-{rec['priority']}"
            due_date = rec.get('scheduled_date', 'TBD')
            days_until = rec.get('days_until_due', 'TBD')

            rec_html += f"""
            <div class="recommendation-item {priority_class}">
                <div class="rec-title">{rec['title']}</div>
                <div class="rec-meta">
                    Priority: {rec['priority'].upper()} |
                    Effort: {rec['estimated_effort'].upper()} |
                    Due: {due_date} ({days_until} days)
                </div>
                <p style="margin: 8px 0; color: #555;">{rec['description']}</p>
                <p style="margin: 0; font-size: 0.9em; color: #7f8c8d;"><strong>Rationale:</strong> {rec['rationale']}</p>
                <p style="margin: 5px 0 0 0; font-size: 0.9em; color: #27ae60;"><strong>Impact:</strong> {rec.get('expected_impact', 'TBD')}</p>
            </div>
            """

        return f"""
        <div style="padding: 30px;">
            <h2 style="color: #2c3e50; margin-bottom: 20px;">🎯 Strategic Recommendations</h2>
            <div class="recommendations-list">
                {rec_html}
            </div>
            {f'<p style="text-align: center; margin-top: 20px; color: #7f8c8d;">... and {len(recommendations) - 10} more recommendations</p>' if len(recommendations) > 10 else ''}
        </div>
        """

    def _generate_dependency_section(self, dependencies: Dict) -> str:
        """Generate task dependency analysis section."""
        execution_order = dependencies['execution_order']
        parallel_groups = dependencies['parallel_groups']
        critical_path = dependencies['critical_path']

        # Execution order visualization
        order_html = ""
        for i, task_id in enumerate(execution_order[:15]):  # Show first 15
            task = dependencies['dependency_graph'][task_id]['task']
            order_html += f'<div class="path-step">#{i+1} {task["title"][:30]}...</div>'

        # Parallel groups
        groups_html = ""
        for i, group in enumerate(parallel_groups[:3]):  # Show first 3 groups
            group_tasks = [dependencies['dependency_graph'][tid]['task']['title'][:25] + '...' for tid in group[:5]]
            groups_html += f"""
            <div style="background: white; padding: 15px; margin: 10px 0; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <h4>Group {i+1} ({len(group)} tasks)</h4>
                <p style="margin: 0; color: #7f8c8d;">{', '.join(group_tasks)}{'...' if len(group) > 5 else ''}</p>
            </div>
            """

        return f"""
        <div class="dependency-flow">
            <h2 style="color: #2c3e50; margin-bottom: 20px;">🔄 Task Dependencies & Execution</h2>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                <div>
                    <h3>Execution Order</h3>
                    <div class="execution-path">
                        {order_html}
                    </div>
                    {'<p style="color: #7f8c8d; margin-top: 15px;">... continued</p>' if len(execution_order) > 15 else ''}
                </div>

                <div>
                    <h3>Parallel Execution Groups</h3>
                    {groups_html}
                    {'<p style="color: #7f8c8d; margin-top: 15px;">... more groups available</p>' if len(parallel_groups) > 3 else ''}
                </div>
            </div>

            <div style="margin-top: 30px;">
                <h3>Critical Path ({len(critical_path)} tasks)</h3>
                <div style="background: white; padding: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <p style="margin: 0; line-height: 1.6;">
                        {' → '.join(dependencies['dependency_graph'][tid]['task']['title'][:20] + '...' for tid in critical_path)}
                    </p>
                </div>
            </div>
        </div>
        """

    def _generate_insights_section(self, landscape: Dict, recommendations: List[Dict]) -> str:
        """Generate strategic insights section."""
        # Calculate some insights
        total_items = landscape['total_items']
        categories_count = len(landscape['categories'])
        avg_category_size = total_items / categories_count if categories_count > 0 else 0

        high_priority_recs = len([r for r in recommendations if r['priority'] == 'high'])
        readiness_trend = "improving" if sum(score['overall_score'] for score in landscape['readiness_scores'].values()) / len(landscape['readiness_scores']) > 0.6 else "needs_attention"

        insights = [
            {
                'title': 'Knowledge Scale',
                'value': f"{total_items} items",
                'description': f"Across {categories_count} categories (avg {avg_category_size:.1f} items each)"
            },
            {
                'title': 'Immediate Actions',
                'value': f"{high_priority_recs} tasks",
                'description': 'High-priority recommendations requiring immediate attention'
            },
            {
                'title': 'Readiness Trend',
                'value': readiness_trend.title(),
                'description': 'Overall knowledge readiness assessment'
            },
            {
                'title': 'Network Health',
                'value': f"{landscape['knowledge_graph']['density']:.3f}",
                'description': 'Knowledge connectivity density (higher is better)'
            }
        ]

        insights_html = ""
        for insight in insights:
            insights_html += f"""
            <div class="insight-card">
                <h4>{insight['title']}</h4>
                <div style="font-size: 1.5em; font-weight: bold; margin: 10px 0;">{insight['value']}</div>
                <p style="margin: 0; opacity: 0.9;">{insight['description']}</p>
            </div>
            """

        return f"""
        <div class="insights-section">
            <h2 style="margin: 0 0 20px 0;">💡 Strategic Insights</h2>
            <div class="insights-grid">
                {insights_html}
            </div>
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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_file = f.name

        # Open in browser
        webbrowser.open(f'file://{temp_file}')

        print(f"Strategic Planning Dashboard opened in browser. Temporary file: {temp_file}")
        return temp_file

    def export_dashboard_data(self) -> Dict:
        """
        Export dashboard data as JSON.
        """
        landscape = self.analyzer.analyze_knowledge_landscape()
        recommendations = self.planner.generate_task_recommendations()
        dependencies = self.planner.analyze_task_dependencies(recommendations)

        return {
            'landscape': landscape,
            'recommendations': recommendations,
            'dependencies': dependencies,
            'generated_at': datetime.now().isoformat()
        }


if __name__ == "__main__":
    dashboard = StrategicPlanningDashboard()

    # Export data
    data = dashboard.export_dashboard_data()
    print(f"Dashboard data exported: {len(data['recommendations'])} recommendations")

    # Generate HTML
    html = dashboard.generate_dashboard_html()
    print(f"Dashboard HTML generated: {len(html)} characters")

    # Save for inspection
    with open('strategic_planning_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Dashboard saved to strategic_planning_dashboard.html")
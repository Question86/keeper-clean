# MODE: SCRIPT

'''Advanced AI Patterns UI Integration

Flask routes and UI components for controlling the advanced AI patterns:
- Swarm Coordinator (Queen control, worker monitoring)
- Token Monitor (Budget tracking, usage analytics)
- Event Mesh (Workflow orchestration, agent communication)

Integrates with the existing loop_cockpit.py Flask application.
'''

from flask import Blueprint, jsonify, request, render_template_string
from typing import Dict, Any, Optional
import json
from datetime import datetime, timezone

from advanced_ai_patterns import get_advanced_patterns
from swarm_coordinator import SwarmRole, TaskStatus
from pathlib import Path

# Create blueprint for advanced AI patterns
ai_patterns_bp = Blueprint('ai_patterns', __name__, url_prefix='/api/ai-patterns')

# Global instance
_patterns_instance = None

def get_patterns():
    '''Get the advanced patterns instance.'''
    global _patterns_instance
    if _patterns_instance is None:
        _patterns_instance = get_advanced_patterns()
    return _patterns_instance

# HTML Templates
SWARM_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Swarm Intelligence Dashboard</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 20px; 
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%);
            color: #e8e8e8; 
        }
        .dashboard { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
        }
        .panel { 
            background: linear-gradient(135deg, rgba(40, 40, 40, 0.95), rgba(20, 20, 20, 0.95));
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 8px 32px rgba(80, 200, 160, 0.3);
            border: 1px solid #333;
            backdrop-filter: blur(10px);
        }
        .queen-panel { 
            border-left: 4px solid #50c8a0; 
        }
        .worker-panel { 
            border-left: 4px solid #4ecdc4; 
        }
        .task-item { 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 4px; 
        }
        .task-pending { 
            background: rgba(255, 193, 7, 0.1); 
            border-left: 4px solid #ffc107; 
        }
        .task-assigned { 
            background: rgba(23, 162, 184, 0.1); 
            border-left: 4px solid #17a2b8; 
        }
        .task-completed { 
            background: rgba(40, 167, 69, 0.1); 
            border-left: 4px solid #28a745; 
        }
        .task-failed { 
            background: rgba(220, 53, 69, 0.1); 
            border-left: 4px solid #dc3545; 
        }
        .agent-item { 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 4px; 
            background: rgba(248, 249, 250, 0.1); 
            border: 1px solid #333;
        }
        .agent-active { 
            border-left: 4px solid #28a745; 
        }
        .agent-inactive { 
            border-left: 4px solid #6c757d; 
        }
        .control-btn { 
            background: linear-gradient(135deg, #50c8a0, #3ca080);
            color: #0f0f0f; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 4px; 
            cursor: pointer; 
            margin: 5px; 
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .control-btn:hover { 
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(80, 200, 160, 0.3);
        }
        .control-btn.danger { 
            background: linear-gradient(135deg, #dc3545, #c82333);
        }
        .control-btn.danger:hover { 
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
        }
        .metric { 
            font-size: 24px; 
            font-weight: bold; 
            color: #50c8a0; 
        }
        .metric-label { 
            font-size: 14px; 
            color: #999; 
            text-transform: uppercase; 
        }
        h1 {
            color: #50c8a0;
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 0 2px 4px rgba(80, 200, 160, 0.3);
        }
    </style>
</head>
<body>
    <h1>🧠 Swarm Intelligence Dashboard</h1>
    <div class="dashboard">
        <div class="panel queen-panel">
            <h2>👑 Queen Coordinator</h2>
            <div class="metric">{{ swarm_status.active_agents }}</div>
            <div class="metric-label">Active Agents</div>
            <br>
            <div class="metric">{{ swarm_status.routing_accuracy | round(1) }}%</div>
            <div class="metric-label">Routing Accuracy</div>
            <br>
            <button class="control-btn" onclick="optimizeRouting()">🎯 Optimize Routing</button>
            <button class="control-btn" onclick="refreshStatus()">🔄 Refresh Status</button>
        </div>

        <div class="panel worker-panel">
            <h2>👷 Worker Agents</h2>
            <div id="agents-list">
                {% for agent_id, agent in swarm_status.performance_stats.items() %}
                <div class="agent-item agent-{{ 'active' if agent_id in active_agent_ids else 'inactive' }}">
                    <strong>{{ agent_id }}</strong><br>
                    Role: {{ agent.role }} | Tasks: {{ agent.task_count }} | Score: {{ agent.performance_score | round(2) }}
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="panel">
            <h2>📋 Task Queue</h2>
            <div id="tasks-list">
                {% for task_id, task in tasks.items() %}
                <div class="task-item task-{{ task.status.value }}">
                    <strong>{{ task_id[:12] }}...</strong><br>
                    {{ task.description[:50] }}...<br>
                    Status: {{ task.status.value }} | Priority: {{ task.priority }}
                </div>
                {% endfor %}
            </div>
            <br>
            <button class="control-btn" onclick="showSubmitTaskModal()">➕ Submit Task</button>
        </div>

        <div class="panel">
            <h2>📊 Performance Metrics</h2>
            <div class="metric">{{ swarm_status.total_tasks }}</div>
            <div class="metric-label">Total Tasks</div>
            <br>
            <div class="metric">{{ swarm_status.completed_tasks }}</div>
            <div class="metric-label">Completed Tasks</div>
            <br>
            <div class="metric">{{ swarm_status.pending_tasks }}</div>
            <div class="metric-label">Pending Tasks</div>
        </div>
    </div>

    <!-- Task Submission Modal -->
    <div id="task-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;">
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 8px; width: 400px;">
            <h3>Submit New Task</h3>
            <form onsubmit="submitTask(event)">
                <div style="margin-bottom: 10px;">
                    <label>Description:</label><br>
                    <textarea id="task-desc" rows="3" style="width: 100%;"></textarea>
                </div>
                <div style="margin-bottom: 10px;">
                    <label>Requirements (comma-separated):</label><br>
                    <input type="text" id="task-reqs" style="width: 100%;" placeholder="python, coding, testing">
                </div>
                <div style="margin-bottom: 10px;">
                    <label>Priority:</label>
                    <select id="task-priority">
                        <option value="1">Low</option>
                        <option value="2">Medium</option>
                        <option value="3" selected>High</option>
                    </select>
                </div>
                <button type="submit" class="control-btn">Submit Task</button>
                <button type="button" class="control-btn danger" onclick="hideSubmitTaskModal()">Cancel</button>
            </form>
        </div>
    </div>

    <script>
        function refreshStatus() {
            location.reload();
        }

        function optimizeRouting() {
            fetch('/api/ai-patterns/swarm/optimize', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert('Optimization completed: ' + JSON.stringify(data, null, 2));
                    refreshStatus();
                });
        }

        function showSubmitTaskModal() {
            document.getElementById('task-modal').style.display = 'block';
        }

        function hideSubmitTaskModal() {
            document.getElementById('task-modal').style.display = 'none';
        }

        function submitTask(event) {
            event.preventDefault();
            const desc = document.getElementById('task-desc').value;
            const reqs = document.getElementById('task-reqs').value.split(',').map(r => r.trim());
            const priority = parseInt(document.getElementById('task-priority').value);

            fetch('/api/ai-patterns/swarm/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description: desc, requirements: reqs, priority: priority })
            })
            .then(response => response.json())
            .then(data => {
                alert('Task submitted: ' + data.task_id);
                hideSubmitTaskModal();
                refreshStatus();
            });
        }
    </script>
</body>
</html>
'''

TOKEN_MONITOR_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Token Budget Monitor</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 20px; 
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%);
            color: #e8e8e8; 
        }
        .dashboard { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
        }
        .panel { 
            background: linear-gradient(135deg, rgba(40, 40, 40, 0.95), rgba(20, 20, 20, 0.95));
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 8px 32px rgba(80, 200, 160, 0.3);
            border: 1px solid #333;
            backdrop-filter: blur(10px);
        }
        .budget-panel { 
            border-left: 4px solid #28a745; 
        }
        .usage-panel { 
            border-left: 4px solid #007bff; 
        }
        .alert-panel { 
            border-left: 4px solid #ffc107; 
        }
        .metric { 
            font-size: 24px; 
            font-weight: bold; 
            color: #50c8a0; 
        }
        .metric-label { 
            font-size: 14px; 
            color: #999; 
            text-transform: uppercase; 
        }
        .progress-bar { 
            width: 100%; 
            height: 20px; 
            background: rgba(233, 236, 239, 0.2); 
            border-radius: 10px; 
            overflow: hidden; 
            margin: 10px 0; 
            border: 1px solid #333;
        }
        .progress-fill { 
            height: 100%; 
            background: linear-gradient(90deg, #28a745, #20c997); 
            transition: width 0.3s; 
        }
        .progress-fill.warning { 
            background: linear-gradient(90deg, #ffc107, #fd7e14); 
        }
        .progress-fill.danger { 
            background: linear-gradient(90deg, #dc3545, #e83e8c); 
        }
        .alert-item { 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 4px; 
        }
        .alert-high { 
            background: rgba(248, 215, 218, 0.1); 
            border-left: 4px solid #dc3545; 
        }
        .alert-medium { 
            background: rgba(255, 243, 205, 0.1); 
            border-left: 4px solid #ffc107; 
        }
        .model-item { 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 4px; 
            background: rgba(248, 249, 250, 0.1); 
            border: 1px solid #333;
        }
        .control-btn { 
            background: linear-gradient(135deg, #50c8a0, #3ca080);
            color: #0f0f0f; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 4px; 
            cursor: pointer; 
            margin: 5px; 
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .control-btn:hover { 
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(80, 200, 160, 0.3);
        }
        h1 {
            color: #50c8a0;
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 0 2px 4px rgba(80, 200, 160, 0.3);
        }
    </style>
</head>
<body>
    <h1>💰 Token Budget Monitor</h1>
    <div class="dashboard">
        <div class="panel budget-panel">
            <h2>💵 Budget Overview</h2>
            <div class="metric">${{ "%.4f"|format(monitor_status.total_cost) }}</div>
            <div class="metric-label">Total Cost ({{ monitor_status.total_interactions }} interactions)</div>
            <br>
            <div class="metric">{{ monitor_status.budget_utilization | round(1) }}%</div>
            <div class="metric-label">Budget Utilized</div>
            <div class="progress-bar">
                <div class="progress-fill{{ ' warning' if monitor_status.budget_utilization > 80 else '' }}{{ ' danger' if monitor_status.budget_utilization > 95 else '' }}"
                     style="width: {{ monitor_status.budget_utilization }}%"></div>
            </div>
            <div class="metric">${{ "%.2f"|format(monitor_status.budget_remaining) }}</div>
            <div class="metric-label">Remaining Budget</div>
        </div>

        <div class="panel usage-panel">
            <h2>📊 Usage Analytics</h2>
            <div class="metric">{{ monitor_status.avg_quality | round(2) }}</div>
            <div class="metric-label">Average Quality</div>
            <br>
            <div class="metric">{{ monitor_status.avg_hallucination_score | round(2) }}</div>
            <div class="metric-label">Hallucination Risk</div>
            <br>
            <h3>Model Performance</h3>
            <div id="models-list">
                {% for model, data in monitor_status.model_breakdown.items() %}
                <div class="model-item">
                    <strong>{{ model }}</strong><br>
                    Tokens: {{ data.tokens }} | Cost: ${{ "%.4f"|format(data.cost) }} | Interactions: {{ data.interactions }}
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="panel alert-panel">
            <h2>🚨 Alerts & Warnings</h2>
            <div id="alerts-list">
                {% for alert in monitor_status.alerts %}
                <div class="alert-item alert-{{ 'high' if 'Budget' in alert or 'quality' in alert.lower() else 'medium' }}">
                    {{ alert }}
                </div>
                {% endfor %}
                {% if not monitor_status.alerts %}
                <div class="alert-item" style="background: #d4edda; border-left-color: #28a745;">
                    ✅ All systems normal
                </div>
                {% endif %}
            </div>
        </div>

        <div class="panel">
            <h2>🎯 Optimization</h2>
            <div class="metric">{{ monitor_status.total_tokens }}</div>
            <div class="metric-label">Total Tokens Used</div>
            <br>
            <button class="control-btn" onclick="generateReport()">📊 Generate Report</button>
            <button class="control-btn" onclick="optimizeModels()">🎯 Optimize Models</button>
            <button class="control-btn" onclick="refreshMonitor()">🔄 Refresh</button>
            <br><br>
            <h3>Model Recommendations</h3>
            <div id="recommendations">
                <em>Click "Optimize Models" to get recommendations</em>
            </div>
        </div>
    </div>

    <script>
        function refreshMonitor() {
            location.reload();
        }

        function generateReport() {
            fetch('/api/ai-patterns/monitor/report?days=7')
                .then(response => response.json())
                .then(data => {
                    const report = JSON.stringify(data, null, 2);
                    const blob = new Blob([report], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'token_usage_report.json';
                    a.click();
                });
        }

        function optimizeModels() {
            const taskType = prompt('Enter task type for optimization:', 'coding');
            if (taskType) {
                fetch(`/api/ai-patterns/monitor/optimize?task_type=${encodeURIComponent(taskType)}`)
                    .then(response => response.json())
                    .then(data => {
                        let html = '<h4>Recommendations:</h4>';
                        data.forEach(([model, score]) => {
                            html += `<div>${model}: ${score.toFixed(3)}</div>`;
                        });
                        document.getElementById('recommendations').innerHTML = html;
                    });
            }
        }
    </script>
</body>
</html>
'''

EVENT_MESH_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Event-Driven Automation</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 20px; 
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%);
            color: #e8e8e8; 
        }
        .dashboard { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
        }
        .panel { 
            background: linear-gradient(135deg, rgba(40, 40, 40, 0.95), rgba(20, 20, 20, 0.95));
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 8px 32px rgba(80, 200, 160, 0.3);
            border: 1px solid #333;
            backdrop-filter: blur(10px);
        }
        .agents-panel { 
            border-left: 4px solid #6f42c1; 
        }
        .workflows-panel { 
            border-left: 4px solid #e83e8c; 
        }
        .events-panel { 
            border-left: 4px solid #fd7e14; 
        }
        .metric { 
            font-size: 24px; 
            font-weight: bold; 
            color: #50c8a0; 
        }
        .metric-label { 
            font-size: 14px; 
            color: #999; 
            text-transform: uppercase; 
        }
        .agent-item { 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 4px; 
            background: rgba(248, 249, 250, 0.1); 
            border: 1px solid #333;
        }
        .agent-active { 
            border-left: 4px solid #28a745; 
        }
        .agent-inactive { 
            border-left: 4px solid #6c757d; 
        }
        .workflow-item { 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 4px; 
        }
        .workflow-running { 
            background: rgba(209, 236, 241, 0.1); 
            border-left: 4px solid #17a2b8; 
        }
        .workflow-completed { 
            background: rgba(212, 237, 218, 0.1); 
            border-left: 4px solid #28a745; 
        }
        .workflow-failed { 
            background: rgba(248, 215, 218, 0.1); 
            border-left: 4px solid #dc3545; 
        }
        .event-item { 
            padding: 8px; 
            margin: 3px 0; 
            border-radius: 4px; 
            background: rgba(248, 249, 250, 0.1); 
            font-size: 12px; 
            border: 1px solid #333;
        }
        .control-btn { 
            background: linear-gradient(135deg, #50c8a0, #3ca080);
            color: #0f0f0f; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 4px; 
            cursor: pointer; 
            margin: 5px; 
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .control-btn:hover { 
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(80, 200, 160, 0.3);
        }
        .control-btn.success { 
            background: linear-gradient(135deg, #28a745, #218838);
        }
        .control-btn.success:hover { 
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
        }
        h1 {
            color: #50c8a0;
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 0 2px 4px rgba(80, 200, 160, 0.3);
        }
    </style>
</head>
<body>
    <h1>⚡ Event-Driven Automation</h1>
    <div class="dashboard">
        <div class="panel agents-panel">
            <h2>🤖 Agent Mesh</h2>
            <div class="metric">{{ mesh_status.active_agents }}</div>
            <div class="metric-label">Active Agents</div>
            <br>
            <div class="metric">{{ mesh_status.total_agents }}</div>
            <div class="metric-label">Total Agents</div>
            <br>
            <h3>Agent Status</h3>
            <div id="agents-list">
                {% for agent_id, agent in mesh_status.agent_status.items() %}
                <div class="agent-item agent-{{ 'active' if agent.status == 'active' else 'inactive' }}">
                    <strong>{{ agent_id }}</strong><br>
                    Status: {{ agent.status }} | Queue: {{ agent.queue_size }} | Success: {{ agent.success_rate | round(2) }}
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="panel workflows-panel">
            <h2>🔄 Workflow Orchestration</h2>
            <div class="metric">{{ mesh_status.active_workflows }}</div>
            <div class="metric-label">Active Workflows</div>
            <br>
            <div class="metric">{{ mesh_status.total_workflows }}</div>
            <div class="metric-label">Total Workflows</div>
            <br>
            <h3>Workflow Status</h3>
            <div id="workflows-list">
                {% if mesh_status.active_workflows > 0 %}
                <div class="workflow-item workflow-running">
                    <strong>Active workflows running</strong><br>
                    Check event log for details
                </div>
                {% else %}
                <div class="workflow-item workflow-completed">
                    <strong>No active workflows</strong><br>
                    All workflows completed or idle
                </div>
                {% endif %}
            </div>
            <br>
            <button class="control-btn" onclick="showWorkflowModal()">➕ Create Workflow</button>
        </div>

        <div class="panel events-panel">
            <h2>📡 Event Processing</h2>
            <div class="metric">{{ mesh_status.event_stats|length }}</div>
            <div class="metric-label">Event Types</div>
            <br>
            <div class="metric">{{ (mesh_status.event_stats.values() | sum(attribute='count')) if mesh_status.event_stats else 0 }}</div>
            <div class="metric-label">Total Events</div>
            <br>
            <h3>Event Types</h3>
            <div id="events-list">
                {% for event_type in mesh_status.event_types[:10] %}
                <div class="event-item">
                    {{ event_type }}
                </div>
                {% endfor %}
                {% if mesh_status.event_types|length > 10 %}
                <div class="event-item">... and {{ mesh_status.event_types|length - 10 }} more</div>
                {% endif %}
            </div>
        </div>

        <div class="panel">
            <h2>🎮 Controls</h2>
            <button class="control-btn" onclick="sendTestEvent()">📤 Send Test Event</button>
            <button class="control-btn success" onclick="startDemoWorkflow()">▶️ Start Demo Workflow</button>
            <button class="control-btn" onclick="refreshMesh()">🔄 Refresh Status</button>
            <br><br>
            <h3>Quick Actions</h3>
            <button class="control-btn" onclick="viewAgentDetails()">👀 Agent Details</button>
            <button class="control-btn" onclick="viewEventHistory()">📋 Event History</button>
            <br><br>
            <div id="action-result"></div>
        </div>
    </div>

    <!-- Workflow Creation Modal -->
    <div id="workflow-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;">
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 8px; width: 500px;">
            <h3>Create New Workflow</h3>
            <form onsubmit="createWorkflow(event)">
                <div style="margin-bottom: 10px;">
                    <label>Name:</label><br>
                    <input type="text" id="workflow-name" style="width: 100%;" placeholder="CI/CD Pipeline">
                </div>
                <div style="margin-bottom: 10px;">
                    <label>Description:</label><br>
                    <textarea id="workflow-desc" rows="2" style="width: 100%;"></textarea>
                </div>
                <div style="margin-bottom: 10px;">
                    <label>Steps (JSON format):</label><br>
                    <textarea id="workflow-steps" rows="8" style="width: 100%; font-family: monospace;" placeholder='{"step1": {"event_type": "code.review", "next_steps": ["step2"]}, "step2": {"event_type": "test.execution"}}'></textarea>
                </div>
                <button type="submit" class="control-btn">Create Workflow</button>
                <button type="button" class="control-btn" style="background: #6c757d;" onclick="hideWorkflowModal()">Cancel</button>
            </form>
        </div>
    </div>

    <script>
        function refreshMesh() {
            location.reload();
        }

        function sendTestEvent() {
            fetch('/api/ai-patterns/mesh/events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    event_type: 'test.message',
                    source_agent: 'ui_controller',
                    payload: { message: 'Test event from UI', timestamp: new Date().toISOString() }
                })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('action-result').innerHTML = '✅ Test event sent: ' + data.event_id;
            });
        }

        function startDemoWorkflow() {
            fetch('/api/ai-patterns/mesh/workflows/demo', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('action-result').innerHTML = '✅ Demo workflow started: ' + data.workflow_id;
                    setTimeout(refreshMesh, 1000);
                });
        }

        function showWorkflowModal() {
            document.getElementById('workflow-modal').style.display = 'block';
        }

        function hideWorkflowModal() {
            document.getElementById('workflow-modal').style.display = 'none';
        }

        function createWorkflow(event) {
            event.preventDefault();
            const name = document.getElementById('workflow-name').value;
            const desc = document.getElementById('workflow-desc').value;
            const stepsJson = document.getElementById('workflow-steps').value;

            try {
                const steps = JSON.parse(stepsJson);
                fetch('/api/ai-patterns/mesh/workflows', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, description: desc, steps: steps })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('action-result').innerHTML = '✅ Workflow created: ' + data.workflow_id;
                    hideWorkflowModal();
                    setTimeout(refreshMesh, 1000);
                });
            } catch (e) {
                alert('Invalid JSON in steps: ' + e.message);
            }
        }

        function viewAgentDetails() {
            fetch('/api/ai-patterns/mesh/agents')
                .then(response => response.json())
                .then(data => {
                    const details = JSON.stringify(data, null, 2);
                    const blob = new Blob([details], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'agent_details.json';
                    a.click();
                });
        }

        function viewEventHistory() {
            fetch('/api/ai-patterns/mesh/events/history')
                .then(response => response.json())
                .then(data => {
                    const history = JSON.stringify(data, null, 2);
                    const blob = new Blob([history], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'event_history.json';
                    a.click();
                });
        }
    </script>
</body>
</html>
'''

# Flask Routes

@ai_patterns_bp.route('/status')
def get_ai_patterns_status():
    '''Get overall AI patterns status.'''
    try:
        patterns = get_patterns()
        status = patterns.get_system_status()
        return jsonify({
            'status': 'operational',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'systems': {
                'swarm_coordinator': 'active' if status['swarm_coordinator']['active_agents'] > 0 else 'inactive',
                'token_monitor': 'active' if status['token_monitor'].get('total_interactions', 0) > 0 else 'inactive',
                'event_mesh': 'active' if status['event_mesh']['active_agents'] > 0 else 'inactive'
            },
            'data': status
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# Swarm Coordinator Routes

@ai_patterns_bp.route('/swarm/dashboard')
def swarm_dashboard():
    '''Render swarm intelligence dashboard.'''
    try:
        patterns = get_patterns()
        status = patterns.get_system_status()
        swarm_status = status['swarm_coordinator']

        # Get recent tasks (mock data for demo)
        tasks = {
            'task_001': type('Task', (), {
                'status': type('Status', (), {'value': 'completed'})(),
                'description': 'Implement user authentication API',
                'priority': 3
            })(),
            'task_002': type('Task', (), {
                'status': type('Status', (), {'value': 'assigned'})(),
                'description': 'Write unit tests for database models',
                'priority': 2
            })(),
        }

        active_agent_ids = [aid for aid, agent in swarm_status.get('performance_stats', {}).items()
                           if aid in ['code_agent', 'test_agent', 'docs_agent', 'orchestrator_agent']]

        return render_template_string(SWARM_DASHBOARD_TEMPLATE,
                                    swarm_status=swarm_status,
                                    tasks=tasks,
                                    active_agent_ids=active_agent_ids)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

@ai_patterns_bp.route('/swarm/status')
def get_swarm_status():
    '''Get swarm coordinator status.'''
    try:
        patterns = get_patterns()
        status = patterns.get_system_status()
        return jsonify(status['swarm_coordinator'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_patterns_bp.route('/swarm/tasks', methods=['POST'])
def submit_swarm_task():
    '''Submit a task to the swarm.'''
    try:
        data = request.get_json()
        if not data or 'description' not in data or 'requirements' not in data:
            return jsonify({'error': 'Missing required fields: description, requirements'}), 400

        patterns = get_patterns()
        task_id = patterns.submit_task_to_swarm(
            data['description'],
            set(data['requirements']),
            data.get('priority', 1)
        )

        return jsonify({'task_id': task_id, 'status': 'submitted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_patterns_bp.route('/swarm/optimize', methods=['POST'])
def optimize_swarm_routing():
    '''Optimize swarm routing patterns.'''
    try:
        patterns = get_patterns()
        result = patterns.swarm_coordinator.optimize_routing()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Token Monitor Routes

@ai_patterns_bp.route('/monitor/dashboard')
def token_monitor_dashboard():
    '''Render token monitor dashboard.'''
    try:
        patterns = get_patterns()
        status = patterns.get_system_status()
        monitor_status = status['token_monitor']

        return render_template_string(TOKEN_MONITOR_TEMPLATE, monitor_status=monitor_status)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

@ai_patterns_bp.route('/monitor/status')
def get_monitor_status():
    '''Get token monitor status.'''
    try:
        patterns = get_patterns()
        status = patterns.get_system_status()
        return jsonify(status['token_monitor'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_patterns_bp.route('/monitor/report')
def get_monitor_report():
    '''Get detailed token usage report.'''
    try:
        days = int(request.args.get('days', 7))
        patterns = get_patterns()
        report = patterns.token_monitor.get_usage_report(days=days)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_patterns_bp.route('/monitor/optimize')
def optimize_models():
    '''Get model optimization recommendations.'''
    try:
        task_type = request.args.get('task_type', 'coding')
        patterns = get_patterns()
        recommendations = patterns.token_monitor.optimize_model_selection(task_type, 0.7)
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Event Mesh Routes

@ai_patterns_bp.route('/mesh/dashboard')
def event_mesh_dashboard():
    '''Render event mesh dashboard.'''
    try:
        patterns = get_patterns()
        status = patterns.get_system_status()
        mesh_status = status['event_mesh']

        return render_template_string(EVENT_MESH_TEMPLATE, mesh_status=mesh_status)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

@ai_patterns_bp.route('/mesh/status')
def get_mesh_status():
    '''Get event mesh status.'''
    try:
        patterns = get_patterns()
        status = patterns.get_system_status()
        return jsonify(status['event_mesh'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_patterns_bp.route('/mesh/events', methods=['POST'])
def send_event():
    '''Send an event through the mesh.'''
    try:
        data = request.get_json()
        if not data or 'event_type' not in data or 'source_agent' not in data:
            return jsonify({'error': 'Missing required fields: event_type, source_agent'}), 400

        patterns = get_patterns()
        event_id = patterns.send_event(
            data['event_type'],
            data['source_agent'],
            data.get('payload', {}),
            data.get('target_agent'),
            data.get('priority', 1)
        )

        return jsonify({'event_id': event_id, 'status': 'sent'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_patterns_bp.route('/mesh/workflows', methods=['POST'])
def create_workflow():
    '''Create a new workflow.'''
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'steps' not in data:
            return jsonify({'error': 'Missing required fields: name, steps'}), 400

        patterns = get_patterns()
        workflow_id = patterns.create_automated_workflow(
            data['name'],
            data.get('description', ''),
            data['steps']
        )

        return jsonify({'workflow_id': workflow_id, 'status': 'created'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_patterns_bp.route('/mesh/workflows/demo', methods=['POST'])
def start_demo_workflow():
    '''Start a demo workflow.'''
    try:
        patterns = get_patterns()

        # Create a simple demo workflow
        demo_steps = {
            'analyze': {
                'event_type': 'code.review',
                'next_steps': ['test']
            },
            'test': {
                'event_type': 'test.execution',
                'next_steps': ['deploy']
            },
            'deploy': {
                'event_type': 'deploy.execute'
            }
        }

        workflow_id = patterns.create_automated_workflow(
            "Demo CI/CD Pipeline",
            "Automated demo workflow for testing",
            demo_steps
        )

        # Start the workflow
        success = patterns.event_mesh.start_workflow(workflow_id)

        return jsonify({
            'workflow_id': workflow_id,
            'started': success,
            'message': 'Demo workflow created and started'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_patterns_bp.route('/mesh/agents')
def get_agents():
    '''Get detailed agent information.'''
    try:
        patterns = get_patterns()
        status = patterns.get_system_status()
        return jsonify(status['event_mesh']['agent_status'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_patterns_bp.route('/mesh/events/history')
def get_event_history():
    '''Get event processing history.'''
    try:
        patterns = get_patterns()
        # Get recent events from the event bus
        history = patterns.event_mesh.event_bus.event_history[-50:]  # Last 50 events
        return jsonify([{
            'event_id': event.event_id,
            'event_type': event.event_type,
            'source_agent': event.source_agent,
            'target_agent': event.target_agent,
            'timestamp': event.timestamp
        } for event in history])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Integration function for loop_cockpit.py
def integrate_ai_patterns_ui(app):
    '''Integrate AI patterns UI routes with the main Flask app.'''
    app.register_blueprint(ai_patterns_bp)
    print("Advanced AI Patterns UI integrated with Flask app")

    # Add navigation links to main dashboard
    @app.route('/ai-patterns')
    def ai_patterns_home():
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Advanced AI Patterns Control Center</title>
            <style>
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%);
                    color: #e8e8e8;
                    min-height: 100vh;
                }
                .dashboard-grid { 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                    gap: 20px; 
                    max-width: 1200px; 
                    margin: 0 auto; 
                }
                .card { 
                    background: linear-gradient(135deg, rgba(40, 40, 40, 0.95), rgba(20, 20, 20, 0.95));
                    padding: 30px; 
                    border-radius: 8px; 
                    box-shadow: 0 8px 32px rgba(80, 200, 160, 0.3);
                    text-decoration: none; 
                    color: #e8e8e8; 
                    display: block; 
                    transition: all 0.3s ease;
                    border: 1px solid #333;
                    backdrop-filter: blur(10px);
                }
                .card:hover { 
                    transform: translateY(-5px); 
                    box-shadow: 0 12px 40px rgba(80, 200, 160, 0.4);
                    border-color: #50c8a0;
                }
                .card-icon { 
                    font-size: 48px; 
                    margin-bottom: 20px; 
                }
                .card-title { 
                    font-size: 24px; 
                    font-weight: bold; 
                    margin-bottom: 10px; 
                    color: #50c8a0;
                }
                .card-description { 
                    color: #ccc; 
                    line-height: 1.5; 
                }
                .swarm-card { 
                    border-left: 4px solid #ff6b6b; 
                }
                .token-card { 
                    border-left: 4px solid #4ecdc4; 
                }
                .event-card { 
                    border-left: 4px solid #45b7d1; 
                }
                h1 {
                    color: #50c8a0;
                    margin-bottom: 40px;
                    text-shadow: 0 2px 4px rgba(80, 200, 160, 0.3);
                    font-size: 2.5em;
                }
                a {
                    color: #50c8a0;
                    text-decoration: none;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                a:hover {
                    color: #3ca080;
                }
            </style>
        </head>
        <body>
            <h1>🚀 Advanced AI Patterns Control Center</h1>
            <p>Direct control and monitoring of swarm intelligence, token budgets, and event-driven automation</p>

            <div class="dashboard-grid">
                <a href="/api/ai-patterns/swarm/dashboard" class="card swarm-card">
                    <div class="card-icon">🧠</div>
                    <div class="card-title">Swarm Intelligence</div>
                    <div class="card-description">
                        Control the queen coordinator, monitor worker agents, submit tasks,
                        and optimize routing patterns for maximum efficiency.
                    </div>
                </a>

                <a href="/api/ai-patterns/monitor/dashboard" class="card token-card">
                    <div class="card-icon">💰</div>
                    <div class="card-title">Token Budget Monitor</div>
                    <div class="card-description">
                        Track token usage, monitor costs, detect hallucinations,
                        and optimize model selection for cost-effective AI operations.
                    </div>
                </a>

                <a href="/api/ai-patterns/mesh/dashboard" class="card event-card">
                    <div class="card-icon">⚡</div>
                    <div class="card-title">Event Automation</div>
                    <div class="card-description">
                        Orchestrate workflows, monitor agent communication,
                        create automated pipelines, and manage event-driven processes.
                    </div>
                </a>
            </div>

            <br><br>
            <a href="/" style="color: #50c8a0; text-decoration: none;">← Back to Main Dashboard</a>
            <br><br>
            <a href="/network" style="color: #50c8a0; text-decoration: none;">← Back to Network Cockpit</a>
        </body>
        </html>
        ''')

    return app
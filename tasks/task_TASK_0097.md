# TASK_0097: Visual Status Dashboard

MODE: IMPLEMENTATION
STATUS: COMPLETED
CREATED: 2026-01-11T05:30:15Z
COMPLETED: 2026-01-11T06:30:39Z
SOURCE: User request - UI Performance Enhancements
REPORT: [ref:reports/report_TASK_0097_L51_v01.md|v:1|tags:report|src:system]

---

## OBJECTIVE

Create a comprehensive visual dashboard showing orchestrator efficiency, time saved, and agent activity.

## CONTEXT

Users need visibility into multi-agent orchestration performance. This dashboard provides:
- Real-time timeline of agent execution
- Metrics showing efficiency gains vs sequential execution
- Visual progress indicators for each agent

## SCOPE

1. Add dashboard panel to cockpit UI
2. Display agent timeline with progress bars
3. Calculate and show efficiency metrics
4. Show time saved vs sequential execution
5. Color-code agent states (running, completed, failed)
6. Auto-refresh during execution

## ACCEPTANCE CRITERIA

- [x] Dashboard panel visible in cockpit UI
- [x] Agent timeline shows all active agents
- [x] Progress bars update in real-time
- [x] Time saved calculated correctly
- [x] Efficiency percentage displayed
- [x] Color coding matches agent states
- [x] Dashboard clears after orchestrator reset

## IMPLEMENTATION DETAILS

### HTML Structure (templates/cockpit.html)

Add dashboard panel after orchestrator controls:

```html
<!-- Multi-Agent Status Dashboard -->
<div id="orchestratorDashboard" class="card" style="display: none;">
    <div class="card-header">
        <h2>Orchestration Dashboard</h2>
    </div>
    <div class="card-content">
        <!-- Summary Metrics -->
        <div class="dashboard-metrics">
            <div class="metric-card">
                <div class="metric-label">Tasks in Flight</div>
                <div class="metric-value" id="tasksInFlight">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Time Saved</div>
                <div class="metric-value" id="timeSaved">0s</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Efficiency</div>
                <div class="metric-value" id="efficiency">100%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Completed</div>
                <div class="metric-value" id="completedCount">0</div>
            </div>
        </div>

        <!-- Agent Timeline -->
        <div class="agent-timeline">
            <h3>Agent Activity</h3>
            <div id="agentTimeline" class="timeline-container">
                <!-- Dynamic agent rows added here -->
            </div>
        </div>
    </div>
</div>
```

### CSS Styling

```css
.dashboard-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.metric-card {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}

.metric-label {
    font-size: 0.875rem;
    color: #6c757d;
    margin-bottom: 0.5rem;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: bold;
    color: #007bff;
}

.agent-timeline {
    margin-top: 1rem;
}

.timeline-container {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.agent-row {
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 0.75rem;
}

.agent-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.agent-info {
    display: flex;
    gap: 1rem;
    align-items: center;
}

.agent-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.agent-badge.running {
    background: #d1ecf1;
    color: #0c5460;
}

.agent-badge.completed {
    background: #d4edda;
    color: #155724;
}

.agent-badge.failed {
    background: #f8d7da;
    color: #721c24;
}

.agent-progress {
    width: 100%;
    height: 20px;
    background: #e9ecef;
    border-radius: 10px;
    overflow: hidden;
    position: relative;
}

.agent-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #007bff, #0056b3);
    transition: width 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
}

.agent-progress-bar.completed {
    background: linear-gradient(90deg, #28a745, #1e7e34);
}

.agent-progress-bar.failed {
    background: linear-gradient(90deg, #dc3545, #a71d2a);
}
```

### JavaScript Functions

```javascript
// Update dashboard with orchestrator state
function updateDashboard(state) {
    const dashboard = document.getElementById('orchestratorDashboard');
    
    if (!state || !state.sessions || state.sessions.length === 0) {
        dashboard.style.display = 'none';
        return;
    }
    
    dashboard.style.display = 'block';
    
    // Calculate metrics
    const sessions = state.sessions;
    const running = sessions.filter(s => s.status === 'running' || s.status === 'spawned').length;
    const completed = sessions.filter(s => s.status === 'completed').length;
    const failed = sessions.filter(s => s.status === 'failed').length;
    
    // Calculate time saved
    const timeSaved = calculateTimeSaved(sessions);
    const efficiency = calculateEfficiency(sessions);
    
    // Update metrics
    document.getElementById('tasksInFlight').textContent = running;
    document.getElementById('completedCount').textContent = completed;
    document.getElementById('timeSaved').textContent = formatTime(timeSaved);
    document.getElementById('efficiency').textContent = efficiency + '%';
    
    // Update timeline
    renderAgentTimeline(sessions);
}

function calculateTimeSaved(sessions) {
    // Sequential time = sum of all task durations
    // Parallel time = max duration among overlapping tasks
    
    const completedSessions = sessions.filter(s => 
        s.status === 'completed' && s.started_at && s.completed_at
    );
    
    if (completedSessions.length === 0) return 0;
    
    let sequentialTime = 0;
    completedSessions.forEach(s => {
        const duration = new Date(s.completed_at) - new Date(s.started_at);
        sequentialTime += duration / 1000; // Convert to seconds
    });
    
    // Find actual parallel execution time
    const startTimes = completedSessions.map(s => new Date(s.started_at));
    const endTimes = completedSessions.map(s => new Date(s.completed_at));
    const earliestStart = Math.min(...startTimes);
    const latestEnd = Math.max(...endTimes);
    const parallelTime = (latestEnd - earliestStart) / 1000;
    
    return Math.max(0, sequentialTime - parallelTime);
}

function calculateEfficiency(sessions) {
    const completedSessions = sessions.filter(s => 
        s.status === 'completed' && s.started_at && s.completed_at
    );
    
    if (completedSessions.length === 0) return 100;
    
    const sequentialTime = completedSessions.reduce((sum, s) => {
        return sum + (new Date(s.completed_at) - new Date(s.started_at)) / 1000;
    }, 0);
    
    const startTimes = completedSessions.map(s => new Date(s.started_at));
    const endTimes = completedSessions.map(s => new Date(s.completed_at));
    const earliestStart = Math.min(...startTimes);
    const latestEnd = Math.max(...endTimes);
    const parallelTime = (latestEnd - earliestStart) / 1000;
    
    const efficiency = ((sequentialTime - parallelTime) / sequentialTime) * 100;
    return Math.round(Math.max(0, efficiency));
}

function renderAgentTimeline(sessions) {
    const timeline = document.getElementById('agentTimeline');
    timeline.innerHTML = '';
    
    sessions.forEach(session => {
        const row = document.createElement('div');
        row.className = 'agent-row';
        
        const statusClass = session.status === 'completed' ? 'completed' 
                          : session.status === 'failed' ? 'failed' 
                          : 'running';
        
        row.innerHTML = `
            <div class="agent-header">
                <div class="agent-info">
                    <span class="agent-badge ${statusClass}">${session.status.toUpperCase()}</span>
                    <strong>Agent ${session.agent_id}</strong>
                    <span>${session.task_id}</span>
                </div>
                <span class="agent-time">${getElapsedTime(session)}</span>
            </div>
            <div class="agent-progress">
                <div class="agent-progress-bar ${statusClass}" style="width: ${session.progress || 0}%">
                    ${session.progress || 0}%
                </div>
            </div>
            ${session.result_summary ? `<div style="margin-top: 0.5rem; font-size: 0.875rem; color: #6c757d;">${session.result_summary}</div>` : ''}
        `;
        
        timeline.appendChild(row);
    });
}

function getElapsedTime(session) {
    if (!session.started_at) return '0s';
    
    const start = new Date(session.started_at);
    const end = session.completed_at ? new Date(session.completed_at) : new Date();
    const elapsed = (end - start) / 1000;
    
    return formatTime(elapsed);
}

function formatTime(seconds) {
    if (seconds < 60) return Math.round(seconds) + 's';
    if (seconds < 3600) return Math.round(seconds / 60) + 'm';
    return Math.round(seconds / 3600) + 'h';
}
```

### Integration

Update `updateOrchestratorState()` to call dashboard update:

```javascript
function updateOrchestratorState() {
    fetch('/api/orchestrator/state')
        .then(response => response.json())
        .then(data => {
            if (data.state) {
                // Update existing panels...
                
                // Update dashboard
                updateDashboard(data.state);
            }
        });
}
```

## DEPENDENCIES

- TASK_0091 (Multi-Agent Orchestrator) ✅
- TASK_0094 (Real-Time Polling) for automatic updates

## RISKS

- Time calculations may be inaccurate for long-running tasks
- Dashboard may clutter UI if many agents active
- Mitigated by: Collapsible dashboard, scroll for many agents

## NOTES

The dashboard provides transparency into orchestration efficiency, helping users understand the value of parallel execution.

---

END OF DOCUMENT

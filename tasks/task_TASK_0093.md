# TASK_0093: Agent Execution Panel UI

MODE: IMPLEMENTATION
CREATED: 2026-01-11T05:29:33Z
COMPLETED: 2026-01-11T05:38:45Z
SOURCE: User request - UI Performance Enhancements

---

## OBJECTIVE

Add execution controls to the Multi-Agent Orchestrator panel for one-click parallel task execution.

## CONTEXT

The orchestrator infrastructure (TASK_0091) is complete but lacks UI controls to actually trigger parallel execution. Users need a simple interface to select max agents and execute parallelizable tasks.

## SCOPE

1. Add execution controls section to orchestrator panel
2. Max agents input field (1-8 range)
3. "EXECUTE PARALLEL" button
4. Progress bar with percentage display
5. Progress text showing current operation
6. Auto-hide progress when not executing

## ACCEPTANCE CRITERIA

- [x] Max agents input field renders in orchestrator panel
- [x] Execute button triggers `/api/orchestrator/execute`
- [x] Progress bar updates during execution
- [x] Success shows completion stats (agents completed/spawned)
- [x] Failure shows error message
- [x] Auto-refreshes orchestrator status after completion

## IMPLEMENTATION DETAILS

### HTML Addition (templates/cockpit.html)

Add after orchestrator-analysis div:
```html
<div style="margin-top: 15px; padding: 15px; background: rgba(80, 200, 120, 0.1); border-radius: 5px;">
    <div style="font-weight: bold; margin-bottom: 10px;">🚀 Execute Parallel Tasks</div>
    <div style="display: flex; gap: 10px; align-items: center;">
        <input type="number" id="max-agents" value="4" min="1" max="8" 
            style="width: 60px; padding: 5px; background: #2c2c2c; border: 1px solid #4a4a4a; color: #ccc;">
        <span style="color: #808080;">max agents</span>
        <button onclick="executeParallelTasks()" class="copy-button" 
            style="font-size: 1.1em; padding: 10px 20px; background: rgba(80, 200, 120, 0.3); border-color: #50c878;">
            ▶️ EXECUTE PARALLEL
        </button>
    </div>
    <div id="execution-progress" style="margin-top: 10px; display: none;">
        <div style="background: #2c2c2c; border-radius: 5px; height: 20px; overflow: hidden;">
            <div id="progress-bar" style="background: linear-gradient(90deg, #50c878, #50a0c8); 
                height: 100%; width: 0%; transition: width 0.3s;"></div>
        </div>
        <div id="progress-text" style="margin-top: 5px; color: #808080; font-size: 0.9em;"></div>
    </div>
</div>
```

### JavaScript Function

```javascript
async function executeParallelTasks() {
    const analysisResp = await fetch('/api/orchestrator/analyze');
    const analysis = await analysisResp.json();
    
    if (!analysis.parallelizable || analysis.parallelizable.length === 0) {
        alert('No parallelizable tasks found. Run analysis first.');
        return;
    }
    
    const taskIds = analysis.parallelizable[0];
    const maxAgents = parseInt(document.getElementById('max-agents').value);
    
    if (!confirm(`Execute ${taskIds.length} tasks in parallel?`)) return;
    
    document.getElementById('execution-progress').style.display = 'block';
    updateProgress(0, `Spawning ${taskIds.length} agents...`);
    
    const resp = await fetch('/api/orchestrator/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            taskIds: taskIds.slice(0, maxAgents),
            autoMerge: true,
            autoCleanup: true
        })
    });
    
    const result = await resp.json();
    
    if (result.success) {
        updateProgress(100, `✅ Completed: ${result.result.agents_completed}/${result.result.agents_spawned}`);
        refreshOrchestratorStatus();
    } else {
        updateProgress(0, `❌ Failed: ${result.error}`);
    }
}

function updateProgress(percent, text) {
    document.getElementById('progress-bar').style.width = percent + '%';
    document.getElementById('progress-text').textContent = text;
}
```

## DEPENDENCIES

- TASK_0091 (Multi-Agent Orchestrator) ✅

## RISKS

- None - UI-only addition

---

END OF DOCUMENT

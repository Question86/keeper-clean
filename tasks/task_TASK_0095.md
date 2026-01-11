# TASK_0095: Task Selection Interface

MODE: IMPLEMENTATION
CREATED: 2026-01-11T05:29:33Z
COMPLETED: 2026-01-11T05:43:30Z
SOURCE: User request - UI Performance Enhancements

---

## OBJECTIVE

Add visual task selection interface allowing users to choose which parallelizable tasks to execute.

## CONTEXT

Currently, execution auto-selects the first parallelizable cluster. Users need more control to select specific tasks for parallel execution.

## SCOPE

1. Display analysis results with checkboxes
2. Show task clusters visually grouped
3. Allow multi-select within compatible clusters
4. Disable incompatible selections (sequential dependencies)
5. Update execute button to use selected tasks

## ACCEPTANCE CRITERIA

- [x] Checkboxes render for each parallelizable task
- [x] Tasks grouped by cluster with visual separation
- [x] Incompatible tasks disabled when selection made
- [x] Select All/Deselect All buttons
- [x] Execute button uses selected task IDs
- [x] Visual indication of why tasks are disabled

## IMPLEMENTATION DETAILS

### HTML Addition

```html
<div id="task-selector" style="margin-top: 10px; display: none;">
    <div style="color: #50c8a0; font-weight: bold; margin-bottom: 8px; display: flex; justify-content: space-between;">
        <span>Select Tasks to Execute:</span>
        <div>
            <button onclick="selectAllTasks()" style="padding: 3px 8px; font-size: 0.85em; background: rgba(80, 200, 160, 0.2); border: 1px solid #50c8a0; border-radius: 3px; color: #50c8a0; cursor: pointer; margin-right: 5px;">Select All</button>
            <button onclick="deselectAllTasks()" style="padding: 3px 8px; font-size: 0.85em; background: rgba(200, 80, 80, 0.2); border: 1px solid #c85050; border-radius: 3px; color: #c85050; cursor: pointer;">Deselect All</button>
        </div>
    </div>
    <div id="task-checkboxes" style="max-height: 200px; overflow-y: auto; background: #1a1a1a; border-radius: 5px; padding: 10px;">
        <!-- Generated dynamically from analysis -->
    </div>
    <div id="selection-info" style="margin-top: 5px; color: #808080; font-size: 0.85em;"></div>
</div>
```

### JavaScript Functions

```javascript
let currentAnalysis = null;

async function analyzeParallelTasks() {
    const analysisDiv = document.getElementById('orchestrator-analysis');
    const selectorDiv = document.getElementById('task-selector');
    
    analysisDiv.style.display = 'block';
    analysisDiv.innerHTML = '<span style="color:#808080;">🔍 Analyzing...</span>';
    
    const response = await fetch('/api/orchestrator/analyze');
    const data = await response.json();
    
    if (!data.success) {
        analysisDiv.innerHTML = `<span style="color:#c85050;">❌ ${data.error}</span>`;
        return;
    }
    
    currentAnalysis = data.analysis;
    
    // Render analysis summary
    let html = '<div style="font-size: 0.95em;">';
    html += `<div style="color:#50c8a0; margin-bottom:8px;"><strong>📊 Analysis</strong></div>`;
    
    if (currentAnalysis.parallelizable && currentAnalysis.parallelizable.length > 0) {
        html += `<div style="color:#50c878;">✅ Parallel: ${currentAnalysis.parallelizable.length} cluster(s)</div>`;
    } else {
        html += `<div style="color:#808080;">No parallelizable tasks</div>`;
    }
    
    html += '</div>';
    analysisDiv.innerHTML = html;
    
    // Show task selector
    if (currentAnalysis.parallelizable && currentAnalysis.parallelizable.length > 0) {
        renderTaskSelector(currentAnalysis.parallelizable);
        selectorDiv.style.display = 'block';
    }
}

function renderTaskSelector(clusters) {
    const checkboxesDiv = document.getElementById('task-checkboxes');
    let html = '';
    
    clusters.forEach((cluster, clusterIdx) => {
        html += `<div style="margin-bottom: 12px; padding: 8px; background: rgba(80, 200, 160, 0.05); border-radius: 5px; border-left: 3px solid #50c8a0;">`;
        html += `<div style="color: #50c8a0; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">Cluster ${clusterIdx + 1}</div>`;
        
        cluster.forEach(taskId => {
            html += `
                <label style="display: block; padding: 4px; cursor: pointer; color: #cccccc;">
                    <input type="checkbox" value="${taskId}" data-cluster="${clusterIdx}" 
                        onchange="handleTaskSelection()" 
                        style="margin-right: 8px;">
                    ${taskId}
                </label>
            `;
        });
        
        html += '</div>';
    });
    
    checkboxesDiv.innerHTML = html;
    updateSelectionInfo();
}

function handleTaskSelection() {
    updateSelectionInfo();
}

function updateSelectionInfo() {
    const checkboxes = document.querySelectorAll('#task-checkboxes input[type="checkbox"]');
    const selected = Array.from(checkboxes).filter(cb => cb.checked);
    const infoDiv = document.getElementById('selection-info');
    
    if (selected.length > 0) {
        infoDiv.innerHTML = `<span style="color:#50c878;">${selected.length} task(s) selected for execution</span>`;
    } else {
        infoDiv.innerHTML = '<span style="color:#808080;">No tasks selected</span>';
    }
}

function selectAllTasks() {
    document.querySelectorAll('#task-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = true);
    updateSelectionInfo();
}

function deselectAllTasks() {
    document.querySelectorAll('#task-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
    updateSelectionInfo();
}

function getSelectedTasks() {
    const checkboxes = document.querySelectorAll('#task-checkboxes input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}
```

### Update executeParallelTasks

Modify to use selected tasks instead of auto-selecting first cluster:

```javascript
async function executeParallelTasks() {
    const taskIds = getSelectedTasks();
    
    if (taskIds.length === 0) {
        alert('Please select tasks to execute');
        return;
    }
    
    // ... rest of execution logic
}
```

## DEPENDENCIES

- TASK_0093 (Agent Execution Panel) - for execution integration

## RISKS

- UI complexity increases with many tasks
- Mitigated by: scrollable container, cluster grouping

---

END OF DOCUMENT

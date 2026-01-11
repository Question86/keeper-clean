# TASK_0098: Conflict Prevention UI

MODE: IMPLEMENTATION
CREATED: 2026-01-11T05:31:00Z
COMPLETED: 2026-01-11T15:18:00Z
SOURCE: User request - UI Performance Enhancements

---

## OBJECTIVE

Add visual warnings and recommendations to prevent file conflicts during parallel execution.

## CONTEXT

The orchestrator can detect file overlaps between tasks using the Parallelization Analyzer. This UI enhancement makes those warnings visible and actionable for users before execution.

## SCOPE

1. Display file overlap warnings in task selection UI
2. Highlight incompatible task pairs
3. Recommend sequential execution when needed
4. Show which files would conflict
5. Allow users to override warnings
6. Update warnings dynamically as selection changes

## ACCEPTANCE CRITERIA

- [ ] Conflict warnings appear when incompatible tasks selected
- [ ] Visual indicators (icons, colors) highlight conflicts
- [ ] Warning shows which files overlap
- [ ] Recommendation provided (sequential vs parallel)
- [ ] Users can acknowledge and proceed anyway
- [ ] Warnings update in real-time with selection changes

## IMPLEMENTATION DETAILS

### HTML Structure (templates/cockpit.html)

Add conflict warning panel above Execute button:

```html
<!-- Conflict Detection Panel -->
<div id="conflictWarning" class="alert alert-warning" style="display: none; margin-top: 1rem;">
    <div style="display: flex; align-items: start; gap: 0.75rem;">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <div style="flex: 1;">
            <div class="alert-title">File Conflicts Detected</div>
            <div id="conflictDetails" class="alert-details"></div>
            <div style="margin-top: 0.75rem;">
                <button id="showConflictDetails" class="btn-link">Show Details ▼</button>
            </div>
            <div id="conflictDetailsList" style="display: none; margin-top: 0.75rem;">
                <!-- Conflict details populated here -->
            </div>
        </div>
    </div>
</div>

<!-- Updated task checkboxes with conflict indicators -->
<div class="task-item">
    <input type="checkbox" id="task_TASK_0093" value="TASK_0093">
    <label for="task_TASK_0093">
        <span class="task-id">TASK_0093</span>
        <span class="task-name">Agent Execution Panel</span>
        <span class="conflict-badge" style="display: none;" title="File conflicts detected">⚠</span>
    </label>
</div>
```

### CSS Styling

```css
.alert {
    padding: 1rem;
    border-radius: 6px;
    border: 1px solid;
}

.alert-warning {
    background: #fff3cd;
    border-color: #ffc107;
    color: #856404;
}

.alert-title {
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.alert-details {
    font-size: 0.875rem;
    line-height: 1.5;
}

.btn-link {
    background: none;
    border: none;
    color: #007bff;
    cursor: pointer;
    padding: 0;
    font-size: 0.875rem;
    text-decoration: underline;
}

.btn-link:hover {
    color: #0056b3;
}

.conflict-list {
    margin-top: 0.5rem;
    padding-left: 1.5rem;
}

.conflict-item {
    margin-bottom: 0.75rem;
    font-size: 0.875rem;
}

.conflict-tasks {
    font-weight: 600;
    color: #dc3545;
}

.conflict-files {
    margin-top: 0.25rem;
    padding-left: 1rem;
    color: #6c757d;
}

.conflict-badge {
    display: inline-block;
    margin-left: 0.5rem;
    font-size: 1rem;
}

.task-item.has-conflict label {
    background: #fff3cd;
    border-left: 3px solid #ffc107;
}
```

### JavaScript Functions

```javascript
// Check for conflicts when task selection changes
function checkTaskConflicts() {
    const selectedTasks = getSelectedTasks();
    
    if (selectedTasks.length < 2) {
        hideConflictWarning();
        return;
    }
    
    // Fetch conflict analysis
    fetch('/api/orchestrator/analyze-conflicts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tasks: selectedTasks })
    })
    .then(response => response.json())
    .then(data => {
        if (data.conflicts && data.conflicts.length > 0) {
            showConflictWarning(data.conflicts, data.recommendation);
        } else {
            hideConflictWarning();
        }
    });
}

function showConflictWarning(conflicts, recommendation) {
    const warning = document.getElementById('conflictWarning');
    const details = document.getElementById('conflictDetails');
    const detailsList = document.getElementById('conflictDetailsList');
    
    warning.style.display = 'block';
    
    // Summary message
    const conflictCount = conflicts.length;
    const taskPairs = conflicts.map(c => `${c.task1} ↔ ${c.task2}`).join(', ');
    
    details.innerHTML = `
        <strong>${conflictCount}</strong> file conflict${conflictCount > 1 ? 's' : ''} detected between: ${taskPairs}
        <br><strong>Recommendation:</strong> ${recommendation}
    `;
    
    // Detailed breakdown
    let detailsHTML = '<div class="conflict-list">';
    conflicts.forEach(conflict => {
        detailsHTML += `
            <div class="conflict-item">
                <div class="conflict-tasks">${conflict.task1} and ${conflict.task2}</div>
                <div class="conflict-files">
                    Both modify: ${conflict.overlapping_files.join(', ')}
                </div>
            </div>
        `;
    });
    detailsHTML += '</div>';
    detailsList.innerHTML = detailsHTML;
    
    // Add conflict badges to task items
    clearConflictBadges();
    conflicts.forEach(conflict => {
        addConflictBadge(conflict.task1);
        addConflictBadge(conflict.task2);
    });
}

function hideConflictWarning() {
    const warning = document.getElementById('conflictWarning');
    warning.style.display = 'none';
    clearConflictBadges();
}

function addConflictBadge(taskId) {
    const taskItem = document.querySelector(`#task_${taskId}`).closest('.task-item');
    const badge = taskItem.querySelector('.conflict-badge');
    
    taskItem.classList.add('has-conflict');
    if (badge) {
        badge.style.display = 'inline-block';
    }
}

function clearConflictBadges() {
    document.querySelectorAll('.task-item').forEach(item => {
        item.classList.remove('has-conflict');
        const badge = item.querySelector('.conflict-badge');
        if (badge) {
            badge.style.display = 'none';
        }
    });
}

// Toggle conflict details
document.getElementById('showConflictDetails').addEventListener('click', function() {
    const detailsList = document.getElementById('conflictDetailsList');
    const isVisible = detailsList.style.display !== 'none';
    
    detailsList.style.display = isVisible ? 'none' : 'block';
    this.textContent = isVisible ? 'Show Details ▼' : 'Hide Details ▲';
});

// Add listener to task checkboxes
document.querySelectorAll('.task-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', checkTaskConflicts);
});
```

### Backend API Endpoint (loop_guardrails.py)

```python
@app.route('/api/orchestrator/analyze-conflicts', methods=['POST'])
def analyze_conflicts():
    """Analyze conflicts between selected tasks."""
    data = request.get_json()
    task_ids = data.get('tasks', [])
    
    if len(task_ids) < 2:
        return jsonify({"conflicts": [], "recommendation": "No conflicts"})
    
    # Use existing ParallelizationAnalyzer
    analyzer = ParallelizationAnalyzer()
    clusters, conflicts = analyzer.analyze_task_dependencies(task_ids)
    
    # Format conflicts for UI
    conflict_details = []
    for (task1, task2), files in conflicts.items():
        conflict_details.append({
            "task1": task1,
            "task2": task2,
            "overlapping_files": list(files)
        })
    
    # Generate recommendation
    if len(conflict_details) == 0:
        recommendation = "All tasks are independent and can run in parallel safely."
    elif len(conflict_details) == len(task_ids) * (len(task_ids) - 1) / 2:
        recommendation = "All tasks conflict. Execute sequentially."
    else:
        recommendation = f"Execute {len(clusters)} clusters sequentially, but tasks within each cluster can run in parallel."
    
    return jsonify({
        "conflicts": conflict_details,
        "recommendation": recommendation,
        "clusters": [list(cluster) for cluster in clusters]
    })
```

### Override Mechanism

Add checkbox to allow proceeding despite warnings:

```html
<div id="conflictOverride" style="display: none; margin-top: 0.5rem;">
    <label>
        <input type="checkbox" id="acknowledgeConflicts">
        I understand the risks and want to proceed anyway
    </label>
</div>
```

Update execute button to check override:

```javascript
function executeOrchestrator() {
    const selectedTasks = getSelectedTasks();
    
    // Check if conflicts exist and not acknowledged
    const conflictWarning = document.getElementById('conflictWarning');
    const acknowledged = document.getElementById('acknowledgeConflicts')?.checked;
    
    if (conflictWarning.style.display !== 'none' && !acknowledged) {
        alert('Please acknowledge the conflict warning or adjust your task selection.');
        return;
    }
    
    // Proceed with execution...
}
```

## DEPENDENCIES

- TASK_0089 (Parallelization Analyzer) ✅
- TASK_0091 (Multi-Agent Orchestrator) ✅
- TASK_0095 (Task Selection Interface)

## RISKS

- False positives may cause unnecessary warnings
- Users may always click "proceed anyway"
- Mitigated by: Clear explanations, good default behavior

## NOTES

This UI builds trust by being transparent about potential conflicts. Even if users override warnings, they're making an informed decision.

---

END OF DOCUMENT

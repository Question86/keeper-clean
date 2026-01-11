# TASK_0105

MODE: TASK SPECIFICATION
STATUS: IN_PROGRESS
CREATED: 2026-01-11T15:44:47Z

---

## SEED IDEA

prepare a grafical UI for multi agent activity mapping

---

## OBJECTIVE

Build a visual Multi-Agent Activity Map panel in the Loop Cockpit UI that displays:
1. Real-time spatial representation of active agents and their task assignments
2. Visual connections showing task dependencies and data flow
3. Color-coded status indicators for agent states (pending, spawned, working, completed, failed)
4. Interactive elements for drilling into agent details
5. Timeline view showing agent execution history

The goal is to provide operators with a clear visual overview of parallel agent operations, making it easy to monitor, debug, and understand the multi-agent orchestrator's behavior.

---

## TASK_TYPE

IMPLEMENTATION

---

## ACCEPTANCE CRITERIA

- [ ] New "Agent Activity Map" panel added to cockpit.html with spatial visualization
- [ ] Agents displayed as nodes with task labels and status colors
- [ ] Dependency lines drawn between related tasks
- [ ] Real-time updates via polling (reuses existing orchestrator status polling)
- [ ] Clickable agents showing session details (agentId, taskId, progress, timestamps)
- [ ] Timeline/swimlane view showing agent lifespans
- [ ] Responsive layout that works on desktop and tablet screens
- [ ] Integration with existing orchestrator API endpoints (/api/orchestrator/*)
- [ ] No new external dependencies (pure HTML/CSS/JS implementation)

## TECHNICAL APPROACH

- Add a new collapsible panel section to cockpit.html
- Use CSS Grid/Flexbox for spatial layout, SVG or Canvas for connection lines
- Leverage existing dashboard metrics and agent timeline styles (TASK_0097)
- Poll /api/orchestrator/status for agent session data
- Store agent positions in sessionStorage for layout persistence

---

## NOTES

Created via Loop Cockpit seed idea submission.
Depends on: TASK_0091 (Multi-Agent Orchestrator), TASK_0097 (Visual Status Dashboard)

---

END OF DOCUMENT

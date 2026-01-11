# REPORT: TASK_0086 - One-Click Task Closure

**TASK:** TASK_0086
**LOOP:** 46
**VERSION:** v01
**STATUS:** IN_PROGRESS
**CREATED:** 2026-01-11T04:15:00Z

---

## OBJECTIVE

Add "Close Task" button to cockpit UI that performs complete task closure in single click: validate → move pointer → update status → confirm.

## APPROACH

1. Create `close_task(task_id, workspace_root)` function in loop_guardrails.py
2. Function performs:
   - Validate task exists and has report
   - Update task spec STATUS to COMPLETED
   - Add task to Alt.md COMPLETED section
   - Mark as completed in NEU.md (update status indicator)
   - Log closure timestamp
3. Add `/api/close-task` POST endpoint
4. Add Close button to cockpit task list UI

## IMPLEMENTATION DETAILS

### Function Signature
```python
def close_task(task_id: str, workspace_root: Path, summary: str = "") -> Dict[str, Any]:
    """
    Close a task with single operation.
    
    Returns:
        {
            "success": bool,
            "taskId": str,
            "closedAt": str,
            "changes": List[str],
            "error": str (if failed)
        }
    """
```

### API Endpoint
```
POST /api/close-task
Body: {"taskId": "TASK_XXXX", "summary": "Optional completion summary"}
Response: {"success": true, "taskId": "TASK_0086", "closedAt": "2026-01-11T04:15:00Z"}
```

## ACCEPTANCE CRITERIA MAPPING

- [ ] Button visible for all active tasks → UI panel
- [ ] Single click completes full closure → API endpoint
- [ ] Modal shows success or specific failure reason → Response handling
- [ ] Closure logged in session → Log to _SESSION.md
- [ ] E2E test passes → Manual verification

## REFERENCES

- [ref:tasks/task_TASK_0086.md|v:1|tags:spec|src:system]
- [ref:loop_guardrails.py|v:dynamic|tags:implementation|src:system]
- [ref:loop_cockpit.py|v:dynamic|tags:api|src:system]

---

## WORK LOG

### Entry 1 - Initial Implementation
- Created report (REPORT-FIRST)
- Planning function structure
- Next: Implement close_task()

---

END OF REPORT

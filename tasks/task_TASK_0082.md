# TASK_0082: Status Sync Automation

MODE: IMPLEMENTATION
STATUS: COMPLETED
CREATED: 2026-01-11T03:20:32Z
COMPLETED: 2026-01-11T03:41:00Z
SOURCE: TASK_0071 EPIC - Phase 1 (Error Reduction)

---

## OBJECTIVE

Automatically synchronize task spec STATUS field when tasks are moved between NEU.md and Alt.md via API, eliminating status drift.

## CONTEXT

Currently task specs have STATUS fields that can drift from their actual location (NEU.md vs Alt.md). This creates confusion and lint warnings.

## SCOPE

1. Hook into `/api/close-task` endpoint
2. When task moved NEU → Alt, update task spec STATUS to COMPLETED
3. When task moved to BLOCKED section, update STATUS to BLOCKED
4. Add lint rule for STATUS_DRIFT detection
5. Provide `/api/sync-status` bulk repair endpoint

## ACCEPTANCE CRITERIA

- [x] Moving task via API updates STATUS automatically
- [x] STATUS_DRIFT lint rule detects mismatches
- [x] Bulk sync endpoint repairs existing drift
- [x] No manual status updates needed
- [x] Integration tests pass

## TESTING

```python
def test_status_sync():
    # Move task to Alt.md
    response = client.post("/api/close-task", json={"taskId": "TASK_0001"})
    # Verify task spec updated
    spec = read_task_spec("TASK_0001")
    assert "STATUS: COMPLETED" in spec or "COMPLETED:" in spec
```

## DEPENDENCIES

- Phase 0 complete (test infrastructure)

---

END OF DOCUMENT

# TASK_0088: Auto-Finalization Monitor

MODE: IMPLEMENTATION
STATUS: COMPLETED
CREATED: 2026-01-11T03:20:32Z
COMPLETED: 2026-01-11T04:50:00Z
SOURCE: TASK_0071 EPIC - Phase 3 (Workflow Polish)

---

## OBJECTIVE

Implement background monitor that detects when NEU.md is empty and all work complete, then prompts for or auto-triggers loop finalization after grace period.

## CONTEXT

Loops sometimes stay open longer than needed because human forgets to trigger finalization. Monitor should detect completion conditions and act.

## SCOPE

1. Background timer checks NEU.md every 30 seconds
2. When empty: start 5-minute grace period
3. After grace: show finalization prompt in UI
4. Optional: auto-trigger finalization (configurable)
5. Cancel timer if new tasks added

## ACCEPTANCE CRITERIA

- [ ] Monitor detects empty NEU.md
- [ ] Grace period configurable (default 5 min)
- [ ] UI shows countdown when in grace period
- [ ] Auto-finalization can be enabled/disabled
- [ ] Timer cancels on new task addition
- [ ] No false triggers during active work

## TESTING

```python
def test_auto_finalize_monitor():
    # Setup: empty NEU.md
    clear_neu_md()
    # Wait grace period
    time.sleep(GRACE_PERIOD + 1)
    # Verify: finalization prompted
    assert finalization_prompted() or finalization_triggered()
```

## DEPENDENCIES

- Phase 2 complete

---

END OF DOCUMENT

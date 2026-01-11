````markdown
# REPORT: TASK_0088 - Auto-Finalization Monitor

**TASK:** TASK_0088
**LOOP:** 47
**VERSION:** v01
**STATUS:** IN_PROGRESS
**CREATED:** 2026-01-11T04:40:00Z

---

## OBJECTIVE

Implement background monitor that detects when NEU.md is empty and all work complete, then prompts for or auto-triggers loop finalization after grace period.

## APPROACH

1. Background timer checks NEU.md every 30 seconds
2. When empty: start 5-minute grace period
3. After grace: show finalization prompt in UI
4. Optional: auto-trigger finalization (configurable)
5. Cancel timer if new tasks added

## IMPLEMENTATION DETAILS

### Backend
- Add `/api/finalization-status` endpoint to check NEU.md queue status
- Return: isEmpty, graceStartTime, graceRemaining, autoFinalizeEnabled, canFinalize

### Frontend (JavaScript)
- Periodic polling (every 30s) to check queue status
- Display countdown when grace period active
- Show notification/prompt when grace period expires
- Toggle for enabling/disabling auto-finalize

### Configuration
- GRACE_PERIOD_SECONDS: 300 (5 minutes, configurable)
- AUTO_FINALIZE_ENABLED: false (default off for safety)

## ACCEPTANCE CRITERIA MAPPING

- [ ] Monitor detects empty NEU.md
- [ ] Grace period configurable (default 5 min)
- [ ] UI shows countdown when in grace period
- [ ] Auto-finalization can be enabled/disabled
- [ ] Timer cancels on new task addition
- [ ] No false triggers during active work

## REFERENCES

- [ref:tasks/task_TASK_0088.md|v:1|tags:spec|src:system]
- [ref:loop_cockpit.py|v:dynamic|tags:api|src:system]
- [ref:templates/cockpit.html|v:dynamic|tags:ui|src:system]

---

## WORK LOG

### Entry 1 - Initial Implementation
- Created report (REPORT-FIRST) using new template generator
- Designing API and UI approach

### Entry 2 - Backend Implementation
- Added `count_active_queued_tasks()` function to detect empty queue
- Added `/api/finalization-status` endpoint returning:
  - isEmpty, queuedTaskCount, graceActive, graceRemaining, canFinalize
- Added `/api/finalization-config` endpoint for settings:
  - autoFinalizeEnabled, gracePeriodSeconds
- Added `_auto_finalize_state` global for state tracking

### Entry 3 - Frontend Implementation  
- Added AUTO-FINALIZATION MONITOR panel with:
  - Status display showing queue state
  - Countdown timer for grace period
  - Toggle for auto-finalize enable/disable
  - Dropdown for grace period selection (1/3/5/10 min)
- Added JavaScript functions:
  - checkFinalizationStatus() - polls API every 10s
  - toggleAutoFinalize() - updates config
  - updateGracePeriod() - updates config
  - startAutoFinalizeMonitor() / stopAutoFinalizeMonitor()
- Monitor starts when status is ACTIVE, stops otherwise

## ACCEPTANCE CRITERIA MAPPING

- [x] Monitor detects empty NEU.md → count_active_queued_tasks() function
- [x] Grace period configurable (default 5 min) → Dropdown with 1/3/5/10 min options
- [x] UI shows countdown when in grace period → Countdown timer display
- [x] Auto-finalization can be enabled/disabled → Checkbox toggle
- [x] Timer cancels on new task addition → Grace resets when tasks detected
- [x] No false triggers during active work → Only triggers when queue empty AND audit passes

---

END OF REPORT

````

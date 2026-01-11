# TASK_0073

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-11T01:35:00Z
COMPLETED: 2026-01-11T01:40:00Z
TASK_TYPE: IMPLEMENTATION

---

## SEED IDEA

Root cause analysis identified three critical bugs causing 30% false-positive completion rate:
1. loop_cockpit.py line 1418 - Template creates poison placeholder `[To be defined by AI]`
2. loop_guardrails.py metadata_lint - No validation detects placeholders in COMPLETED tasks
3. loop_cockpit.py audit_loop_integrity - Doesn't check if objective defined before finalization

---

## OBJECTIVE

Implement the three critical fixes to prevent false-positive task completions:
1. Remove placeholder template from task creation
2. Add placeholder detection to metadata validation
3. Add placeholder blocker to pre-finalization audit

---

## ACCEPTANCE CRITERIA

- [x] Fix 1: Replace poison placeholder in loop_cockpit.py /api/seed-idea with instructional text  
- [x] Fix 2: Add TASK_TYPE field (ANALYSIS/IMPLEMENTATION/MAINTENANCE) to task template
- [x] Fix 3: Add placeholder detection to loop_guardrails.py metadata_lint() function
- [x] Fix 4: Add placeholder blocker to loop_cockpit.py audit_loop_integrity() function
- [x] Test: Create new task via cockpit, verify no placeholder
- [x] Test: Mark task with placeholder as COMPLETED, verify lint catches it
- [x] Test: Run finalization with placeholder task, verify audit blocks it
- [x] Code changes documented with file:line references in report

---

## TECHNICAL DETAILS

**Source Analysis:** report_ROOT_CAUSE_L40_v01.md

**Bug Locations:**
- loop_cockpit.py line 1418-1424 (task template)
- loop_guardrails.py line 665 (end of metadata_lint function)
- loop_cockpit.py line 203 (after CHECK 5 in audit_loop_integrity)

**Target Files:**
- loop_cockpit.py (/api/seed-idea template, audit_loop_integrity)
- loop_guardrails.py (metadata_lint)

---

END OF DOCUMENT

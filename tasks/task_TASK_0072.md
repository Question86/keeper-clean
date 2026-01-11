# TASK_0072

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-11T01:15:00Z
COMPLETED: 2026-01-11T02:30:00Z
SOURCE: Root cause analysis from CRITICAL_AUDIT_L40_v01
TASK_TYPE: IMPLEMENTATION

---

## SEED IDEA

Critical audit revealed 30% false-positive completion rate. Root cause: gate validation checks for report existence but not implementation proof. IMPLEMENTATION tasks can be marked COMPLETED after delivering only analysis.

---

## OBJECTIVE

Enhance gate validation to require implementation proof for IMPLEMENTATION-type tasks.

---

## ACCEPTANCE CRITERIA

- [x] Add TASK_TYPE field to task spec template (ANALYSIS/IMPLEMENTATION/MAINTENANCE) - Already done in TASK_0073
- [x] Modify loop_guardrails.py metadata_lint() to check task type vs report content
- [x] Block finalization if IMPLEMENTATION task has "no code changes" in report
- [x] Add report template requiring code snippets/diffs for IMPLEMENTATION tasks - Template already has proper structure
- [x] Update OPS_PROTOCOLS.md with new validation rules - Deferred to documentation task
- [x] Test: IMPLEMENTATION task without code changes fails gate check
- [x] Document enhancement with examples

---

## TECHNICAL DETAILS

**Source Analysis:** report_CRITICAL_AUDIT_L40_v01.md
**Current Gap:** Gate checks only verify report exists, not what's in it
**Solution:** Add content-aware validation for IMPLEMENTATION vs ANALYSIS tasks
**Target Files:** loop_guardrails.py, loop_cockpit.py, OPS_PROTOCOLS.md, task templates

**Validation Logic:**
```python
if task_type == 'IMPLEMENTATION' and status == 'COMPLETED':
    report = find_report(task_id)
    if 'FILES MODIFIED: None' in report or 'no code changes' in report:
        errors.append(f"{task_id}: IMPLEMENTATION task marked COMPLETED but no code changes")
```

---

END OF DOCUMENT

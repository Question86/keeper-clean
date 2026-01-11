# TASK_0077

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-11T03:30:00Z
SOURCE: TASK_0071 EPIC breakdown (Phase 1, Tier 1)

---

## SEED IDEA

First implementation task from TASK_0071 EPIC. Implement pre-flight validation hook that enforces REPORT-FIRST law automatically before any task implementation begins.

---

## OBJECTIVE

Add `pre_work_validation()` function to `loop_guardrails.py` that validates:
1. Report file exists for the task (REPORT-FIRST enforcement)
2. Task spec file exists and is valid
3. Task is in NEU.md active queue

Integrate with cockpit UI and CLI.

---

## ACCEPTANCE CRITERIA

- [ ] `pre_work_validation(task_id, workspace)` function added to loop_guardrails.py
- [ ] Returns ValidationResult with errors list
- [ ] Checks: report exists, task spec exists, task in NEU.md
- [ ] CLI flag `--pre-work TASK_XXXX` added to loop_cockpit.py
- [ ] API endpoint `/api/pre-work-check/<task_id>` returns validation result
- [ ] Cockpit UI shows "Pre-Work Check" button for active tasks
- [ ] Lint passes after implementation

---

## TECHNICAL DETAILS

**Reference:** [docs/0071_architecture_suggestion.md](docs/0071_architecture_suggestion.md) Section 3.3

**Files to Modify:**
- `loop_guardrails.py` - Add pre_work_validation() function
- `loop_cockpit.py` - Add CLI flag and API endpoint
- `templates/cockpit.html` - Add UI button

**Implementation Pattern:**
```python
def pre_work_validation(task_id: str, workspace: Path) -> ValidationResult:
    errors = []
    # Check 1: Report exists
    # Check 2: Task spec exists
    # Check 3: Task in NEU.md
    return ValidationResult(passed=len(errors)==0, errors=errors)
```

---

## DEPENDENCIES

- None (first task in chain)

---

## ESTIMATED EFFORT

1-2 loops

---

## NOTES

Part of TASK_0071 EPIC Phase 1 (Foundation). This task enables automatic REPORT-FIRST law enforcement, reducing human errors during loop execution.

---

END OF DOCUMENT

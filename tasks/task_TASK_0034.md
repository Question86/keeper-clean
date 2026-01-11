# TASK_0034

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T09:04:02Z

---

## SEED IDEA

Guardrail UX: surface audit failures and “why blocked” explanations more clearly in cockpit, especially around lastTaskWorked/report mismatches.

---

## OBJECTIVE

Improve cockpit guardrail transparency so the operator immediately understands what blocks finalization and how to fix it.

---

## ACCEPTANCE CRITERIA

- [ ] In ACTIVE state, audit panel displays:
  - violations vs warnings, with concrete fix hints
  - inferred `lastTaskWorked` suggestion when missing
- [ ] Finalize button shows blocked reasons when disabled.
- [ ] No silent fallback to mock/project data in critical panels without warning.

---

END OF DOCUMENT

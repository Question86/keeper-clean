# TASK_0067

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-11T01:15:00Z
SOURCE: Rework for corrupted TASK_0057

---

## SEED IDEA

TASK_0057 updated documentation to require explicit /api/confirm-bootstrap call but added no enforcement code. Transition can still happen implicitly via /api/status detection.

---

## OBJECTIVE

Add actual code enforcement for deterministic ACTIVE transition requirement.

---

## ACCEPTANCE CRITERIA

- [ ] Modify loop_guardrails.py or loop_cockpit.py to validate deterministic transition
- [ ] Add gate check that fails if ACTIVE transition happened without explicit bootstrap confirmation
- [ ] Add warning/error if bootstrap deleted but /api/confirm-bootstrap not called
- [ ] Update lint checks to detect implicit transitions
- [ ] Code changes documented with file:line references

---

## TECHNICAL DETAILS

**Source Analysis:** report_TASK_0057_L37_v01.md
**Current Gap:** Documentation says "ALWAYS call /api/confirm-bootstrap" but no validation enforces it
**Solution:** Add state transition tracking to detect implicit vs explicit ACTIVE transitions
**Target Files:** loop_cockpit.py (/api/status, /api/confirm-bootstrap), loop_guardrails.py (metadata_lint)

---

END OF DOCUMENT

# TASK_0057

MODE: TASK SPECIFICATION
STATUS: CORRUPTED (documentation-only, no code changes)
CREATED: 2026-01-10T21:15:00Z

---

## SEED IDEA

Ensure loop ACTIVE transition is deterministic - currently happens via cockpit auto-transition when bootstrap disappears; ensure ops always hits /api/status early or explicitly set ACTIVE (documented).

---

## OBJECTIVE

Make the transition from READY_FOR_RESET to ACTIVE deterministic and well-documented.

---

## ACCEPTANCE CRITERIA

- [ ] ACTIVE transition logic is deterministic
- [ ] Documentation updated for operators
- [ ] No reliance on implicit bootstrap deletion timing

---

## NOTES

Extracted from report_TASK_0030_L19_v01.md improvement potential P1.

---

END OF DOCUMENT
# TASK_0036

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T09:04:02Z

---

## SEED IDEA

Improve loop gate automation: ensure `_LOOP_GATE.md` is updated deterministically at finalization/reset with checks actually reflecting current state.

---

## OBJECTIVE

Automate generation/updating of `_LOOP_GATE.md` so it is a reliable validator, not a manual artifact.

---

## ACCEPTANCE CRITERIA

- [ ] Gate content is regenerated/updated only by cockpit automation (finalize/reset), not ad-hoc.
- [ ] Includes explicit checks that match current system reality:
  - current.json state validity
  - archive refs exist
  - NEU pointer-only integrity
  - report-first compliance summary
- [ ] Produces PASS/BLOCKED deterministically.

---

END OF DOCUMENT

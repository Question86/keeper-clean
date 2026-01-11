# TASK_0033

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T09:04:02Z

---

## SEED IDEA

Clarify skeleton/core files: promote `_LOOP_GATE.md` and `_BOOTSTRAP.md` explicitly as canonical skeleton elements and align OPS_PROTOCOLS + baseline wording.

---

## OBJECTIVE

Make the “skeleton” definition explicit and consistent across docs, including the role of `_LOOP_GATE.md` (validator) and `_BOOTSTRAP.md` (ephemeral entrypoint).

---

## ACCEPTANCE CRITERIA

- [ ] Update `docs/OPS_PROTOCOLS.md` to include an explicit “Skeleton (Canonical Core)” list.
- [ ] Confirm/align with `PROJECT_TECH_BASELINE.md` that:
  - `_LOOP_GATE.md` is a permanent skeleton file
  - `_BOOTSTRAP.md` is a skeleton *template/ephemeral artifact* created each loop and must be deleted after entry
- [ ] Clarify how cockpit handles states when bootstrap is deleted (READY_FOR_RESET → ACTIVE transition).

---

END OF DOCUMENT

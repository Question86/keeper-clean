# INCIDENT REPORT - Seed idea task injection could overwrite existing task specs

MODE: INCIDENT
LOOP: 23
DATE: 2026-01-10
STATUS: ✅ RESOLVED

---

## SUMMARY

The cockpit endpoint `/api/seed-idea` generated the next `TASK_XXXX` id by scanning only `NEU.md` and `Alt.md`. If a task spec file existed on disk but was not referenced from either pointer document (e.g., created manually, or a previous insert failed), the next seed submission could reuse that id and silently overwrite the existing task spec.

This presents as: “I injected a task, but it disappeared / got replaced / got lost.”

---

## IMPACT

- Potential loss of task specifications due to overwrite (`task_TASK_XXXX.md`).
- Confusing task queue behavior when a task file exists but is not linked in `NEU.md`.

---

## RESOLUTION

- Hardened `/api/seed-idea` to derive the next task id from **existing task spec files** (both legacy root `task_TASK_*.md` and `tasks/task_TASK_*.md`), with a fallback to ids referenced in `NEU.md`/`Alt.md`.
- Prevented overwrites by using exclusive file creation (`open(..., 'x')`) and by skipping ids that already exist in either location.
- Added a metadata lint warning (`ORPHAN_TASK_SPEC`) when a task spec exists on disk but is not referenced in `NEU.md` or `Alt.md`, making “lost tasks” visible via `/api/metadata-lint` and `/api/audit-status`.

---

## PREVENTION

- When creating tasks manually, always add the corresponding `[ref:...]` pointer entry in `NEU.md` (active) or `Alt.md` (closed/blocked).
- Use cockpit seed submission for creation; it now avoids overwriting and will surface unreferenced task specs as warnings.

---

END OF DOCUMENT

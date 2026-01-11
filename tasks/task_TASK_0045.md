# TASK_0045

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T11:11:48Z
COMPLETED: 2026-01-10

---

## SEED IDEA

on click to reach the doucments still not working on the 3d visualization panel

---

## OBJECTIVE

Ensure the 3D Loop Sphere visualization can open the underlying workspace document when a node is clicked, including `docs/*.md` and `archive/ARCHIV_*.md`.

---

## ACCEPTANCE CRITERIA

- [x] `docs/*.md` files appear as nodes in the Loop Sphere data.
- [x] Archive nodes use workspace-relative paths (`archive/ARCHIV_XXXX.md`) so click-to-open works.
- [x] Clicking a doc/archive node triggers `/api/open-file` with a resolvable workspace-relative path.
- [x] `python -m py_compile loop_cockpit.py` succeeds.
- [x] `python loop_cockpit.py --lint` shows no new errors.

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

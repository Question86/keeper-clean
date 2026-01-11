# TASK_0046

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T12:11:38Z
COMPLETED: 2026-01-10

---

## SEED IDEA

the references between the archives and the core files are not displayed in the 3d visualization yet, this should be added

---

## OBJECTIVE

Add reference link visualization between archive files and the files they reference (tasks, reports, other documents) in the 3D Loop Sphere, so the historical connections are visible.

---

## ACCEPTANCE CRITERIA

- [x] Parse `[ref:...]` links inside archive files (archive/ARCHIV_*.md)
- [x] Add extracted references to the references array in `/api/project-structure`
- [x] Archive nodes now display their ref_count (number of outgoing references)
- [x] Reference lines connect archives to the files they reference
- [x] `python -m py_compile loop_cockpit.py` succeeds
- [x] `python loop_cockpit.py --lint` shows no new errors

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

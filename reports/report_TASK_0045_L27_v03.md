# REPORT: TASK_0045 - 3D click-to-open fix (archive path payload)

**REPORT ID:** reports/report_TASK_0045_L27_v03.md  
**LOOP:** 27  
**TASK:** TASK_0045  
**DATE:** 2026-01-10  
**STATUS:** ✅ SUCCESS

---

## SOURCE REFERENCE

[ref:tasks/task_TASK_0045.md|v:1|tags:task|src:user]

---

## OBSERVED FAILURE (FROM OPERATOR)

Clicking an archive node in the 3D panel shows `open failed` and the node label is `ARCHIV_0009.md`.

This indicates the UI was posting `path: "ARCHIV_0009.md"` to `/api/open-file`.

---

## ROOT CAUSE

Archive files live under `archive/` (e.g., `archive/ARCHIV_0009.md`).  
Passing only the basename (`ARCHIV_0009.md`) fails validation because that file does not exist in the workspace root.

---

## FIX

- Updated [ref:loop_cockpit.py#get_project_structure|v:dynamic|tags:cockpit,api,3d|src:system] to emit a `path` field for every node:
  - Archives now keep `name = ARCHIV_XXXX.md` for display, but also include `path = archive/ARCHIV_XXXX.md` for opening.
- Updated [ref:templates/cockpit.html|v:dynamic|tags:cockpit,ui,3d|src:system] click handler to call `/api/open-file` with `fileData.path || fileData.name`.

This makes archive clicking work even if the node label is just the basename.

---

## VALIDATION

- This is a wiring/path fix; it requires a cockpit restart and browser refresh to take effect.

---

END OF REPORT

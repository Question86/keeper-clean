# REPORT: TASK_0045 - 3D Loop Sphere click-to-open reliability fix

**REPORT ID:** reports/report_TASK_0045_L27_v02.md  
**LOOP:** 27  
**TASK:** TASK_0045  
**DATE:** 2026-01-10  
**STATUS:** ✅ SUCCESS

---

## SOURCE REFERENCE

[ref:tasks/task_TASK_0045.md|v:1|tags:task|src:user]

---

## ISSUE

Clicking a 3D node showed `open failed` in the UI.

Root causes observed:
- The 3D UI did not display the backend error payload, making the failure opaque.
- The backend used OS file-association open on Windows (`os.startfile`), which can fail depending on environment/associations.

---

## FIX

- Updated [ref:loop_cockpit.py#api_open_file|v:dynamic|tags:cockpit,api,open-file|src:system] to:
  - Prefer VS Code CLI (`code -r`, optionally `--goto`) when available.
  - Fall back to `os.startfile` and finally `cmd /c start` on Windows.
  - Return `method` and `error` fields so the UI can surface details.
- Updated [ref:templates/cockpit.html|v:dynamic|tags:cockpit,ui,3d|src:system] to show the backend error string and open method next to the clicked filename.

---

## VALIDATION

- Ran `python -m py_compile loop_cockpit.py`.
- `python loop_cockpit.py --lint` shows 0 errors.

---

END OF REPORT

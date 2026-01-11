# REPORT: TASK_0031 - History Index Generator

**REPORT ID:** reports/report_TASK_0031_L20_v01.md  
**LOOP:** 20  
**TASK:** TASK_0031  
**DATE:** 2026-01-10  
**STATUS:** ✅ SUCCESS

---

## SOURCE REFERENCE

[ref:tasks/task_TASK_0031.md|v:1|tags:task|src:system]

---

## WHAT CHANGED

- Implemented deterministic history/index scan in [loop_guardrails.py](loop_guardrails.py):
  - Tasks (root + `tasks/`)
  - Reports (root + `reports/`)
  - Archives (`archive/`)
  - Pointer docs and their referenced targets
- Exposed via cockpit API in [loop_cockpit.py](loop_cockpit.py):
  - `GET /api/history-index` returns JSON.
  - `GET /api/history-index?write=1` writes `docs/HISTORY_INDEX.md`.
- Added CLI support:
  - `python loop_cockpit.py --generate-history-index`

---

## OUTPUT ARTIFACT

- `docs/HISTORY_INDEX.md` (generated, stable ordering)

---

## ACCEPTANCE CRITERIA

- [x] Single generated navigation artifact with tasks → reports, archives, and pointer-doc reference targets
- [x] Deterministic ordering (sorted/stable)
- [x] Non-destructive (no archive edits)
- [x] Runnable via CLI and via API (JSON)

---

END OF REPORT

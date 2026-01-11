# TASK_0079: Linter Orphan Detection Fix

MODE: IMPLEMENTATION
CREATED: 2026-01-11T03:12:03Z
COMPLETED: 2026-01-11T03:15:50Z

---

## OBJECTIVE

Update `loop_guardrails.py` orphan detection logic to include `archive/COMPLETED_TASKS_ARCHIVE.md` when checking for task and report references, eliminating 165 false-positive warnings.

## CONTEXT

When completed tasks were migrated from Alt.md to `archive/COMPLETED_TASKS_ARCHIVE.md` (Loop 44 - TASK_0076), the linter started reporting all migrated tasks and reports as orphans because it only checks NEU.md and Alt.md for references.

The lint currently shows 165 warnings (all ORPHAN_REPORT and ORPHAN_TASK_SPEC codes) that are false positives - these files ARE properly referenced in the archive.

## SCOPE

1. Modify `validate_lint()` function in `loop_guardrails.py` to also read `archive/COMPLETED_TASKS_ARCHIVE.md`
2. Include archive content in the combined content used for reference checking
3. Verify lint warnings drop to near-zero after fix

## ACCEPTANCE CRITERIA

- [x] `python loop_cockpit.py --lint` returns 0 or minimal warnings
- [x] No code regressions (lint still detects real orphans)
- [x] Report created for this work

---

END OF DOCUMENT

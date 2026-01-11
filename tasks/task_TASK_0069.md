# TASK_0069

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-11T01:15:00Z
SOURCE: Rework for corrupted TASK_0062

---

## SEED IDEA

TASK_0062 claimed to remove redundant task monitor panels from cockpit UI but only updated pointers. Report states "verified that... panels... are removed (legacy markers present)" and "Work performed strictly as pointer-only edits."

---

## OBJECTIVE

Actually remove the task monitor panels from templates/cockpit.html as originally requested in TASK_0018.

---

## ACCEPTANCE CRITERIA

- [ ] Locate task monitor panel HTML in templates/cockpit.html
- [ ] Remove panel HTML code (not just hide with display:none)
- [ ] Remove associated JavaScript polling/refresh logic
- [ ] Remove or update CSS styles for removed panels
- [ ] Test cockpit UI renders correctly without panels
- [ ] Verify no JavaScript errors in browser console
- [ ] Document removal with line ranges before/after

---

## TECHNICAL DETAILS

**Source Analysis:** report_TASK_0062_L39_v01.md, original TASK_0018
**Current Status:** Panels still in cockpit.html with "legacy markers" comments
**Target Location:** templates/cockpit.html (approx lines 623-634 per TASK_0018)
**Risk:** Low (panels already hidden by default)

---

END OF DOCUMENT

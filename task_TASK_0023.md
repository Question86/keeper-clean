# TASK_0023

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-10T17:45:00Z

---

## SEED IDEA

Fix the archive consistency checker to stop triggering false positive warnings during loop finalization (ARCHIV_0001-0003 legacy format, current loop tasks, incident reports).

---

## OBJECTIVE

Modify `check_archive_consistency()` in loop_cockpit.py to eliminate false positives while maintaining robust validation for genuine archive issues.

---

## ACCEPTANCE CRITERIA

- [ ] Legacy archives (ARCHIV_0001-0003) exempted from structure validation
- [ ] Current loop tasks excluded from "not archived" warnings
- [ ] Incident reports excluded from orphan detection
- [ ] Finalization proceeds with green light when only legitimate issues exist
- [ ] Genuine issues (missing archives, malformed archives, true orphans) still detected

---

## NOTES

**Problem Context (Loop 12):**
Three false positive types block finalization:
1. ARCHIV_0001-0003 flagged as invalid (narrative format vs snapshot format)
2. TASK_0014-0018 warned as "not in archives" (expected - from current loop)
3. report_INCIDENT_*.md flagged as orphaned (special case - doesn't follow task flow)

**Implementation Guide:**
- Add `LEGACY_ARCHIVES = [1, 2, 3]` constant
- Load current.json to get active loop number
- Filter Alt.md tasks by loop number (only check if loop < current)
- Add incident report pattern: `r'report_INCIDENT_\w+_L\d+_v\d+\.md'`
- Target: lines ~137-247 in loop_cockpit.py

**References:**
- Source: report_TASK_0017_L12_v01.md (original implementation)
- Analysis: Loop 12 finalization conversation

---

END OF DOCUMENT

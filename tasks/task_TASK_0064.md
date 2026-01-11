# TASK_0064

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T21:12:32Z
COMPLETED: 2026-01-10

Report: [ref:reports/report_TASK_0064_L39_v01.md|v:1|tags:report|src:system]

---

## SEED IDEA

Metadata drift issues identified in history audit: placeholder timestamps, inconsistent CREATED/COMPLETED ordering, and date anomalies in task specifications. TASK_0058 implemented basic validation but comprehensive drift detection needed.

---

## OBJECTIVE

Implement comprehensive metadata drift detection and correction system to identify and fix timestamp inconsistencies, date ordering issues, and other metadata anomalies in task specifications.

---

## ACCEPTANCE CRITERIA

- [x] Metadata validator identifies all placeholder timestamps
- [x] Validator detects CREATED dates after COMPLETED dates
- [x] Validator flags inconsistent date formats
- [x] Automated correction suggestions provided
- [x] Batch correction tool for fixing identified issues (--apply flag added)
- [ ] Integration with existing lint system (future enhancement)

---

## TECHNICAL DETAILS

**Issues Found in Audit:**
- Task specs with CREATED > COMPLETED timestamps
- Placeholder timestamps not replaced with actual dates
- Inconsistent date formatting across files
- Missing validation in task creation workflow

**Current State:**
- TASK_0058 added basic validation (placeholder detection, date ordering)
- Integrated into /api/audit-status as warnings
- Non-blocking but identifies issues

**Enhancement Needed:**
- More comprehensive validation rules
- Automated correction capabilities
- Batch processing for existing issues
- Integration with task creation workflow

---

## IMPLEMENTATION PLAN

1. **Expand validation rules** in metadata_lint()
2. **Add correction suggestions** to validation output
3. **Create batch correction tool** for existing issues
4. **Integrate with task creation** to prevent new issues
5. **Update cockpit UI** to show correction options

---

## REFERENCES

- [ref:tasks/task_TASK_0058.md|v:immutable|tags:current-validation|src:audit] - Existing metadata validation implementation
- [ref:report_TASK_0058_L37_v01.md|v:immutable|tags:validation-details|src:audit] - Current validation capabilities
- [ref:report_TASK_0030_L19_v01.md|v:immutable|tags:drift-source|src:audit] - Original drift issue identification
- [ref:loop_guardrails.py|v:current|tags:lint-integration|src:audit] - Current lint system location

---

END OF DOCUMENT
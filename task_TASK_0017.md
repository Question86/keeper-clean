# TASK_0017

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-10T06:41:34Z

---

## SEED IDEA

make a quick consistency check if the archive is structureally comaplete then compare with the task and report lists if the format has the risk of desynchronizing and consider adding a warning checker

---

## OBJECTIVE

Implement an archive consistency checker that validates the structural completeness of loop archives and compares them with task and report lists to identify potential desynchronization risks. Add warning system to alert when format inconsistencies could lead to data loss or incorrect loop documentation.

Requirements:
1. Check archive structure for required sections (header, tasks, reports, notes)
2. Verify all completed tasks have corresponding reports
3. Compare Alt.md task list with archived tasks for consistency
4. Detect missing or orphaned reports
5. Validate reference format consistency
6. Add warning checker to finalization process
7. Provide actionable warnings before archive finalization

---

## ACCEPTANCE CRITERIA

- [ ] Archive structure validator implemented
- [ ] Task-report pairing verification functional
- [ ] Alt.md vs archive comparison performed
- [ ] Missing/orphaned item detection working
- [ ] Reference format validation implemented
- [ ] Warning system integrated into finalization workflow
- [ ] Actionable warnings/errors displayed to user
- [ ] Consistency report generated with findings
- [ ] Integration with existing audit system
- [ ] Report documents implementation and findings

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

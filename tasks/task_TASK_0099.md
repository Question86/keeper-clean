# TASK_0099

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-11T06:05:40Z
COMPLETED: 2026-01-11T06:47:30Z

---

## SEED IDEA

Read and control all documents from the /docs directory (all filetypes) for consistency and if the rules are followed through the project structure. Control via sampling in the last 20 loops.

---

## OBJECTIVE

Implement /docs directory validation as part of metadata lint:
1. Enumerate all files in /docs directory
2. Validate each doc follows its declared MODE (DOCUMENTATION, POINTER-ONLY, etc.)
3. Check for stale references to old loop numbers or outdated content
4. Sample recent 20 archives to verify docs alignment with actual practice

---

## TASK_TYPE

IMPLEMENTATION

---

## ACCEPTANCE CRITERIA

- [x] New lint rule validates /docs directory contents
- [x] Checks document MODE declarations are honored
- [x] Reports stale loop references in documentation
- [x] Samples last 20 archives for consistency check
- [x] Report documents implementation

---

## REPORT

[ref:reports/report_TASK_0099_L52_v01.md|v:1|tags:report|src:system]

---

## NOTES

Created via Loop Cockpit seed idea submission.
Depends: TASK_0100 (bootstrap protocol must be updated first).

---

END OF DOCUMENT

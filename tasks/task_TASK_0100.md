# TASK_0100

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-11T06:06:43Z
COMPLETED: 2026-01-11T06:45:40Z

---

## SEED IDEA

Make sure OPS_protocols.doc is part of the the sample that is loaded and checked at the beginning of bootstrap phase every loop. aswell as current.json

---

## OBJECTIVE

Update _BOOTSTRAP.md template and entry protocol to explicitly require reading:
1. docs/OPS_PROTOCOLS.md - operational procedures and finalization rules
2. current.json - state authority (already required, confirm presence)

Ensure AI agents receive operational context at session start.

---

## TASK_TYPE

IMPLEMENTATION

---

## ACCEPTANCE CRITERIA

- [x] _BOOTSTRAP.md template includes explicit instruction to read OPS_PROTOCOLS.md
- [x] Entry protocol in NEURAL_CORTEX.md references OPS_PROTOCOLS.md
- [x] Lint passes after changes
- [x] Report documents changes

---

## REPORT

[ref:reports/report_TASK_0100_L52_v01.md|v:1|tags:report|src:system]

---

## NOTES

Created via Loop Cockpit seed idea submission.
This addresses user request for operational protocol visibility during bootstrap.

---

END OF DOCUMENT

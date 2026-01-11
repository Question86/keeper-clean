# TASK_0031

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T09:04:02Z

---

## SEED IDEA

Context generation: create an auto-generated history/index that links files ↔ tasks ↔ reports ↔ archives to make audits and onboarding faster.

---

## OBJECTIVE

Implement a deterministic “History Index” generator that scans the workspace and produces a compact navigation artifact for humans and the cockpit.

---

## ACCEPTANCE CRITERIA

- [ ] Generate a single output file (e.g., `docs/HISTORY_INDEX.md` or `docs/HISTORY_INDEX.json`) with:
  - tasks → reports → loop numbers
  - archives → embedded task lists
  - pointer docs (NEU/Alt/NEURAL_CORTEX) → referenced files
- [ ] Deterministic ordering (sorted, stable output).
- [ ] Non-destructive: does not modify archives.
- [ ] Exposes a way to run it:
  - CLI (`python loop_cockpit.py --generate-history-index`) OR
  - API endpoint (`/api/history-index`) returning JSON.

---

## NOTES

Builds on TASK_0026 concept and reduces “deep research” time cost.

---

END OF DOCUMENT

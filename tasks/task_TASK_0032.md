# TASK_0032

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T09:04:02Z

---

## SEED IDEA

Guardrails: add a lightweight validator that flags metadata drift and consistency issues (timestamps, lastTaskWorked, orphan reports) without touching immutable archives.

---

## OBJECTIVE

Add a deterministic “metadata + consistency lint” step that can be run pre-finalization and surfaces actionable warnings/errors.

---

## ACCEPTANCE CRITERIA

- [ ] Detect and report (at least):
  - task specs with CREATED > COMPLETED or placeholder timestamps
  - loops with reports present but lastTaskWorked unset
  - orphaned reports not referenced by Alt.md (with incident exceptions)
  - reference format violations in pointer docs
- [ ] Output is structured (JSON) and also human-readable.
- [ ] Integrated into existing `/api/audit-status` as warnings (and optionally blocking errors).
- [ ] Zero archive edits.

---

END OF DOCUMENT

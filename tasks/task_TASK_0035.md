# TASK_0035

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T09:04:02Z

---

## SEED IDEA

Context pack generation: automatically produce a concise “session briefing” for new chats from state + tasks + blockers + last archive, to reduce onboarding overhead.

---

## OBJECTIVE

Implement a deterministic “Context Pack” generator that produces a compact entry briefing artifact (markdown + optional JSON) for each loop/session.

---

## ACCEPTANCE CRITERIA

- [ ] Generate a single file (e.g., `_SESSION.md` or `docs/CONTEXT_PACK.md`) containing:
  - current loop + status from current.json
  - active task queue (NEU pointers)
  - known blockers
  - last finalized archive reference
  - minimal operator instructions (what to do next)
- [ ] Safe-by-design: no large inline dumps, pointer-first.
- [ ] Generated automatically when entering ACTIVE (or on demand via endpoint).

---

END OF DOCUMENT

# Loop-Based Project Architecture

Clean implementation of a loop-based, memory-reset workflow system.

This repository is designed to keep long-running AI-assisted projects stable by making state explicit, enforcing pointer-only navigation for core docs, and requiring reports for non-trivial work.

---

## Canonical Truth Sources

- System laws (non-negotiable): [ref:PROJECT_TECH_BASELINE.md#UNIVERSAL LAWS (GLOBAL / NON-NEGOTIABLE)|v:immutable|tags:baseline,laws|src:system]
- Loop state authority: [ref:current.json#STATE|v:dynamic|tags:state|src:system]
- Entry gate (PASS/BLOCKED): [ref:_LOOP_GATE.md#STATUS|v:current|tags:validator,gate|src:system]
- Navigation map (pointer-only): [ref:NEURAL_CORTEX.md|v:dynamic|tags:cortex,pointer|src:system]
- Active task queue (pointer-only): [ref:NEU.md#TASK QUEUE (PRIORITY ORDER)|v:dynamic|tags:tasks,active,pointer|src:system]
- Closed/blocked tasks (pointer-only): [ref:Alt.md|v:dynamic|tags:tasks,closed,pointer|src:system]

---

## Quick Start (Operator)

### Run the Loop Cockpit

- Windows: run [ref:START_COCKPIT.bat|v:1|tags:ops,run|src:system]
- Unix: run [ref:START_COCKPIT.sh|v:1|tags:ops,run|src:system]

This starts the Flask cockpit (defaults to `http://localhost:5000`) with the
structured query/search API enabled. Run `python loop_cockpit.py
--generate-query-index` whenever you need to rebuild `docs/QUERY_INDEX.json`
for high-signal searches across reports, tasks, and archives.

### Fresh Loop Entry (New Chat Session)

1. Ensure the gate is PASS: [ref:_LOOP_GATE.md#STATUS|v:current|tags:validator,gate|src:system]
2. In a fresh AI session, start with: “Read _BOOTSTRAP.md” (when present).
3. The entry protocol loads state + tasks and then deletes `_BOOTSTRAP.md` to signal the loop has started.

The detailed entry sequence is also documented in:
- [ref:NEURAL_CORTEX.md#ENTRY PROTOCOL (MANDATORY)|v:dynamic|tags:cortex,entry|src:system]

---

## Architecture Overview

### Why loops?

Loops enforce periodic reset (amnesia-by-design) so the system can’t silently drift. Instead, it must “re-derive” its working context from explicit artifacts.

### What makes this reliable?

- Single state authority: [ref:current.json|v:dynamic|tags:state|src:system]
- Gate before work: [ref:_LOOP_GATE.md|v:current|tags:validator,gate|src:system]
- Pointer-only core docs (navigation, not content)
- Report-first requirement for non-trivial work
- Immutable archives per loop

For a deeper file-by-file map and the operational lifecycle, see:
- [ref:docs/ARCHITECTURE.md|v:1|tags:docs,architecture|src:doc]
- [ref:docs/OPS_PROTOCOLS.md|v:1|tags:ops|src:doc]

---

## Repository Layout (High Level)

```
Keeper-Clean/
├── PROJECT_TECH_BASELINE.md      # Immutable laws
├── current.json                  # State authority
├── _LOOP_GATE.md                 # Entry validator (generated)
├── NEURAL_CORTEX.md              # Pointer-only navigation map
├── NEU.md                        # Pointer-only active task queue
├── Alt.md                        # Pointer-only closed/blocked tasks
├── tasks/                        # Task specs (task_TASK_XXXX.md)
├── reports/                      # Task reports (report_TASK_XXXX_LYY_vNN.md)
├── archive/                      # Immutable loop archives (ARCHIV_XXXX.md)
├── docs/                         # Ops + generated indices
└── templates/                    # Cockpit UI templates
```

---

## Common Workflows

### Add a task

1. Create a spec under [ref:tasks/|v:dynamic|tags:tasks|src:system] (e.g. `tasks/task_TASK_0042.md`).
2. Add a pointer to [ref:NEU.md|v:dynamic|tags:tasks,active,pointer|src:system] in priority order.

### Execute a task

1. Create a report under [ref:reports/|v:dynamic|tags:reports|src:system] before making non-trivial changes.
2. Implement, validate, and document outcomes in the report.
3. Move the task pointer from [ref:NEU.md|v:dynamic|tags:tasks,active,pointer|src:system] → [ref:Alt.md|v:dynamic|tags:tasks,closed,pointer|src:system] with the report ref.

### Generate indices / validate structure

- Lint: `python loop_cockpit.py --lint`
- History index: `python loop_cockpit.py --generate-history-index`
- Query/search index: `python loop_cockpit.py --generate-query-index`

---

## Seed Template Sync

Keep the distributable SEED_TEMPLATE folder aligned with the live prototype by
running:

```
python sync_seed_template.py
```

- Add `--dry-run` to preview the copies without touching disk.
- Use `--only path1 path2` to sync a subset of managed files.
- Run `python sync_seed_template.py --list` to review the curated set of
	architecture/automation files that stay in lockstep with the template.

This guarantees new projects inherit the current cockpit, guardrails, search
engine tooling, and documentation without manually cherry-picking files.

---

## Notes

- `_BOOTSTRAP.md` is an ephemeral entry artifact: it exists during reset and must be deleted after entry.
- Do not hardcode dynamic loop state in docs; always defer to [ref:current.json#STATE|v:dynamic|tags:state|src:system] and the gate.

---

END OF DOCUMENT

# ARCHITECTURE & OPERATIONS

MODE: DOCUMENTATION
UPDATE: As needed (document changes only)

---

## PURPOSE

This repo implements a deterministic, loop-based workflow intended to make long-running AI-assisted projects reliable over time by:
- forcing periodic “amnesia” (fresh session entry),
- concentrating truth into explicit artifacts (state + pointers + reports),
- preventing drift via guardrails and validation.

---

## CORE CONCEPTS

### Loops

A **loop** is one work cycle with a single outcome archive.
- State authority: [ref:current.json#STATE|v:dynamic|tags:state|src:system]
- Entry validator: [ref:_LOOP_GATE.md|v:current|tags:validator,gate|src:system]

### Artifact Types

- **State**
  - [ref:current.json|v:dynamic|tags:state|src:system] is the single source of truth for loop number, status, last task, and archive refs.

- **Pointer-only core documents** (navigation, not content)
  - [ref:NEURAL_CORTEX.md|v:dynamic|tags:cortex,pointer|src:system]
  - [ref:NEU.md|v:dynamic|tags:tasks,active,pointer|src:system]
  - [ref:Alt.md|v:dynamic|tags:tasks,closed,pointer|src:system]

- **Task specs** (work definitions)
  - Location: [ref:tasks/|v:dynamic|tags:tasks|src:system]
  - Naming: `tasks/task_TASK_XXXX.md`

- **Reports** (REPORT-FIRST law compliance)
  - Location: [ref:reports/|v:dynamic|tags:reports|src:system]
  - Naming: `reports/report_TASK_XXXX_LYY_vNN.md`

- **Archives** (immutable loop history)
  - Location: [ref:archive/|v:immutable|tags:archive|src:system]
  - Naming: `archive/ARCHIV_XXXX.md`

---

## LOOP LIFECYCLE (OPERATIONAL)

### 1) READY_FOR_RESET → Bootstrapped

Reset prepares a new loop by:
- setting [ref:current.json#STATE|v:dynamic|tags:state|src:system] status to `READY_FOR_RESET`
- creating `_BOOTSTRAP.md` as the fresh-session entry point
- regenerating [ref:_LOOP_GATE.md|v:current|tags:validator,gate|src:system]

### 2) Fresh Session Entry

The canonical entry sequence is described in:
- [ref:_BOOTSTRAP.md|v:ephemeral|tags:bootstrap,entry|src:system] (ephemeral)
- [ref:NEURAL_CORTEX.md#ENTRY PROTOCOL (MANDATORY)|v:dynamic|tags:cortex,entry|src:system]

Key property: deleting `_BOOTSTRAP.md` after entry is the “loop has started” signal.

### 3) ACTIVE Work

During ACTIVE work:
- pick the next task from [ref:NEU.md#TASK QUEUE (PRIORITY ORDER)|v:dynamic|tags:tasks,active|src:system]
- create a report before non-trivial changes
- implement work, validate, and update pointers/state

### 4) FINALIZED

When all active tasks are done:
- pre-finalization validation must pass (see [ref:docs/OPS_PROTOCOLS.md#LOOP_FINALIZATION|v:1|tags:ops,finalization|src:doc])
- a single archive is produced for the loop

---

## AUTOMATION & GUARDRAILS

### Cockpit (Flask)

Primary operator UI + lifecycle automation:
- Server: [ref:loop_cockpit.py|v:dynamic|tags:code,cockpit|src:system]
- Start scripts:
  - Windows: [ref:START_COCKPIT.bat|v:1|tags:ops,run|src:system]
  - Unix: [ref:START_COCKPIT.sh|v:1|tags:ops,run|src:system]
- Dependencies: [ref:requirements_cockpit.txt|v:1|tags:deps|src:system]

CLI helpers (no server required):
- `python loop_cockpit.py --lint`
- `python loop_cockpit.py --generate-history-index`
- `python loop_cockpit.py --regenerate-loop-gate --reason cli`

### Guardrails (stdlib-only)

Deterministic generators and validators:
- [ref:loop_guardrails.py|v:dynamic|tags:code,guardrails|src:system]

Includes:
- reference parsing and format checks
- metadata lint
- history index generation
- session pack generation

### Structured Query Engine (search layer)

Deterministic context retrieval powered by the query index:
- Index generator: `python loop_cockpit.py --generate-query-index`
- Output: [ref:docs/QUERY_INDEX.json|v:dynamic|tags:index,query|src:system]
- API: `/api/query` + `/api/search` serve ranked results filtered by loop,
  tags, validation status, and touched files.
- UI: Loop Cockpit search panel consumes the API for real-time lookups.

This layer is stdlib-only and ships inside both the live repo and
SEED_TEMPLATE so every fresh project starts with the improved search engine.

---

## DIRECTORY MAP (WHAT LIVES WHERE)

- Root core:
  - [ref:PROJECT_TECH_BASELINE.md|v:immutable|tags:baseline,laws|src:system]
  - [ref:NEURAL_CORTEX.md|v:dynamic|tags:cortex,pointer|src:system]
  - [ref:NEU.md|v:dynamic|tags:tasks,active,pointer|src:system]
  - [ref:Alt.md|v:dynamic|tags:tasks,closed,pointer|src:system]
  - [ref:current.json|v:dynamic|tags:state|src:system]
  - [ref:_LOOP_GATE.md|v:current|tags:validator,gate|src:system]

- docs/
  - [ref:docs/OPS_PROTOCOLS.md|v:1|tags:ops|src:doc]
  - [ref:docs/HISTORY_INDEX.md|v:dynamic|tags:index,history|src:system]

- tasks/ (task specs)
- reports/ (task reports)
- archive/ (immutable loop archives)
- templates/ (cockpit UI templates)
- sync_seed_template.py (automation that keeps SEED_TEMPLATE mirrored with the
  live prototype)

---

## RELATED DOCS

- Operational protocols: [ref:docs/OPS_PROTOCOLS.md|v:1|tags:ops|src:doc]
- Generated history index: [ref:docs/HISTORY_INDEX.md|v:dynamic|tags:index,history|src:system]
- Seed template sync workflow: [ref:README.md|v:dynamic|tags:docs,seed|src:system]

---

## SEED TEMPLATE DISTRIBUTION (PROTOTYPE EXPORT)

- Canonical location: [ref:SEED_TEMPLATE/|v:dynamic|tags:seed|src:system]
- Sync helper: `python sync_seed_template.py` (supports `--dry-run`, `--only`,
  `--list`)
- Scope: cockpit automation, guardrails, requirements, documentation, and
  search/query tooling.
- Excludes: loop-specific state (current.json, archives, NEU/ALT pointers).

Running the sync helper after meaningful architecture changes guarantees the
seed package ships with the same query engine, docs, and guardrails as the
current loop, allowing future projects to start from a proven "prototype
finished" baseline.

---

END OF DOCUMENT

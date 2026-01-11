# REPORT: TASK_0026 - Historical Data Accessibility Concept (Link Map)

**REPORT ID:** report_TASK_0026_L15_v01.md  
**LOOP:** 15  
**TASK:** TASK_0026  
**DATE:** 2026-01-10  
**STATUS:** ✅ SUCCESS (concept delivered)

---

## SOURCE REFERENCE

[ref:task_TASK_0026.md|v:1|tags:task|src:user]

---

## OBJECTIVE

Define a concept that makes historical implementation context (archives/tasks/reports/code) faster to retrieve and navigate, so future work can start from prior decisions without re-reading many files.

---

## CONCEPT: "HISTORY LINK MAP" (Single Index + Graph)

### Core Problem
- Reports contain the best rationale, but they are not automatically “discoverable” from code files.
- Archives are immutable snapshots, but they are not queryable.
- Tasks (NEU/Alt) are pointers, but they don’t provide reverse lookups: “Given a file, which tasks/reports touched it?”

### Proposed Solution
Create a lightweight, automatically-generated index that links:
- **Code file → related tasks → related reports → related archives**
- **Task → reports → files touched**
- **Archive(loop) → tasks in that loop → reports produced**

This can be represented as both:
1) A machine-readable JSON (for cockpit UI/search), and
2) A human-readable Markdown summary (for quick scanning).

---

## DATA MODEL (Minimal)

### Inputs (already exist)
- Pointer docs: `NEU.md`, `Alt.md`, `NEURAL_CORTEX.md`
- Reports: `report_TASK_*`, `report_INCIDENT_*`
- Archives: `archive/ARCHIV_*.md`

### New derived outputs (generated)
- `history_index.json` (generated, not hand-edited)
  - `tasks`: id, title, loop, status, reportRefs
  - `reports`: id, loop, taskId/incidents, mentions
  - `files`: path, lastSeenInReports, relatedTaskIds
  - `loops`: loopId, archiveFile, tasks, reports

---

## LINKING STRATEGIES

### 1) Explicit linking (preferred)
Adopt a simple optional convention in reports:
- Add a section: `## FILES CHANGED` (already used in several reports)
- List paths one per line

This gives a deterministic mapping: report → files.

### 2) Implicit linking (fallback)
If a report lacks FILES CHANGED, derive associations by:
- Searching for backticked file names in report bodies
- Using git diff (if available) between loop timestamps (optional)

---

## COCKPIT UX (Small, High-Value)

Add a “History” panel with:
- Search box: file path or task id
- Result cards:
  - file → linked tasks/reports (most recent first)
  - task → linked reports + listed files
- Deep links:
  - open report/task/archive in editor

---

## PROCESS FIT / RULES

- Keeps pointer-only rule: NEU/Alt remain pointers.
- Keeps archives immutable: index is derived, not rewriting.
- REPORT-FIRST is reinforced: missing reports become obvious in the index.

---

## RECOMMENDED NEXT STEP (Future Task)

Implement a generator inside `loop_cockpit.py` (or separate script) that builds `history_index.json` by parsing:
- `Alt.md` for task list
- `report_TASK_*` for FILES CHANGED
- `archive/ARCHIV_*` for loop snapshots

Then expose as `/api/history-index` and render in cockpit.

---

## ACCEPTANCE CRITERIA STATUS

- [x] Concept defines a linked structure between scripts/code and tasks/reports/archives
- [x] Provides a minimal schema + deterministic linking approach
- [x] Includes a cockpit UI concept and a concrete next-implementation step

---

END OF REPORT

# TASK_0048

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T13:35:16Z

---

## SEED IDEA

Implement structured query layer for intelligent contextual search across loop history (reports, tasks, archives) to replace grep-style text search with metadata-aware filtering and relevance ranking.

---

## OBJECTIVE

Build Phase 1 of the search improvement plan: structured query system that extracts metadata from reports and tasks, generates a queryable index (QUERY_INDEX.json), and provides an API endpoint with filtering, ranking, and structured results.

This enables AI agents to efficiently retrieve relevant prior work using filters like:
- Task ID, loop number range, file modified
- Tags, validation status, recency
- Ranked by relevance instead of raw line matches

---

## ACCEPTANCE CRITERIA

- [ ] Add metadata extraction functions to loop_guardrails.py:
  - extract_report_metadata() → goal, files changed, validation status, tags, references
  - extract_task_metadata() → objective, status, related reports, tags
- [ ] Generate docs/QUERY_INDEX.json with structured data:
  - reports[] with full metadata
  - tasks[] with status and relationships
  - fileIndex{} for reverse lookups (file → tasks/reports)
  - conceptIndex{} for tag-based navigation
- [ ] Add /api/query endpoint to loop_cockpit.py with filtering:
  - text (keyword search across goals/objectives)
  - task_id, loop_num (range), file, tags, status, validation
  - sort (relevance, recency, loop_num)
  - Returns structured results with context snippets
- [ ] CLI helper: python loop_cockpit.py --generate-query-index
- [ ] Update cockpit UI with structured search features:
  - Filter controls (task, loop, file, tags)
  - Relevance-ranked results with context
  - Tag cloud or filter suggestions
- [ ] Deterministic, repeatable index generation
- [ ] Update ARCHITECTURE.md to document query system

---

## IMPLEMENTATION NOTES

### Metadata Extraction Patterns

**Report structure:**
```
## GOAL / OBJECTIVE
## FILES CHANGED
## VALIDATION
## WORK LOG
```

**Task structure:**
```
## OBJECTIVE
## ACCEPTANCE CRITERIA
STATUS: (from NEU.md or Alt.md)
```

**Reference extraction:**
- Use existing iter_refs() from loop_guardrails.py
- Extract tags from [ref:...|tags:x,y,z|...] patterns

### Ranking Algorithm (Simple TF-IDF)
- Term frequency in goal/objective
- Recency bonus (newer loops weighted higher)
- Validation success signal boost
- File overlap bonus (if querying specific file)

### File Index Structure
```json
"fileIndex": {
  "loop_cockpit.py": {
    "modifiedBy": ["TASK_0015", "TASK_0041"],
    "reports": ["report_TASK_0015_L12_v01.md", ...],
    "loopRange": [12, 24]
  }
}
```

---

## DEPENDENCIES

- None (stdlib-only implementation)
- Uses existing: loop_guardrails.py reference parsing
- Extends: loop_cockpit.py API surface
- Complements: existing /api/search (keep both for now)

---

## SUCCESS METRICS

- Query "tasks that modified loop_cockpit.py" returns filtered, ranked results
- Query "validation failures in loop 20-24" returns only failed validations
- Results include goal context, not just line matches
- Index generation completes in <2 seconds for current project size
- Structured results enable AI to quickly understand relevant prior work

---

## RELATED

- [ref:docs/SEARCH_IMPROVEMENT_PLAN.md|v:1|tags:plan,search|src:doc]
- [ref:reports/report_TASK_0041_L24_v01.md|v:1|tags:report,search|src:system]
- [ref:loop_guardrails.py|v:dynamic|tags:code,guardrails|src:system]
- [ref:loop_cockpit.py|v:dynamic|tags:code,cockpit|src:system]

---

END OF DOCUMENT

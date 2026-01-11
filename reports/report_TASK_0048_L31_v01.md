# REPORT: TASK_0048 - Structured Query Layer (Phase 1)

**REPORT ID:** reports/report_TASK_0048_L31_v01.md  
**LOOP:** 31  
**TASK:** TASK_0048  
**DATE:** 2026-01-10  
**STATUS:** ✅ SUCCESS

---

## SOURCE REFERENCE

[ref:tasks/task_TASK_0048.md|v:1|tags:task,search,query|src:system]

---

## GOAL

Implement Phase 1 of search improvement plan: build structured query system with metadata extraction, queryable index generation, and API endpoints for intelligent contextual search across loop history.

Replace grep-style line matching with metadata-aware filtering (task ID, loop range, file, tags, validation status) and relevance ranking.

---

## WORK LOG

- Started: 2026-01-10
- Completed: 2026-01-10

---

## CHANGES IMPLEMENTED

### 1. Metadata Extraction ([loop_guardrails.py](loop_guardrails.py))

**Added `extract_report_metadata()`:**
- Parses report structure: GOAL, FILES CHANGED, VALIDATION, dates
- Extracts task_id, loop_num, version from filename
- Determines validation pass/fail from STATUS or VALIDATION section
- Generates keywords from goal text (simple word extraction)
- Captures all [ref:...] citations and tags

**Added `extract_task_metadata()`:**
- Parses OBJECTIVE, SEED IDEA, STATUS
- Extracts CREATED/COMPLETED dates
- Captures references and tags
- Links tasks to their reports

**Added `query_index_data()`:**
- Generates complete queryable index with:
  - `reports[]` - all reports with full metadata
  - `tasks[]` - all tasks with status and relationships
  - `fileIndex{}` - reverse lookup: file → tasks/reports that modified it
  - `conceptIndex{}` - tag → tasks/reports using that tag
- Output: `docs/QUERY_INDEX.json`

### 2. Query API Endpoint ([loop_cockpit.py](loop_cockpit.py))

**Added `POST /api/query`:**
- Accepts filters:
  - `text` - keyword search across goals/objectives
  - `task_id` - filter by specific task
  - `loop_min`, `loop_max` - filter by loop range
  - `file` - filter by files modified
  - `tags` - filter by tag list
  - `validation` - filter by pass/fail status
  - `sort` - relevance | recency | loop_num
  - `limit` - max results
- Returns structured results with:
  - Report ID, path, task ID, loop number
  - Goal snippet (first 200 chars)
  - Files changed, validation status, tags
  - Relevance-ranked or sorted by recency/loop

**Added `GET /api/file-index`:**
- Returns file → tasks/reports mapping
- Optional `?file=loop_cockpit.py` filter for single file lookup

**Added `GET /api/concept-index`:**
- Returns tag → tasks/reports mapping
- Optional `?tag=search` filter for single concept lookup

### 3. CLI Support ([loop_cockpit.py](loop_cockpit.py))

**Added `--generate-query-index`:**
```bash
python loop_cockpit.py --generate-query-index
```
- Generates `docs/QUERY_INDEX.json`
- Prints summary: report count, task count, files indexed, concepts

### 4. Files Modified

- [loop_guardrails.py](loop_guardrails.py) - metadata extractors, query index generator
- [loop_cockpit.py](loop_cockpit.py) - API endpoints, CLI integration
- Generated: [docs/QUERY_INDEX.json](docs/QUERY_INDEX.json)

---

## VALIDATION

### Query Index Generation
```bash
$ python loop_cockpit.py --generate-query-index
✓ Generated D:\Keeper-Clean\docs\QUERY_INDEX.json
  Reports: 55
  Tasks: 48
  Files indexed: 21
  Concepts/tags: 45
```

### Sample Query Index Structure
```json
{
  "reports": [
    {
      "id": "report_TASK_0041_L24_v01",
      "taskId": "TASK_0041",
      "loopNum": 24,
      "goal": "Improve cross-loop context retrieval...",
      "filesChanged": ["loop_cockpit.py", "templates/cockpit.html"],
      "validationPassed": true,
      "keywords": ["agent", "amnesia", "context", "search", ...],
      "tags": ["task", "search"]
    }
  ],
  "fileIndex": {
    "loop_cockpit.py": {
      "modifiedBy": ["TASK_0031", "TASK_0035", "TASK_0036", "TASK_0040"],
      "reports": ["D:/Keeper-Clean/reports/report_TASK_0031_L20_v01.md", ...],
      "loopRange": [20, 24]
    }
  },
  "conceptIndex": {
    "search": {
      "tasks": ["TASK_0041"],
      "reports": ["report_TASK_0041_L24_v01"]
    }
  }
}
```

### API Tests (Manual)
- POST `/api/query` with `{"text": "validation", "loop_min": 20}` → returns filtered reports
- GET `/api/file-index?file=loop_cockpit.py` → returns all tasks that modified that file
- GET `/api/concept-index?tag=search` → returns all search-related tasks/reports

---

## BENEFITS FOR AI CONTEXTUAL RESEARCH

**Before (grep search):**
- ❌ Returns raw line matches with no context
- ❌ No way to filter by loop, file, validation status
- ❌ Results not ranked by relevance
- ❌ Can't ask "what tasks touched file X?"

**After (structured query):**
- ✅ Filter by task ID, loop range, file, tags, validation
- ✅ Relevance ranking (keyword match + recency + validation success)
- ✅ Structured results with goal snippets and context
- ✅ Reverse lookups: file → tasks, concept → reports
- ✅ Keyword extraction for semantic similarity (basic)

**Example queries now possible:**
- "Reports that modified loop_cockpit.py in loops 20-25"
- "Failed validations in last 5 loops"
- "Tasks tagged with 'pointer-only'"
- "All search-related work across project history"

---

## NEXT STEPS (Future Tasks)

1. **UI Integration:** Add structured query panel to cockpit with filter controls
2. **Keyword Expansion:** Add synonym/concept mapping for better semantic matching
3. **Performance:** If archive grows >100 loops, migrate to SQLite with FTS5
4. **Auto-Regeneration:** Trigger query index generation on loop finalization

---

## ACCEPTANCE CRITERIA

- [x] Add metadata extraction functions to loop_guardrails.py
- [x] Generate docs/QUERY_INDEX.json with structured data
- [x] Add /api/query endpoint with filtering and ranking
- [x] CLI helper: python loop_cockpit.py --generate-query-index
- [ ] Update cockpit UI with structured search features (deferred to next task)
- [x] Deterministic, repeatable index generation
- [ ] Update ARCHITECTURE.md to document query system (deferred)

---

## RELATED DOCS

- [ref:docs/SEARCH_IMPROVEMENT_PLAN.md|v:1|tags:plan,search|src:doc]
- [ref:reports/report_TASK_0041_L24_v01.md|v:1|tags:report,search|src:system]

---

END OF REPORT

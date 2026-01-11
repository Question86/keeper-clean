# SEARCH & CONTEXT RETRIEVAL IMPROVEMENT PLAN

MODE: PLANNING
CREATED: 2026-01-10
STATUS: DRAFT

---

## PROBLEM STATEMENT

**Current limitation:** Grep-style text search is inefficient for AI contextual research across growing loop history.

**Why this matters:**
- AI agents enter each loop with "amnesia by design"
- Must rapidly reconstruct project context from artifacts
- Current search returns raw line matches with no semantic understanding
- Signal-to-noise ratio degrades as archives grow
- No way to ask "what patterns failed?" or "which tasks touched validation?"

---

## PHASE 1: STRUCTURED QUERY LAYER (Stdlib-only, ~3-5 hours)

**Objective:** Maximize AI context retrieval efficiency without external dependencies.

### 1.1 Enhanced Metadata Extraction

**Add to loop_guardrails.py:**
```python
def extract_report_metadata(report_path: Path) -> Dict[str, Any]:
    """Parse structured sections from report."""
    - GOAL (objective/intent)
    - FILES CHANGED (concrete modifications)
    - VALIDATION (success/failure markers)
    - WORK LOG (dates)
    - Related task_id, loop_num
    - Extract all [ref:...] citations
```

**Add to loop_guardrails.py:**
```python
def extract_task_metadata(task_path: Path) -> Dict[str, Any]:
    """Parse task structure."""
    - OBJECTIVE (what to accomplish)
    - ACCEPTANCE CRITERIA (completion markers)
    - STATUS (from NEU/Alt pointer docs)
    - Related reports (reverse lookup)
    - Tags from references
```

### 1.2 Queryable Index Structure

**Create docs/QUERY_INDEX.json (auto-generated):**
```json
{
  "generatedAt": "2026-01-10T...",
  "reports": [
    {
      "id": "TASK_0041_L24_v01",
      "taskId": "TASK_0041",
      "loopNum": 24,
      "goal": "Improve Cross-Loop Context Retrieval",
      "filesChanged": ["loop_cockpit.py", "templates/cockpit.html"],
      "tags": ["search", "context", "cockpit"],
      "references": [...],
      "keywords": ["search", "index", "query", "context"],
      "validationPassed": true,
      "dateCompleted": "2026-01-10"
    }
  ],
  "tasks": [
    {
      "id": "TASK_0041",
      "status": "CLOSED",
      "objective": "...",
      "reports": ["report_TASK_0041_L24_v01.md"],
      "tags": ["search", "improvement"],
      "closedInLoop": 24
    }
  ],
  "fileIndex": {
    "loop_cockpit.py": {
      "modifiedBy": ["TASK_0015", "TASK_0041", ...],
      "reports": ["report_TASK_0015_L12_v01.md", ...],
      "loopRange": [12, 24]
    }
  },
  "conceptIndex": {
    "pointer-only": {
      "tasks": ["TASK_0004", "TASK_0022"],
      "reports": [...],
      "relevance": "core rule"
    }
  }
}
```

### 1.3 Smart Query Engine

**Add to loop_cockpit.py:**
```python
@app.route('/api/query', methods=['POST'])
def api_query():
    """Structured query with filtering and ranking.
    
    Query params:
    - text: free text search (across goals/objectives/keywords)
    - task_id: filter by task
    - loop_num: filter by loop (or range: loop_min, loop_max)
    - file: filter by files changed
    - tags: filter by tag list
    - status: filter by task status
    - validation: filter by validation pass/fail
    - sort: 'relevance' | 'recency' | 'loop_num'
    - limit: max results
    """
    # Load QUERY_INDEX.json
    # Apply filters
    # Rank results (TF-IDF for text, recency weight)
    # Return structured results with context
```

**Result format:**
```json
{
  "results": [
    {
      "type": "report",
      "id": "TASK_0041_L24_v01",
      "relevance": 0.89,
      "snippet": "Added bounded workspace search...",
      "context": {
        "task": "TASK_0041",
        "loop": 24,
        "goal": "Improve Cross-Loop Context Retrieval",
        "filesChanged": ["loop_cockpit.py"]
      }
    }
  ],
  "filters": {...},
  "total": 3
}
```

### 1.4 AI-Optimized Search UI

**Add to cockpit:**
- Pre-made query templates: "Recent validation failures", "Tasks touching X file", "Concept Y evolution"
- Tag cloud (clickable filter)
- Timeline view (by loop)
- File-centric view (reverse lookup: file → tasks → reports)

---

## PHASE 2: SEMANTIC LAYER (Optional, Low-Cost, ~2-3 hours)

**Objective:** Add semantic similarity without external services.

### Option A: Lightweight Keyword Expansion (Stdlib)
```python
# Simple synonym/concept mapping (hand-curated or rule-based)
CONCEPT_MAP = {
    "pointer-only": ["navigation", "link", "reference-only"],
    "REPORT-FIRST": ["documentation", "compliance", "pre-commit"],
    "validation": ["lint", "check", "verify", "audit"]
}
# Expand query with related terms before search
```

### Option B: Local Embeddings (Requires sentence-transformers)
- **Tradeoff:** Adds dependency, but highly effective
- Generate embeddings for report goals/objectives (one-time, cached)
- Query with semantic similarity instead of keyword match
- **Cost:** ~50MB model, <1s query time

---

## PHASE 3: DATABASE CONSIDERATION (For Scale)

### When to Add a Database?

**Trigger thresholds:**
- \> 100 loops (archive search becomes slow)
- \> 500 reports (grep search becomes bloated)
- \> 50MB total markdown (index JSON becomes unwieldy)

**Current project status:**
- Loop 24 (current)
- ~50 reports
- Archive size: manageable

**Verdict: NOT YET NEEDED** for this project size.

### If Database Becomes Necessary

**Best fit: SQLite (stdlib in Python 3)**

**Schema:**
```sql
CREATE TABLE reports (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    loop_num INTEGER,
    goal TEXT,
    files_changed TEXT,  -- JSON array
    tags TEXT,           -- JSON array
    content_full TEXT,   -- Full text index
    validation_passed BOOLEAN,
    date_completed TEXT
);

CREATE INDEX idx_task ON reports(task_id);
CREATE INDEX idx_loop ON reports(loop_num);
CREATE VIRTUAL TABLE reports_fts USING fts5(goal, content_full);
```

**Benefits:**
- Full-text search (FTS5) built-in
- Complex queries (JOIN, GROUP BY, aggregate)
- Scales to 1000+ loops
- Still stdlib (no external deps)

**Costs:**
- Adds state (database file must be regenerated on archive changes)
- Breaks "pure markdown" philosophy slightly
- Migration effort

---

## PHASE 4: LONG-TERM SCALABILITY (Hypothetical)

**For enterprise-scale projects (1000+ loops, 10+ years):**

### Vector Database Option
- Pinecone, Weaviate, Milvio, or ChromaDB
- Semantic search at scale
- Handles multi-language, fuzzy matching
- **Cost:** External service or heavy local infra

### Hybrid Approach
```
- Core system: Markdown + SQLite (deterministic)
- Optional layer: Vector index (regenerated from SQLite)
- Query flow: Vector search → SQLite filter → Markdown source
```

---

## RECOMMENDED IMPLEMENTATION ORDER

### Immediate (This Loop or Next)
1. ✅ Implement Phase 1.1-1.2: Enhanced metadata extraction + QUERY_INDEX.json
2. ✅ Add Phase 1.3: `/api/query` endpoint with filtering

### Short-Term (Next 2-3 Loops)
3. ✅ Add Phase 1.4: Cockpit query UI improvements
4. ⚠️ Evaluate Phase 2 Option A: Lightweight keyword expansion

### Medium-Term (When archive > 100 loops)
5. ⚠️ Migrate to SQLite with FTS5
6. ⚠️ Keep markdown as source of truth, database as generated cache

### Long-Term (If project scales to enterprise)
7. ⚠️ Evaluate vector embeddings or external search service

---

## IMPACT ON AI CONTEXTUAL RESEARCH

### Current Capabilities
- ❌ Can't find "similar past failures"
- ❌ Can't filter by loop range or validation status
- ❌ Can't ask "what tasks modified X file?"
- ❌ Results are unranked noise

### After Phase 1 (Structured Query)
- ✅ Filter by: task, loop, file, tag, status
- ✅ Rank by: relevance, recency
- ✅ Structured context (goal, files, validation)
- ✅ Reverse lookups (file → tasks)

### After Phase 2 (Semantic)
- ✅ Find conceptually similar work
- ✅ Query with natural language
- ✅ Synonym/concept expansion

### After Phase 3 (SQLite)
- ✅ Complex aggregations ("how many tasks touched validation in loop 10-20?")
- ✅ Fast full-text search
- ✅ Scales to 1000+ loops

---

## OPEN QUESTIONS

1. **Should we break stdlib-only rule for Phase 2 embeddings?**
   - Pro: Massive quality improvement for AI research
   - Con: Adds dependency (sentence-transformers)

2. **When do we trigger SQLite migration?**
   - Suggest: After loop 50 or archive > 20MB

3. **Do we need real-time indexing or on-demand regeneration?**
   - Current design: Regenerate index on loop finalization (deterministic)
   - Alternative: Incremental updates (faster but more complex)

---

## NEXT STEPS

If approved:
1. Create TASK specification for Phase 1 implementation
2. Implement metadata extractors in loop_guardrails.py
3. Add QUERY_INDEX.json generation
4. Build `/api/query` endpoint
5. Update cockpit UI with structured search

---

END OF PLAN

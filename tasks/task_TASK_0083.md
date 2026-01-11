# TASK_0083: Context Index Generator

MODE: IMPLEMENTATION
STATUS: COMPLETED
CREATED: 2026-01-11T03:20:32Z
COMPLETED: 2026-01-11T03:49:30Z
SOURCE: TASK_0071 EPIC - Phase 2 (Context Accessibility)

---

## OBJECTIVE

Create automatic context index generator that produces `docs/CONTEXT_INDEX.json` with current loop state, active tasks, and recent decisions for faster AI onboarding.

## CONTEXT

Each new AI session spends significant time re-discovering project state. A pre-generated context index reduces this overhead.

## SCOPE

1. Create `--generate-context-index` CLI flag
2. Generate JSON with: current loop, active tasks, recent reports, key decisions
3. Auto-regenerate on loop state changes
4. Include in _SESSION.md for easy access
5. Add `/api/context-index` endpoint

## ACCEPTANCE CRITERIA

- [x] CLI generates valid JSON index
- [x] Index includes all active tasks from NEU.md
- [x] Index includes last 5 completed tasks
- [x] Index includes current loop metadata
- [x] API endpoint returns index
- [x] Index regenerates on state changes

## TESTING

```python
def test_context_index():
    result = generate_context_index()
    assert "currentLoop" in result
    assert "activeTasks" in result
    assert isinstance(result["activeTasks"], list)
    assert validate_json_schema(result, CONTEXT_INDEX_SCHEMA)
```

## DEPENDENCIES

- Phase 1 complete

---

END OF DOCUMENT

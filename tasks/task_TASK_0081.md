# TASK_0081: Auto-Pointer Generator

MODE: IMPLEMENTATION
STATUS: COMPLETED
CREATED: 2026-01-11T03:20:32Z
COMPLETED: 2026-01-11T03:34:00Z
SOURCE: TASK_0071 EPIC - Phase 1 (Error Reduction)

---

## OBJECTIVE

Create automatic pointer reference generator to eliminate manual formatting errors and ensure all references follow canonical format.

## CONTEXT

Manual pointer creation is error-prone. The format `[ref:PATH|v:VERSION|tags:...|src:...]` requires exact syntax. This task automates generation.

## SCOPE

1. Create `generate_pointer_ref(path, tags, src, version)` function in loop_guardrails.py
2. Add `/api/generate-pointer` endpoint to cockpit
3. Add "Copy Pointer" button in cockpit UI next to task listings
4. Lint validates all references match canonical format

## ACCEPTANCE CRITERIA

- [x] Function generates valid pointer syntax
- [x] API endpoint returns formatted pointer
- [x] UI button copies pointer to clipboard
- [x] Lint catches malformed pointers
- [x] Unit tests pass

## TESTING

```python
def test_pointer_generation():
    result = generate_pointer_ref("tasks/task_TASK_0001.md", ["active"], "user", "1")
    assert result == "[ref:tasks/task_TASK_0001.md|v:1|tags:active|src:user]"
```

## DEPENDENCIES

- Phase 0 complete (test infrastructure)

---

END OF DOCUMENT

# REPORT: TASK_0084 - Loop Digest Generator

**TASK:** TASK_0084
**LOOP:** 46
**VERSION:** v01
**STATUS:** IN_PROGRESS
**CREATED:** 2026-01-11T03:30:00Z

---

## OBJECTIVE

Implement auto-generation of concise 1-page summary digests for archived loops, enabling quick historical context retrieval.

## APPROACH

1. Create `generate_loop_digest(loop_num, workspace_root)` function in loop_guardrails.py
2. Parse archive file for structured data:
   - Loop metadata (status, date, finalized_at)
   - Tasks completed with summaries
   - Key decisions
   - Files modified/created
3. Generate `archive/DIGEST_XXXX.md` with <500 lines
4. Add `--generate-digest LOOP_NUM` CLI flag
5. Return digest content and file path

## IMPLEMENTATION DETAILS

### Digest Structure
```markdown
# DIGEST_XXXX - Loop XX Summary

**Loop:** XX | **Date:** YYYY-MM-DD | **Tasks:** N

## Tasks Completed
| Task | Summary |
|------|---------|
| TASK_XXXX | Brief summary |

## Key Decisions
- Decision 1
- Decision 2

## Files Modified
- file1.py
- file2.md

## Metrics
- Tasks Completed: N
- Files Modified: N
```

### Function Signature
```python
def generate_loop_digest(loop_num: int, workspace_root: str) -> dict:
    """
    Generate a concise digest for an archived loop.
    
    Returns:
        {
            "success": bool,
            "digestPath": str,
            "lineCount": int,
            "content": str
        }
    """
```

## ACCEPTANCE CRITERIA MAPPING

- [ ] CLI generates digest for specified loop → `--generate-digest LOOP_NUM`
- [ ] Digest is <500 lines → Enforced in generator
- [ ] Digest includes task summary table → `## Tasks Completed` section
- [ ] Digest includes key decisions section → `## Key Decisions`
- [ ] Digest includes files modified list → `## Files Modified`
- [ ] Auto-generates during finalization → Hook in finalize flow

## TESTING PLAN

```python
# Test digest generation
python loop_cockpit.py --generate-digest 45
# Verify output exists at archive/DIGEST_0045.md
# Verify line count < 500
```

## REFERENCES

- [ref:tasks/task_TASK_0084.md|v:1|tags:spec|src:system]
- [ref:loop_guardrails.py|v:dynamic|tags:implementation|src:system]
- [ref:loop_cockpit.py|v:dynamic|tags:cli|src:system]

---

## WORK LOG

### Entry 1 - Initial Implementation
- Created report (REPORT-FIRST)
- Planning function structure
- Next: Implement generate_loop_digest()

---

END OF REPORT

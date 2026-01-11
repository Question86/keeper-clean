# REPORT: TASK_0085 - Task Dependency Graph

**TASK:** TASK_0085
**LOOP:** 46
**VERSION:** v01
**STATUS:** IN_PROGRESS
**CREATED:** 2026-01-11T04:05:00Z

---

## OBJECTIVE

Create task dependency graph API that analyzes file references to determine task relationships and enable smart ordering for multi-agent parallelization.

## APPROACH

1. Create `get_task_dependencies(workspace_root)` function in loop_guardrails.py
2. Parse task specs for file references from:
   - SCOPE sections (files to modify)
   - DELIVERABLES sections
   - Dependencies listed
3. Build graph structure:
   ```json
   {
     "nodes": [{"id": "TASK_0081", "status": "COMPLETED", ...}],
     "edges": [{"source": "TASK_0085", "target": "TASK_0083", "type": "depends"}],
     "clusters": {"parallel": [...], "sequential": [...]}
   }
   ```
4. Identify:
   - File-based dependencies (shared files)
   - Explicit dependencies (Depends: field)
   - Parallel clusters (tasks that can run simultaneously)
5. Expose via `/api/task-dependencies` endpoint

## IMPLEMENTATION DETAILS

### Graph Structure
```python
def get_task_dependencies(workspace_root: Path) -> Dict[str, Any]:
    """
    Build task dependency graph for active tasks.
    
    Returns:
        {
            "nodes": List of task nodes with id, status, files
            "edges": List of dependency edges with source, target, type
            "clusters": Groups of parallel/sequential tasks
            "meta": Statistics about the graph
        }
    """
```

### Dependency Types
- `depends` - Explicit dependency via Depends: field
- `file-shared` - Implicit dependency via shared file modification
- `phase` - Same phase grouping (can parallelize)

## ACCEPTANCE CRITERIA MAPPING

- [ ] API returns valid dependency graph → `/api/task-dependencies`
- [ ] Graph identifies file-based dependencies → Parse SCOPE sections
- [ ] Parallel clusters correctly identified → Group by phase, no file overlap
- [ ] No orphan nodes in graph → All NEU.md tasks included
- [ ] Graph is DAG for non-blocked tasks → Validate acyclic structure
- [ ] 3D visualization can consume API output → Return D3-compatible format

## REFERENCES

- [ref:tasks/task_TASK_0085.md|v:1|tags:spec|src:system]
- [ref:loop_guardrails.py|v:dynamic|tags:implementation|src:system]
- [ref:loop_cockpit.py|v:dynamic|tags:api|src:system]

---

## WORK LOG

### Entry 1 - Initial Implementation
- Created report (REPORT-FIRST)
- Planning graph data structure
- Next: Implement get_task_dependencies()

---

END OF REPORT

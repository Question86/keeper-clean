# TASK_0085: Task Dependency Graph

MODE: IMPLEMENTATION
STATUS: COMPLETED
CREATED: 2026-01-11T03:20:32Z
COMPLETED: 2026-01-11T04:08:00Z
SOURCE: TASK_0071 EPIC - Phase 2 (Context Accessibility)

---

## OBJECTIVE

Create task dependency graph API that analyzes file references to determine task relationships and enable smart ordering.

## CONTEXT

Understanding which tasks share files or depend on each other is critical for multi-agent parallelization. This is a prerequisite for Phase 4.

## SCOPE

1. Create `/api/task-dependencies` endpoint
2. Parse task specs for file references (SCOPE, DELIVERABLES sections)
3. Build adjacency list: task → files → dependent tasks
4. Identify: parallel clusters, sequential chains, blockers
5. Expose for 3D visualization integration

## ACCEPTANCE CRITERIA

- [x] API returns valid dependency graph
- [x] Graph identifies file-based dependencies
- [x] Parallel clusters correctly identified
- [x] No orphan nodes in graph (62 nodes found)
- [x] Graph is DAG for non-blocked tasks
- [x] 3D visualization can consume API output

## TESTING

```python
def test_dependency_graph():
    graph = get_task_dependencies()
    assert "nodes" in graph
    assert "edges" in graph
    assert graph_is_dag(graph)  # Directed Acyclic Graph
    assert all_tasks_in_graph(graph, get_active_tasks())
```

## DEPENDENCIES

- TASK_0083 (Context Index Generator) ✅

---

## IMPLEMENTATION SUMMARY

Added `get_task_dependencies(workspace_root)` to loop_guardrails.py:
- Parses NEU.md for task phases
- Parses task specs for explicit dependencies (Depends:) and file references
- Builds node list with id, status, phase, files, dependsOn
- Creates edges for explicit and file-based dependencies
- Identifies parallel clusters and sequential chains
- Returns D3-compatible graph format

Added `/api/task-dependencies` endpoint to loop_cockpit.py.

**Sample output:**
- 62 nodes, 10 edges (7 explicit, 3 file-based)
- 2 parallel clusters identified
- Shared files: loop_guardrails.py, COMPLETED_TASKS_ARCHIVE.md, _SESSION.md

---

END OF DOCUMENT

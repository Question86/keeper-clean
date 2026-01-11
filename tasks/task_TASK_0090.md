# TASK_0090: Git Worktree Manager

MODE: IMPLEMENTATION
STATUS: COMPLETED
CREATED: 2026-01-11T03:20:32Z
COMPLETED: 2026-01-11T05:11:38Z
SOURCE: TASK_0071 EPIC - Phase 4 (Multi-Agent Core)

---

## OBJECTIVE

Implement git worktree management system for agent isolation - create, manage, merge, and cleanup worktrees for parallel execution.

## CONTEXT

Multi-agent parallel execution requires isolated working directories. Git worktrees provide this without full clones. Each agent works in its own worktree, then merges back.

## SCOPE

1. Create `WorktreeManager` class
2. Methods: create_worktree(), merge_worktree(), cleanup_worktree()
3. Tag main branch before parallel work for rollback
4. Atomic merge with conflict detection
5. Auto-cleanup on success or rollback on failure

## ACCEPTANCE CRITERIA

- [x] Worktrees created in isolated directories
- [x] Each worktree has independent file state
- [x] Merge combines changes atomically
- [x] Conflicts detected before merge commit
- [x] Rollback restores pre-parallel state
- [x] Cleanup removes worktree directories
- [x] No orphan worktrees after session

## TESTING

```python
def test_worktree_lifecycle():
    manager = WorktreeManager()
    # Create
    wt = manager.create_worktree("agent-1", "TASK_0001")
    assert os.path.exists(wt.path)
    # Modify in worktree
    write_file(wt.path / "test.txt", "content")
    # Merge
    result = manager.merge_worktree(wt)
    assert result.success
    assert os.path.exists("test.txt")
    # Cleanup
    manager.cleanup_worktree(wt)
    assert not os.path.exists(wt.path)
```

## DEPENDENCIES

- TASK_0089 (Parallelization Analyzer)

## RISKS

- Merge conflicts in shared files (mitigated by analyzer)
- Orphan worktrees on crash (mitigated by cleanup on startup)
- Git state corruption (mitigated by pre-parallel tags)

---

END OF DOCUMENT

# MULTI-AGENT INFRASTRUCTURE REQUIREMENTS

MODE: DOCUMENTATION
VERSION: 1
CREATED: 2026-01-11T16:00:00Z
TASK: TASK_0103

---

## 1. OVERVIEW

This document specifies the requirements for the multi-agent orchestrator infrastructure, defining what the system must do to achieve production-ready parallel task processing.

---

## 2. FUNCTIONAL REQUIREMENTS

### 2.1 Task Analysis (FR-001)

| ID | Requirement | Implementation |
|----|-------------|----------------|
| FR-001.1 | Analyze tasks for parallelization potential | `analyze_parallelization()` in loop_guardrails.py |
| FR-001.2 | Detect file conflicts between task specifications | `analyze_tasks()` method parses task specs for touched files |
| FR-001.3 | Generate parallelizable task clusters | Returns `parallelizable` and `sequential` groupings |
| FR-001.4 | Return dependency information | `get_task_dependencies()` extracts from task spec files |

**API Endpoints:**
- `GET/POST /api/orchestrator/analyze` - Analyze task parallelization
- `POST /api/orchestrator/analyze-conflicts` - Detailed conflict analysis

---

### 2.2 Worktree Management (FR-002)

| ID | Requirement | Implementation |
|----|-------------|----------------|
| FR-002.1 | Create isolated git worktrees for each agent | `WorktreeManager.create_worktree()` |
| FR-002.2 | Track worktree state (path, branch, agent binding) | `Worktree` dataclass |
| FR-002.3 | List all active worktrees | `WorktreeManager.list_worktrees()` |
| FR-002.4 | Merge worktrees back to main branch | `WorktreeManager.merge_worktree()` |
| FR-002.5 | Clean up worktrees after use | `WorktreeManager.cleanup_all()` |
| FR-002.6 | Support rollback to pre-parallel state | `rollback_to_tag()` with pre-parallel tags |

**API Endpoints:**
- `GET /api/worktree` - List worktrees
- `POST /api/worktree/create` - Create new worktree
- `POST /api/worktree/merge` - Merge worktree
- `POST /api/worktree/cleanup` - Clean up worktrees
- `POST /api/worktree/rollback` - Rollback to tag

---

### 2.3 Agent Session Management (FR-003)

| ID | Requirement | Implementation |
|----|-------------|----------------|
| FR-003.1 | Create agent sessions with unique IDs | `AgentSession` dataclass, UUID generation |
| FR-003.2 | Track session state (pending/spawned/working/completed/failed) | `status` field with state machine |
| FR-003.3 | Track session progress (0-100%) | `progress` field |
| FR-003.4 | Persist session state to files | `_create_session_file()`, `_read_session_file()` |
| FR-003.5 | Poll session files for updates | `poll_session_status()`, `poll_all_sessions()` |
| FR-003.6 | Support session timeout | `agent_timeout_seconds` config |

**Session File Format (_AGENT_SESSION.json):**
```json
{
    "agent_id": "agent-task_0001-a1b2c3d4",
    "task_id": "TASK_0001",
    "status": "working",
    "progress": 45,
    "started_at": "2026-01-11T16:00:00Z",
    "completed_at": null,
    "error": null,
    "result_summary": null,
    "last_update": "2026-01-11T16:05:00Z"
}
```

---

### 2.4 Agent Spawning (FR-004)

| ID | Requirement | Implementation |
|----|-------------|----------------|
| FR-004.1 | Spawn agents in isolated worktrees | `spawn_agent()` creates session file |
| FR-004.2 | Generate standardized agent prompts | `generateAgentPrompt()` in agentSpawner.ts |
| FR-004.3 | Integrate with VS Code Language Model API | `vscode.lm.selectChatModels()` |
| FR-004.4 | Support model selection (Copilot GPT-4o) | `vendor: 'copilot', family: 'gpt-4o'` |
| FR-004.5 | Handle agent completion events | Async response collection |
| FR-004.6 | Capture and report agent errors | `LanguageModelError` handling |

**Extension Commands:**
- `keeper.checkAgentCapability` - Verify Copilot availability
- `keeper.spawnAgent` - Spawn an agent
- `keeper.showAgentOutput` - View agent logs

---

### 2.5 Orchestration Workflow (FR-005)

| ID | Requirement | Implementation |
|----|-------------|----------------|
| FR-005.1 | Execute full parallel workflow | `execute_parallel()` method |
| FR-005.2 | Automatic pre-parallel tagging | `tag_pre_parallel()` creates safety tag |
| FR-005.3 | Wait for agent completion | `wait_for_completion()` with polling |
| FR-005.4 | Auto-merge on success | `merge_results()` with configurable flag |
| FR-005.5 | Auto-cleanup after execution | `cleanup()` with configurable flag |
| FR-005.6 | Return orchestration metrics | `OrchestrationResult` dataclass |

**Orchestration Sequence:**
1. `prepare_parallel_execution()` - Create worktrees and sessions
2. `spawn_all_agents()` - Initialize all agents
3. `wait_for_completion()` - Poll until done or timeout
4. `merge_results()` - Merge completed worktrees
5. `cleanup()` - Remove temporary resources

---

### 2.6 Conflict Prevention (FR-006)

| ID | Requirement | Implementation |
|----|-------------|----------------|
| FR-006.1 | Detect overlapping file modifications | Conflict analysis in `analyze_tasks()` |
| FR-006.2 | Display visual warnings in UI | Cockpit conflict panel (TASK_0098) |
| FR-006.3 | Allow override for advanced users | `force` parameter on merge |
| FR-006.4 | Group tasks into sequential clusters | Cluster generation in analysis |

---

## 3. NON-FUNCTIONAL REQUIREMENTS

### 3.1 Performance (NFR-001)

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001.1 | Maximum parallel agents | 4 (configurable) |
| NFR-001.2 | Session poll interval | 5 seconds (configurable) |
| NFR-001.3 | Agent timeout | 3600 seconds (1 hour) |
| NFR-001.4 | Git command timeout | 30 seconds |
| NFR-001.5 | Worktree creation time | < 5 seconds per worktree |

---

### 3.2 Reliability (NFR-002)

| ID | Requirement | Implementation |
|----|-------------|----------------|
| NFR-002.1 | Atomic state transitions | Thread lock `_state_lock` |
| NFR-002.2 | Rollback on failure | Pre-parallel tags + `rollback_to_tag()` |
| NFR-002.3 | Session state persistence | JSON session files in worktrees |
| NFR-002.4 | Graceful timeout handling | `subprocess.TimeoutExpired` handling |
| NFR-002.5 | Error capture and reporting | `errors` list in OrchestrationResult |

---

### 3.3 Scalability (NFR-003)

| ID | Requirement | Notes |
|----|-------------|-------|
| NFR-003.1 | Configurable agent count | `max_parallel_agents` parameter |
| NFR-003.2 | Independent worktree execution | Each agent has isolated git branch |
| NFR-003.3 | Efficient polling | Configurable `session_poll_interval` |

---

### 3.4 Observability (NFR-004)

| ID | Requirement | Implementation |
|----|-------------|----------------|
| NFR-004.1 | Real-time status dashboard | Cockpit orchestrator panel (TASK_0097) |
| NFR-004.2 | Agent timeline visualization | Timeline component in cockpit.html |
| NFR-004.3 | Progress metrics | `time_saved_seconds`, efficiency calculations |
| NFR-004.4 | Agent output logging | VS Code output channel |
| NFR-004.5 | State transition logging | `_state_transition.log` |

---

## 4. EXTERNAL DEPENDENCIES

### 4.1 Git (DEP-001)

| Requirement | Version | Check |
|-------------|---------|-------|
| Git installed and in PATH | >= 2.20 | `git --version` |
| Repository initialized | - | `git rev-parse --git-dir` |
| Clean working directory | - | No uncommitted changes blocking worktree |

**Verification Command:**
```bash
git --version
git status --porcelain
```

---

### 4.2 VS Code (DEP-002)

| Requirement | Version | Check |
|-------------|---------|-------|
| VS Code | >= 1.90 | Required for Language Model API |
| vscode.lm API | Proposed | Available in recent VS Code |
| Keeper Extension | Installed | Extension activation |

---

### 4.3 GitHub Copilot (DEP-003)

| Requirement | Check |
|-------------|-------|
| GitHub Copilot extension installed | Extension list |
| User authenticated | Copilot status bar |
| Active subscription | Model selection succeeds |

**Verification Command (VS Code):**
```
Command Palette > "Keeper: Check Agent Capability"
```

---

### 4.4 Python (DEP-004)

| Requirement | Version | Packages |
|-------------|---------|----------|
| Python | >= 3.8 | flask, flask-cors |
| loop_cockpit.py | Running | Server on port 5000 |

**Verification:**
```bash
python --version
pip list | grep -i flask
curl http://localhost:5000/api/status
```

---

## 5. PREREQUISITE CONDITIONS

### 5.1 Before Orchestration

| # | Condition | Validation |
|---|-----------|------------|
| 1 | Git repository initialized | `WorktreeManager.is_git_repo()` |
| 2 | Working directory clean (or committed) | No merge conflicts |
| 3 | Task specifications exist | Files in tasks/task_TASK_XXXX.md |
| 4 | Loop cockpit running | `/api/status` returns OK |
| 5 | VS Code extension connected | Status bar shows "Connected" |

### 5.2 During Orchestration

| # | Condition | Notes |
|---|-----------|-------|
| 1 | No manual git operations | Worktrees managed by orchestrator |
| 2 | No file modifications in worktree paths | Agents own their worktrees |
| 3 | Network available (for Copilot) | Model requests require internet |

---

## 6. ERROR SCENARIOS

### 6.1 Worktree Errors

| Error | Cause | Expected Behavior |
|-------|-------|-------------------|
| "Not a git repository" | No .git directory | Return error, abort orchestration |
| "Failed to create worktree" | Disk full, permissions | Return error, cleanup partial |
| "Merge conflict" | Overlapping changes | Report conflict, allow force merge |
| "Worktree not found" | Already cleaned up | Log warning, continue |

---

### 6.2 Agent Errors

| Error | Cause | Expected Behavior |
|-------|-------|-------------------|
| "No Copilot chat models available" | Extension not installed | Show warning, graceful degradation |
| "Access denied" | Subscription issue | Show error, abort agent |
| "Agent timeout" | Task took too long | Mark failed, continue with others |
| "Model request failed" | Network/API issue | Retry once, then fail |

---

### 6.3 State Errors

| Error | Cause | Expected Behavior |
|-------|-------|-------------------|
| "Invalid transition" | Wrong state machine path | Reject, log error |
| "Failed to read current.json" | File locked/missing | Return error with details |
| "Session file corrupt" | Invalid JSON | Use defaults, log warning |

---

## 7. PRODUCTION READINESS CHECKLIST

### 7.1 Required for Testing

- [x] FR-001: Task analysis implemented
- [x] FR-002: Worktree management implemented
- [x] FR-003: Session management implemented
- [x] FR-004: Agent spawning implemented (VS Code extension)
- [x] FR-005: Orchestration workflow implemented
- [x] FR-006: Conflict prevention implemented
- [x] NFR-001: Performance targets configurable
- [x] NFR-002: Reliability mechanisms in place
- [x] NFR-004: Observability dashboard available

### 7.2 Required for Production

- [ ] Automated test suite (TASK_0104)
- [ ] Load testing with multiple agents
- [ ] Error recovery testing
- [ ] Documentation for operators
- [ ] Monitoring/alerting setup

### 7.3 Future Enhancements

- [ ] Multi-window agent execution (true parallelism)
- [ ] Session persistence across restarts
- [ ] Agent result summarization
- [ ] Automatic retry on transient failures
- [ ] Queue management for > max_parallel_agents tasks

---

## 8. TRACEABILITY MATRIX

| Requirement | Implementation File | Function/Class |
|-------------|---------------------|----------------|
| FR-001.* | loop_guardrails.py | `analyze_parallelization()`, `get_task_dependencies()` |
| FR-002.* | loop_guardrails.py | `WorktreeManager` class |
| FR-003.* | loop_guardrails.py | `AgentSession` dataclass, `MultiAgentOrchestrator` |
| FR-004.* | vscode-extension/src/agentSpawner.ts | `AgentSpawner` class |
| FR-005.* | loop_guardrails.py | `MultiAgentOrchestrator.execute_parallel()` |
| FR-006.* | loop_cockpit.py | `/api/orchestrator/analyze-conflicts` |
| NFR-001.* | loop_guardrails.py | Constructor parameters |
| NFR-002.* | loop_cockpit.py | `_state_lock`, state transitions |
| NFR-004.* | templates/cockpit.html | Dashboard components |

---

END OF DOCUMENT


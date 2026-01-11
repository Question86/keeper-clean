# TASK_0096: External Agent Integration (GitHub Copilot)

MODE: IMPLEMENTATION
CREATED: 2026-01-11T05:29:33Z
COMPLETED: 2026-01-11T15:45:00Z
STATUS: COMPLETED
SOURCE: User request - UI Performance Enhancements

---

## OBJECTIVE

Integrate GitHub Copilot Chat API to spawn real AI agents in worktrees for parallel execution.

## CONTEXT

The orchestrator currently simulates agent execution by creating session files. This task implements actual agent spawning via GitHub Copilot Chat API, enabling true parallel AI execution.

## SCOPE

1. Research GitHub Copilot Chat API capabilities
2. Implement agent spawning via API
3. Create prompt template for agent work instructions
4. Monitor agent progress via session file polling
5. Handle agent completion and error states
6. Add fallback for API unavailability

## ACCEPTANCE CRITERIA

- [ ] GitHub Copilot API integrated and working
- [ ] Agents spawn in isolated worktrees
- [ ] Agents update session files with progress
- [ ] Agents complete tasks following REPORT-FIRST law
- [ ] Agent errors captured and reported
- [ ] Graceful degradation if API unavailable

## IMPLEMENTATION DETAILS

### Agent Spawning (loop_guardrails.py)

Update `MultiAgentOrchestrator.spawn_agent()`:

```python
import subprocess
import os

def spawn_agent(self, session: AgentSession) -> bool:
    """Spawn a GitHub Copilot agent to work on a task."""
    session.status = "spawned"
    session.started_at = utc_now_iso()
    
    # Create session file
    self._create_session_file(session)
    
    # Create agent prompt
    prompt = self._generate_agent_prompt(session)
    
    # Option A: GitHub Copilot Chat API (recommended)
    try:
        success = self._spawn_copilot_agent(session, prompt)
        if success:
            return True
    except Exception as e:
        session.error = f"Copilot spawn failed: {e}"
    
    # Option B: Fallback to simulation
    return self._simulate_agent(session)

def _generate_agent_prompt(self, session: AgentSession) -> str:
    """Generate work instructions for agent."""
    return f"""You are Agent {session.agent_id} working on {session.task_id}.

Working directory: {session.worktree_path}
Task spec: tasks/task_{session.task_id}.md

INSTRUCTIONS:
1. Read the task specification carefully
2. Create a report file following REPORT-FIRST law:
   - File: reports/report_{session.task_id}_L{{loop}}_v01.md
   - Include objective, approach, implementation details
3. Implement the task as specified
4. Test your implementation
5. Update this session file every 5 minutes:
   - File: _AGENT_SESSION.json
   - Fields: status, progress (0-100), result_summary

CRITICAL RULES:
- Follow all rules in PROJECT_TECH_BASELINE.md
- Never modify files outside your worktree
- Update session file regularly
- Set status to 'completed' when done
- Set status to 'failed' on errors with error description

Current session file location: {session.worktree_path}/_AGENT_SESSION.json

Begin work now. Good luck!"""

def _spawn_copilot_agent(self, session: AgentSession, prompt: str) -> bool:
    """Spawn agent via GitHub Copilot API."""
    # TODO: Research actual GitHub Copilot API
    # This is a placeholder for the integration
    
    # Potential approaches:
    # 1. VS Code Extension API to open chat with prompt
    # 2. GitHub Copilot REST API (if available)
    # 3. CLI tool invocation
    
    # For now, write a marker file that extension could monitor
    marker_file = session.worktree_path / "_AGENT_PROMPT.txt"
    marker_file.write_text(prompt, encoding="utf-8")
    
    return False  # Not yet implemented

def _simulate_agent(self, session: AgentSession) -> bool:
    """Fallback simulation for testing."""
    # Current behavior - mark as completed
    session.status = "completed"
    session.completed_at = utc_now_iso()
    session.progress = 100
    session.result_summary = "Simulated completion (no real agent)"
    self._create_session_file(session)
    return True
```

### Research Required

1. **GitHub Copilot Chat API Documentation**
   - Check if REST API exists
   - Authentication requirements
   - Rate limits and quotas

2. **VS Code Extension Integration**
   - Can extensions trigger Copilot chats programmatically?
   - How to pass context (working directory, files)
   - How to monitor completion

3. **Alternative: VS Code Tasks API**
   - Create a VS Code task that runs in the worktree
   - Task opens Copilot chat with context
   - User can manually execute or automate

### Phase 1: Investigation

Create a spike task to:
- Test GitHub Copilot API capabilities
- Prototype agent spawning mechanism
- Document findings and recommendations

### Phase 2: Implementation

Based on findings, implement chosen approach:
- API integration if available
- Extension bridge if needed
- Subprocess spawning as fallback

## DEPENDENCIES

- TASK_0091 (Multi-Agent Orchestrator) ✅
- GitHub Copilot API access
- Potential: TASK_0092 (VSCode Extension) if API unavailable

## RISKS

- GitHub Copilot API may not support programmatic agent spawning
- Authentication and permissions complexity
- Rate limiting could block parallel execution
- Mitigated by: Fallback to simulation, manual execution option

## NOTES

This is a **research-heavy task**. Initial implementation should focus on:
1. Documenting what's possible with current APIs
2. Creating a proof-of-concept
3. Designing fallback strategies

Full automation may require custom tooling or VS Code extension development.

---

END OF DOCUMENT

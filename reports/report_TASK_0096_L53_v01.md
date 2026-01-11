# REPORT: TASK_0096 - External Agent Integration Research

MODE: WORK ARTIFACT
STATUS: BLOCKED
LOOP: 53
VERSION: 1
CREATED: 2026-01-11T15:22:00Z

---

## OBJECTIVE

Research GitHub Copilot API integration for spawning real AI agents in parallel worktrees.

## RESEARCH FINDINGS

### VS Code Language Model API

The `vscode.lm` API provides programmatic access to Copilot models:

```typescript
// Select a Copilot model
const [model] = await vscode.lm.selectChatModels({ vendor: 'copilot', family: 'gpt-4o' });

// Send a chat request
const request = model.sendRequest(craftedPrompt, {}, token);
```

**Key Capabilities:**
- `vscode.lm.selectChatModels()` - Select available LM models
- `model.sendRequest()` - Send prompts and receive responses
- `vscode.chat.createChatParticipant()` - Create custom chat participants
- `vscode.lm.registerTool()` - Register tools for chat use

### Implementation Requirements

To spawn real agents using Copilot:

1. **VS Code Extension Required**
   - Must be a VS Code extension to access `vscode.lm` API
   - Cannot be done from external Python/Flask code
   - Requires TASK_0092 (VSCode Extension Bridge)

2. **Architecture Options:**
   
   **Option A: Extension-First (Recommended)**
   - VS Code extension handles agent spawning
   - Flask cockpit sends requests via WebSocket
   - Extension creates chat sessions per worktree
   
   **Option B: CLI Bridge**
   - Use `code` CLI to open files in worktrees
   - Trigger extension commands from CLI
   - More complex, less reliable

3. **Authentication:**
   - Uses existing VS Code Copilot authentication
   - No separate API keys needed
   - Subject to Copilot subscription limits

### Current Simulation Mode

The existing fallback (`_simulate_agent()`) provides:
- Session file creation for tracking
- Immediate completion simulation
- Adequate for testing orchestrator logic

### Blockers

1. **TASK_0092 Dependency**: VS Code Extension Bridge is deferred
2. **Stable Loop Requirement**: TASK_0092 needs 5+ stable loops
3. **No External API**: GitHub Copilot has no public REST API for chat

## RECOMMENDATION

**Mark TASK_0096 as BLOCKED pending TASK_0092.**

Reasons:
- True agent spawning requires VS Code extension
- Current simulation mode is functional for development
- Waiting for Phase 5 gate (5+ stable loops) is appropriate

Alternative consideration:
- Could implement a "semi-automated" mode where:
  - Cockpit prepares agent prompts in `_AGENT_PROMPT.txt`
  - Human manually pastes prompt into Copilot chat
  - Agent updates session file when complete
  - Cockpit monitors and merges results

## NEXT STEPS

1. Update TASK_0096 status to BLOCKED in NEU.md
2. Document dependency on TASK_0092
3. Consider creating TASK_0099 for "manual agent mode" if needed
4. Revisit when Phase 5 is ready

## DEPENDENCIES

- TASK_0091 (Multi-Agent Orchestrator) ✅
- TASK_0092 (VSCode Extension Bridge) ⏸️ DEFERRED
- GitHub Copilot subscription (for `vscode.lm` API)

---

END OF REPORT

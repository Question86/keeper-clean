# TASK_0071 Architecture Suggestion: Multi-Agent Infrastructure Implementation

MODE: DOCUMENTATION (HISTORICAL)

**DOCUMENT TYPE:** Implementation Guide  
**CREATED:** 2026-01-11 (Loop 43)  
**PURPOSE:** Methodology and architecture vision for TASK_0071 implementation  
**TARGET LOOPS:** 44-60+

---

## EXECUTIVE SUMMARY

This document describes the suggested methodology and architecture for implementing the multi-agent infrastructure outlined in TASK_0065's 918-line analysis report. The goal is to transform the Keeper cockpit from a single-agent sequential system into a multi-agent parallel execution platform while maintaining the REPORT-FIRST law and pointer-only architecture.

---

## PART 1: IMPLEMENTATION METHODOLOGY

### Guiding Principles

1. **Incremental Value Delivery**: Each subtask delivers standalone value
2. **Foundation First**: Build infrastructure before advanced features
3. **Test Before Advancing**: Each phase validates before next begins
4. **Preserve Laws**: REPORT-FIRST and pointer-only architecture remain sacred
5. **Rollback Ready**: Every change must be revertible

### Recommended Implementation Order

```
PHASE 1: Foundation (Loops 44-47)
├── TASK_0078: Auto-Format Pointer Generator
├── TASK_0079: Status Sync Automation
├── TASK_0077: Pre-Flight Validation Hook
└── TASK_0083: One-Click Task Closure

PHASE 2: Context & Accessibility (Loops 48-51)
├── TASK_0080: Context Index Generator
├── TASK_0081: Loop Digest Generator
├── TASK_0082: Task Dependency Graph API
└── TASK_0084: Smart Report Templates

PHASE 3: Workflow Automation (Loops 52-55)
├── TASK_0085: Auto-Finalization Monitor
└── Integration testing of Phase 1-2 features

PHASE 4: Multi-Agent Core (Loops 56-62)
├── TASK_0086: Task Dependency Analyzer
├── TASK_0087: Multi-Agent Orchestrator Core
└── Parallel execution testing

PHASE 5: Full Integration (Loops 63-70)
├── TASK_0088: Cockpit-VSCode Extension Bridge
├── Embedded chat panel
└── Mobile cockpit PWA
```

### How to Approach Each Subtask

**Pattern for Implementation Tasks:**

```
1. READ the detailed spec in task file
2. READ the relevant section of report_TASK_0065_L39_v01.md
3. CREATE report file BEFORE implementation (REPORT-FIRST)
4. IMPLEMENT in small, testable increments
5. RUN lint after each change
6. UPDATE report with outcomes
7. MOVE task to Alt.md
```

**Pattern for Testing:**

```
1. Start cockpit: python loop_cockpit.py
2. Test new endpoint/feature via browser or curl
3. Verify no regressions in existing functionality
4. Document test results in report
```

---

## PART 2: ARCHITECTURE VISION

### Current Architecture (Loop 43)

```
┌─────────────────────────────────────────────────────────────┐
│                    KEEPER COCKPIT v43                        │
├─────────────────────────────────────────────────────────────┤
│  STATE MACHINE                                               │
│  ┌─────────────┐    ┌────────┐    ┌───────────┐             │
│  │READY_FOR_   │───▶│ ACTIVE │───▶│ FINALIZED │             │
│  │   RESET     │    │        │    │           │             │
│  └─────────────┘    └────────┘    └───────────┘             │
│        ▲                                  │                  │
│        └──────────────────────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  SINGLE AGENT EXECUTION                                      │
│  ┌──────────────────────────────────────┐                   │
│  │  AI Agent reads task → creates report │                   │
│  │  → implements → updates report →      │                   │
│  │  moves pointer → next task            │                   │
│  └──────────────────────────────────────┘                   │
├─────────────────────────────────────────────────────────────┤
│  COCKPIT CONTROL                                             │
│  • Flask server (loop_cockpit.py)                           │
│  • HTML UI (templates/cockpit.html)                         │
│  • Validation (loop_guardrails.py)                          │
│  • 3D Visualization (Three.js)                              │
└─────────────────────────────────────────────────────────────┘
```

### Target Architecture (Post-TASK_0071)

```
┌─────────────────────────────────────────────────────────────┐
│                    KEEPER COCKPIT v2.0                       │
├─────────────────────────────────────────────────────────────┤
│  ORCHESTRATOR LAYER (NEW)                                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  • Task Dependency Analyzer                              ││
│  │  • Agent Pool Manager (3-5 concurrent)                   ││
│  │  • Merge Conflict Detector                               ││
│  │  • Rollback Controller                                   ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  MULTI-AGENT EXECUTION                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │                   │
│  │ TASK_A   │  │ TASK_B   │  │ TASK_C   │                   │
│  │ (branch) │  │ (branch) │  │ (branch) │                   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                   │
│       │             │             │                          │
│       └─────────────┼─────────────┘                          │
│                     ▼                                        │
│              ┌──────────────┐                                │
│              │ MERGE POINT  │                                │
│              │ (atomic)     │                                │
│              └──────────────┘                                │
├─────────────────────────────────────────────────────────────┤
│  ENHANCED CONTROL LAYER                                      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  • Pre-Flight Validation (auto REPORT-FIRST check)       ││
│  │  • Auto-Format Pointers (no manual formatting)           ││
│  │  • Status Sync (task spec ↔ pointer location)            ││
│  │  • One-Click Operations (task lifecycle buttons)         ││
│  │  • Smart Templates (pre-filled reports)                  ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  CONTEXT LAYER (NEW)                                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  • Context Index (docs/CONTEXT_INDEX.json)               ││
│  │  • Loop Digests (archive/DIGEST_XXXX.md)                 ││
│  │  • Task Dependency Graph (visual + API)                  ││
│  │  • Semantic Search (enhanced /api/search)                ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  UNIFIED INTERFACE (Future)                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  • VS Code Extension Bridge                              ││
│  │  • Embedded Chat Panel                                   ││
│  │  • Mobile PWA                                            ││
│  │  • Natural Language Task Creation                        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## PART 3: KEY COMPONENT DESIGNS

### 3.1 Multi-Agent Orchestrator

**File:** `multi_agent_orchestrator.py` (new)

```python
# Core classes (conceptual design)

class TaskDependencyGraph:
    """Analyzes task specs to find parallelizable clusters."""
    def analyze(self, tasks: List[str]) -> DependencyResult:
        # Parse each task for file references
        # Build adjacency list: task → files → tasks
        # Identify independent clusters
        # Return: {parallel: [...], sequential: [...]}
        pass

class AgentPool:
    """Manages isolated agent workspaces."""
    def spawn(self, task_id: str) -> Agent:
        # Create git worktree for isolation
        # Copy necessary state files
        # Return agent handle
        pass
    
    def collect_results(self) -> List[AgentResult]:
        # Wait for all agents to complete
        # Gather report files and changes
        pass

class MergeController:
    """Handles atomic merging of parallel work."""
    def merge(self, results: List[AgentResult]) -> MergeResult:
        # Check for file conflicts
        # If conflicts: reject all, return to sequential
        # If clean: merge all branches
        # Run lint validation
        # Commit as single atomic change
        pass
```

### 3.2 Context Index System

**File:** `docs/CONTEXT_INDEX.json` (auto-generated)

```json
{
  "generatedAt": "2026-01-11T12:00:00Z",
  "loopNumber": 44,
  "quickStart": {
    "currentLoop": 44,
    "status": "ACTIVE",
    "activeTaskCount": 3,
    "topPriorityTask": "TASK_0078"
  },
  "recentDecisions": [
    {
      "loop": 43,
      "decision": "EPIC decomposition approved",
      "impact": "12 subtasks created"
    }
  ],
  "fileMap": {
    "loop_cockpit.py": {
      "purpose": "Main Flask server",
      "lines": 1847,
      "lastModified": "Loop 43"
    }
  },
  "patterns": {
    "reportCreation": "Create BEFORE implementation",
    "pointerFormat": "[ref:path|v:id|tags:...|src:...]"
  }
}
```

### 3.3 Pre-Flight Validation Hook

**Addition to:** `loop_guardrails.py`

```python
def pre_work_validation(task_id: str, workspace: Path) -> ValidationResult:
    """Run BEFORE any file edits for a task."""
    errors = []
    
    # 1. Check report exists (REPORT-FIRST enforcement)
    report = find_latest_report(task_id, workspace)
    if not report:
        errors.append({
            "code": "REPORT_FIRST_VIOLATION",
            "message": f"No report found for {task_id}. Create report BEFORE implementation."
        })
    
    # 2. Check task spec exists and is valid
    task_spec = workspace / "tasks" / f"task_{task_id}.md"
    if not task_spec.exists():
        errors.append({
            "code": "MISSING_TASK_SPEC",
            "message": f"Task spec not found: {task_spec}"
        })
    
    # 3. Check task is in NEU.md (active queue)
    if not task_in_neu(task_id, workspace):
        errors.append({
            "code": "TASK_NOT_ACTIVE",
            "message": f"{task_id} not found in NEU.md active queue"
        })
    
    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors
    )
```

### 3.4 Auto-Format Pointer Generator

**Addition to:** `loop_cockpit.py`

```python
@app.route('/api/generate-pointer', methods=['POST'])
def generate_pointer():
    """Generate correctly formatted pointer reference."""
    data = request.json
    task_id = data.get('task_id')
    version = data.get('version', '1')
    tags = data.get('tags', [])
    source = data.get('source', 'system')
    
    # Build canonical pointer format
    pointer = f"[ref:tasks/task_{task_id}.md|v:{version}|tags:{','.join(tags)}|src:{source}]"
    
    return jsonify({
        "pointer": pointer,
        "copyable": True
    })
```

### 3.5 One-Click Task Closure

**Addition to:** `templates/cockpit.html`

```html
<!-- Task Quick Actions Panel -->
<div class="task-actions" data-task-id="TASK_XXXX">
  <button onclick="closeTask(this)" class="btn btn-success">
    ✓ Close Task (Move to Alt)
  </button>
  <button onclick="validateTask(this)" class="btn btn-info">
    🔍 Pre-Closure Check
  </button>
</div>

<script>
async function closeTask(btn) {
  const taskId = btn.closest('.task-actions').dataset.taskId;
  
  // 1. Validate report exists
  const validation = await fetch(`/api/validate-task/${taskId}`);
  if (!validation.ok) {
    alert('Validation failed. Check report exists.');
    return;
  }
  
  // 2. Move pointer NEU → Alt
  const result = await fetch('/api/close-task', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({task_id: taskId, status: 'SUCCESS'})
  });
  
  // 3. Show result
  if (result.ok) {
    location.reload();
  } else {
    alert('Failed to close task');
  }
}
</script>
```

---

## PART 4: IMPLEMENTATION CHECKLIST

### Phase 1 Checklist (Loops 44-47)

- [ ] **TASK_0078**: Auto-Format Pointer Generator
  - [ ] Add `/api/generate-pointer` endpoint
  - [ ] Add "Copy Pointer" button in cockpit
  - [ ] Update lint to validate format
  - [ ] Write tests

- [ ] **TASK_0079**: Status Sync Automation
  - [ ] Modify `/api/close-task` to update task spec STATUS
  - [ ] Add drift detection warning
  - [ ] Test bidirectional sync

- [ ] **TASK_0077**: Pre-Flight Validation Hook
  - [ ] Add `pre_work_validation()` to guardrails
  - [ ] Add `--pre-work` CLI flag
  - [ ] Integrate with cockpit UI

- [ ] **TASK_0083**: One-Click Task Closure
  - [ ] Add task action buttons to UI
  - [ ] Wire to `/api/close-task`
  - [ ] Add confirmation modal

### Success Criteria

After Phase 1:
- [ ] Manual pointer formatting eliminated
- [ ] Task status drift detected automatically
- [ ] REPORT-FIRST violations caught before implementation
- [ ] Task closure is one click, not manual file editing

---

## PART 5: RISK MITIGATION

### Risk: Breaking Existing Functionality

**Mitigation:**
- Run lint after EVERY change
- Keep cockpit server restart-safe
- Document rollback steps in each report

### Risk: Multi-Agent Merge Conflicts

**Mitigation:**
- Conservative dependency analysis (prefer sequential if unclear)
- No auto-merge of conflicts (reject and retry sequentially)
- Atomic commits only (all-or-nothing)

### Risk: Scope Creep

**Mitigation:**
- Each subtask has clear acceptance criteria
- EPIC remains decomposed (no monolithic implementation)
- Human approval required before Phase 4+

---

## PART 6: QUICK REFERENCE

### Key Files

| File | Purpose | Modification Expected |
|------|---------|----------------------|
| loop_cockpit.py | Flask server | New endpoints |
| loop_guardrails.py | Validation | New functions |
| templates/cockpit.html | UI | New panels/buttons |
| multi_agent_orchestrator.py | NEW | Orchestration logic |
| docs/CONTEXT_INDEX.json | NEW | Auto-generated index |

### Key Endpoints (Planned)

| Endpoint | Purpose | Phase |
|----------|---------|-------|
| `/api/generate-pointer` | Format pointers | 1 |
| `/api/close-task` | One-click closure | 1 |
| `/api/pre-work-check` | Validation hook | 1 |
| `/api/context-index` | Serve context | 2 |
| `/api/task-dependencies` | Graph API | 2 |
| `/api/parallelize-tasks` | Multi-agent | 4 |

### Command Reference

```bash
# Lint check
python loop_cockpit.py --lint

# Generate context index
python loop_cockpit.py --generate-context-index

# Pre-work validation
python loop_cockpit.py --pre-work TASK_XXXX

# Run cockpit server
python loop_cockpit.py
```

---

## CONCLUSION

This document provides the methodology and architecture vision for implementing TASK_0071's multi-agent infrastructure. The key insight is to build incrementally:

1. **Foundation first** - Error reduction and workflow polish
2. **Context second** - Make information accessible
3. **Automation third** - Reduce manual overhead
4. **Multi-agent last** - Only after foundation is solid

Each loop should pick 1-2 subtasks from the priority list, implement them fully, and validate before moving on. The estimated timeline is 18-25 loops, but this will compress as momentum builds.

---

**Reference this document at the start of each implementation loop.**

END OF DOCUMENT

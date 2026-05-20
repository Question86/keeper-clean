# CANONICAL SYSTEM SPECIFICATION

MODE: DOCUMENTATION
VERSION: 1.0
CREATED: 2026-01-12T21:55:00Z
TASK: TASK_0138
STATUS: CANONICAL

---

## TABLE OF CONTENTS

1. [Canonical File Structure](#1-canonical-file-structure)
2. [Canonical File Formats](#2-canonical-file-formats)
3. [Canonical Rules (System Laws)](#3-canonical-rules-system-laws)
4. [Roles & Rights](#4-roles--rights)
5. [Canonical Loop Structure](#5-canonical-loop-structure)
6. [Unpatchable Filestack](#6-unpatchable-filestack)
7. [Human Access Levels](#7-human-access-levels)
8. [Security Audit Checklist](#8-security-audit-checklist)

---

## 1. CANONICAL FILE STRUCTURE

### 1.1 Required Root Files

| File | Purpose | Mutability | Owner |
|------|---------|------------|-------|
| `PROJECT_TECH_BASELINE.md` | Immutable system laws | IMMUTABLE | Human |
| `NEURAL_CORTEX.md` | Pointer-only navigation map | DYNAMIC | AI |
| `NEU.md` | Active task queue (pointer-only) | DYNAMIC | AI |
| `Alt.md` | Closed tasks (pointer-only) | DYNAMIC | AI |
| `current.json` | State authority (single source of truth) | DYNAMIC | System/Cockpit |
| `_LOOP_GATE.md` | Entry validator | GENERATED | Cockpit |
| `_BOOTSTRAP.md` | Fresh session entry (ephemeral) | EPHEMERAL | Cockpit |
| `_SESSION.md` | Current session context (optional) | GENERATED | Cockpit |
| `knownissues.json` | Blocker registry | DYNAMIC | AI |
| `milestone_XX.json` | Goal tracking | DYNAMIC | AI/Human |
| `README.md` | Project documentation | STATIC | Human |

### 1.2 Required Directories

| Directory | Purpose | Contents |
|-----------|---------|----------|
| `archive/` | Immutable loop history | `ARCHIV_XXXX.md` files |
| `tasks/` | Task specifications | `task_TASK_XXXX.md` files |
| `reports/` | Execution reports | `report_TASK_XXXX_LYY_vNN.md` files |
| `bugs/` | Bug incident documentation | `BUG_XXXX_LYYY.md` files |
| `code/` | Code component documentation | `CODE_XXXX_LYYY.md` files |
| `docs/` | Operational documentation | Protocols, indices, guides |
| `templates/` | UI templates | `cockpit.html` |

### 1.3 Automation Files (Required for Full Operation)

| File | Purpose | Dependencies |
|------|---------|--------------|
| `loop_cockpit.py` | Flask web UI + API | Flask |
| `loop_guardrails.py` | Stdlib validators/generators | Python stdlib only |
| `metadata_validator.py` | JSON/YAML validation | Python stdlib |
| `START_COCKPIT.bat` | Windows launcher | PowerShell |
| `START_COCKPIT.sh` | Unix launcher | Bash |
| `requirements_cockpit.txt` | Python dependencies | pip |
| `config.json` | Runtime configuration | None |

---

## 2. CANONICAL FILE FORMATS

### 2.1 Archive Format (ARCHIV_XXXX.md)

**CANONICAL REFERENCE:** ARCHIV_0071, ARCHIV_0072, ARCHIV_0073

```markdown
# ARCHIV_XXXX

MODE: IMMUTABLE
FINALIZED: YYYY-MM-DDTHH:MM:SSZ

---

## LOOP SUMMARY

**Loop ID:** XX
**Last Task Worked:** TASK_XXXX
**Finalization Date:** YYYY-MM-DD

---

## TASKS AT FINALIZATION

### Active Tasks (NEU.md)
```
[Embedded snapshot of NEU.md at finalization time]
```

### Closed Tasks (Alt.md)
```
[Embedded snapshot of Alt.md at finalization time]
```

---

## TASKS COMPLETED

### TASK_XXXX - [Title] ✅
**Report (example):** reports/report_TASK_XXXX_LYY_v01.md (example)
**Status:** ✅ SUCCESS

**Summary:**
[Brief description of work completed]

---

## FILES CREATED

| File | Purpose |
|------|---------|
| path/file.ext | Description |

---

## FILES MODIFIED

| File | Change |
|------|--------|
| path/file.ext | Description of change |

---

## LESSONS LEARNED

1. [Key insight from this loop]

---

## NEXT LOOP SEED

[Recommendations or pending work for next loop]

---

## VALIDATION

- [x] All tasks have reports
- [x] Reports marked SUCCESS
- [x] Tasks moved NEU.md → Alt.md
- [x] current.json updated
- [x] No UNIVERSAL LAW violations
- [x] Pre-finalization GREEN LIGHT received

---

END OF DOCUMENT
```

### 2.2 Task Specification Format (task_TASK_XXXX.md)

```markdown
# TASK_XXXX

MODE: TASK SPECIFICATION
STATUS: [NEW|IN_PROGRESS|COMPLETED|BLOCKED]
CREATED: YYYY-MM-DDTHH:MM:SSZ
[COMPLETED: YYYY-MM-DDTHH:MM:SSZ]
PRIORITY: [HIGH|MEDIUM|LOW]

---

## SEED IDEA

[Original idea/request that spawned this task]

---

## OBJECTIVE

[Concrete, measurable objectives derived from seed idea]

---

## TASK_TYPE

[ANALYSIS|IMPLEMENTATION|MAINTENANCE|DOCUMENTATION|PROCESS]

---

## ACCEPTANCE CRITERIA

- [ ] Criterion 1
- [ ] Criterion 2

---

## NOTES

[Additional context or constraints]

---

END OF DOCUMENT
```

### 2.3 Report Format (report_TASK_XXXX_LYY_vNN.md)

```markdown
# REPORT: TASK_XXXX

**Task:** [Task title]
**Loop:** YY
**Version:** NN
**Status:** [✅ SUCCESS|⚠️ PARTIAL|❌ FAILED|🔒 BLOCKED]
**Created:** YYYY-MM-DDTHH:MM:SSZ

---

## OBJECTIVE

[What was the goal]

---

## WORK PERFORMED

[Detailed description of work]

---

## RESULTS

[Outcomes, metrics, evidence]

---

## CONCLUSION

[Summary and next steps]

---

END OF DOCUMENT
```

### 2.4 Bug Documentation Format (BUG_XXXX_LYYY.md)

```markdown
# BUG_XXXX: [Brief Title]

**Bug ID:** BUG_XXXX
**Created:** YYYY-MM-DDTHH:MM:SSZ
**Last Modified:** YYYY-MM-DDTHH:MM:SSZ
**Author:** [System|User]
**Loop:** YYY
**Priority:** [Critical|Major|Minor]
**Tags:** [tag1, tag2, ...]

---

## TITLE
[Full descriptive title]

## SEVERITY
[Critical|Major|Minor]

## STATUS
[Open|Resolved|In Progress]

## DESCRIPTION
[Detailed description of the bug or incident]

## IMPACT
[What systems/components are affected]

## ROOT CAUSE
[Analysis of what caused the issue]

## RESOLUTION
[How the bug was fixed, or current mitigation]

## PREVENTION
[Measures to prevent recurrence]

---

END OF DOCUMENT
```

### 2.5 Code Documentation Format (CODE_XXXX_LYYY.md)

```markdown
# CODE_XXXX: [Brief Title]

**Code ID:** CODE_XXXX
**Created:** YYYY-MM-DDTHH:MM:SSZ
**Last Modified:** YYYY-MM-DDTHH:MM:SSZ
**Author:** [System|User]
**Language:** [Python|JavaScript|etc]
**Complexity:** [High|Medium|Low]
**Maintenance Priority:** [High|Medium|Low]
**Tags:** [tag1, tag2, ...]

---

## TITLE
[Full descriptive title]

## PURPOSE
[What this code component implements]

## ARCHITECTURE
[High-level design and structure]

## IMPLEMENTATION
[Key implementation details and algorithms]

## DEPENDENCIES
[External libraries, modules, or components required]

## USAGE
[How to use this code component]

## TESTING
[Test coverage and validation approach]

## MAINTENANCE NOTES
[Known issues, TODOs, or future improvements]

---

END OF DOCUMENT
```

### 2.6 Pointer Document Format (NEU.md, Alt.md, NEURAL_CORTEX.md)

```markdown
# [DOCUMENT_NAME]

MODE: POINTER-ONLY
CONTENT: FORBIDDEN

Process Rules:
[ref:docs/OPS_PROTOCOLS.md#SECTION|v:1|tags:ops|src:doc]

---

## SECTION TITLE

ref(path/to/file.md#SECTION|v:VERSION|tags:TAG1,TAG2|src:SOURCE)

---

END OF DOCUMENT
```

### 2.7 State Authority Format (current.json)

```json
{
  "STATE": {
    "loop": 77,
    "status": "ACTIVE|READY_FOR_RESET|FINALIZED",
    "archiveCurrent": "archive/ARCHIV_XXXX.md",
    "archiveInProgress": null,
    "lastTaskWorked": "TASK_XXXX",
    "lastUpdate": "YYYY-MM-DDTHH:MM:SSZ",
    "summary": "Human-readable status summary",
    "validationHash": null,
    "transitionTrigger": "source-of-transition",
    "pendingArchiv": null
  },
  "lastTaskWorked": "TASK_XXXX"
}
```

---

## 3. CANONICAL RULES (SYSTEM LAWS)

### 3.1 Universal Laws (Non-Negotiable)

| # | Law | Description | Enforcement |
|---|-----|-------------|-------------|
| 1 | REPORT-FIRST | Non-trivial work requires dedicated report | Lint validation |
| 2 | NO INLINE CONTEXT | Core docs contain refs only, never content | Lint validation |
| 3 | REFERENCE FORMAT | All refs use ref(DOC#SECTION|v:ID|tags:...|src:...) | Pattern matching |
| 4 | LOOP FINALITY | One loop = exactly one archive | State enforcement |
| 5 | ARCHIVE IMMUTABILITY | Archives are final, never edited | File permissions |
| 6 | AMNESIA IS A FEATURE | Fresh chat required after finalization | Process enforcement |
| 7 | LOCATION LAW | Each doc has allowed actions; wrong location = STOP | AI training |
| 8 | POINTER-ONLY CORE | NEURAL_CORTEX, NEU, ALT = pointers only | Lint validation |
| 9 | DETERMINISTIC NAMING | Zero-padded canonical names | Schema validation |
| 10 | VIOLATION = INVALID | Rule violation invalidates output | Pre-finalization check |
| 11 | GATE VALIDATION | Fresh sessions MUST check _LOOP_GATE.md | Bootstrap sequence |
| 12 | STATE AUTHORITY | current.json is single source of truth | Schema validation |

### 3.2 Operational Rules

| Rule | Description | Trigger |
|------|-------------|---------|
| Auto-finalize | When NEU.md has no active tasks and work was done | Post-task completion |
| Green Light | Pre-finalization validation must pass | Before archive creation |
| Bootstrap Delete | Deleting _BOOTSTRAP.md signals loop start | Entry complete |
| Confirm Bootstrap | Call `/api/confirm-bootstrap` after entry | Deterministic transition |

---

## 4. ROLES & RIGHTS

### 4.1 File Ownership Matrix

| File/Directory | Create | Read | Update | Delete |
|----------------|--------|------|--------|--------|
| PROJECT_TECH_BASELINE.md | Human | All | Human (exceptional) | Never |
| NEURAL_CORTEX.md | System | All | Human (exceptional) | Never |
| NEU.md | System | All | AI | Never |
| Alt.md | System | All | AI | Never |
| current.json | System | All | Cockpit/API | Never |
| _LOOP_GATE.md | Cockpit | All | Cockpit | Cockpit |
| _BOOTSTRAP.md | Cockpit | AI | Never | AI |
| _SESSION.md | Cockpit | AI | Cockpit | Cockpit |
| archive/*.md | AI | All | Never | Never |
| tasks/*.md | AI/Cockpit | All | AI | Never |
| reports/*.md | AI | All | AI (version) | Never |
| bugs/*.md | AI | All | AI | Never |
| code/*.md | AI | All | AI | Never |
| docs/*.md | AI/Human | All | AI/Human | Human |
| docs/COMPLETED_TASKS_ARCHIVE.md | AI | All | AI | Never |

### 4.2 AI Agent Types & Permissions

| Agent Type | Scope | Can Create | Can Modify | Restrictions |
|------------|-------|------------|------------|--------------|
| **Primary Loop Agent** | Full session | Tasks, Reports, Archives | NEU, Alt, current.json (via API) | Must follow all laws |
| **Sub-Agent (Research)** | Read-only | None | None | Information gathering only |
| **Sub-Agent (Worker)** | Limited scope | Reports (draft) | None | Must report to primary |
| **Cockpit Automation** | System files | Gate, Bootstrap, Session | current.json, indices | Deterministic operations only |

### 4.3 Cockpit API Permissions

#### Core State Management
| Endpoint | Method | Effect | Authorization |
|----------|--------|--------|---------------|
| `/api/status` | GET | Read current state | None |
| `/api/confirm-bootstrap` | POST | READY_FOR_RESET → ACTIVE | AI entry only |
| `/api/finalize-loop` | POST | ACTIVE → FINALIZED (with validation) | Pre-validation required |
| `/api/reset-loop` | POST | Move archive, increment loop | Human confirmation |
| `/api/finalization-status` | GET | Check finalization readiness | None |
| `/api/finalization-config` | GET | Get finalization configuration | None |
| `/api/finalization-check` | GET | Validate finalization requirements | None |

#### Task Management
| Endpoint | Method | Effect | Authorization |
|----------|--------|--------|---------------|
| `/api/tasks` | GET | List all tasks | None |
| `/api/tasks/active` | GET | List active tasks | None |
| `/api/tasks/complete` | POST | Mark task as completed | Task validation |
| `/api/blocked-tasks` | GET | List blocked tasks | None |
| `/api/reopen-task` | POST | Reopen completed task | Human confirmation |
| `/api/close-task` | POST | Close task with reason | Task validation |
| `/api/pre-work-check/<task_id>` | GET | Validate task prerequisites | None |
| `/api/task-dependencies` | GET | Get task dependency graph | None |

#### Validation & Auditing
| Endpoint | Method | Effect | Authorization |
|----------|--------|--------|---------------|
| `/api/lint` | GET | Metadata validation report | None |
| `/api/validate-schemas` | GET | Schema validation | None |
| `/api/validate-gates` | GET | Gate validation status | None |
| `/api/audit-status` | GET | Audit system status | None |
| `/api/metadata-lint` | GET | Comprehensive metadata lint | None |

#### Knowledge & Search
| Endpoint | Method | Effect | Authorization |
|----------|--------|--------|---------------|
| `/api/search` | GET | File and content search | None |
| `/api/query` | GET | Knowledge base query | None |
| `/api/knowledge/rebuild` | POST | Rebuild knowledge index | Admin |
| `/api/knowledge/stats` | GET | Knowledge statistics | None |
| `/api/knowledge/search` | GET | Knowledge search | None |
| `/api/knowledge/lessons` | GET | Extract lessons learned | None |
| `/api/knowledge/file-history` | GET | File change history | None |
| `/api/knowledge/chat` | POST | Knowledge-based chat | None |

#### File & Index Operations
| Endpoint | Method | Effect | Authorization |
|----------|--------|--------|---------------|
| `/api/file-index` | GET | File index status | None |
| `/api/concept-index` | GET | Concept index status | None |
| `/api/context-index` | GET | Context index | None |
| `/api/regenerate-index` | POST | Regenerate indices | Admin |
| `/api/sync-status` | GET | Synchronization status | None |
| `/api/file-activity` | GET | Recent file activity | None |
| `/api/project-structure` | GET | Project structure overview | None |

#### Session & Bootstrap
| Endpoint | Method | Effect | Authorization |
|----------|--------|--------|---------------|
| `/api/session-pack` | GET | Generate session pack | None |
| `/api/inject-bootstrap` | POST | Inject bootstrap file | Admin |
| `/api/ack-incident` | POST | Acknowledge incident | Human confirmation |
| `/api/force-active` | POST | Force ACTIVE status | Emergency only |

#### Advanced Features
| Endpoint | Method | Effect | Authorization |
|----------|--------|--------|---------------|
| `/api/parallel-analysis` | POST | Parallel task analysis | Admin |
| `/api/worktree` | GET | Worktree status | None |
| `/api/worktree/create` | POST | Create worktree | Admin |
| `/api/worktree/merge` | POST | Merge worktree | Admin |
| `/api/worktree/cleanup` | POST | Cleanup worktrees | Admin |
| `/api/worktree/rollback` | POST | Rollback worktree | Admin |
| `/api/orchestrator` | GET | Orchestrator status | None |
| `/api/orchestrator/analyze` | POST | Analyze with orchestrator | Admin |
| `/api/orchestrator/execute` | POST | Execute orchestrated tasks | Admin |
| `/api/orchestrator/rollback` | POST | Rollback orchestration | Admin |

#### Utility & Monitoring
| Endpoint | Method | Effect | Authorization |
|----------|--------|--------|---------------|
| `/api/health` | GET | System health check | None |
| `/api/token-monitor` | GET | Token usage monitoring | None |
| `/api/life-coordinates` | GET | AI behavioral state coordinates | None |
| `/api/transaction-log` | GET | Transaction log | None |
| `/api/history-index` | GET | History index | None |
| `/api/milestone` | GET | Milestone status | None |
| `/api/archives` | GET | Archive list | None |

**Notes:**
- "None" authorization means no special permissions required
- "Admin" requires administrative access
- "Human confirmation" requires explicit user approval
- "Task validation" requires task-specific preconditions
- "Emergency only" for critical system recovery
- "Pre-validation required" means finalization checks must pass

---

## 5. CANONICAL LOOP STRUCTURE

### 5.1 Loop States

```
READY_FOR_RESET → ACTIVE → FINALIZED → (reset) → READY_FOR_RESET
```

| State | Description | Allowed Actions |
|-------|-------------|-----------------|
| READY_FOR_RESET | Loop prepared, awaiting entry | Read, Bootstrap entry |
| ACTIVE | Work in progress | All AI operations |
| FINALIZED | Archive created, awaiting reset | Read only, Human reset |

### 5.2 Canonical Loop Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: RESET (Human + Cockpit)                                    │
│ • Move archive to archive/                                          │
│ • Increment loop counter                                            │
│ • Generate _BOOTSTRAP.md                                            │
│ • Regenerate _LOOP_GATE.md                                          │
│ • Status: READY_FOR_RESET                                           │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: ENTRY (AI)                                                 │
│ • Read _BOOTSTRAP.md                                                │
│ • Validate _LOOP_GATE.md (PASS required)                            │
│ • Load current.json state                                           │
│ • Read NEURAL_CORTEX.md structure                                   │
│ • Identify active task from NEU.md                                  │
│ • Internalize PROJECT_TECH_BASELINE.md laws                         │
│ • Delete _BOOTSTRAP.md                                              │
│ • Call /api/confirm-bootstrap                                       │
│ • Status: ACTIVE                                                    │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3: WORK (AI)                                                  │
│ • Execute tasks from NEU.md (priority order)                        │
│ • Create reports for all work (REPORT-FIRST law)                    │
│ • Move completed tasks NEU.md → Alt.md                              │
│ • Update current.json via API                                       │
│ • Repeat until NEU.md empty                                         │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 4: FINALIZATION (AI + Cockpit)                                │
│ • Pre-finalization validation (GREEN LIGHT required)                │
│ • Generate ARCHIV_XXXX.md (CANONICAL FORMAT!)                       │
│ • Update current.json status = FINALIZED                            │
│ • Announce completion to human                                      │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
                    [Human clicks RESET LOOP]
                                 ↓
                         [Back to PHASE 1]
```

---

## 6. UNPATCHABLE FILESTACK

### 6.1 Definition

**Unpatchable files** are those that MUST NOT be modified after creation, even to fix errors. The only remedy is documentation and prevention of recurrence.

### 6.2 Unpatchable Files

| Category | Files | Rationale |
|----------|-------|-----------|
| **Archives** | `archive/ARCHIV_XXXX.md` | Historical integrity (Law 5) |
| **Finalized Reports** | Reports in archive context | Part of immutable record |
| **System Laws** | `PROJECT_TECH_BASELINE.md` | Foundation stability |

### 6.3 Handling Errors in Unpatchable Files

1. **Document the error** in current loop's work
2. **Create incident report** if significant
3. **Add prevention measures** to operational docs
4. **Do NOT modify** the original file

**Example:** ARCHIV_0074 format deviation was documented but NOT corrected. Format was restored in ARCHIV_0075+.

---

## 7. HUMAN ACCESS LEVELS

### 7.1 Access Tiers

| Tier | Role | Access | Actions |
|------|------|--------|---------|
| **T0: Observer** | Reader | Read all | None |
| **T1: Operator** | Daily user | Read all, Cockpit UI | Reset loops, submit seeds |
| **T2: Maintainer** | Developer | Read all, Cockpit + CLI | Modify docs, config, scripts |
| **T3: Administrator** | Owner | Full access | Modify baseline, schema, all files |

### 7.2 Human-Only Operations

| Operation | Tier Required | How |
|-----------|---------------|-----|
| Reset Loop | T1+ | Cockpit UI button |
| Submit Task Seed | T1+ | Cockpit UI form |
| Modify Documentation | T2+ | Direct file edit |
| Modify Automation | T2+ | Code edit + test |
| Modify System Laws | T3 | Exceptional only |

### 7.3 Human Intervention Points

| Situation | Required Action | Outcome |
|-----------|-----------------|---------|
| Loop finalized | Click RESET LOOP | New loop begins |
| AI blocked | Review and provide input | AI resumes work |
| System error | Debug and fix | Continue or restart |
| Law violation | Assess and document | Prevention measures |

---

## 8. SECURITY AUDIT CHECKLIST

### 8.1 Pre-Milestone Audit

**File Integrity:**
- [ ] All archives present and unmodified
- [ ] Archive sequence complete (no gaps)
- [ ] Archive formats follow canonical specification (0071-0073 reference)
- [ ] All tasks have corresponding reports

**State Consistency:**
- [ ] current.json loop matches latest archive + 1
- [ ] NEU.md and Alt.md are valid pointer-only documents
- [ ] No orphaned tasks (referenced but missing)
- [ ] No orphaned reports (file exists but no task reference)

**Law Compliance:**
- [ ] REPORT-FIRST: All non-trivial work has reports
- [ ] POINTER-ONLY: Core docs contain no inline content
- [ ] REFERENCE FORMAT: All refs follow canonical pattern
- [ ] ARCHIVE IMMUTABILITY: No archive modifications detected
- [ ] STATE AUTHORITY: No hardcoded loop IDs in markdown

**Automation Health:**
- [ ] Cockpit starts without errors
- [ ] All API endpoints respond correctly
- [ ] Lint passes with 0 errors
- [ ] Schema validation passes
- [ ] Gate generation works

**Documentation Currency:**
- [ ] OPS_PROTOCOLS.md reflects current procedures
- [ ] ARCHITECTURE.md reflects current system
- [ ] README.md is accurate
- [ ] This spec (CANONICAL_SYSTEM_SPEC.md) is current

### 8.2 Audit Frequency

| Audit Type | Frequency | Trigger |
|------------|-----------|---------|
| Quick Lint | Every loop | Automatic (entry + finalization) |
| Schema Validation | Every loop | Automatic |
| Full Audit | Every 10 loops | Manual or milestone |
| Security Audit | Per milestone | Before milestone sign-off |

### 8.3 Audit Evidence Requirements

For milestone sign-off, provide:
1. Lint output showing 0 errors
2. Schema validation output showing all valid
3. Archive sequence verification
4. Manual review confirmation of critical files

---

## APPENDIX A: Quick Reference

### A.1 Canonical File Names

```
ARCHIV_XXXX.md      (zero-padded 4 digits)
task_TASK_XXXX.md   (zero-padded 4 digits)
report_TASK_XXXX_LYY_vNN.md  (task 4 digits, loop 2 digits, version 2 digits)
milestone_XX.json   (zero-padded 2 digits)
```

### A.2 Reference Format

```
[ref:FILE#SECTION|v:VERSION|tags:TAG1,TAG2|src:SOURCE]
```

- **FILE:** Relative path from workspace root
- **SECTION:** Heading or ID within file (optional)
- **VERSION:** Version number or `dynamic`
- **tags:** Comma-separated classification
- **src:** Origin (`system`, `doc`, `user`, `loopXX`)

### A.3 Status Values

**Task Status:** `NEW`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`
**Report Status:** `SUCCESS`, `PARTIAL`, `FAILED`, `BLOCKED`
**Loop Status:** `READY_FOR_RESET`, `ACTIVE`, `FINALIZED`

---

END OF DOCUMENT

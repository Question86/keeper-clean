# Loop-Based Project Architecture

**Clean implementation of memory-reset workflow system**

[![Sponsor](https://img.shields.io/badge/Sponsor-question86-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/question86)

## Support This Project

If this system saves you time or prevents costly workflow failures, support development through GitHub Sponsors:

- https://github.com/sponsors/question86
- Sponsorship tiers and deliverables: [SPONSORSHIP.md](SPONSORSHIP.md)
- Monetization playbook: [docs/GITHUB_MONETIZATION_PLAYBOOK.md](docs/GITHUB_MONETIZATION_PLAYBOOK.md)

---

## What is This?

A deterministic, loop-based project management system designed to:
- Enforce **amnesia** through fresh AI sessions between loops
- Prevent **context drift** and rule erosion over time
- Maintain **single source of truth** via `current.json`
- Ensure **discoverable** project state through pointer documents

---

## Quick Start

### For Fresh Loop Entry:
1. Start a new chat window
2. Tell AI: **"Read _BOOTSTRAP.md"**
3. AI will validate gate, load state, and begin work
4. _BOOTSTRAP.md self-deletes after entry

### Core Documents (Read These):
- **PROJECT_TECH_BASELINE.md** - Immutable system laws
- **NEURAL_CORTEX.md** - Project navigation map
- **current.json** - Current loop state (authoritative)
- **_LOOP_GATE.md** - Entry validator

### Entry Flow:
```
_BOOTSTRAP.md → _LOOP_GATE.md → current.json → NEURAL_CORTEX.md → NEU.md → [TASK]
```

---

## Architecture Principles

1. **Amnesia is a Feature**  
   Fresh chat session required between loops. Forces explicit knowledge crystallization.

2. **Single Source of Truth**  
   `current.json` owns loop state. No hardcoded IDs in markdown files.

3. **Pointer-Only Core**  
   Core documents (NEURAL_CORTEX, NEU, ALT) contain references only, never content.

4. **Gate Validation**  
   _LOOP_GATE.md validates entry conditions. BLOCKED status stops all work.

5. **Deterministic Naming**  
   All files use canonical, zero-padded names (ARCHIV_0001.md, TASK_0042, etc.)

---

## File Structure

```
Keeper-Clean/
├── PROJECT_TECH_BASELINE.md    # Immutable laws
├── NEURAL_CORTEX.md            # Navigation map
├── current.json                # State authority
├── _LOOP_GATE.md               # Entry validator
├── _BOOTSTRAP.md               # Fresh session entry (ephemeral)
├── NEU.md                      # Active task queue
├── Alt.md                      # Closed/blocked tasks
├── milestone_01.json           # Goal tracking
├── knownissues.json            # Blocker registry
├── archive/                    # Immutable loop history
│   └── ARCHIV_XXXX.md
└── docs/
    └── OPS_PROTOCOLS.md        # Process documentation
```

---

## Loop Lifecycle

### 1. Loop Active
- Work on tasks from NEU.md
- Create reports: `report_TASK_XXXX_LXX_vNN.md`
- Update task references

### 2. Loop Finalization
- AI creates ARCHIV_XXXX.md
- Sets current.json status = "FINALIZED"
- Tells human: "Move ARCHIV to /archive/"

### 3. Human Handoff
- Move ARCHIV_XXXX.md → /archive/
- Update current.json: status = "READY_FOR_RESET", loop++
- Close chat window

### 4. Fresh Loop Start
- Start new chat session
- Tell AI: "Read _BOOTSTRAP.md"
- AI validates, loads state, begins work

---

## Key Features

✓ **No Context Drift** - Fresh AI session forces rule rediscovery  
✓ **No Hardcoded State** - current.json is single source of truth  
✓ **Entry Validation** - _LOOP_GATE.md prevents broken state entry  
✓ **Clear Handoff** - _BOOTSTRAP.md guides session start  
✓ **Immutable History** - Archive files never edited  
✓ **Pointer Navigation** - Core docs reference, never contain content  

---

## Status

**Current Loop:** 1 (initial)  
**Status:** ACTIVE  
**Gate:** PASS  
**Architecture:** Stable  

Ready for first task assignment.

---

END OF DOCUMENT

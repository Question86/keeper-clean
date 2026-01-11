# TASK_0004

MODE: TASK SPECIFICATION
STATUS: IN_PROGRESS
CREATED: 2026-01-10T15:50:00Z
STARTED: 2026-01-10T16:00:00Z

---

## SEED IDEA

System violation discovered: Loop 4 had undocumented work (code changes to loop_cockpit.py and current.json) without creating a report file. This violates UNIVERSAL LAW #1 (REPORT-FIRST LAW) and creates amnesia gaps across loops. Root cause analysis and enforcement mechanism required.

---

## OBJECTIVE

**Primary Goal:** Implement systematic enforcement of REPORT-FIRST LAW to prevent undocumented work across loops.

**Secondary Goal:** Document the desynchronization incident and establish fail-safes.

---

## ROOT CAUSE ANALYSIS

### Violation Details - Loop 4

**Evidence:**
1. **Archive Claims:** ARCHIV_0004.md states "Last Task Worked: None"
2. **Code Changes Made:**
   - Modified loop_cockpit.py lines 171-181 (bootstrap detection logic)
   - Modified current.json (status transition READY_FOR_RESET → ACTIVE)
3. **Missing Report:** No report_TASK_XXXX_L04_vNN.md file exists for this work
4. **State Corruption:** current.json showed "lastTaskWorked: null" despite code modifications

### Pattern Identification

**Archive Review Results:**
- ✅ **Loop 1:** TASK_0001 completed WITH report (report_TASK_0001_L01_v01.md)
- ❌ **Loop 2:** Finalized with "Last Task Worked: TASK_0001" but no Loop 2 work - suspicious
- ❌ **Loop 3:** Finalized with "Last Task Worked: None" - no work claimed
- ❌ **Loop 4:** **CRITICAL VIOLATION** - Undocumented code changes with false "None" claim

**First Occurrence:** Loop 2 shows first signs of desynchronization (claiming previous loop's task)

### Structural Flaws Identified

**FLAW #1: No Enforcement Mechanism**
- PROJECT_TECH_BASELINE.md defines REPORT-FIRST LAW but has no enforcement
- AI can make code changes without system-level validation
- No pre-commit hooks or file monitoring

**FLAW #2: Human Bypass Opportunity**
- User can directly ask AI to "make quick fixes" 
- AI may comply without triggering report protocol
- No reminder system for REPORT-FIRST requirement

**FLAW #3: Archive Process Doesn't Validate**
- Finalization API (/api/finalize-loop) doesn't check for orphaned changes
- current.json "lastTaskWorked" can be null even with file modifications
- Archive captures state snapshot but doesn't audit work completeness

**FLAW #4: No Report Registry**
- System doesn't track which files were modified per loop
- No way to cross-reference code changes against report files
- Missing validation: "If files changed → report MUST exist"

**FLAW #5: Bootstrap Entry Doesn't Detect Violations**
- _BOOTSTRAP.md entry protocol doesn't validate previous loop integrity
- Fresh sessions start blind to prior violations
- Gate validator (_LOOP_GATE.md) doesn't check for orphaned work

---

## ACCEPTANCE CRITERIA

### Phase 1: Documentation & Analysis (This Task)
- [x] Identify root cause of Loop 4 violation
- [x] Trace violation pattern through all archives
- [x] Document structural flaws in system
- [x] Create comprehensive report for this investigation

**Phase 1 Status:** ✅ COMPLETE (report_TASK_0004_L06_v01.md)
**Completion Date:** 2026-01-10T16:05:00Z

### Phase 2: Prevention System (Future Implementation)
- [x] Implement file change tracking per loop
- [x] Create report validation in finalization API
- [x] Add pre-finalization audit that blocks if changes exist without reports
- [ ] Enhance _LOOP_GATE.md with previous loop integrity check
- [x] Add "REPORT-FIRST REMINDER" in cockpit UI when starting work

**Phase 2 Status:** ✅ CORE COMPLETE (report_TASK_0004_L06_v02.md)
**Completion Date:** 2026-01-10T16:20:00Z
**Remaining:** Loop work log registry, enhanced gate validation

### Phase 3: Recovery (Future)
- [ ] Retroactively document Loop 4 undocumented work
- [ ] Consider creating remedial report_LOOP4_UNDOCUMENTED_L05_v01.md
- [ ] Update ARCHIV_0004.md with violation notice (breaks immutability but necessary)

---

## PROPOSED FIX ARCHITECTURE

### Solution 1: Pre-Finalization Audit Hook
```python
def audit_loop_integrity():
    """
    Called before finalization. Returns (bool, list[issues])
    
    Checks:
    1. Compare files modified since loop start
    2. Cross-reference against reports in root
    3. Verify lastTaskWorked has corresponding report
    4. Block finalization if violations found
    """
    pass
```

### Solution 2: Report Registry File
Create `_LOOP_WORK_LOG.json` (ephemeral, cleared on reset):
```json
{
  "loop": 5,
  "workStarted": "2026-01-10T15:30:00Z",
  "reports": ["report_TASK_0003_L05_v01.md"],
  "filesModified": ["templates/cockpit.html", "current.json"],
  "validated": false
}
```

### Solution 3: Enhanced Gate Validation
Modify _LOOP_GATE.md generation to include:
```
✓ **Previous Loop Integrity**
  - All work documented with reports
  - No orphaned file changes
  - Archive matches actual work performed
```

### Solution 4: Cockpit UI Enforcement
Add to ACTIVE state panel:
```
⚠️ REMINDER: Starting work? Create report file FIRST!
Format: report_TASK_XXXX_L05_vNN.md
```

### Solution 5: Pre-Finalization Green Light Check
**Requirement:** Automated validation routine that runs BEFORE finalization button activates

**Implementation Location:** loop_cockpit.py - /api/finalize-loop endpoint

**Check List:**
1. ✅ All work has corresponding report files
2. ✅ lastTaskWorked has valid report reference
3. ✅ No orphaned code changes
4. ✅ NEU.md and Alt.md properly updated
5. ✅ current.json state is valid
6. ✅ No violations of UNIVERSAL LAWS

**Behavior:**
- If ANY check fails → Block finalization, display violations in UI
- If ALL checks pass → Display green light summary, enable finalize button
- Log check results to console for debugging

**UI Integration:**
- Add "Pre-Flight Check" status indicator to cockpit
- Show ✅/❌ for each validation item
- Require explicit "I CONFIRM" button after green light

### Solution 6: Trust Measurement System
**Purpose:** Quantify system integrity over time based on loop history

**Metrics to Track:**
```json
{
  "trustScore": 0-100,
  "loopsCompleted": 5,
  "loopsWithViolations": 1,
  "reportsGenerated": 2,
  "tasksCompleted": 2,
  "orphanedChanges": 1,
  "lawViolations": 1,
  "consecutiveCleanLoops": 0,
  "lastViolation": "Loop 4"
}
```

**Scoring Algorithm:**
- Start at 100 (perfect trust)
- -20 points per violation detected
- +5 points per clean loop (with report)
- +10 bonus for 3+ consecutive clean loops
- Decay old violations (50% weight after 5 loops)

**Display Location:**
- Cockpit dashboard as "System Trust Score"
- Color coded: Green (80+), Yellow (50-79), Red (<50)
- Show trend graph over time

**Action Triggers:**
- Trust < 50 → Warning banner: "System integrity compromised"
- Trust < 30 → Block finalization until violations addressed
- Trust = 100 → Display achievement badge

**Storage:** Create `trust_metrics.json` updated on each finalization

---

## RECOMMENDED PRIORITY

**CRITICAL** - This is a system integrity issue affecting core loop architecture.

**Why Critical:**
- Violates fundamental law that enables amnesia-resistant workflow
- Creates knowledge gaps that compound across loops
- Already happened once, will happen again without fix
- Undermines entire purpose of report-based documentation

**Suggested Execution:**
1. Complete THIS task's report (document the investigation)
2. Move TASK_0004 to NEU.md as highest priority for Loop 5 or 6
3. Implementation should be multi-loop effort with testing

---

## DEPENDENCIES

**Required Reading:**
- [ref:PROJECT_TECH_BASELINE.md#UNIVERSAL LAWS|v:immutable]
- [ref:loop_cockpit.py#finalize_loop|v:current]
- [ref:archive/ARCHIV_0004.md|v:immutable]

**Files to Modify (Future):**
- loop_cockpit.py - Add audit_loop_integrity() and pre_finalization_green_light()
- loop_cockpit.py - Add trust score calculation system
- templates/cockpit.html - Add report reminder and trust score display
- _LOOP_GATE.md - Add integrity check section
- docs/OPS_PROTOCOLS.md - Document audit process
- trust_metrics.json (NEW) - Trust measurement data storage

---

## IMPLEMENTATION PHASES

### Phase 1: Core Enforcement (High Priority)
- Solution 1: Pre-finalization audit hook
- Solution 5: Green light check routine
- Block finalization if violations detected

### Phase 2: Prevention & UX (Medium Priority)
- Solution 2: Loop work log registry
- Solution 4: Cockpit UI reminders
- Enhanced visibility for report requirements

### Phase 3: Intelligence & Metrics (Nice-to-Have)
- Solution 6: Trust measurement system
- Historical violation tracking
- Trend analysis and scoring

### Phase 4: Deep Integration (Long-term)
- Solution 3: Enhanced gate validation
- Cross-loop integrity verification
- Automated remediation suggestions

---

## NOTES

**Critical Quote from PROJECT_TECH_BASELINE.md:**
> "1. REPORT-FIRST LAW  
>    Any non-trivial work requires a dedicated report file.  
>    No report → work is invalid."

The system violated its own foundational law. This task exists to ensure it never happens again.

**Created by:** Loop 5 integrity audit
**Triggered by:** User observation of Loop 4 archive discrepancy

---

END OF DOCUMENT

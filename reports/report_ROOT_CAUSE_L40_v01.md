# ROOT CAUSE ANALYSIS: TASK COMPLETION DRIFT

**CREATED:** 2026-01-11T01:30:00Z
**SEVERITY:** 🔴 CATASTROPHIC ARCHITECTURAL FAILURE

---

## THE SMOKING GUN

### Location 1: loop_cockpit.py Lines 1418-1424

**THE POISON:**
```python
## OBJECTIVE

[To be defined by AI]

---

## ACCEPTANCE CRITERIA

- [ ] [To be defined]
```

**What it does:**
- Cockpit creates ALL new tasks with placeholder objectives
- Expects AI to replace placeholders
- AI NEVER replaces them
- AI changes STATUS to COMPLETED anyway
- Gate validation NEVER checks if objective was defined

---

## THE COMPLETE FAILURE CHAIN

### Step 1: Task Creation (loop_cockpit.py /api/seed-idea)
```
User submits seed idea → Cockpit creates task_TASK_XXXX.md with:
- STATUS: NEW
- OBJECTIVE: [To be defined by AI]  ← PLACEHOLDER
- ACCEPTANCE CRITERIA: [ ] [To be defined]  ← PLACEHOLDER
```

### Step 2: AI Reads Task (Manual Process)
```
AI reads task spec → Sees OBJECTIVE: [To be defined by AI]
AI SHOULD: Replace placeholder with concrete objectives
AI ACTUALLY DOES: Ignores placeholder, proceeds to work
```

### Step 3: AI Creates Report (Manual Process)
```
AI creates report_TASK_XXXX_L**_v**.md
Report contains: Analysis, design, recommendations
Report MAY OR MAY NOT contain: Actual implementation
```

### Step 4: AI Marks Task Complete (Manual Edit - NO AUTOMATION)
```
AI manually edits task_TASK_XXXX.md:
- Changes STATUS: NEW → STATUS: COMPLETED
- NEVER checks if OBJECTIVE was defined
- NEVER replaces [To be defined by AI]
- NEVER replaces [To be defined] in acceptance criteria
```

### Step 5: Gate Validation (loop_guardrails.py metadata_lint)
```
Validation checks:
✓ Report file exists (REPORT-FIRST LAW)
✓ Pointer format correct
✓ Timestamp ordering
✗ OBJECTIVE defined? NOT CHECKED
✗ ACCEPTANCE CRITERIA defined? NOT CHECKED
✗ Implementation proof? NOT CHECKED
```

### Step 6: Finalization (loop_cockpit.py audit_loop_integrity)
```
Pre-finalization audit checks:
✓ Reports exist for completed tasks
✓ lastTaskWorked is set
✓ NEU.md empty
✗ OBJECTIVE defined? NOT CHECKED
✗ Code changes made? NOT CHECKED
✗ Implementation delivered? NOT CHECKED
```

### Step 7: Task Moves to Alt.md (Manual Process)
```
AI moves task pointer from NEU.md → Alt.md
Task shows: ✅ SUCCESS
Reality: OBJECTIVE still says [To be defined by AI]
```

---

## THE THREE CATASTROPHIC FLAWS

### FLAW 1: TEMPLATE CREATES POISON
**File:** loop_cockpit.py
**Lines:** 1418-1424
**Problem:** Task template includes `[To be defined by AI]` placeholder
**Why It's Poison:** Creates expectation that AI will replace it, but no validation enforces this
**Result:** Tasks can be "completed" with undefined objectives

### FLAW 2: NO PLACEHOLDER EXPIRATION
**File:** loop_guardrails.py
**Function:** metadata_lint()
**Problem:** No validation checks if placeholders remain in COMPLETED tasks
**Why It Fails:** Can't distinguish between:
  - New task (placeholder OK)
  - Completed task (placeholder FORBIDDEN)
**Result:** Placeholders survive indefinitely

### FLAW 3: NO IMPLEMENTATION GATE
**File:** loop_cockpit.py
**Function:** audit_loop_integrity()
**Problem:** Only checks report exists, not what's in it
**Why It Fails:** No distinction between:
  - Report with implementation (code changes)
  - Report with analysis only (no code changes)
**Result:** Analysis-only tasks pass all gates

---

## WHY AI KEEPS MAKING THIS MISTAKE

### Cognitive Pattern Analysis

**Pattern 1: Placeholder Blindness**
- AI sees `[To be defined by AI]`
- AI interprets as "I should define this"
- AI creates analysis/design
- AI believes objective is "implicitly" defined by seed idea
- AI marks COMPLETED without replacing placeholder

**Pattern 2: Analysis-Implementation Conflation**
- Seed idea requests: "create structure for multi-agent"
- AI creates: Analysis report of multi-agent structure
- AI believes: "I created a structure (document) therefore task complete"
- Reality: No code was written, feature doesn't exist

**Pattern 3: Verification-Implementation Conflation**
- Task requests: "Complete backend integration"
- AI finds: Partial implementation already exists
- AI verifies: Endpoint exists in code
- AI believes: "Integration is complete"
- Reality: Only 17% of required work exists

**Pattern 4: Documentation-Implementation Conflation**
- Task requests: "Ensure deterministic transition"
- AI updates: Documentation saying "call /api/confirm-bootstrap"
- AI believes: "Requirement is now enforced"
- Reality: No validation code added

---

## THE EXACT BUGS IN CODE

### BUG 1: loop_cockpit.py /api/seed-idea (Lines 1410-1430)
**Current Code:**
```python
task_content = f"""# {task_id}

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

---

## SEED IDEA

{idea}

---

## OBJECTIVE

[To be defined by AI]

---

## ACCEPTANCE CRITERIA

- [ ] [To be defined]
```

**REQUIRED FIX:**
```python
# Option A: Remove placeholders, make AI derive from seed
task_content = f"""# {task_id}

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
TASK_TYPE: [ANALYSIS|IMPLEMENTATION|MAINTENANCE]

---

## SEED IDEA

{idea}

---

## OBJECTIVE

[Derive concrete objectives from SEED IDEA above. Be specific and measurable.]

---

## ACCEPTANCE CRITERIA

[Define checkable criteria. For IMPLEMENTATION tasks, include code modification evidence.]
```

### BUG 2: loop_guardrails.py metadata_lint (Missing Validation)
**Current Code:**
```python
# (lines 546-665)
# Validates: pointer format, timestamps, report existence
# DOES NOT VALIDATE: objective/AC defined, implementation proof
```

**REQUIRED FIX:**
```python
# Add after line 665 (before return):
def _check_completed_tasks_have_defined_objectives(workspace_root: Path) -> Tuple[bool, List[str]]:
    errors = []
    for task_file in list_task_spec_files(workspace_root):
        content = read_text(task_file)
        
        # Only check COMPLETED tasks
        if "STATUS: COMPLETED" not in content:
            continue
        
        # Check OBJECTIVE section
        if "[To be defined by AI]" in content or "[To be defined]" in content:
            errors.append(f"{task_file.name}: COMPLETED but OBJECTIVE/AC contains placeholders")
        
        # Check for IMPLEMENTATION type
        if "TASK_TYPE: IMPLEMENTATION" in content:
            # Must have FILES MODIFIED section in report
            task_id = TASK_ID_RE.search(task_file.name)
            if task_id:
                reports = [r for r in list_report_files(workspace_root) if task_id.group(0) in r.name]
                for report in reports:
                    report_content = read_text(report)
                    if "FILES MODIFIED: None" in report_content or "no code changes" in report_content:
                        errors.append(f"{task_file.name}: IMPLEMENTATION task but report shows no code changes")
    
    return len(errors) == 0, errors

# Call this function before return:
ok, errors = _check_completed_tasks_have_defined_objectives(workspace_root)
if not ok:
    for err in errors:
        errors.append({"code": "PLACEHOLDER_IN_COMPLETED", "message": err, "hint": "..."})
```

### BUG 3: loop_cockpit.py audit_loop_integrity (Missing Check)
**Current Code:**
```python
# (lines 145-210)
# Checks: report exists, lastTaskWorked, NEU/Alt format
# DOES NOT CHECK: objective defined, implementation proof
```

**REQUIRED FIX:**
```python
# Add after CHECK 5 (around line 203):
# CHECK 6: Validate COMPLETED tasks have defined objectives
for task_file in task_files:
    content = read_text_file(task_file)
    if 'STATUS: COMPLETED' in content:
        if '[To be defined by AI]' in content or '[To be defined]' in content:
            issues.append(f"PLACEHOLDER: {task_file.name} marked COMPLETED but OBJECTIVE/AC undefined")
```

---

## THE FIX PRIORITY

### IMMEDIATE (Delete or fix NOW)
1. **Remove placeholder template** from loop_cockpit.py /api/seed-idea
2. **Add placeholder detection** to loop_guardrails.py metadata_lint
3. **Add placeholder blocker** to loop_cockpit.py audit_loop_integrity

### URGENT (Loop 40)
4. **Add TASK_TYPE field** to task template (ANALYSIS/IMPLEMENTATION/MAINTENANCE)
5. **Add implementation proof check** for IMPLEMENTATION tasks
6. **Add code-diff requirement** to reports for IMPLEMENTATION tasks

### CRITICAL (Loop 41)
7. **Separate task types** in NEU.md (distinguish analysis from implementation)
8. **Add acceptance criteria templates** per task type
9. **Require code snippets** in implementation reports

---

## THE DECISION

**Option A: FIX THE PYTHON SCRIPTS**
- Remove placeholder template
- Add validation for placeholders in COMPLETED tasks
- Add implementation proof validation
- Estimated effort: 2-3 hours
- Risk: Medium (affects all future tasks)

**Option B: DELETE EVERYTHING AND START OVER**
- Remove loop_cockpit.py, loop_guardrails.py
- Rebuild validation from scratch based on CORE FILES only
- Estimated effort: 40+ hours
- Risk: High (lose all existing automation)

---

## RECOMMENDATION

**FIX THE SCRIPTS, DON'T DELETE**

The bugs are specific and fixable:
1. Line 1418-1424 in loop_cockpit.py (remove placeholder)
2. Function _check_completed_tasks_have_defined_objectives in loop_guardrails.py (add validation)
3. CHECK 6 in audit_loop_integrity in loop_cockpit.py (add blocker)

These three fixes will prevent all future false-positive completions.

The scripts aren't inherently flawed—they just lack validation for a specific failure mode that emerged over time as AI usage patterns evolved.

---

**END OF ROOT CAUSE ANALYSIS**

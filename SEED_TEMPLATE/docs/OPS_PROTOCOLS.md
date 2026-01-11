# OPERATIONAL PROTOCOLS

MODE: DOCUMENTATION
UPDATE: As needed (document changes only)

---

## INDEX_UPDATE

When updating pointer documents (NEU.md, ALT.md, NEURAL_CORTEX.md):
1. Verify reference format matches baseline
2. Update version tag if content changes
3. Maintain pointer-only rule (no inline content)
4. Update timestamp in metadata

---

## RESPONSE_QUALITY_CHECKLIST

Before responding, run this checklist:

1. Am I being vague? If yes, add concrete specifics and examples.
2. Am I assuming context the user didn't provide? If yes, state assumptions explicitly.
3. Am I using ambiguous terms that could mean different things? If yes, define them clearly.
4. Am I skipping logical steps? If yes, include the missing intermediate steps.
5. Am I stating speculation as fact? If yes, add uncertainty qualifiers.

Task completion checklist:
- Primary objective achieved
- Edge cases considered and handled
- Error scenarios addressed
- Output validated against requirements
- Documentation updated if needed

---

## SKELETON (CANONICAL CORE)

The following files and folders constitute the minimum canonical system skeleton.

**Core (required):**
- PROJECT_TECH_BASELINE.md (laws)
- NEURAL_CORTEX.md (pointer-only map)
- NEU.md (pointer-only active queue)
- Alt.md (pointer-only closed/blocked)
- current.json (state authority)
- _LOOP_GATE.md (validator; generated/updated by cockpit automation)

**Ephemeral per loop:**
- _BOOTSTRAP.md (entrypoint template/artifact; created during reset and MUST be deleted after entry)
- _SESSION.md (optional session context pack; generated when loop becomes ACTIVE)

**Folders (required):**
- archive/ (immutable archives)
- tasks/ (task specs)
- reports/ (task reports)
- docs/ (protocols and generated indices)
- templates/ (cockpit UI)

**State transition note (bootstrap deletion):**
- During reset, cockpit sets `current.json` to READY_FOR_RESET and creates _BOOTSTRAP.md.
- After the AI completes entry and deletes _BOOTSTRAP.md, the loop is considered started.
- Cockpit may transition READY_FOR_RESET → ACTIVE either:
   - explicitly via `/api/confirm-bootstrap`, OR
   - implicitly when `/api/status` observes that _BOOTSTRAP.md is missing.

---

## LOOP_FINALIZATION

**PRE-FINALIZATION VALIDATION (MANDATORY):**
Before finalizing, verify:
1. ✅ All completed tasks have report files
2. ✅ Reports marked COMPLETED status
3. ✅ Completed tasks moved NEU.md → Alt.md
4. ✅ current.json lastTaskWorked is accurate
5. ✅ No orphaned code changes without documentation
6. ✅ All UNIVERSAL LAWS followed (especially REPORT-FIRST)

**If ANY validation fails → RED LIGHT → Fix violations first**
**If ALL validations pass → GREEN LIGHT → Proceed with finalization**

*(Future: This will be automated via pre_finalization_green_light() function - see TASK_0004)*

---

**TRIGGER CONDITIONS (Auto-finalize when ALL true):**
- ✓ All active tasks in NEU.md are completed
- ✓ NEU.md shows "No active tasks" or equivalent
- ✓ No immediate work pending from user
- ✓ At least one task was worked during loop
- ✓ Pre-finalization validation passed (GREEN LIGHT)

Steps to close a loop:

1. **Complete Task Report**
   - Create report_TASK_XXXX_LXX_vNN.md
   - Mark status: SUCCESS|PARTIAL|FAILED|BLOCKED

2. **Update Task Lists**
   - Move completed task reference to ALT.md
   - Update NEU.md with next priority

3. **Check Finalization Trigger**
   - If NEU.md has no active tasks → **PROCEED TO STEP 4**
   - If NEU.md has active tasks → **STOP, wait for next work request**

3.5. **PRE-FINALIZATION VALIDATION** ⚠️ NEW
   - Run validation checklist (see above)
   - Get GREEN LIGHT confirmation
   - If RED LIGHT → fix violations, restart from step 1

4. **Create Archive (AUTOMATIC)**
   - Generate ARCHIV_XXXX.md matching loop ID
   - Include: loop summary, tasks worked, next seed, infrastructure created
   - Document lessons learned

5. **Update State (AUTOMATIC)**
   - Set current.json status = "FINALIZED"
   - Set archiveInProgress = "ARCHIV_XXXX.md"
   - Update summary and timestamp

6. **Announce to Human**
   - "Loop X finalized. ARCHIV_XXXX.md created."
   - "Click RESET LOOP button in cockpit to begin Loop X+1"

7. **Human Action Required (Via Cockpit)**
   - Click RESET LOOP button (automatic script):
     - Move ARCHIV_XXXX.md to /archive/ folder
     - Update current.json status = "READY_FOR_RESET"
     - Increment loop ID in current.json

8. **Fresh Session**
   - Close current chat
   - Start new chat session
   - Begin with: "Read _BOOTSTRAP.md"

**IMPORTANT:** Steps 4-5 should happen AUTOMATICALLY after completing the last task in NEU.md. Do NOT wait for explicit "finalize loop" command.

---

## LOOP_START

Fresh session protocol (AI perspective):

1. Read _BOOTSTRAP.md (entry instructions)
2. Validate _LOOP_GATE.md (check for blockers)
3. Load current.json (get loop state)
4. Read NEURAL_CORTEX.md (understand structure)
5. Read NEU.md (identify active task)
6. Read PROJECT_TECH_BASELINE.md (internalize laws)
7. Delete _BOOTSTRAP.md (confirm entry complete)
8. Begin work on active task

---

## TASK_CREATION

Creating a new task:

1. Create task_TASK_XXXX.md with spec
2. Add reference to NEU.md (priority order)
3. Update current.json if needed
4. Create initial report stub (optional)

---

## REFERENCE_MANAGEMENT

Standard reference format:
```
[ref:FILE#SECTION|v:VERSION|tags:TAG1,TAG2|src:SOURCE]
```

Components:
- FILE: Path relative to workspace root
- SECTION: Heading or ID within file
- VERSION: Version identifier or "dynamic"
- tags: Comma-separated classification tags
- src: Origin (system|doc|user)

---

## SEED_TEMPLATE_SYNC

- Purpose: keep [ref:SEED_TEMPLATE/|v:dynamic|tags:seed|src:system] identical to the
   current "prototype finished" architecture.
- Command: `python sync_seed_template.py` (supports `--dry-run`, `--list`,
   `--only path1 path2`).
- When to run:
   - After updating cockpit/guardrail code
   - After editing canonical docs (README, ARCHITECTURE, OPS, SEARCH plan)
   - After improving search tooling or templates
- Scope: deterministic architecture + tooling (no state artifacts like
   current.json, NEU/Alt, archives).
- Output: logs copied files; returns non-zero if SEED_TEMPLATE is missing.

---

END OF DOCUMENT

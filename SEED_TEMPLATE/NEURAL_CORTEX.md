# NEURAL CORTEX

MODE: POINTER-ONLY
INVALID IF CONTAINS CONTENT

Process Rules:
[ref:docs/OPS_PROTOCOLS.md#INDEX_UPDATE|v:1|tags:ops,index|src:doc]

---

## LOOP METADATA (DYNAMIC)

**Read from:**
[ref:current.json#STATE|v:dynamic|tags:state|src:system]

Loop state, archive refs, and status are maintained in current.json.
This document contains NO hardcoded loop IDs.

---

## AXIS

**WHAT WE HAVE →**
[ref:current.json#STATE|v:dynamic|tags:state|src:system]

**WHERE WE WANT TO GO →**
[ref:milestone_01.json#GOALS|v:1|tags:milestone|src:doc]

**WHAT STANDS IN THE WAY →**
[ref:knownissues.json#BLOCKERS|v:dynamic|tags:blocker|src:system]

---

## ACTIVE CHALLENGE
[ref:NEU.md#TASK QUEUE (PRIORITY ORDER)|v:dynamic|tags:active|src:system]

---

## ENTRY PROTOCOL (MANDATORY)

**Fresh Session Start:**
1. **CHECK:** Read [ref:_LOOP_GATE.md#STATUS|v:current|tags:validator|src:system]
   - If BLOCKED → STOP and report violations
   - If PASS → Continue to step 2

2. **READ STATE:** Open [ref:current.json#STATE|v:dynamic|tags:state|src:system]
   - Get current loop number
   - Get archive status
   - Get last task worked

3. **READ TASKS:** Open [ref:NEU.md#TASK QUEUE|v:dynamic|tags:active|src:system]
   - Identify next active task
   - Check priority order

4. **READ BLOCKERS:** Open [ref:knownissues.json#BLOCKERS|v:dynamic|tags:blocker|src:system]
   - Review known issues
   - Check task dependencies

5. **PROCEED:** Open ALT.md or start work on active task

---

## NAVIGATION MAP

- Project Laws → [ref:PROJECT_TECH_BASELINE.md|v:immutable|tags:baseline,laws|src:system]
- Active Tasks → [ref:NEU.md|v:dynamic|tags:tasks,active|src:system]
- Closed Tasks → [ref:Alt.md|v:dynamic|tags:tasks,closed|src:system]
- State Tracker → [ref:current.json|v:dynamic|tags:state|src:system]
- Entry Gate → [ref:_LOOP_GATE.md|v:current|tags:validator,gate|src:system]
- Architecture & Ops → [ref:docs/ARCHITECTURE.md|v:1|tags:docs,architecture|src:doc]

---

END OF DOCUMENT

# TASK_0074

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-11T02:35:00Z
TASK_TYPE: IMPLEMENTATION

---

## SEED IDEA

Cockpit consistently fails to transition from READY_FOR_RESET to ACTIVE state. Bootstrap deletion succeeds but status remains stuck. Root cause: fragile state machine in loop_cockpit.py with multiple failure points in /api/confirm-bootstrap, implicit detection logic, and race conditions between file deletion and status update.

---

## OBJECTIVE

Complete rewrite of cockpit state transition logic with:
1. Explicit state machine with atomic transitions
2. Reliable bootstrap detection without race conditions
3. Comprehensive error logging for debugging stuck states
4. Idempotent operations that can be safely retried
5. Status endpoint that accurately reflects current state

---

## TASK_TYPE

IMPLEMENTATION

---

## ACCEPTANCE CRITERIA

- [ ] Rewrite state machine in loop_cockpit.py with explicit FSM pattern
- [ ] Implement atomic READY_FOR_RESET → ACTIVE transition with file locks
- [ ] Add detailed transition logging (timestamp, trigger, outcome)
- [ ] Fix /api/confirm-bootstrap to be idempotent
- [ ] Fix /api/status to detect bootstrap deletion reliably
- [ ] Add /api/force-active endpoint for manual unsticking
- [ ] Test: Bootstrap deletion → immediate ACTIVE transition
- [ ] Test: Repeated /api/status calls show consistent state
- [ ] Test: Manual force-active recovers stuck states
- [ ] Document transition logic with state diagram in code comments

---

## TECHNICAL DETAILS

**Current Bugs:**
1. Bootstrap file deletion succeeds but status stays READY_FOR_RESET
2. /api/status has race condition checking file existence vs reading JSON
3. /api/confirm-bootstrap sometimes fails silently
4. No logging makes debugging impossible
5. State updates are not atomic (file delete, JSON update separate)

**Proposed Solution:**
- Use explicit FSM with logged transitions
- Implement transition as: check preconditions → update JSON → verify → log
- Add transition lock file to prevent concurrent updates
- Bootstrap detection should be: file_exists OR (status==ACTIVE)
- All state-changing endpoints return complete state snapshot

**Files to Modify:**
- loop_cockpit.py (state machine refactor ~300 lines)
- Add docs/STATE_MACHINE.md with transition diagram
- Update OPS_PROTOCOLS.md with new debugging procedures

---

END OF DOCUMENT

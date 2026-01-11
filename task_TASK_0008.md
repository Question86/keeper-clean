# TASK_0008

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-10T05:50:00Z

---

## SEED IDEA

Fix cockpit UI state management - READY_FOR_RESET state shows wrong panel ("LOOP READY TO START") when user is stuck between loops. This is confusing and doesn't clearly show what action is needed. The multi-page UI approach is fundamentally flawed - user gets stuck at wrong state screens. Need either: (1) Fix state panels to be clearer about current position and required actions, OR (2) Implement single-page unified visualization (3D UI from TASK_0005) that shows complete loop state at once without confusing page transitions.

---

## OBJECTIVE

**Primary Goal:** Fix UI state confusion where READY_FOR_RESET shows "loop ready to start" panel but user hasn't started new session yet, causing them to be stuck at wrong screen.

**Secondary Goal:** Consider replacing multi-page approach with unified visualization to prevent state confusion entirely.

---

## ACCEPTANCE CRITERIA

### Phase 1: Immediate Fix
- [ ] Analyze cockpit.html state management logic
- [ ] Fix READY_FOR_RESET panel to clearly show current state
- [ ] Add clear "YOU ARE HERE" indicators for loop position
- [ ] Show what user needs to do next (close chat, start new session)
- [ ] Prevent "stuck at wrong screen" scenarios

### Phase 2: Long-term Solution
- [ ] Evaluate feasibility of single-page unified UI
- [ ] Consider implementing 3D visualization from TASK_0005 Phase 2
- [ ] Design state-agnostic visualization that shows full loop context
- [ ] Eliminate confusing page transitions entirely

---

## NOTES

User feedback: "WRONG SHEET FOR THIS STATE OF LOOP" - stuck at READY_FOR_RESET showing "ready to start" when they're between loops. Gate shows BLOCKED but UI doesn't make it clear why or what to do.

Root issue: Multi-page conditional rendering based on status creates confusion. User doesn't know where they are in the loop or what action to take.

Created based on direct user frustration with current UI state management.

---

END OF DOCUMENT

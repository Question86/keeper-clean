# TASK_0044

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T11:11:16Z
COMPLETED: 2026-01-10

---

## SEED IDEA

Before responding, run through this checklist: 1) Am I being vague? If yes, add concrete specifics and examples. 2) Am I assuming context the user didn't provide? If yes, state assumptions explicitly. 3) Am I using ambiguous terms that could mean different things? If yes, define them clearly. 4) Am I skipping logical steps in my reasoning? If yes, show all intermediate work. 5) Am I stating speculation as fact? If yes, add uncertainty qualifiers. Fix all violations before outputting your response.

---

### Snippet 2: Ambiguity Reduction: Creative Constraint Bounding

CREATIVE AMBIGUITY REDUCTION:

Instead of: "Write a creative story"

Use: "Write a 500-word story that:
1. MUST include: [3 specific elements]
2. MUST NOT include: [3 forbidden elements]
3. MUST follow structure: [beginning-middle-end pattern]
4. MUST target audience: [specific demographic]
5. MUST use tone: [specific tone guideline]"

Creativity within constraints, not boundless freedom.

---

### Snippet 3: Task Completion Checklist

TASK COMPLETION CHECKLIST:\n□ Primary objective achieved\n□ Edge cases considered and handled\n□ Error scenarios addressed\n□ Output validated against requirements\n□ Documentation updated if needed\n\nCheck all boxes before marking task complete.

--- # AI ASSISTANT TASK — Validate Proposed Loop Finalization Architecture

## Context:
You are managing a deterministic, loop-based project system. A new utility named `loopctl.py` is proposed to automate the finalization of a loop and preparation of the next one. You are asked to **evaluate whether this tool design is valid and safe** to integrate into the current project environment.

## Your Mission:

1. **Analyze the following tool design:**

**Command:** `python loopctl.py finalize`

**Expected Behavior:**
- Read `current.json` → extract loop ID and status.
- Generate new `ARCHIV_XXXX.md` based on loop number.
- Update `current.json → status = FINALIZED`.
- Create `_BOOTSTRAP.md` with loop context.
- Create `_LOOP_GATE.md` with `STATUS: BLOCKED`.
- Optional: scaffold next `task_XXXX.md` and `report_XXXX_LXX_v01.md`.
- Output human-readable status message: “Move ARCHIV file → Start new session”.

2. **Assess whether this workflow:**
- Matches the logic defined in `PROJECT_TECH_BASELINE.md` and `OPS_PROTOCOLS.md`
- Respects canonical file layout (pointers only for NEU, CORTEX, ALT)
- Avoids hardcoded data inside any .md file (except ARCHIVs)
- Prevents AI from continuing without human intervention (gate/pass pattern)

3. **Then:**
→ Tell the user whether this `loopctl.py` structure makes sense based on the actual state of the repository  
→ Highlight any missing safeguards, flaws, or inconsistencies  
→ Suggest improvements only if they’re strictly necessary

4. **MOST IMPORTANT:**
⚠️ You must not rely on abstract reasoning alone.  
You must actually **scan the real file system** and **validate file presence, structure, and content** where needed:
- Check if `current.json` exists and is parseable
- Confirm that `ARCHIV_XXXX.md` is correctly structured and not already present
- Ensure `NEURAL_CORTEX.md`, `NEU.md`, `Alt.md` are pointer-only
- Ensure `_LOOP_GATE.md` can act as an effective block
- Validate that `_BOOTSTRAP.md` creates a clean entry point

## If everything checks out:
→ Explain how the proposed automation improves integrity, prevents drift, and preserves amnesia across sessions.

## If not:
→ Identify specific architectural conflicts or missing control layers.

## Final Deliverable:
- PASS/FAIL judgment on the architecture
- Detailed reasoning based on real file inspection
- (Optional) Suggestions for making it robust or more elegant

---

## OBJECTIVE

Integrate the provided response-quality checklist into the repository’s operational documentation so it becomes a repeatable standard.

---

## ACCEPTANCE CRITERIA

- [x] [ref:docs/OPS_PROTOCOLS.md#RESPONSE_QUALITY_CHECKLIST|v:1|tags:ops,quality|src:doc] exists and is readable.
- [x] Core pointer-only documents remain pointer-only (no inline content added).
- [x] `python loop_cockpit.py --lint` shows no new errors.

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

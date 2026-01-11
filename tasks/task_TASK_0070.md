# TASK_0070

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-11T01:15:00Z
SOURCE: Rework for corrupted TASK_0063

---

## SEED IDEA

TASK_0063 claimed to "complete deferred 3D visualization backend integration" but only verified that /api/project-structure endpoint exists. Report shows "Inspected... Confirmed... Verified" with no actual implementation. Reference coverage was 17% (7/41), should be 100%.

---

## OBJECTIVE

Actually complete the 3D visualization backend integration by achieving full reference coverage and connecting all workspace data.

---

## ACCEPTANCE CRITERIA

- [ ] Enhance /api/project-structure to parse all reference types (read/write/pointer)
- [ ] Achieve 100% reference coverage (currently 17% = 7/41 potential refs)
- [ ] Include all file types: core, state, tasks, reports, archives, docs
- [ ] Parse references from all markdown files in workspace
- [ ] Return complete reference graph for 3D visualization
- [ ] Test 3D Loop Sphere displays all 70+ files with correct relationships
- [ ] Document enhancement with before/after coverage metrics

---

## TECHNICAL DETAILS

**Source Analysis:** report_TASK_0063_L39_v01.md, TASK_0015, TASK_0014
**Current Gap:** Only 17% of potential references parsed
**Target File:** loop_cockpit.py (@app.route('/api/project-structure'))
**Expected Output:** Complete file graph with all [ref:...] links visualized

---

END OF DOCUMENT

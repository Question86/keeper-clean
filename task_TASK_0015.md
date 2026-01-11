# TASK_0015

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-10T06:38:50Z

---

## SEED IDEA

ALL reference links in the CORE md files must be shown correctly in the 3d visualization panel

---

## OBJECTIVE

Implement backend integration for the 3D Loop Sphere visualization to parse and display ALL reference links from core pointer-only documents (NEURAL_CORTEX.md, NEU.md, Alt.md) instead of using mock data.

This task addresses the gap identified in TASK_0014 where only 7 of 41 references (17%) were displayed due to hardcoded mock data.

Implementation requirements:
1. Create backend API endpoint to scan and parse reference links
2. Extract [ref:...] patterns from all markdown files in workspace
3. Replace frontend mock data with real-time parsed data
4. Display all 41+ references from core documents in 3D visualization
5. Properly classify reference types (read/write/pointer) based on context

---

## ACCEPTANCE CRITERIA

- [ ] Backend `/api/project-structure` endpoint created
- [ ] Regex parser extracts all [ref:FILE#SECTION|v:X|tags:...|src:...] references
- [ ] All markdown files in workspace scanned for references
- [ ] Core pointer-only documents (NEURAL_CORTEX.md, NEU.md, Alt.md) fully parsed
- [ ] Frontend fetches real data instead of using generateMockFileData()
- [ ] 3D visualization displays all 41+ actual references
- [ ] Reference metadata extracted (filename, section, version, tags, source)
- [ ] Reference type classification implemented (read/write/pointer)
- [ ] Verification confirms 100% reference coverage vs TASK_0014 baseline
- [ ] Report documents implementation and validation

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

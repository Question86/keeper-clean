# TASK_0063

MODE: TASK SPECIFICATION
STATUS: CORRUPTED (verification-only, integration incomplete)
CREATED: 2026-01-10T21:12:32Z
COMPLETED: 2026-01-10

Report: [ref:reports/report_TASK_0063_L39_v01.md|v:1|tags:report|src:system]

---

## SEED IDEA

3D Loop Sphere visualization backend integration was deferred in multiple archives (0014, 0015, 0019, etc.). Frontend implemented in Loop 11 but backend data integration never completed. History audit shows this as repeated deferred work.

---

## OBJECTIVE

Complete the deferred 3D visualization backend integration by implementing the /api/project-structure endpoint and connecting real workspace data to the 3D Loop Sphere visualization.

---

## ACCEPTANCE CRITERIA

- [ ] /api/project-structure endpoint fully implemented
- [ ] Real workspace file data flows to 3D visualization
- [ ] Reference parsing from core pointer documents working
- [ ] 3D visualization shows complete project state (all 70+ files)
- [ ] File type geometries and color coding functional
- [ ] Reference link visualization active

---

## TECHNICAL DETAILS

**Deferred Since:** Loop 11 (TASK_0015)
**Current Gap:** 17% reference coverage (7/41) vs 100% potential
**Impact:** Users see incomplete/incorrect project visualization

**Requirements from TASK_0014:**
- /api/project-structure endpoint with regex-based reference parser
- Dynamic file scanning for workspace markdown files
- Real-time data flow replacing mock data
- Type-based positioning and color coding
- Reference link visualization (read/write/pointer types)

**Implementation Scope:**
- Backend: Python endpoint in loop_cockpit.py
- Frontend: Update 3D visualization to consume real data
- Data: Parse NEURAL_CORTEX.md, NEU.md, Alt.md for references
- Testing: Verify all file types and reference types display correctly

---

## REFERENCES

- [ref:archive/ARCHIV_0011.md#TASK_0012|v:immutable|tags:frontend-complete|src:audit] - 3D visualization frontend implementation
- [ref:archive/ARCHIV_0014.md#TASK_0014|v:immutable|tags:deferred-requirements|src:audit] - Backend integration requirements
- [ref:report_TASK_0015_L12_v01.md|v:immutable|tags:endpoint-spec|src:audit] - API endpoint specification
- [ref:templates/cockpit.html|v:current|tags:3d-integration|src:audit] - Frontend integration point

---

END OF DOCUMENT
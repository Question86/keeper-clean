# PROJECT TECH BASELINE

MODE: READ-ONLY
UPDATE POLICY: NEVER (except full system reboot)

SYSTEM LAWS OVERRIDE ALL OTHER SECTIONS IN THIS DOCUMENT.

---

## UNIVERSAL LAWS (GLOBAL / NON-NEGOTIABLE)

1. REPORT-FIRST LAW  
   Any non-trivial work requires a dedicated report file.  
   No report → work is invalid.

2. NO INLINE CONTEXT  
   Core documents may contain references only, never content.

3. REFERENCE FORMAT LAW  
   All references MUST follow:  
   [ref:DOC#SECTION|v:ID|tags:...|src:...]

4. LOOP FINALITY  
   One loop produces exactly one archive file.

5. ARCHIVE IMMUTABILITY  
   Archive files are final and never edited or reopened.

6. AMNESIA IS A FEATURE  
   After loop finalization, all working context is discarded.  
   Fresh chat session required for new loop start.  
   Entry point: _BOOTSTRAP.md

7. LOCATION LAW  
   Each document is a location with allowed actions.  
   Wrong location → STOP.

8. POINTER-ONLY CORE  
   NEURAL_CORTEX.md, NEU.md, ALT.md contain pointers only.

9. DETERMINISTIC NAMING  
   All files use canonical, zero-padded names.

10. VIOLATION = INVALID OUTPUT

11. GATE VALIDATION LAW  
    Fresh sessions MUST check _LOOP_GATE.md before any work.  
    BLOCKED status → STOP immediately.

12. STATE AUTHORITY LAW  
    current.json is the single source of truth for loop state.  
    No hardcoded loop IDs in markdown files.

---

## SYSTEM IDENTITY
Project Name: [Your Project Name]
Project DNA: [Core purpose/essence]
Final Goal: [Ultimate objective]

---

## TECH STACK (IMMUTABLE)
Languages: [e.g., TypeScript, Python]
Frameworks: [e.g., Electron, React]
Runtime: [e.g., Node.js]
Database: [e.g., SQLite]
Infrastructure: [e.g., Desktop app]
Deployment: [e.g., electron-builder]

---

## DATA & API RULES
API style: [e.g., REST, GraphQL]
Auth model: [e.g., Token-based]
Data formats: [e.g., JSON]
Versioning: [e.g., Semantic]

---

## CANONICAL DOCUMENT SET

**Core System Files:**
- PROJECT_TECH_BASELINE.md (immutable laws)
- NEURAL_CORTEX.md (pointer map, dynamic)
- current.json (state authority, updated per loop)
- _LOOP_GATE.md (entry validator; generated/updated by cockpit automation)
- _BOOTSTRAP.md (fresh session entry point; created during reset, MUST be deleted after entry)

**Task Management:**
- NEU.md (active task queue, pointer-only)
- ALT.md (closed/blocked tasks, pointer-only)

**Work Artifacts:**
- ARCHIV_XXXX.md (loop history, zero-padded, immutable)
- task_TASK_XXXX.md (task specs)
- report_TASK_XXXX_LXX_vNN.md (execution reports)

**Operational Docs:**
- docs/OPS_PROTOCOLS.md (process documentation)
- milestone_XX.json (goal tracking)
- knownissues.json (blocker registry)

**Optional Observability:**
- _SESSION.md (current session state tracker, ephemeral)

---

## LOOP START TRANSITION (BOOTSTRAP DELETION)

- Reset prepares the next loop by setting `current.json` to READY_FOR_RESET and creating `_BOOTSTRAP.md`.
- A loop is considered *started* when `_BOOTSTRAP.md` is deleted after entry.
- Cockpit may transition READY_FOR_RESET → ACTIVE either explicitly (`/api/confirm-bootstrap`) or implicitly when `/api/status` detects the missing bootstrap.

---

END OF DOCUMENT

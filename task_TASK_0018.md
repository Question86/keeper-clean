# TASK_0018

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T06:41:57Z
COMPLETED: 2026-01-10

---

## SEED IDEA

remove active tasks monitor and closed tabs monitor from the cockpick ui

---

## OBJECTIVE

Remove the "Active Tasks (NEU.md)" and "Closed Tasks (Alt.md)" monitor panels from the cockpit UI to simplify the interface and reduce clutter. These panels duplicate information that is already available through other cockpit features and the VS Code file system.

Rationale:
- Users can view NEU.md and Alt.md directly in VS Code
- The seed idea panel already provides task submission functionality
- The 3D visualization shows project structure
- Removing redundant panels improves UI clarity and performance

---

## ACCEPTANCE CRITERIA

- [x] Active Tasks panel removed from HTML
- [x] Closed Tasks panel removed from HTML
- [x] JavaScript code for updating these panels removed
- [x] API calls to fetch task content removed (if exclusive to these panels)
- [x] UI layout responsive without these panels
- [x] No JavaScript errors after removal
- [x] Other cockpit features unaffected
- [x] Report documents changes

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

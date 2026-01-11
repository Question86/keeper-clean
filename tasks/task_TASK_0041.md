# TASK_0041

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T10:36:22Z
COMPLETED: 2026-01-10

---

## SEED IDEA

Scan the project architecture, the documentation and so on and consider improvements in the method/design that would allow ai to use the file system more efficiently for context creation esopecially under the regime, that the ai loses all context awareness one time per loop due to the fact that ever loop has its own chatbox with ai agent per definition. its always only 1 agent per loop and 1 loop per agent - can we improve data structure so ai can find former "lessonst learned" from the archive, task or report more easily?

---

## OBJECTIVE

Make it easy for a fresh-loop AI agent (no chat memory) to quickly retrieve prior “lessons learned” and relevant historical work by adding a fast, workspace-scoped search API and cockpit UI that can search archives/reports/tasks and jump to source files.

---

## ACCEPTANCE CRITERIA

- [x] Cockpit exposes a simple search UI for past artifacts (archives/reports/tasks/core docs).
- [x] Backend provides a bounded, workspace-scoped text search endpoint.
- [x] Search results can be opened using the existing safe open-file mechanism.
- [x] Report documents changes and usage.

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

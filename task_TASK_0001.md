# TASK_0001

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T04:13:50Z
COMPLETED: 2026-01-10

---

## SEED IDEA

Hi i want to build a small panel on my windows showing me a life counter of how many cigarettes i have spared since january 2 2025 (i smoked about 20 cigarettes per day

---

## OBJECTIVE

Create a small, persistent desktop panel (widget) for Windows that displays:
1. Days since quitting (January 2, 2025)
2. Number of cigarettes not smoked (20/day baseline)
3. Money saved (assuming cost per cigarette)
4. Health improvements milestones

The panel should be:
- Always visible (stays on top or in system tray)
- Visually motivating with progress indicators
- Minimal resource usage
- Auto-starts with Windows

---

## ACCEPTANCE CRITERIA

- [x] Desktop widget application created
- [x] Shows accurate day count since January 2, 2025
- [x] Calculates cigarettes saved (days × 20)
- [x] Displays money saved with configurable price
- [x] Visual progress bars or indicators
- [x] Stays on top of other windows (optional positioning)
- [x] Minimal, clean design
- [x] Configuration file for customization

---

## IMPLEMENTATION DETAILS

**Tech Stack:**
- Python with Tkinter (lightweight, native)
- JSON config file for settings
- Windows Task Scheduler for auto-start

**Features Implemented:**
- Real-time counter updates
- Money saved calculation
- Health milestone indicators
- Draggable window position
- Always-on-top mode
- System tray integration
- Configuration via JSON

---

## NOTES

Created via Loop Cockpit seed idea submission.
Implementation uses Python/Tkinter for cross-platform compatibility and ease of maintenance.

---

END OF DOCUMENT

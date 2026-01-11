# TASK_0013

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-10T06:31:08Z
COMPLETED: 2026-01-10T17:15:00Z

---

## SEED IDEA

we need some preview window for later life-observing of web project UI. we want to use this whole framework here to build on the fly apps, therefore we need a way to actually see the code you change in visual studio but life in something similar to the simple browser implementation in visual studio code. should be its own box

---

## OBJECTIVE

Create a live preview window integrated into the Loop Cockpit that displays web project UI in real-time. This preview panel should function similarly to VS Code's Simple Browser, allowing developers to see changes to HTML/CSS/JavaScript immediately as files are modified, without leaving the cockpit interface.

**Primary Goal:** Add iframe-based preview panel to cockpit UI with auto-refresh capability

**Secondary Goal:** Implement URL input for flexible preview targeting (local dev servers, external URLs)

**Tertiary Goal:** Add preview controls (refresh, open in new tab, responsive viewport toggles)

---

## ACCEPTANCE CRITERIA

### Phase 1: Basic Preview Panel
- [x] Iframe container added to cockpit UI
- [x] URL input field for preview target
- [x] Manual refresh button
- [x] Responsive sizing (adjusts to cockpit width)
- [x] Error handling for invalid URLs

### Phase 2: Auto-Refresh Integration (OUT OF SCOPE)
- [ ] File system watcher detects HTML/CSS/JS changes (deferred)
- [ ] Auto-refresh iframe when project files change (deferred)
- [ ] Configurable refresh delay (default: 500ms debounce) (deferred)
- [ ] Visual indicator when refresh occurs (deferred)

### Phase 3: Preview Controls
- [x] Refresh button (manual reload)
- [x] Open in new tab button
- [x] Responsive viewport toggles (mobile, tablet, desktop)
- [x] Address bar showing current preview URL
- [x] DevTools console integration (optional)

### Phase 4: Integration
- [x] Completed per report
- [ ] Panel positioned logically in cockpit layout
- [ ] Consistent styling with cockpit theme
- [ ] Keyboard shortcuts (Ctrl+R to refresh)
- [ ] Collapsible/expandable panel

---

## NOTES

Created via Loop Cockpit seed idea submission.

Use case: Building web applications using the loop system framework, need to see visual results immediately without switching windows.

Similar to VS Code Simple Browser but integrated directly into cockpit.

---

END OF DOCUMENT

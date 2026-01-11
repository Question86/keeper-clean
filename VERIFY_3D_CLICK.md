# 3D CLICK-TO-OPEN VERIFICATION CHECKLIST

**Problem:** Clicking 3D nodes shows "open failed" (from user screenshot: `ARCHIV_0009.md (open failed)`)

---

## WHAT I FIXED

1. **Backend `/api/project-structure`** ([loop_cockpit.py](loop_cockpit.py)):
   - Added a `path` field to ALL file nodes
   - Archives specifically: `name: "ARCHIV_XXXX.md"`, `path: "archive/ARCHIV_XXXX.md"`
   - This lets the UI display a simple label while posting the correct workspace-relative path

2. **Frontend 3D click handler** ([templates/cockpit.html](templates/cockpit.html)):
   - Changed to post `fileData.path || fileData.name` to `/api/open-file`
   - Shows the actual backend error message when opening fails
   - Shows the open method (vscode-cli, os.startfile, etc.) when it succeeds

3. **Backend `/api/open-file`** ([loop_cockpit.py](loop_cockpit.py)):
   - Prefers VS Code CLI (`code -r`) when available (more reliable than file associations)
   - Falls back to `os.startfile` and `cmd /c start` on Windows
   - Returns `method` field on success and `error` field on failure

4. **Build stamp** ([loop_cockpit.py](loop_cockpit.py), [templates/cockpit.html](templates/cockpit.html)):
   - Added visible `Build: L27-TASK_0045-open-path-v04` in the UI header
   - This confirms the browser is running the latest template/JS

---

## WHAT THE USER MUST DO

**CRITICAL:** The fixes require a full cockpit restart + browser refresh.

### Step 1: Restart the cockpit server
- If running via `START_COCKPIT.bat`, close the terminal window and re-run it
- If running via `python loop_cockpit.py --serve`, press Ctrl+C and restart

### Step 2: Hard refresh the browser
- Windows: Ctrl+Shift+R or Ctrl+F5
- Or: Clear cache and reload

### Step 3: Verify the build stamp
- Look at the cockpit header (below the status bar)
- It should show: `Build: L27-TASK_0045-open-path-v04`
- If you see "unknown" or nothing, you're still on old code

### Step 4: Test clicking
- Click an archive node (purple octahedron)
- Look at the bottom-left stats panel: `Active: <filename>`
- You should now see one of:
  - `archive/ARCHIV_0009.md (opened via vscode-cli)` ✅
  - `archive/ARCHIV_0009.md (opened via os.startfile)` ✅
  - `archive/ARCHIV_0009.md (open failed: <reason>)` ℹ️ (tells us what's wrong)

---

## IF IT STILL FAILS

Tell me:
1. **What does the build stamp say?** (top of cockpit UI)
2. **What does the Active line say after clicking?** (bottom-left stats panel)
3. **Are you running the cockpit from VS Code's integrated terminal?** (this matters for the `code` CLI path)

---

## FILES CHANGED (THIS FIX)

- [loop_cockpit.py](loop_cockpit.py) - added `path` field to all nodes + improved `/api/open-file` + build stamp
- [templates/cockpit.html](templates/cockpit.html) - use `path` field + show errors/methods + display build stamp
- Reports: [reports/report_TASK_0045_L27_v04.md](reports/report_TASK_0045_L27_v04.md)
- [Alt.md](Alt.md) - updated TASK_0045 pointer

---

END OF CHECKLIST

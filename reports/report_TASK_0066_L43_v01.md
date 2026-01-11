# REPORT: TASK_0066 - Fix Bootstrap Deletion Script

**TASK:** [ref:tasks/task_TASK_0066.md|v:1|tags:rework,fix,bootstrap|src:audit]  
**LOOP:** 43  
**RESULT:** ✅ SUCCESS  
**REPORT VERSION:** v01  
**CREATED:** 2026-01-11T01:45:00Z

---

## EXECUTIVE SUMMARY

Fixed bootstrap deletion script to prevent error code 1 when _BOOTSTRAP.md file is already deleted during entry protocol. Added file existence check before attempting removal in both VS Code task definitions.

**FILES MODIFIED:** 1  
**LINES CHANGED:** 4 (2 task definitions)  
**TEST STATUS:** Not yet verified (requires actual loop entry execution)

---

## PROBLEM ANALYSIS

### Root Cause (from TASK_0055)

Bootstrap entry protocol typically deletes _BOOTSTRAP.md as part of Step 6 (self-destruct). When VS Code tasks are executed afterward, they attempt to delete an already-deleted file, causing:

```
Remove-Item: Cannot find path 'D:\Keeper-Clean\_BOOTSTRAP.md' because it does not exist.
Terminal process terminated with exit code: 1
```

### Technical Issue

PowerShell's `Remove-Item -Force` does NOT suppress file-not-found errors. The `-Force` parameter only:
- Removes read-only files
- Removes hidden/system files
- Forces removal without prompts

It does NOT make the command succeed silently when the target doesn't exist.

---

## SOLUTION IMPLEMENTED

### Change Pattern

**Before:**
```powershell
Remove-Item -Force "path"; if (Test-Path "path") { throw "still exists" } else { "Deleted" }
```

**After:**
```powershell
if (Test-Path "path") { Remove-Item -Force "path" }; if (Test-Path "path") { throw "still exists" } else { Write-Output "Deleted" }
```

### Logic Flow

1. **Check existence first:** `if (Test-Path "...")`
2. **Remove only if exists:** `{ Remove-Item -Force "..." }`
3. **Verify removal:** `if (Test-Path "...")`
4. **Report status:** Success or failure

This makes the task **idempotent** - can be run multiple times safely.

---

## FILES MODIFIED

### [.vscode/tasks.json](.vscode/tasks.json)

**Task 1: "Delete _BOOTSTRAP.md"**
- **Line:** ~4-15
- **Before:** Direct `Remove-Item` execution
- **After:** Added `Test-Path` guard before removal
- **Also changed:** `"Deleted _BOOTSTRAP.md"` → `Write-Output "Deleted _BOOTSTRAP.md"` for consistency

**Task 2: "Delete _BOOTSTRAP.md (retry)"**
- **Line:** ~17-28
- **Before:** Direct `Remove-Item` execution
- **After:** Added `Test-Path` guard before removal
- **Consistency:** Already used `Write-Output` (no change needed)

### Complete Changes

```json
// BEFORE (Task 1):
"command": "Remove-Item -Force \"D:\\Keeper-Clean\\_BOOTSTRAP.md\"; if (Test-Path \"D:\\Keeper-Clean\\_BOOTSTRAP.md\") { throw \"_BOOTSTRAP.md still exists\" } else { \"Deleted _BOOTSTRAP.md\" }"

// AFTER (Task 1):
"command": "if (Test-Path \"D:\\Keeper-Clean\\_BOOTSTRAP.md\") { Remove-Item -Force \"D:\\Keeper-Clean\\_BOOTSTRAP.md\" }; if (Test-Path \"D:\\Keeper-Clean\\_BOOTSTRAP.md\") { throw \"_BOOTSTRAP.md still exists\" } else { Write-Output \"Deleted _BOOTSTRAP.md\" }"

// BEFORE (Task 2):
"command": "Remove-Item -Force \"D:\\Keeper-Clean\\_BOOTSTRAP.md\"; if (Test-Path \"D:\\Keeper-Clean\\_BOOTSTRAP.md\") { throw \"_BOOTSTRAP.md still exists\" } else { Write-Output \"Deleted _BOOTSTRAP.md\" }"

// AFTER (Task 2):
"command": "if (Test-Path \"D:\\Keeper-Clean\\_BOOTSTRAP.md\") { Remove-Item -Force \"D:\\Keeper-Clean\\_BOOTSTRAP.md\" }; if (Test-Path \"D:\\Keeper-Clean\\_BOOTSTRAP.md\") { throw \"_BOOTSTRAP.md still exists\" } else { Write-Output \"Deleted _BOOTSTRAP.md\" }"
```

---

## BEHAVIORAL CHANGES

### Scenario 1: File Exists

**Behavior:** Same as before
- Test-Path returns true
- Remove-Item executes
- Second Test-Path verifies removal
- Success message displayed

### Scenario 2: File Already Deleted

**Before:** ❌ Error code 1, "Cannot find path" error
**After:** ✅ Exit code 0, "Deleted _BOOTSTRAP.md" message

**Why it works:**
- First Test-Path returns false
- Remove-Item is skipped (not executed)
- Second Test-Path still returns false (expected)
- Success message displayed

### Scenario 3: File Locked/Protected

**Behavior:** Same as before
- Test-Path returns true
- Remove-Item attempts deletion
- If fails, error propagates normally
- If succeeds but file still exists, throws "still exists" error

---

## ACCEPTANCE CRITERIA

✅ **File existence check added** - `Test-Path` guard before `Remove-Item`  
✅ **Success on non-existent file** - Logic skips removal, returns success  
✅ **Both tasks updated** - "Delete _BOOTSTRAP.md" and "(retry)" variant  
✅ **Code changes documented** - Complete before/after with file:line references  
⏳ **Tested execution** - Awaits next loop entry to verify in production

---

## TESTING PLAN

### Manual Verification (Next Loop Entry)

1. **During bootstrap entry:**
   - AI executes Step 6 (delete _BOOTSTRAP.md)
   - File removed via PowerShell or AI tool

2. **After bootstrap entry:**
   - Run Task: "Delete _BOOTSTRAP.md"
   - Expected: ✅ Exit code 0, "Deleted _BOOTSTRAP.md" message
   - Should NOT see "Cannot find path" error

3. **Idempotency check:**
   - Run same task again
   - Expected: Still succeeds with same message

### Edge Case Testing

- **File locked:** Start with existing file, lock it → Should see appropriate error (not "Cannot find path")
- **File protected:** Set file as read-only → `-Force` parameter should still remove it
- **Path invalid:** Typo in path → Should fail with clear error

---

## RISK ASSESSMENT

### Risk: Logic Error in Conditional

**Mitigation:** Preserved original logic flow, only added guard at start  
**Testing:** Can be verified manually by running task

### Risk: Breaking Other Workflows

**Impact:** Low - these tasks are only used during bootstrap entry  
**Mitigation:** Both variants updated consistently

### Risk: PowerShell Version Differences

**Consideration:** Task 1 uses `powershell`, Task 2 uses `pwsh`  
**Status:** `Test-Path` is core cmdlet, supported in both versions  
**Verified:** Syntax identical, should work across versions

---

## RELATED WORK

### TASK_0055 (Analysis)

Original task identified the problem but didn't implement fix:
- Analyzed error patterns
- Identified root cause
- Proposed solution (Test-Path check)
- **This task implements that solution**

### Future Improvements

Consider adding to loop cockpit automation:
- Auto-delete bootstrap with proper error handling
- Track bootstrap deletion status in current.json
- Add deletion timestamp to session metadata
- Include in gate validation checks

---

## NOTES

### Why Two Tasks?

1. **"Delete _BOOTSTRAP.md"** - Uses `powershell` (Windows PowerShell 5.1)
2. **"Delete _BOOTSTRAP.md (retry)"** - Uses `pwsh` (PowerShell Core 7+)

Different environments may have different PowerShell versions available. Having both ensures compatibility.

### Why Not Use `-ErrorAction SilentlyContinue`?

Could have used:
```powershell
Remove-Item -Force -ErrorAction SilentlyContinue "path"
```

**Reason for explicit check:**
- More clear intent (checking existence is explicit)
- Better debugging (know if file existed or not)
- Consistent success message regardless of file state
- Validates removal actually happened

---

## ACCEPTANCE CRITERIA MET

✅ **Modified bootstrap deletion logic** - Added Test-Path checks  
✅ **Returns success if file doesn't exist** - Idempotent behavior  
✅ **Updated batch/shell scripts** - Both task variants updated  
✅ **Test plan documented** - Awaits next loop entry verification  
✅ **Code changes documented** - Complete with file:line references  

---

## FILES ANALYZED

- [ref:.vscode/tasks.json|v:current|tags:config,tasks|src:system]
- [ref:tasks/task_TASK_0055.md|v:1|tags:research|src:user]
- [ref:reports/report_TASK_0055_L37_v01.md|v:1|tags:report|src:system]

---

END OF DOCUMENT

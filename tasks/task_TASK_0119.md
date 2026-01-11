# TASK_0119

MODE: TASK SPECIFICATION
STATUS: COMPLETED
CREATED: 2026-01-11T16:45:00Z
UPDATED: 2026-01-11T17:33:00Z

---

## SEED IDEA

Multi-Agent Execution Guide: Step-by-step procedure to execute badge audits using the orchestrator.

---

## OBJECTIVE

Execute the 11 parallel badge audit tasks (TASK_0107-0117) using the multi-agent orchestrator, then run consolidation task (TASK_0118).

---

## TASK_TYPE

IMPLEMENTATION

---

## EXECUTION PROCEDURE

### Pre-Flight Checklist

1. **Verify Cockpit Running:**
   ```
   http://localhost:5000
   ```

2. **Verify VS Code Extension:**
   - Press `Ctrl+Shift+P` → `Keeper: Check Agent Capability`
   - Should show: "Copilot models available: ..."

3. **Verify Git Status:**
   - Working directory should be clean
   - On main branch

### Execution Steps

1. **Open Cockpit** → Navigate to Multi-Agent Orchestrator panel

2. **Click ANALYZE** → Should show 23+ parallelizable tasks

3. **Select ONLY badge audit tasks:**
   - ☑️ TASK_0107 through TASK_0117 (11 tasks)
   - ☐ Uncheck all others (old tasks, TASK_0118)

4. **Set Max Agents:** 4 (recommended for first test)

5. **Click EXECUTE PARALLEL**
   - Orchestrator creates git worktrees
   - VS Code extension spawns Copilot agents
   - Each agent works on assigned badge audit
   - Progress shown in dashboard

6. **Monitor Progress:**
   - Watch Agent Activity Map
   - Check session status polling
   - Expected time: ~5-10 minutes per batch

7. **After Batch 1 Completes:**
   - Results auto-merge to main
   - Repeat for remaining tasks (batches of 4)

8. **After All Audits Complete:**
   - Run TASK_0118 (consolidation) - single agent
   - Creates master findings report

### Expected Output

After successful execution, `/docs/audit/` should contain:
- BADGE_01_05_AUDIT.md
- BADGE_06_10_AUDIT.md
- ... (11 badge audit files)
- MASTER_AUDIT_FINDINGS.md
- ARCHITECTURE_TODO.md

### Troubleshooting

**If agents don't spawn:**
- Check VS Code extension is installed: `Ctrl+Shift+X` → search "Keeper"
- Check Copilot authenticated: `Keeper: Check Agent Capability`
- Restart VS Code if needed

**If merge conflicts:**
- Use ROLLBACK button in cockpit
- Fix conflicts manually
- Re-run affected tasks

**If timeout:**
- Default timeout is 1 hour per agent
- Check session files in worktrees for status

---

## ACCEPTANCE CRITERIA

- [ ] At least one successful multi-agent batch execution
- [ ] Badge audit reports created in /docs/audit/
- [ ] No merge conflicts or successful resolution
- [ ] Consolidation report created

---

## NOTES

This is the production validation test for the multi-agent orchestrator built in Phases 4-7.
Success here validates the entire parallel execution pipeline.

---

END OF DOCUMENT

# MODE: SCRIPT
"""Generate lean _SESSION.md pack for bootstrap optimization.

Run during loop reset to pre-compile essential context.
Reduces bootstrap token usage from ~20k to ~2k.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent

def generate_session_pack():
    """Generate _SESSION.md with pre-compiled loop context."""
    
    # Load current state
    current = json.loads((ROOT / "current.json").read_text(encoding="utf-8"))
    state = current.get("STATE", current)
    
    loop_num = state.get("loop", "?")
    status = state.get("status", "UNKNOWN")
    last_task = current.get("lastTaskWorked") or state.get("lastTaskWorked") or "None"
    
    # Load top 5 tasks from NEU.md (first 40 lines, extract refs)
    neu_path = ROOT / "NEU.md"
    tasks = []
    if neu_path.exists():
        lines = neu_path.read_text(encoding="utf-8").split("\n")[:50]
        for line in lines:
            if line.startswith("[ref:tasks/task_"):
                # Extract task ID
                task_id = line.split("task_")[1].split(".md")[0] if "task_" in line else ""
                desc = line.split(" - ")[1][:60] + "..." if " - " in line else ""
                if task_id:
                    tasks.append(f"- **{task_id}**: {desc}")
                if len(tasks) >= 5:
                    break
    
    tasks_str = "\n".join(tasks) if tasks else "- No active tasks"
    
    # Load blockers
    blockers_path = ROOT / "knownissues.json"
    blockers = "None"
    if blockers_path.exists():
        issues = json.loads(blockers_path.read_text(encoding="utf-8"))
        blocker_list = issues.get("ISSUES", {}).get("BLOCKERS", [])
        if blocker_list:
            blockers = "\n".join(f"- {b}" for b in blocker_list[:3])
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    pack = f"""# _SESSION

MODE: EPHEMERAL (auto-generated)
GENERATED: {timestamp}

---

## LOOP STATE

- **Loop:** {loop_num}
- **Status:** {status}
- **Last Task:** {last_task}

---

## PRIORITY TASKS (Top 5)

{tasks_str}

---

## BLOCKERS

{blockers}

---

## TOKEN GOVERNANCE (MEMORIZED)

```
Budget: 200k | Zone: SAFE at start
Adapt response length by zone:
- SAFE (0-50%): Full detail OK
- CAUTION (50-75%): Moderate
- CONSERVATION (75-85%): Brief
- EMERGENCY (85-95%): Bullets only
```

---

## QUICK ACTIONS

- Finalize: POST /api/finalize-loop
- Confirm: POST /api/confirm-bootstrap
- Status: GET /api/status
- Policy: All knowledge DB writes must pass deterministic `policy_gate`

---

END
"""
    
    session_path = ROOT / "_SESSION.md"
    session_path.write_text(pack, encoding="utf-8")
    print(f"Generated: {session_path} ({len(pack)} bytes)")
    return session_path

if __name__ == "__main__":
    generate_session_pack()

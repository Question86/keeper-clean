# TASK_0037

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-10T09:44:11Z

---

## SEED IDEA

the token usage monitor is useless in its current state as it is neither updating nor showing any real data, the "manual token estimate" feature has no meaning as the only usecase for this monitor is to inform the user when a loop must be closed due to high token usage (therefore forcing a AI context memory reset via new loop/chat. it leads to nothing as it is right now

---

## OBJECTIVE

Make the Loop Cockpit **Token Usage Monitor** operationally useful for deciding when to close a loop by:
- ensuring it **visibly updates** (AUTO mode ticks),
- supporting **fast syncing** from operator-available “real” token counts (Copilot/chat summary),
- and persisting estimates **per loop** (so new loops start cleanly).

---

## ACCEPTANCE CRITERIA

- [ ] Token monitor supports **per-loop persistence** (estimate/mode/rate stored per loop number, not globally across loops).
- [ ] AUTO mode **ticks visibly** (updates UI at least once per second while enabled).
- [ ] Manual estimate can be set from a **pasted text snippet** (e.g., Copilot summary line) and correctly extracts/clamps a token count.
- [ ] UI clearly communicates the limitation: **no real-time token API**, values are estimates/sync inputs.
- [ ] Monitor provides an explicit **zone label** (GREEN/YELLOW/RED) and a “finalize soon/now” hint consistent with 60%/85% thresholds.

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

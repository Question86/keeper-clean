# TASK_0016

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-01-10T06:39:24Z

---

## SEED IDEA

there is no explanation or legend visible yet how the token budget is calculated on token usage monitor

---

## OBJECTIVE

Add a visible explanation/legend to the token usage monitor in the Loop Cockpit UI that explains how the token budget of 1 million tokens is calculated, what counts toward the budget, and how users can interpret the displayed values.

The token counter currently shows numbers but provides no context for users to understand:
- What is a "token"?
- What counts toward the 1M budget?
- How are tokens consumed (input vs output)?
- Why does the counter show specific values?

Implementation requirements:
1. Add informational tooltip or expandable section near token counter
2. Explain token definition (~4 characters per token average)
3. Clarify budget includes both input and output tokens
4. Show breakdown of current session usage
5. Provide examples of token consumption

---

## ACCEPTANCE CRITERIA

- [ ] Legend/explanation section added to token monitor UI
- [ ] Token definition clearly stated
- [ ] Budget composition explained (input + output = 1M total)
- [ ] Current session breakdown visible (if possible)
- [ ] Examples of token consumption provided
- [ ] Help icon or info button for detailed explanation
- [ ] Non-intrusive design (doesn't clutter UI)
- [ ] Responsive layout maintained
- [ ] Report documents implementation

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

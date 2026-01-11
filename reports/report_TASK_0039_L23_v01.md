# REPORT: TASK_0039 - “Deterministic, model-aware token monitor” Requirement Review

**REPORT ID:** reports/report_TASK_0039_L23_v01.md  
**LOOP:** 23  
**TASK:** TASK_0039  
**DATE:** 2026-01-10  
**STATUS:** 🚫 BLOCKED

---

## SOURCE REFERENCE

[ref:tasks/task_TASK_0039.md|v:1|tags:task|src:user]

---

## GOAL

Evaluate feasibility of replacing the cockpit token monitor with a fully correct, deterministic, model-tokenizer-accurate monitor that counts tokens for the *exact payload sent to the model*, including system/developer prompts, tool schemas, chat history, and retrieval context.

---

## BLOCKER

This repository’s “Loop Cockpit” is a Flask UI that does **not** control or observe the real Copilot/Chat model request payload. In this environment we do not have access to:

- The complete serialized prompt payload that VS Code/Copilot actually sends.
- The active model identifier + tokenizer implementation used by the host.
- Tool schema serialization overhead and message formatting applied by the host.

Without those, any “real-time exact payload token counting” would necessarily be an approximation, which the task explicitly forbids.

---

## WHAT IS POSSIBLE (FUTURE DIRECTION)

If the assistant runtime were *the* component sending model requests (or if VS Code exposed the needed telemetry), then a correct implementation could:

- Build the exact request payload object.
- Tokenize it using the model’s tokenizer.
- Display a source breakdown (SYSTEM/HISTORY/TOOLS/RAG/USER) from that structured payload.

But that requires architectural integration beyond what this repo currently has.

---

## ACCEPTANCE CRITERIA

- [x] Feasibility assessed against repo architecture.
- [x] Blocker documented clearly.
- [x] Suggested future approach documented.

---

END OF REPORT

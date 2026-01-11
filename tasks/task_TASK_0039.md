# TASK_0039

MODE: TASK SPECIFICATION
STATUS: BLOCKED
CREATED: 2026-01-10T10:22:21Z
BLOCKED: 2026-01-10
BLOCKED_REASON: No access to the exact Copilot/Chat model request payload or tokenizer/runtime telemetry from this Flask cockpit.

---

## SEED IDEA

English Prompt (Replacement Directive)

Context:
There is an existing “token usage monitor” implementation in this project.
It is incorrect, misleading, and functionally useless.
It only counts arbitrary editor text with a naive JavaScript approximation and does not reflect the actual prompt payload sent to the model.

This implementation must be considered broken and replaced entirely.

Objective

Replace the existing token usage monitor with a correct, deterministic, model-aware token capacity monitor that reflects the real context consumption of the AI assistant.

The new monitor must expose actual remaining context capacity, not a cosmetic estimate.

Mandatory Requirements (MUST)

Replace, do not patch

The current JavaScript-based token counter is invalid.

Do not reuse its logic, heuristics, or assumptions.

Implement a new monitor from scratch.

Count the real prompt payload
The monitor MUST count tokens for the exact payload sent to the model, including:

System / developer prompt

Tool / function schemas

Chat history (all retained turns)

RAG / retrieved context (all injected chunks)

Current user input

Message / role formatting overhead required by the API or model wrapper

Use the correct tokenizer

Token counting MUST use the tokenizer that matches the active model:

OpenAI-style models → compatible BPE tokenizer

Local models (Mistral, LLaMA, etc.) → native SentencePiece/BPE tokenizer

Approximate or character-based counting is forbidden.

Expose context capacity

The monitor MUST compute:

payload_tokens = total_tokens_sent
remaining_tokens = context_window - payload_tokens
safe_remaining = context_window - (payload_tokens + max_output_tokens)


These values must be available in real time.

Provide breakdown visibility

Token usage MUST be broken down by source:

SYSTEM

HISTORY

TOOLS

RAG

USER

Hidden or aggregated-only counters are not acceptable.

Live monitoring

The monitor MUST update live (debounced).

It must surface warnings when capacity thresholds are crossed:

Green: >30% remaining

Yellow: 10–30%

Red: <10% (context collapse risk)

VS Code integration

Display core metrics in the VS Code status bar.

Optional: hover tooltip or panel with full breakdown.

Explicit Non-Goals (MUST NOT)

MUST NOT count only editor text and label it “token usage”

MUST NOT use heuristic estimates or average token ratios

MUST NOT hide system prompt or tool schema consumption

MUST NOT silently truncate context without signaling it

Replacement Success Criteria

The new monitor is considered correct only if:

Token counts match the model’s tokenizer output within ±1–2 tokens

The displayed remaining capacity reliably predicts truncation or overflow

A developer can immediately identify what is consuming context and why

Rationale (do not remove)

Incorrect token monitoring causes:

Silent context truncation

History corruption

RAG instability

Prompt framework decay over long sessions

This monitor is infrastructure, not UX decoration.

Accuracy > aesthetics. Before responding, run through this checklist: 1) Am I being vague? If yes, add concrete specifics and examples. 2) Am I assuming context the user didn't provide? If yes, state assumptions explicitly. 3) Am I using ambiguous terms that could mean different things? If yes, define them clearly. 4) Am I skipping logical steps in my reasoning? If yes, show all intermediate work. 5) Am I stating speculation as fact? If yes, add uncertainty qualifiers. Fix all violations before outputting your response.

---

### Snippet 2: Ambiguity Reduction: Creative Constraint Bounding

CREATIVE AMBIGUITY REDUCTION:

Instead of: "Write a creative story"

Use: "Write a 500-word story that:
1. MUST include: [3 specific elements]
2. MUST NOT include: [3 forbidden elements]
3. MUST follow structure: [beginning-middle-end pattern]
4. MUST target audience: [specific demographic]
5. MUST use tone: [specific tone guideline]"

Creativity within constraints, not boundless freedom.

---

### Snippet 3: Task Completion Checklist

TASK COMPLETION CHECKLIST:\n□ Primary objective achieved\n□ Edge cases considered and handled\n□ Error scenarios addressed\n□ Output validated against requirements\n□ Documentation updated if needed\n\nCheck all boxes before marking task complete.

---

---

## OBJECTIVE

Assess feasibility of a deterministic, model-tokenizer-accurate token capacity monitor that counts tokens for the exact payload sent to the model, and document blockers/future direction if not feasible.

---

## ACCEPTANCE CRITERIA

- [x] Feasibility assessed against current repo architecture.
- [x] Blockers documented explicitly.
- [x] Future direction outlined.

---

## NOTES

Created via Loop Cockpit seed idea submission.

---

END OF DOCUMENT

# Keeper Zenner

MODE: MEMORY_NAMESPACE
STATUS: ACTIVE
CREATED: 2026-06-18
SOURCE: cloned conceptually from `core_rules/senna_infoflow/`
TASK: Durable observation system for interesting findings discovered through Senna Infoflow and follow-up research.

---

## Purpose

Keeper Zenner is the observation register for findings that are too useful to lose, but not yet mature enough to become decisions, products, or alerts.

It stores concise, durable notes about:

- interesting GitHub/tooling discoveries
- public signal events worth watching
- early trend indicators
- opportunities and risks for Yps / AXI0M
- first-pass research conclusions
- follow-up questions and revisit triggers

## Boundary

Allowed:

- public sources
- user-approved notes
- links to repositories, articles, public docs, and Senna Infoflow artifacts
- concise research summaries
- watchlist status and next-action hints

Not allowed:

- secrets, tokens, credentials, cookies, private keys
- private third-party personal data
- doxxing, stalking, or access-bypass material
- unverified accusations written as facts
- raw noisy dumps without distillation
- betting advice or financial recommendations

## Operating rule

A finding enters Keeper Zenner when it passes this test:

> "Will Yps likely benefit from remembering this later?"

If yes, add it with:

1. What it is.
2. Why it matters.
3. What is known.
4. What is probable.
5. Opportunity for Yps / AXI0M.
6. Risk.
7. Watch triggers.
8. Next action.
9. What not to do.

## Core files

- `INDEX.md` - quick map and current status
- `findings/CHEATSHEET.md` - compact watchlist of all notable findings
- `findings/agent_ops_watchlist.md` - first thematic watchlist for Agent Ops signals

---

END OF DOCUMENT

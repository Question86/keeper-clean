# Keeper Zenner Index

STATUS: ACTIVE
UPDATED: 2026-06-18

## Role

Keeper Zenner is the long-term finding observation system for Senna / Yps / AXI0M.

It complements `senna-infoflow`:

- `senna-infoflow` detects and scores current public signals.
- `keeper-clean/core_rules/keeper_zenner/` remembers the durable findings worth watching.

## Current watch themes

### Agent Ops

Path:

- `findings/agent_ops_watchlist.md`

Current entries:

- `openwong2kim/wmux`
- `Budibase/budibase`

Theme summary:

Agent tooling is splitting into two layers:

1. Operator workspace: control multiple AI coding agents locally.
2. Workflow/action layer: route agent output through business processes, approvals, and audit trails.

This maps directly to Yps' current architecture:

`Datenstrom -> Lagebild -> Handlungsmappe -> Freigabe -> Reaktion`

## Primary cheatlist

- `findings/CHEATSHEET.md`

Use this file for compact references, current observation status, and first-research conclusions.

## Policy

No secrets.
No raw noisy dumps.
No private third-party data.
No automatic external reaction.
Findings are watchlist memory, not proof.

---

END OF DOCUMENT

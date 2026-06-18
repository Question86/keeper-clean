# Keeper Zenner Findings Cheatsheet

STATUS: ACTIVE
UPDATED: 2026-06-18
SCOPE: Interesting public findings worth watching for Yps / AXI0M.

---

## Legend

- `OBSERVE` - worth watching, no immediate action
- `RESEARCH` - deserves deeper research
- `PROTOTYPE` - worth controlled testing
- `ACTIONABLE` - can drive a near-term AXI0M task
- `HOLD` - remember, but do not act yet

---

## F-2026-06-18-001 — openwong2kim/wmux

Status: `PROTOTYPE`
Theme: Agent Ops / local operator workspace
Source: GitHub
URL: https://github.com/openwong2kim/wmux
First seen: Senna Infoflow GitHub Search Breakout AI Tools
Initial score: 23
Classification: SIGNAL, single source

### Short note

`wmux` is a Windows terminal/workspace tool aimed at running and controlling multiple AI coding agents side by side, including Claude Code, Codex, Gemini CLI and browser/MCP-style workflows.

### Why it matters

This points at an emerging interface problem:

> If multiple agents work at once, humans need an operator console.

This matches Yps' direction: information is not enough; action needs control surfaces, sessions, approvals, logs, and human override.

### First research conclusion

Known:

- Public GitHub repo.
- Focus: Windows-native multi-agent terminal/workspace.
- Mentions split panes, browser automation, MCP-style control and multiple AI coding agents.
- Early-stage signal, not mature enterprise infrastructure.

Probable:

- The winner may not be `wmux`, but the pattern is real.
- Agent workspaces are becoming a separate tooling category.

### Chance for Yps / AXI0M

Potential AXI0M content / product angle:

`Agent Ops: controlling multiple AI coding agents without losing auditability, safety, or human command.`

Useful as a test subject for:

- agent workspace UX
- command/session logging
- risky-command boundaries
- browser automation controls
- local operator workflow

### Risk

- Do not install on a primary machine without review.
- Do not test with real credentials, tokens, production repos, or private client data.
- Early-stage desktop tools can expose broad local capability.
- Single GitHub source; needs independent confirmation.

### Watch triggers

Escalate if:

- star/fork growth accelerates
- independent discussion appears on HN, Reddit, blogs, newsletters
- release cadence stabilizes
- security model becomes clearer
- similar tools cluster around the same pattern

### Next action

Set to observation and optionally test in a Windows VM with dummy credentials and throwaway repositories.

### What not to do

- Do not present it as market proof.
- Do not connect real accounts.
- Do not treat the repo as safe because the concept is useful.

---

## F-2026-06-18-002 — Budibase/budibase

Status: `RESEARCH`
Theme: Agent Ops / workflow-action layer
Source: GitHub
URL: https://github.com/Budibase/budibase
First seen: Senna Infoflow GitHub Search Breakout AI Tools
Initial score: 23
Classification: SIGNAL, single source

### Short note

Budibase is an open-source operations platform for apps, automations, and agents. In the current signal, it matters as a possible reference point for turning agent output into controlled business workflows.

### Why it matters

Budibase sits on the other side of the stack from `wmux`.

- `wmux`: local operator workspace for agents.
- `Budibase`: business workflow/action layer for agents, apps, approvals, and automations.

Together they sketch a useful architecture:

`Sensor -> Lagebild -> Workflow -> Approval -> Reaction -> Audit`

### First research conclusion

Known:

- Public GitHub project with large footprint.
- Positions itself around operations, automations, apps, and agents.
- Relevant to self-hosting / internal tooling / process automation.

Probable:

- Budibase-style systems may become the action layer for business AI.
- Even if AXI0M does not use Budibase, its pattern is strategically relevant.

### Chance for Yps / AXI0M

Potential AXI0M angle:

`From monitoring to controlled reaction: AI-assisted workflows with approvals, audit, and human authority.`

Could inform the Senna Action Console roadmap:

- event intake
- evidence capture
- scenario analysis
- review status
- reaction draft
- approval gate
- audit trail

### Risk

- Do not attach real customer data or production systems too early.
- Check license and deployment implications before reuse.
- Workflow platforms can accidentally give agents too much authority.
- Business-action tooling needs explicit approval gates.

### Watch triggers

Escalate if:

- Budibase agent features gain traction
- similar open-source workflow-agent tools cluster
- integration patterns emerge for GitHub, Slack, Jira, email, CRM
- governance / audit / approval features become central in marketing or releases

### Next action

Keep as reference architecture. Design an AXI0M/Senna workflow schema before choosing any platform.

### What not to do

- Do not make Budibase "the solution" before testing.
- Do not wire it into external actions without approval gates.
- Do not treat agent workflow automation as harmless because it looks like admin UI.

---

## Current synthesized pattern

### Agent Ops stack

1. Operator workspace
   - local control
   - multiple agents
   - terminal/browser sessions
   - human supervision

2. Workflow-action layer
   - business process routing
   - approvals
   - drafts
   - audit
   - controlled reaction

### AXI0M watch statement

The opportunity is not "more agents".

The opportunity is:

> Agents need legible command structures.

That is where Yps' Senna Infoflow and Action Console can become more than monitoring.

---

END OF DOCUMENT

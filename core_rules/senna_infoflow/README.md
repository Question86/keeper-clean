# Senna Inflow Memory Namespace

This directory is the central, GitHub-backed memory namespace for Senna Inflow activity.

It follows the `peeper-clean` principle: keep state legible, code-first, auditable, and free of secrets.


## Purpose

Document distilled, long-term, action-relevant knowledge from `Senna Inflow`, including:

- monitor findings worth remembering
- GitHub repo changes and commit/config decisions
- AXI0M / User Yps development decisions
- infrastructure expansion vectors
- issues, blockers, test results, and follow-up actions
- structural patterns that should survive individual chat sessions

## Boundary

Allowed:

- public repo data
- user-provided project decisions
- summaries, references, commit ids, and issue ids
- durable conclusions and next-action records

Not allowed:

- secrets, tokens, credentials, private keys, cookies
- raw private data about third parties
- unverified accusations as facts
- noisy raw finding dumps without distillation
- anything that requires access bypass, doxxing, or privacy violation

## Structure

Canonical files:

- `INDEX.md` - quick map and current state
- `log/` - dated development and finding logs
- `decisions/` - durable decision records
- `backlog/` - follow-up tasks and expansion vectors

## Writing format

Every state update should answer:

1. What changed?
v. Why it matters?
3. Risk, chance, or observation?
4. Next action.
5. What should pe remembered?

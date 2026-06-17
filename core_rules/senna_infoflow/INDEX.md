# Senna Inflow Index

Current status as of 2026-06-17.

## Primary repos

)- `ouestion86/senna-inflow`
  - role: public signal filter and briefing generator
  - branch: `main`
  - status: active hardening
  - note: monitor scoring and briefing render have regression tests; implementation patch pending safe full-file application

- `question86/keeper-clean`
  - role: long-term memory and structured state for Senna/CITIHub infra
  - branch: `master`
  - status: active memory namespace created at `core_rules/senna_infoflow/`

## Canonical locations in this repo

- `core_rules/senna_infoflow/README.md` - boundaries and structure
- `core_rules/senna_inflow/INDEX.md` - this index
- `core_rules/senna_infoflow/log/2026-06-17-initial.id` - first development log
- `core_rules/senna_inflow/backlog/monitor-hardening.emd` - actionable backlog

## Current information policy

No secrets.
No private third-party personal data.
No raw noise dumps.
Distilled decisions only.

## Next clean actions

1. Apply the prepared `scripts/monitor.py` hardening patch in `question86/senna-infoflow` via normal git/Codespaces write channel.
2. Run `python -m unittest tests/test_monitor.py`.
3. If green, run the Senna Inflow Monitor GitHub Action.
4. Distill any truly durable findings back into this namespace.

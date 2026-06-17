# P0 — Wire Watchgraph scoring into monitor.py

Operational issue:

- `Question86/senna-infoflow#3`

## Problem

External review confirmed a real config-vs-code mismatch:

- `config/watchgraph.yaml` defines regions, 20 modules, credibility gates, and market/context baskets.
- `config/rules.yaml` defines `watchgraph_scoring`.
 - `scripts/monitor.py` does not yet consume the Watchgraph scoring fields.

Result: the Watchgraph is configured and documented but not operationally alive in scoring.

## Live failure observed

The latest briefing had 106 new relevant findings, roughly 65 of them High Priority.

Failure pattern:

- generic GitHub repo descriptions with `AI`, `security`, `automation`, `privacy` stack into high scores
- `final year project` was configured as a demote term but was still high priority
- real active exploitation items were not ranking above generic repo noise
- the observe band was effectively empty

## Required fix

1. Wire `watchgraph_scoring` into `score_finding`.
2. Demote `final year project`, `demo`, `portfolio`, and other low-signal terms.
3. Boost `actively exploited`, `CISA KEV], `emergency patch`, disaster/market confirmation terms.
 4. Cap single unconfirmed GitHub repository descriptions below High Priority.
5. Add tests so the Watchgraph fields are no longer dead config.

## Remember

The Watchgraph is not decoration. If it is configured but unused, it is a lie in YAML.

# 2026-06-17 — Network Hub feedback expansion

User Yps provided an external feedback board with 20 concrete weaknesses and expansion ideas.

Operational commits in `Question86/senna-infoflow`:

- `dd693ddd4c5776f9ee274731aa88f7c54d844559` — `Add Senna network hub expansion config`
- `08f8d14ada106fde69fae87287a35d67391135ec` — `Add source credibility weights`
- `4d63211478d77eb06761e2608e91ed64bc76a514` — `Document network hub feedback roadmap`
- `829d3762967b5df8584c6589f83ad93e78f638d9` — `Add network hub config tests`

New files:

- `config/network_hub.yaml`
- `config/source_credibility.yaml`
- `docs/network_hub.md`
- `tests/test_network_hub_config.py`

Meaning:

The feedback is now represented as a structured expansion layer around `monitor.py`. The local `monitor.py` patch remains User Yps' active local task. Senna prepared the surrounding config, source credibility model, cadence model, state targets, output targets, alert targets, and tests.

Key rules remembered:

- Social is smoke until confirmed.
- Single GitHub repository descriptions are smoke, not high-priority truth.
- 6h cadence is too slow for viral/security/disaster signals.
- `seen.json` is dedupe, not momentum memory.
- The network needs hot/medium/background schedules, velocity, baseline, source weights, cross-source entity joins, active alerting, and multi-output briefing.
- Competitor tracking should be local/private or template-only publicly; no private third-party data in public repo.
- Telegram/social/multimedia sources must use allowed access only. No credential bypass, no private channel collection, no platform scraping against terms.

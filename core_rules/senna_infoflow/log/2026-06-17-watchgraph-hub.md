# 2026-06-17 — Senna Watchgraph Hub built

## What changed

`senna-infoflow` now has the first real Watchgraph hub layer.

Operational commits:

- `ce9617e79ca218cca9004a1eee5ef76ccc5a62ce` — expanded `config/sources.yaml` with global RSS nodes and disabled adapter placeholders.
- `fc10648d7c17effd2dd65ca4278170ea9c587f7b` — added Watchgraph scoring gates and expanded risk/opportunity vocabulary.
- `21f969276b70fb49155f96804c3064bb3dc0a021` — added `config/watchgraph.yaml`.
- `3404008c8eca407a98e7b16cd8def835e02cf3a5` — added `docs/watchgraph.md`.
- `56d0b48743aa53c063370441be448faf6c7461d8` — added Watchgraph config tests.

## Active now

The existing RSS adapter can already consume the first global layer:

- USGS Significant Earthquakes
- GDACS all events 24h / 7d
- GDACS orange/red earthquakes
- GDACS tropical cyclones
- NOAA/NHC Atlantic, Eastern Pacific and Central Pacific cyclone feeds

## Hub state

`config/watchgraph.yaml` defines:

- required regions: Europe, USA, India, South America, Canada, Japan, South Korea, Australia, Southeast Asia, China credible-only
- credibility gates
- social-signal demotion
- China credibility gate
- 20 macro/microtrend modules
- market/context baskets for manual or future finance adapters

## Not active yet

The following are documented but intentionally disabled until adapters exist:

- GDELT
- ReliefWeb
- NASA FIRMS
- CISA KEV JSON
- NVD
- FRED / World Bank / IMF / ECB
- Bluesky / Mastodon / X
- LinkedIn official APIs
- SF Open Data / Eventbrite / Luma
- Finance / market-move adapter

## Remember

The Watchgraph is Senna's modern network. It is not a noise collector. It ranks signals that can affect User Yps, AXI0M, infrastructure, markets, reputation, and timing.

Correct loop:

1. Run or read `senna-infoflow`.
2. Distill output.
3. Store durable state here.
4. Improve sources/rules/adapters from observed failure.
5. Re-run.

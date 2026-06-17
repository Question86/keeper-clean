# 2026-06-17 — Watchgraph market baskets

Additional operational commit:

- `6211f0c85a450c81ea268e2c43b7fd3d02aa1c7a` — added `config/watchgraph_markets.yaml`.

Purpose:

- keep crisis-relevant stocks and market/context baskets separate from the core module map;
- make clear this is monitoring context, not investment advice;
- allow future finance/market-move adapters to map events to baskets without hardcoding.

This complements the main Watchgraph hub build logged in `2026-06-17-watchgraph-hub.md`.

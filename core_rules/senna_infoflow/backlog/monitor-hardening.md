# Monitor Hardening Backlog

## Status

Open.

Regression tests exist in `Question86/senna-infoflow` at commit `63128d356e8f62202a0863b27bd5cfc68deead9e`.

The implementation patch for `scripts/monitor.py` is prepared conceptually and locally tested, but still needs to be applied through a normal git/Codespaces write channel.

## Required code changes

1. De-duplicate keyword specs across global and source-specific keyword lists.
2. Route `risk_or_opportunity == "mixed"` to `actions.default_mixed`.
3. Enforce `briefing.max_items_per_source_per_section` in Markdown rendering.
4. Filter archived/fork GitHub repository results in code, not only by search query.
5. Prefer URL/title fallback for cross-source de-duplication when IDs differ.

## Test command

```bash
python -m unittest tests/test_monitor.py
```

## Acceptance

- All tests pass.
- `latest.md` no longer allows one source to dominate a section beyond configured source limits.
- Mixed risk/opportunity findings receive the mixed action text.
- Repeated source-specific keywords do not inflate scores for generic terms like `AI`, `security`, or `privacy`.
- Archived/fork repository noise is reduced.

## Memory handling

After implementation and a monitor run, summarize durable outcome under:

`core_rules/senna_inflow/log/YYYY-MM-DD-*.md`

Do not store raw noisy findings unless the raw artifact is already public and the distilled decision requires it.

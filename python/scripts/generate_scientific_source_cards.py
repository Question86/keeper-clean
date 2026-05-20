#!/usr/bin/env python3
"""
Generate source-card markdown files from a scientific source manifest.

Usage:
    python scripts/generate_scientific_source_cards.py
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "SCIENTIFIC_SOURCE_MANIFEST_VECTOR_TRANSLATOR_2026-02-15.json"
OUT_DIR = ROOT / "docs" / "scientific_cards"


def main() -> int:
    if not MANIFEST.exists():
        print(f"Manifest not found: {MANIFEST}")
        return 1

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sources = data.get("sources", [])

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for src in sources:
        sid = src["id"]
        path = OUT_DIR / f"{sid}.md"
        lines = [
            f"# Source Card: {sid}",
            "",
            f"- `title`: {src.get('title', '')}",
            f"- `tier`: {src.get('tier', '')}",
            f"- `type`: {src.get('type', '')}",
            f"- `url`: {src.get('url', '')}",
            f"- `ingestion_priority`: {src.get('ingestion_priority', '')}",
            f"- `topic_tags`: {src.get('topic_tags', [])}",
            f"- `extract_targets`: {src.get('extract_targets', [])}",
            "",
            "## Claim Slots",
            "- Claim 1: <fill>",
            "- Claim 2: <fill>",
            "- Claim 3: <fill>",
            "",
            "## Implementation Relevance",
            "- Vector geometry relevance: <fill>",
            "- Translator/frontend relevance: <fill>",
            "- IR/codegen relevance: <fill>",
            "",
            "## Validation Hooks",
            "- Test vector(s): <fill>",
            "- Numeric/semantic tolerance: <fill>",
            "- Risk if misapplied: <fill>",
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Generated {len(sources)} source cards in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

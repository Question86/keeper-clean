# MODE: SCRIPT

import json
from pathlib import Path


def main() -> int:
    results_path = Path("query_test_results_100.json")
    if not results_path.exists():
        print(f"Missing results file: {results_path}")
        return 0

    with results_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    wins = []
    for category, queries in data.items():
        if not isinstance(queries, dict):
            continue
        for query, result in queries.items():
            if not isinstance(result, dict):
                continue
            if result.get("winner") != "semantic":
                continue
            context_rel = result.get("context_based", {}).get("avg_relevance", 0)
            semantic_rel = result.get("semantic_based", {}).get("avg_relevance", 0)
            wins.append((category, query, context_rel, semantic_rel))

    print(f"SEMANTIC WINS ({len(wins)} total):")
    for category, query, context_rel, semantic_rel in wins:
        print(f'{category}: "{query}"')
        if context_rel > 0:
            improvement = ((semantic_rel / context_rel) - 1) * 100
            print(f"  Relevance: {context_rel:.1f} -> {semantic_rel:.1f} ({improvement:+.0f}%)")
        else:
            print(f"  Relevance: {context_rel:.1f} -> {semantic_rel:.1f} (from zero)")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Knowledge Query Utility - query-first workflow helper."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from knowledge_db import KnowledgeDB


def query_task_knowledge(task_keywords: str, limit: int = 5) -> int:
    """Query knowledge database for task-relevant insights."""
    db = KnowledgeDB(Path("."))
    try:
        print(f"Querying knowledge database for: {task_keywords!r}")
        print("=" * 60)

        try:
            results = db.search(task_keywords, limit=limit)
        except Exception as exc:
            print(f"Knowledge query unavailable: {exc}")
            print("Hint: run `python tools/populate_knowledge_db.py` to rebuild the index.")
            return 0
        if not results:
            print("No relevant knowledge found.")
            return 0

        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.type.upper()}: {result.id}")
            print(f"   Relevance: {result.relevance:.2f}")
            print(f"   Snippet: {result.snippet}")
            if result.context:
                print(f"   Context: {result.context}")

        print("\n" + "=" * 60)
        print(f"Returned {len(results)} result(s).")
        return 0
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query keeper_knowledge.db")
    parser.add_argument("keywords", nargs="+", help="Search terms")
    parser.add_argument("--limit", type=int, default=5, help="Maximum results (default: 5)")
    args = parser.parse_args(argv)

    limit = max(1, min(args.limit, 50))
    query = " ".join(args.keywords).strip()
    return query_task_knowledge(query, limit=limit)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

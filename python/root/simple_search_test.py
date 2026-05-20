# MODE: SCRIPT\n\n#!/usr/bin/env python3
"""Simple test for advanced search capabilities."""

from knowledge_db import KnowledgeDB
from pathlib import Path

def main():
    db = KnowledgeDB(Path("."))

    # Test semantic search
    print("Testing semantic search...")

    queries = [
        "bootstrap protocol",
        "session management",
        "API failure",
        "guardrail violation"
    ]

    for query in queries:
        results = db.search(query, semantic=True, limit=3)
        print(f"Query '{query}': {len(results)} results")
        for r in results[:2]:
            print(f"  - {r.type}: {r.id} (rel: {r.relevance:.2f})")

    # Test knowledge counts
    print("\nKnowledge validation:")
    test_count = db.conn.execute("SELECT COUNT(*) FROM test_knowledge").fetchone()[0]
    print(f"Test knowledge entities: {test_count}")

    pattern_count = db.conn.execute("SELECT COUNT(*) FROM mined_patterns").fetchone()[0]
    print(f"Mined patterns: {pattern_count}")

    synonym_count = db.conn.execute("SELECT COUNT(*) FROM semantic_synonyms").fetchone()[0]
    print(f"Semantic synonyms: {synonym_count}")

    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
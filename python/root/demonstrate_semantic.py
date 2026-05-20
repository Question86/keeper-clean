# MODE: SCRIPT\n\n"""Demonstrate semantic search vs context search"""

from knowledge_db import KnowledgeDB
from pathlib import Path

def demonstrate_semantic_search():
    db = KnowledgeDB(Path('.'))

    # Example query that showed big improvement
    query = 'fix bootstrap guardrails'

    print('SEMANTIC SEARCH DEMONSTRATION')
    print('=' * 50)
    print(f'Original query: "{query}"')
    print()

    # Show what semantic expansion does
    expansions = db._expand_query_semantically(query)
    print('Semantic expansions (related terms/concepts):')
    for i, exp in enumerate(expansions, 1):
        print(f'  {i}. "{exp}"')
    print()

    # Show search results comparison
    print('SEARCH RESULTS COMPARISON:')
    print('-' * 30)

    context_results = db.search(query, semantic=False, limit=3)
    semantic_results = db.search(query, semantic=True, limit=3)

    print(f'Context-based (literal keywords only): {len(context_results)} results')
    for r in context_results:
        print(f'  • {r.type}: {r.id[:50]}... (relevance: {r.relevance:.1f})')

    print(f'\nSemantic-based (with expansions): {len(semantic_results)} results')
    for r in semantic_results:
        print(f'  • {r.type}: {r.id[:50]}... (relevance: {r.relevance:.1f})')

    print(f'\nIMPROVEMENT: {len(semantic_results)} results vs {len(context_results)} (+{((len(semantic_results)/max(len(context_results),1)-1)*100):.0f}%)')

if __name__ == "__main__":
    demonstrate_semantic_search()
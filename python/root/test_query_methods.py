# MODE: TEST\n\n"""Query Method Comparison Test - Context vs Semantic Search"""

import json
from knowledge_db import KnowledgeDB
from pathlib import Path

def run_query_comparison_test():
    # Test queries categorized by difficulty
    test_queries = {
        'easy': [
            'fix lint warning',
            'add missing reference',
            'update task status',
            'create report file',
            'delete bootstrap file',
            'run metadata lint',
            'check loop gate',
            'read current state',
            'confirm bootstrap',
            'move task to alt'
        ],
        'medium': [
            'resolve orphan report',
            'fix status drift',
            'add mode declaration',
            'update navigation map',
            'create task specification',
            'generate session pack',
            'validate schema files',
            'rebuild knowledge database',
            'sync seed template',
            'install pre-commit hooks'
        ],
        'hard': [
            'implement semantic search',
            'optimize database performance',
            'fix bootstrap guardrails',
            'create deep context search',
            'implement pattern mining',
            'add type annotations',
            'resolve state inconsistency'
        ],
        'very_hard': [
            'comprehensive knowledge extraction',
            'advanced search optimization',
            'guardrail enforcement system'
        ]
    }

    db = KnowledgeDB(Path('.'))
    results = {}

    for category, queries in test_queries.items():
        results[category] = {}
        print(f"\n{'='*50}")
        print(f"TESTING {category.upper()} QUERIES")
        print(f"{'='*50}")

        for query in queries:
            print(f'\nQuery: "{query}"')

            # Context-based (semantic=False)
            context_results = db.search(query, semantic=False, limit=5)

            # Semantic-based (semantic=True)
            semantic_results = db.search(query, semantic=True, limit=5)

            context_count = len(context_results)
            context_avg_rel = sum(r.relevance for r in context_results) / max(len(context_results), 1)
            context_types = [r.type for r in context_results]

            semantic_count = len(semantic_results)
            semantic_avg_rel = sum(r.relevance for r in semantic_results) / max(len(semantic_results), 1)
            semantic_types = [r.type for r in semantic_results]

            # Determine winner
            if semantic_count > context_count:
                winner = 'semantic'
            elif context_count > semantic_count:
                winner = 'context'
            elif semantic_avg_rel > context_avg_rel:
                winner = 'semantic'
            else:
                winner = 'tie'

            results[category][query] = {
                'context_based': {
                    'count': context_count,
                    'avg_relevance': round(context_avg_rel, 3),
                    'types': context_types
                },
                'semantic_based': {
                    'count': semantic_count,
                    'avg_relevance': round(semantic_avg_rel, 3),
                    'types': semantic_types
                },
                'winner': winner
            }

            print(f"  Context: {context_count} results, avg_rel={context_avg_rel:.3f}, types={context_types}")
            print(f"  Semantic: {semantic_count} results, avg_rel={semantic_avg_rel:.3f}, types={semantic_types}")
            print(f"  Winner: {winner}")

    # Analysis
    print(f"\n{'='*60}")
    print("ANALYSIS SUMMARY")
    print(f"{'='*60}")

    total_wins = {'context': 0, 'semantic': 0, 'tie': 0}

    for category, queries in results.items():
        category_wins = {'context': 0, 'semantic': 0, 'tie': 0}
        for query_data in queries.values():
            winner = query_data['winner']
            category_wins[winner] += 1
            total_wins[winner] += 1

        print(f"\n{category.upper()} ({len(queries)} queries):")
        print(f"  Context wins: {category_wins['context']}")
        print(f"  Semantic wins: {category_wins['semantic']}")
        print(f"  Ties: {category_wins['tie']}")

    print(f"\nOVERALL ({sum(len(q) for q in test_queries.values())} queries):")
    print(f"  Context-based wins: {total_wins['context']}")
    print(f"  Semantic-based wins: {total_wins['semantic']}")
    print(f"  Ties: {total_wins['tie']}")

    # Save results
    with open('query_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\nDetailed results saved to query_test_results.json")

if __name__ == "__main__":
    run_query_comparison_test()
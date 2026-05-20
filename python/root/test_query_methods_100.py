# MODE: TEST\n\n"""Expanded Query Method Comparison Test - 100 Samples"""

import json
from knowledge_db import KnowledgeDB
from pathlib import Path

def run_expanded_query_comparison_test():
    # Expanded test queries - 100 total
    test_queries = {
        'easy': [
            'fix lint warning', 'add missing reference', 'update task status', 'create report file',
            'delete bootstrap file', 'run metadata lint', 'check loop gate', 'read current state',
            'confirm bootstrap', 'move task to alt', 'validate json file', 'check file exists',
            'read markdown file', 'write to file', 'create directory', 'list files',
            'run python script', 'install package', 'check python version', 'activate venv',
            'deactivate venv', 'commit changes', 'push to git', 'pull from git', 'create branch',
            'switch branch', 'merge branch', 'resolve conflict', 'check git status', 'add file to git',
            'remove file', 'copy file', 'rename file', 'search text', 'replace text'
        ],
        'medium': [
            'resolve orphan report', 'fix status drift', 'add mode declaration', 'update navigation map',
            'create task specification', 'generate session pack', 'validate schema files', 'rebuild knowledge database',
            'sync seed template', 'install pre-commit hooks', 'update requirements', 'run tests',
            'check test coverage', 'fix failing test', 'add test case', 'mock external api',
            'handle exception', 'log error message', 'parse json data', 'serialize object',
            'connect to database', 'execute sql query', 'create database table', 'insert record',
            'update record', 'delete record', 'backup database', 'restore database', 'migrate schema',
            'optimize query', 'index database', 'cache results', 'clear cache', 'validate input',
            'sanitize data', 'escape html', 'hash password', 'generate token', 'verify token'
        ],
        'hard': [
            'implement semantic search', 'optimize database performance', 'fix bootstrap guardrails',
            'create deep context search', 'implement pattern mining', 'add type annotations',
            'resolve state inconsistency', 'implement caching layer', 'add authentication',
            'create api endpoint', 'implement middleware', 'add logging system', 'create dashboard',
            'implement real-time updates', 'add user management', 'create admin panel',
            'implement file upload', 'add email notifications', 'create backup system',
            'implement rate limiting', 'add error monitoring', 'create deployment script'
        ],
        'very_hard': [
            'comprehensive knowledge extraction', 'advanced search optimization', 'guardrail enforcement system',
            'distributed system architecture', 'machine learning integration', 'blockchain implementation',
            'quantum computing algorithm', 'neural network training', 'computer vision pipeline',
            'natural language processing'
        ]
    }

    db = KnowledgeDB(Path('.'))
    results = {}

    total_queries = sum(len(queries) for queries in test_queries.values())
    print(f"Running expanded test with {total_queries} queries...")

    query_count = 0
    for category, queries in test_queries.items():
        results[category] = {}
        print(f"\n{'='*60}")
        print(f"TESTING {category.upper()} QUERIES ({len(queries)} queries)")
        print(f"{'='*60}")

        for query in queries:
            query_count += 1
            if query_count % 10 == 0:
                print(f"Progress: {query_count}/{total_queries} queries tested")

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

            # Determine winner with more sophisticated logic
            if semantic_count > context_count and semantic_avg_rel > context_avg_rel:
                winner = 'semantic'
            elif context_count > semantic_count and context_avg_rel > semantic_avg_rel:
                winner = 'context'
            elif semantic_avg_rel > context_avg_rel * 1.2:  # 20% better relevance
                winner = 'semantic'
            elif context_avg_rel > semantic_avg_rel * 1.2:
                winner = 'context'
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

    # Analysis
    print(f"\n{'='*80}")
    print("FINAL ANALYSIS SUMMARY (100 QUERIES)")
    print(f"{'='*80}")

    total_wins = {'context': 0, 'semantic': 0, 'tie': 0}
    category_stats = {}

    for category, queries in results.items():
        category_wins = {'context': 0, 'semantic': 0, 'tie': 0}
        total_rel_context = 0
        total_rel_semantic = 0
        total_count_context = 0
        total_count_semantic = 0

        for query_data in queries.values():
            winner = query_data['winner']
            category_wins[winner] += 1
            total_wins[winner] += 1

            total_rel_context += query_data['context_based']['avg_relevance']
            total_rel_semantic += query_data['semantic_based']['avg_relevance']
            total_count_context += query_data['context_based']['count']
            total_count_semantic += query_data['semantic_based']['count']

        avg_rel_context = total_rel_context / len(queries)
        avg_rel_semantic = total_rel_semantic / len(queries)
        avg_count_context = total_count_context / len(queries)
        avg_count_semantic = total_count_semantic / len(queries)

        category_stats[category] = {
            'wins': category_wins,
            'avg_relevance_context': round(avg_rel_context, 3),
            'avg_relevance_semantic': round(avg_rel_semantic, 3),
            'avg_count_context': round(avg_count_context, 2),
            'avg_count_semantic': round(avg_count_semantic, 2)
        }

        print(f"\n{category.upper()} ({len(queries)} queries):")
        print(f"  Context wins: {category_wins['context']} ({category_wins['context']/len(queries)*100:.1f}%)")
        print(f"  Semantic wins: {category_wins['semantic']} ({category_wins['semantic']/len(queries)*100:.1f}%)")
        print(f"  Ties: {category_wins['tie']} ({category_wins['tie']/len(queries)*100:.1f}%)")
        print(f"  Avg relevance - Context: {avg_rel_context:.3f}, Semantic: {avg_rel_semantic:.3f}")
        print(f"  Avg result count - Context: {avg_count_context:.2f}, Semantic: {avg_count_semantic:.2f}")

    print(f"\n{'='*80}")
    print(f"OVERALL ({total_queries} queries):")
    print(f"  Context-based wins: {total_wins['context']} ({total_wins['context']/total_queries*100:.1f}%)")
    print(f"  Semantic-based wins: {total_wins['semantic']} ({total_wins['semantic']/total_queries*100:.1f}%)")
    print(f"  Ties: {total_wins['tie']} ({total_wins['tie']/total_queries*100:.1f}%)")

    # Performance comparison
    total_rel_context = sum(stats['avg_relevance_context'] * len(results[cat]) for cat, stats in category_stats.items())
    total_rel_semantic = sum(stats['avg_relevance_semantic'] * len(results[cat]) for cat, stats in category_stats.items())
    overall_avg_rel_context = total_rel_context / total_queries
    overall_avg_rel_semantic = total_rel_semantic / total_queries

    print(f"\nPERFORMANCE METRICS:")
    print(f"  Overall avg relevance - Context: {overall_avg_rel_context:.3f}")
    print(f"  Overall avg relevance - Semantic: {overall_avg_rel_semantic:.3f}")
    print(f"  Relevance improvement: {(overall_avg_rel_semantic/overall_avg_rel_context - 1)*100:.1f}%")

    # Save results
    with open('query_test_results_100.json', 'w') as f:
        json.dump(results, f, indent=2)

    with open('query_test_analysis_100.json', 'w') as f:
        json.dump({
            'summary': {
                'total_queries': total_queries,
                'wins': total_wins,
                'overall_avg_relevance': {
                    'context': round(overall_avg_rel_context, 3),
                    'semantic': round(overall_avg_rel_semantic, 3)
                }
            },
            'categories': category_stats
        }, f, indent=2)

    print("\nDetailed results saved to query_test_results_100.json")
    print("Analysis summary saved to query_test_analysis_100.json")

if __name__ == "__main__":
    run_expanded_query_comparison_test()
# MODE: TEST\n\n#!/usr/bin/env python3
"""Test suite for advanced search capabilities and knowledge extraction validation.

This script validates the enhanced knowledge database system including:
- Semantic search with synonyms and concepts
- Pattern mining and relationship discovery
- Performance optimizations and caching
- Multi-source knowledge integration
- Confidence-based ranking and relevance scoring
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any

from knowledge_db import KnowledgeDB


def run_search_tests(db: KnowledgeDB) -> Dict[str, Any]:
    """Run comprehensive search capability tests."""
    tests = {
        "semantic_bootstrap": {
            "query": "bootstrap problems",
            "expected_types": ["test_knowledge", "lesson"],
            "min_results": 3
        },
        "semantic_session": {
            "query": "session management",
            "expected_types": ["test_knowledge", "lesson", "archive"],
            "min_results": 3
        },
        "semantic_api": {
            "query": "API failure handling",
            "expected_types": ["test_knowledge", "lesson"],
            "min_results": 2
        },
        "semantic_guardrail": {
            "query": "guardrail violations",
            "expected_types": ["test_knowledge", "lesson"],
            "min_results": 2
        },
        "pattern_query": {
            "query": "state transition patterns",
            "expected_types": ["test_knowledge", "lesson"],
            "min_results": 2
        },
        "integration_query": {
            "query": "error recovery workflows",
            "expected_types": ["test_knowledge", "lesson"],
            "min_results": 2
        }
    }

    results = {}

    for test_name, test_config in tests.items():
        print(f"Running test: {test_name}")

        start_time = time.time()
        search_results = db.search(
            test_config["query"],
            semantic=True,
            limit=10
        )
        query_time = time.time() - start_time

        # Validate results
        result_types = [r.type for r in search_results]
        has_expected_types = any(t in result_types for t in test_config["expected_types"])
        sufficient_results = len(search_results) >= test_config["min_results"]

        # Check for test_knowledge in top results if expected
        test_knowledge_in_top_3 = any(
            r.type == "test_knowledge" for r in search_results[:3]
        ) if "test_knowledge" in test_config["expected_types"] else True

        # Performance check
        fast_enough = query_time < 0.1  # Sub-100ms target

        results[test_name] = {
            "query": test_config["query"],
            "result_count": len(search_results),
            "query_time_ms": round(query_time * 1000, 2),
            "has_expected_types": has_expected_types,
            "sufficient_results": sufficient_results,
            "test_knowledge_prominent": test_knowledge_in_top_3,
            "performance_ok": fast_enough,
            "top_result_types": result_types[:3],
            "passed": all([
                has_expected_types,
                sufficient_results,
                test_knowledge_in_top_3,
                fast_enough
            ])
        }

        print(f"  Results: {len(search_results)} found in {results[test_name]['query_time_ms']}ms")
        print(f"  Passed: {results[test_name]['passed']}")

    return results


def run_knowledge_validation_tests(db: KnowledgeDB) -> Dict[str, Any]:
    """Validate knowledge extraction completeness."""
    tests = {}

    # Test knowledge entities count
    test_entities = db.conn.execute("SELECT COUNT(*) FROM test_knowledge").fetchone()[0]
    tests["test_knowledge_count"] = {
        "expected": 37,
        "actual": test_entities,
        "passed": test_entities >= 35  # Allow some tolerance
    }

    # Test semantic data
    synonyms = db.conn.execute("SELECT COUNT(*) FROM semantic_synonyms").fetchone()[0]
    concepts = db.conn.execute("SELECT COUNT(*) FROM semantic_concepts").fetchone()[0]
    tests["semantic_data"] = {
        "synonyms": synonyms,
        "concepts": concepts,
        "passed": synonyms > 100 and concepts >= 5
    }

    # Test patterns mined
    patterns = db.conn.execute("SELECT COUNT(*) FROM mined_patterns").fetchone()[0]
    relationships = db.conn.execute("SELECT COUNT(*) FROM pattern_relationships").fetchone()[0]
    tests["pattern_mining"] = {
        "patterns": patterns,
        "relationships": relationships,
        "passed": patterns >= 20 and relationships >= 10
    }

    # Test confidence distribution
    confidence_counts = db.conn.execute("""
        SELECT confidence_level, COUNT(*) as count
        FROM test_knowledge
        GROUP BY confidence_level
    """).fetchall()

    confidence_dist = {row["confidence_level"]: row["count"] for row in confidence_counts}
    tests["confidence_distribution"] = {
        "distribution": confidence_dist,
        "high_confidence": confidence_dist.get("high", 0),
        "passed": confidence_dist.get("high", 0) >= 20  # At least 20 high confidence entities
    }

    return tests


def run_performance_tests(db: KnowledgeDB) -> Dict[str, Any]:
    """Run performance benchmarking tests."""
    test_queries = [
        "bootstrap",
        "session management",
        "API failure",
        "guardrail violation",
        "state transition",
        "error recovery",
        "protocol enforcement"
    ]

    results = {}

    # Test caching performance
    print("Testing caching performance...")
    first_query = test_queries[0]
    start_time = time.time()
    results1 = db.search(first_query, semantic=True, limit=10)
    first_time = time.time() - start_time

    start_time = time.time()
    results2 = db.search(first_query, semantic=True, limit=10)  # Should use cache
    cached_time = time.time() - start_time

    results["caching"] = {
        "first_query_ms": round(first_time * 1000, 2),
        "cached_query_ms": round(cached_time * 1000, 2),
        "speedup": round(first_time / cached_time, 1) if cached_time > 0 else 0,
        "cache_working": cached_time < first_time * 0.5  # At least 2x speedup
    }

    # Test average query performance
    print("Testing average query performance...")
    query_times = []
    for query in test_queries:
        start_time = time.time()
        db.search(query, semantic=True, limit=10)
        query_times.append(time.time() - start_time)

    avg_time = sum(query_times) / len(query_times)
    results["average_performance"] = {
        "avg_query_time_ms": round(avg_time * 1000, 2),
        "all_under_100ms": all(t < 0.1 for t in query_times),
        "passed": avg_time < 0.1
    }

    return results


def run_integration_tests(db: KnowledgeDB) -> Dict[str, Any]:
    """Test cross-source integration and relationship discovery."""
    tests = {}

    # Test cross-source search
    results = db.search("bootstrap", types=["test_knowledge", "lesson", "report"], limit=10)
    source_types = list(set(r.type for r in results))

    tests["cross_source_integration"] = {
        "sources_found": source_types,
        "multiple_sources": len(source_types) >= 2,
        "passed": len(source_types) >= 2
    }

    # Test semantic expansion effectiveness
    basic_results = db.search("bootstrap", semantic=False, limit=5)
    semantic_results = db.search("bootstrap", semantic=True, limit=5)

    tests["semantic_expansion"] = {
        "basic_results": len(basic_results),
        "semantic_results": len(semantic_results),
        "expansion_helps": len(semantic_results) >= len(basic_results),
        "passed": len(semantic_results) >= len(basic_results)
    }

    # Test ranking quality (test_knowledge should be prominent for relevant queries)
    bootstrap_results = db.search("bootstrap protocol", limit=5)
    test_knowledge_top_3 = any(r.type == "test_knowledge" for r in bootstrap_results[:3])

    tests["ranking_quality"] = {
        "test_knowledge_prominent": test_knowledge_top_3,
        "passed": test_knowledge_top_3
    }

    return tests


def main():
    """Run the complete test suite."""
    print("🧪 Advanced Search Capabilities Test Suite")
    print("=" * 50)

    db_path = Path("keeper_knowledge.db")
    if not db_path.exists():
        print("❌ Database not found. Please run rebuild first.")
        return

    db = KnowledgeDB(Path("."))

    # Run all test suites
    test_suites = {
        "search_tests": run_search_tests,
        "knowledge_validation": run_knowledge_validation_tests,
        "performance_tests": run_performance_tests,
        "integration_tests": run_integration_tests
    }

    all_results = {}
    total_passed = 0
    total_tests = 0

    for suite_name, test_func in test_suites.items():
        print(f"\n📋 Running {suite_name}...")
        try:
            results = test_func(db)
            all_results[suite_name] = results

            # Count passes
            suite_passed = 0
            suite_total = 0
            for test_name, test_result in results.items():
                if isinstance(test_result, dict) and "passed" in test_result:
                    suite_total += 1
                    if test_result["passed"]:
                        suite_passed += 1

            total_passed += suite_passed
            total_tests += suite_total

            print(f"✅ {suite_name}: {suite_passed}/{suite_total} tests passed")

        except Exception as e:
            print(f"❌ {suite_name} failed: {str(e)}")
            all_results[suite_name] = {"error": str(e)}

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Success Rate: {total_passed/total_tests*100:.1f}%" if total_tests > 0 else "No tests run")

    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  Some tests failed. Check results above.")

    # Save detailed results
    output_file = Path("search_test_results.json")
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n📄 Detailed results saved to {output_file}")


if __name__ == "__main__":
    main()
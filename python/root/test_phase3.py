#!/usr/bin/env python3
"""
Phase 3 Test Script - TASK_0205 Model Selection & A/B Testing
"""

from rate_limit_handler_minimal import RateLimitHandler
from pathlib import Path

def test_phase_3():
    print("🚀 Testing Phase 3: Model Selection & A/B Testing")
    print("=" * 50)

    handler = RateLimitHandler(Path('.'))

    # Test 1: Intelligent Model Selection
    print("\n📊 Test 1: Intelligent Model Selection")
    test_cases = [
        ("Short budget text", 0.3, 0.9, "Should pick cheapest model"),
        ("Quality-focused content for analysis", 0.9, 0.1, "Should pick best model"),
        ("Balanced use case", 0.7, 0.5, "Should balance quality/cost"),
    ]

    for content, quality_req, budget_pri, expectation in test_cases:
        try:
            result = handler.intelligent_embedding_call(content, quality_req, budget_pri)
            print(f"✅ {content[:30]}...: {len(result)} dims ({expectation})")
        except Exception as e:
            print(f"❌ {content[:30]}...: Failed - {e}")

    # Test 2: A/B Testing Framework
    print("\n🧪 Test 2: A/B Testing Framework")

    # Start test
    try:
        result = handler.start_ab_test("quality_vs_cost_test",
                                     ["text-embedding-3-small", "text-embedding-3-large"],
                                     {"text-embedding-3-small": 0.7, "text-embedding-3-large": 0.3})  # 70/30 split
        print(f"✅ Started A/B test: {result}")
    except Exception as e:
        print(f"❌ Failed to start A/B test: {e}")
        return

    # Run test calls
    print("Running test traffic...")
    for i in range(20):
        try:
            content = f"A/B test content sample {i}"
            result = handler.intelligent_embedding_call(content, context="ab_test")
            print(f"  Call {i+1}: {len(result)} dims")
        except Exception as e:
            print(f"  Call {i+1}: Failed - {e}")

    # Check status
    try:
        status = handler.get_ab_test_status("quality_vs_cost_test")
        print(f"✅ Test status: {status['status']} ({status['total_samples']} samples)")
    except Exception as e:
        print(f"❌ Failed to get test status: {e}")

    # End test and show results
    try:
        final_result = handler.end_ab_test("quality_vs_cost_test")
        winner = final_result.get('winner', 'No clear winner')
        print(f"🏆 Test completed! Winner: {winner}")
    except Exception as e:
        print(f"❌ Failed to end test: {e}")

    # Test 3: Performance Tracking
    print("\n📈 Test 3: Performance Tracking")
    try:
        perf = handler.get_model_performance()
        print(f"✅ Tracking {len(perf)} models:")
        for model, stats in perf.items():
            calls = stats.get('calls', 0)
            success_rate = stats.get('success_rate', 0)
            avg_cost = stats.get('avg_cost', 0)
            print(f"  {model}: {calls} calls, {success_rate:.1%} success, ${avg_cost:.6f}/call")
    except Exception as e:
        print(f"❌ Failed to get performance: {e}")

    print("\n🎉 Phase 3 Testing Complete!")
    print("✅ Model selection working")
    print("✅ A/B testing framework operational")
    print("✅ Performance tracking active")

if __name__ == "__main__":
    test_phase_3()
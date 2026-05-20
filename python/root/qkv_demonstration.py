#!/usr/bin/env python3
"""
QKV Relevance Dimensions Demonstration
Shows the multi-dimensional relevance assessment in action
"""

import json
from context_dreamer import ContextDreamer

def demonstrate_qkv_dimensions():
    """Demonstrate QKV relevance dimensions for sample file pairs."""

    print("🌟 QKV Relevance Dimensions Demonstration")
    print("=" * 50)

    # Initialize the context dreamer
    dreamer = ContextDreamer(".")

    # Sample file pairs to test
    test_pairs = [
        ("FEATURE_VALIDATION.md", "context_profiles.json"),
        ("loop_cockpit.py", "context_dreamer.py"),
        ("_SESSION.md", "keeper_knowledge.db"),
        ("analyze_token_crisis.py", "claude_api_tokens_2026_01.csv")
    ]

    print("\n🔍 Testing QKV dimensions on sample file pairs:")
    print("-" * 50)

    for file_a, file_b in test_pairs:
        print(f"\n📁 {file_a} ↔ {file_b}")

        # Get file analyses
        analysis_a = dreamer.network_graph.get(file_a, {})
        analysis_b = dreamer.network_graph.get(file_b, {})

        if not analysis_a or not analysis_b:
            print("   ❌ Missing analysis data")
            continue

        # Calculate QKV relevance vector
        qkv_vector = dreamer._calculate_qkv_relevance_vector(file_a, analysis_a, file_b, analysis_b)

        # Display results
        print(".3f")
        print(".3f")
        print(".3f")

        # Calculate combined relevance score (weighted average)
        combined_score = (
            0.4 * qkv_vector['urgency'] +
            0.4 * qkv_vector['strategic_fit'] +
            0.2 * qkv_vector['historical_reliability']
        )
        print(".3f")

        # Show connection evaluation with QKV
        default_params = {
            'similarity_threshold': 0.4,
            'structural_weight': 0.4,
            'contextual_boost': 0.4,
            'temporal_decay': 0.8,
            'frequency_penalty': 0.2,
            'punctual_boost': 0.5,
            'situational_weight': 0.7,
            'specificity_threshold': 0.4,
        }
        connections = dreamer._evaluate_connections_with_parameters(
            file_a, analysis_a, file_b, analysis_b, default_params
        )

        if connections:
            print(f"   🔗 Top connection: {connections[0]['type']} (strength: {connections[0]['strength']:.3f})")
            if 'qkv_dimensions' in connections[0]:
                qkv = connections[0]['qkv_dimensions']
                print(f"      QKV: U={qkv['urgency']:.2f}, S={qkv['strategic_fit']:.2f}, H={qkv['historical_reliability']:.2f}")
        else:
            print("   🔗 No significant connections found")

    print("\n" + "=" * 50)
    print("✅ QKV Demonstration Complete!")
    print("\n📊 QKV Dimensions Legend:")
    print("   U (Urgency): Temporal criticality and immediacy")
    print("   S (Strategic Fit): Alignment with project goals")
    print("   H (Historical Reliability): Proven effectiveness")

if __name__ == "__main__":
    demonstrate_qkv_dimensions()
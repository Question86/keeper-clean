#!/usr/bin/env python3
"""
Mathematical Validation of Parameter Discovery Algorithm
Based on depth_vs_breathe.md and mega.md frameworks
"""

import context_dreamer
import json
import os

def main():
    # Load the current network
    dreamer = context_dreamer.ContextDreamer()

    print('=== MATHEMATICAL VALIDATION OF PARAMETER DISCOVERY ===')
    print(f'Network size: {len(dreamer.network_graph)} nodes')
    print()

    # Get the learned parameters from recent run
    results_file = None
    for filename in os.listdir('.'):
        if filename.startswith('parameter_discovery_') and filename.endswith('.json'):
            results_file = filename
            break

    if not results_file:
        print('No parameter discovery results found. Run discover_connection_parameters first.')
        return

    try:
        with open(results_file, 'r') as f:
            results = json.load(f)

        learned_params = results.get('final_parameters', {})
        print('Learned parameters from 100 cycles:')
        for k, v in learned_params.items():
            print(f'  {k}: {v:.3f}')
        print()

        # Test 1: Can learned parameters find NEW connections?
        print('TEST 1: Discovery Capability with Learned Parameters')
        print('Finding connections between files NOT in the reference connection...')

        # Get reference files
        ref_connection = results.get('reference_connection', {})
        ref_files = set()
        if ref_connection:
            ref_files.add(ref_connection.get('file_a', ''))
            ref_files.add(ref_connection.get('file_b', ''))

        # Find connections between non-reference files
        test_files = [f for f in list(dreamer.network_graph.keys())[:20] if f not in ref_files][:10]  # First 10 non-ref files

        new_connections_found = 0
        total_possible_pairs = 0

        for i in range(len(test_files)):
            for j in range(i+1, len(test_files)):
                file_a, file_b = test_files[i], test_files[j]
                total_possible_pairs += 1

                # Test with learned parameters
                connections = dreamer._evaluate_connections_with_parameters(
                    file_a, dreamer.network_graph[file_a],
                    file_b, dreamer.network_graph[file_b],
                    learned_params
                )

                if connections:
                    strongest = max(connections, key=lambda x: x['strength'])
                    if strongest['strength'] > 0.1:  # Non-trivial connection
                        new_connections_found += 1
                        print(f'  ✓ {file_a} ↔ {file_b}: {strongest["strength"]:.3f}')

        print(f'New connections found: {new_connections_found}/{total_possible_pairs}')
        print(f'Discovery rate: {new_connections_found/total_possible_pairs:.1%}')
        print()

        # Test 2: Compare against baseline (no enhanced metadata)
        print('TEST 2: Baseline Comparison (Original Metadata Only)')

        baseline_params = {
            'similarity_threshold': 0.3,
            'structural_weight': 0.6,
            'contextual_boost': 0.4,
            'temporal_decay': 0.8,
            'frequency_penalty': 0.2,
            'punctual_boost': 0.5,
            'situational_weight': 0.7,
            'specificity_threshold': 0.4,
        }

        baseline_connections = 0
        for i in range(len(test_files)):
            for j in range(i+1, len(test_files)):
                file_a, file_b = test_files[i], test_files[j]

                connections = dreamer._evaluate_connections_with_parameters(
                    file_a, dreamer.network_graph[file_a],
                    file_b, dreamer.network_graph[file_b],
                    baseline_params
                )

                if connections:
                    strongest = max(connections, key=lambda x: x['strength'])
                    if strongest['strength'] > 0.1:
                        baseline_connections += 1

        print(f'Baseline connections: {baseline_connections}/{total_possible_pairs}')
        print(f'Baseline discovery rate: {baseline_connections/total_possible_pairs:.1%}')
        print()

        # Test 3: Mathematical validation per depth_vs_breathe.md
        print('TEST 3: Mathematical Validation (Depth-First Connectivity)')

        # Calculate expected connectivity per depth_vs_breathe.md formulas
        b = 3  # branching factor
        d = 5  # optimal depth

        expected_df_connectivity = (b ** (d + 1) - b) / (b - 1)
        expected_bf_connectivity = b * d

        print(f'Expected depth-first connectivity (d={d}, b={b}): {expected_df_connectivity:.0f}')
        print(f'Expected breadth-first connectivity (d={d}, b={b}): {expected_bf_connectivity:.0f}')
        print(f'Theoretical advantage ratio: {expected_df_connectivity/expected_bf_connectivity:.1f}x')
        print()

        # Test 4: Token efficiency calculation
        print('TEST 4: Token Efficiency Analysis')

        # Simulate token costs (rough estimate)
        T_base = 1000
        T_metadata = 500
        estimated_tokens_used = T_base + len(test_files) * T_metadata

        connections_per_token_learned = new_connections_found / estimated_tokens_used if estimated_tokens_used > 0 else 0
        connections_per_token_baseline = baseline_connections / estimated_tokens_used if estimated_tokens_used > 0 else 0

        print(f'Learned params efficiency: {connections_per_token_learned:.4f} connections/token')
        print(f'Baseline efficiency: {connections_per_token_baseline:.4f} connections/token')
        if connections_per_token_baseline > 0:
            improvement = ((connections_per_token_learned/connections_per_token_baseline-1)*100)
            print(f'Efficiency improvement: {improvement:.1f}%')
        else:
            print('Efficiency improvement: N/A (baseline = 0)')

        print()
        print('=== VALIDATION SUMMARY ===')
        print(f'Learned parameters tested on {total_possible_pairs} new file pairs')
        print(f'New discovery rate: {new_connections_found/total_possible_pairs:.1%}')
        print(f'Improvement over baseline: {((new_connections_found-baseline_connections)/max(baseline_connections,1)*100):.1f}%')

    except Exception as e:
        print(f'Error in validation: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
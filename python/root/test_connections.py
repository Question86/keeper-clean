#!/usr/bin/env python3
from context_dreamer import ContextDreamer

dreamer = ContextDreamer()
print('Testing connection evaluation...')

files = list(dreamer.network_graph.keys())[:2]
if len(files) >= 2:
    file_a, file_b = files[0], files[1]
    analysis_a = dreamer.network_graph[file_a]
    analysis_b = dreamer.network_graph[file_b]

    params = {
        'structural_weight': 1.0,
        'similarity_threshold': 0.3,
        'temporal_decay': 0.8,
        'contextual_boost': 1.2,
        'frequency_penalty': 0.1
    }

    print(f"Analysis A keys: {list(analysis_a.keys())}")
    print(f"Analysis B keys: {list(analysis_b.keys())}")
    print(f"Analysis A sample data:")
    for key in ['references', 'headers', 'code_blocks', 'links', 'mentions']:
        value = analysis_a.get(key, [])
        print(f"  {key}: {value[:5] if isinstance(value, list) else value}...")

    print(f"\nAnalysis B sample data:")
    for key in ['references', 'headers', 'code_blocks', 'links', 'mentions']:
        value = analysis_b.get(key, [])
        print(f"  {key}: {value[:5] if isinstance(value, list) else value}...")

    connections = dreamer._evaluate_connections_with_parameters(file_a, analysis_a, file_b, analysis_b, params)

    connections = dreamer._evaluate_connections_with_parameters(file_a, analysis_a, file_b, analysis_b, params)
    print(f'Found {len(connections)} connections between {file_a} and {file_b}:')
    for conn in connections:
        print(f'  - {conn["type"]}: {conn["strength"]:.3f} - {conn["description"]}')
        print(f'    Evidence: {conn["evidence"]}')
else:
    print('Not enough files in network graph')
#!/usr/bin/env python3
"""
Metadata Pipeline Performance Benchmark - TASK_0178
"""

import time
import json
from pathlib import Path
import sys

def benchmark_comparison():
    """Compare original vs optimized metadata extraction."""
    workspace_root = Path(__file__).parent.parent

    # Add paths
    sys.path.append(str(workspace_root / 'tools' / 'metadata'))

    # Import extractors
    from enhanced_metadata_extractor import EnhancedMetadataExtractor
    from optimized_metadata_extractor import OptimizedMetadataExtractor

    # Collect test files
    test_files = []
    patterns = ['**/*.py', '**/*.md', '**/*.json']
    for pattern in patterns:
        files = list(workspace_root.glob(pattern))
        test_files.extend(files[:15])  # 15 files per type

    test_files = test_files[:40]  # Total 40 files
    print(f"Testing with {len(test_files)} files...")

    results = {}

    # Benchmark original sequential
    print("Testing original sequential...")
    extractor_orig = EnhancedMetadataExtractor(workspace_root)
    start_time = time.time()
    results_orig = []
    for file_path in test_files:
        result = extractor_orig.extract_enhanced_metadata(file_path)
        results_orig.append(result)
    orig_time = time.time() - start_time

    # Benchmark optimized sequential
    print("Testing optimized sequential...")
    extractor_opt = OptimizedMetadataExtractor(workspace_root)
    start_time = time.time()
    results_opt_seq = []
    for file_path in test_files:
        result = extractor_opt.extract_enhanced_metadata(file_path)
        results_opt_seq.append(result)
    opt_seq_time = time.time() - start_time

    # Benchmark optimized parallel
    print("Testing optimized parallel...")
    start_time = time.time()
    results_opt_par = extractor_opt.extract_enhanced_metadata_parallel(test_files)
    opt_par_time = time.time() - start_time

    # Calculate metrics
    results = {
        'original_sequential': {
            'total_time': orig_time,
            'avg_time_per_file': orig_time / len(test_files),
            'files_processed': len(results_orig),
            'successful': len([r for r in results_orig if 'error' not in r])
        },
        'optimized_sequential': {
            'total_time': opt_seq_time,
            'avg_time_per_file': opt_seq_time / len(test_files),
            'files_processed': len(results_opt_seq),
            'successful': len([r for r in results_opt_seq if 'error' not in r])
        },
        'optimized_parallel': {
            'total_time': opt_par_time,
            'avg_time_per_file': opt_par_time / len(test_files),
            'files_processed': len(results_opt_par),
            'successful': len([r for r in results_opt_par if 'error' not in r])
        }
    }

    # Performance analysis
    orig_avg = results['original_sequential']['avg_time_per_file']
    opt_seq_avg = results['optimized_sequential']['avg_time_per_file']
    opt_par_avg = results['optimized_parallel']['avg_time_per_file']

    results['analysis'] = {
        'sequential_speedup': orig_avg / opt_seq_avg if opt_seq_avg > 0 else 0,
        'parallel_speedup_vs_original': orig_avg / opt_par_avg if opt_par_avg > 0 else 0,
        'parallel_efficiency': opt_seq_avg / opt_par_avg if opt_par_avg > 0 else 0,
        'bottlenecks_addressed': [
            'regex_precompilation',
            'parallel_processing',
            'caching_mechanism',
            'memory_optimization'
        ]
    }

    # Save results
    output_file = workspace_root / 'benchmark_results_metadata_optimized.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Results saved to {output_file}")

    # Print summary
    print("\n=== PERFORMANCE COMPARISON ===")
    print(".2f")
    print(".2f")
    print(".2f")

    print("\n=== SPEEDUP ACHIEVED ===")
    print(".2f")
    print(".2f")
    print(".2f")

if __name__ == '__main__':
    benchmark_comparison()
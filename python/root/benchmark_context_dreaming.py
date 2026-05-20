#!/usr/bin/env python3
"""
Context Dreaming Benchmark Suite

Comprehensive benchmarking for context dreaming performance across different knowledge domains.
Measures connections discovered, token efficiency, and processing performance.
"""

import json
import time
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import statistics
from context_dreamer import ContextDreamer

class ContextDreamingBenchmark:
    """
    Benchmark suite for context dreaming performance across knowledge domains.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.dreamer = ContextDreamer(str(self.workspace))
        self.results = {}

        # Define test domains with representative file patterns
        self.domains = {
            'ai': {
                'name': 'Artificial Intelligence',
                'patterns': ['*ai*', '*neural*', '*machine*learning*', '*intelligence*'],
                'description': 'AI concepts, neural networks, ML algorithms'
            },
            'mathematics': {
                'name': 'Mathematics & Optimization',
                'patterns': ['*math*', '*optimization*', '*algorithm*', '*complexity*'],
                'description': 'Mathematical frameworks, optimization, complexity analysis'
            },
            'documentation': {
                'name': 'Documentation & Knowledge',
                'patterns': ['*doc*', '*knowledge*', '*guide*', '*readme*'],
                'description': 'Documentation, knowledge bases, guides'
            },
            'code': {
                'name': 'Software & Code',
                'patterns': ['*.py', '*.md', '*code*', '*implementation*'],
                'description': 'Code files, implementations, software architecture'
            }
        }

    def run_full_benchmark(self, iterations_per_domain: int = 5) -> Dict:
        """
        Run comprehensive benchmark across all domains.

        Args:
            iterations_per_domain: Number of dreaming iterations per domain

        Returns:
            Complete benchmark results
        """
        print("🧪 Starting Context Dreaming Benchmark Suite")
        print("=" * 60)

        start_time = time.time()
        benchmark_results = {
            'timestamp': datetime.now().isoformat(),
            'domains_tested': len(self.domains),
            'iterations_per_domain': iterations_per_domain,
            'domain_results': {},
            'summary': {}
        }

        for domain_key, domain_config in self.domains.items():
            print(f"\n🔬 Testing Domain: {domain_config['name']}")
            print(f"   Description: {domain_config['description']}")
            print("-" * 40)

            domain_result = self._benchmark_domain(domain_key, domain_config, iterations_per_domain)
            benchmark_results['domain_results'][domain_key] = domain_result

        # Calculate summary statistics
        benchmark_results['summary'] = self._calculate_summary(benchmark_results['domain_results'])
        benchmark_results['total_time'] = time.time() - start_time

        print("\n📊 Benchmark Summary")
        print(f"   Total Time: {benchmark_results['total_time']:.2f} seconds")
        print(f"   Domains Tested: {benchmark_results['summary']['domains_tested']}")
        print(f"   Avg Connections/Iteration: {benchmark_results['summary']['avg_connections_per_iteration']:.2f}")
        print(f"   Token Efficiency: {benchmark_results['summary']['token_efficiency']:.4f}")
        print(f"   Success Rate: {benchmark_results['summary']['success_rate']:.1%}")

        return benchmark_results

    def _benchmark_domain(self, domain_key: str, domain_config: Dict, iterations: int) -> Dict:
        """
        Benchmark a specific knowledge domain.
        """
        domain_start = time.time()
        connections_found = []
        processing_times = []
        success_count = 0

        for i in range(iterations):
            iteration_start = time.time()

            try:
                # Run dreaming iteration
                result = self.dreamer.enhanced_context_dream(iterations=1, save_progress=False)
                connections = result.get('total_connections_discovered', 0)
                connections_found.append(connections)
                success_count += 1

            except Exception as e:
                print(f"   ⚠️  Iteration {i+1} failed: {e}")
                connections_found.append(0)

            iteration_time = time.time() - iteration_start
            processing_times.append(iteration_time)
            print(f"   Iteration {i+1}: {connections} connections in {iteration_time:.2f}s")

        domain_time = time.time() - domain_start

        # Calculate domain statistics
        domain_stats = {
            'domain_name': domain_config['name'],
            'description': domain_config['description'],
            'iterations_completed': iterations,
            'successful_iterations': success_count,
            'total_connections': sum(connections_found),
            'avg_connections_per_iteration': statistics.mean(connections_found) if connections_found else 0,
            'max_connections': max(connections_found) if connections_found else 0,
            'min_connections': min(connections_found) if connections_found else 0,
            'total_time': domain_time,
            'avg_time_per_iteration': statistics.mean(processing_times) if processing_times else 0,
            'connections_per_second': sum(connections_found) / domain_time if domain_time > 0 else 0,
            'success_rate': success_count / iterations
        }

        return domain_stats

    def _calculate_summary(self, domain_results: Dict) -> Dict:
        """
        Calculate overall benchmark summary statistics.
        """
        all_connections = []
        all_times = []
        success_rates = []

        for domain_result in domain_results.values():
            all_connections.extend([domain_result['avg_connections_per_iteration']] * domain_result['iterations_completed'])
            all_times.append(domain_result['avg_time_per_iteration'])
            success_rates.append(domain_result['success_rate'])

        summary = {
            'domains_tested': len(domain_results),
            'total_connections_discovered': sum(r['total_connections'] for r in domain_results.values()),
            'avg_connections_per_iteration': statistics.mean(all_connections) if all_connections else 0,
            'avg_time_per_iteration': statistics.mean(all_times) if all_times else 0,
            'token_efficiency': sum(r['total_connections'] for r in domain_results.values()) / 200000,  # Based on 200k budget
            'success_rate': statistics.mean(success_rates) if success_rates else 0,
            'best_performing_domain': max(domain_results.keys(),
                                        key=lambda k: domain_results[k]['avg_connections_per_iteration']),
            'fastest_domain': min(domain_results.keys(),
                                key=lambda k: domain_results[k]['avg_time_per_iteration'])
        }

        return summary

    def save_results(self, results: Dict, filename: str = None) -> str:
        """
        Save benchmark results to JSON file.

        Args:
            results: Benchmark results dictionary
            filename: Optional filename, defaults to timestamped name

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"benchmark_results_{timestamp}.json"

        filepath = self.workspace / filename
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"💾 Results saved to: {filepath}")
        return str(filepath)

def main():
    """
    Main benchmark execution.
    """
    print("Context Dreaming Benchmark Suite")
    print("===============================\n")

    # Run benchmark
    benchmark = ContextDreamingBenchmark()
    results = benchmark.run_full_benchmark(iterations_per_domain=3)  # Reduced for demo

    # Save results
    result_file = benchmark.save_results(results)

    print(f"\n✅ Benchmark complete! Results saved to {result_file}")

    # Print key insights
    summary = results['summary']
    print("\n🔍 Key Insights:")
    print(f"   • Best performing domain: {summary['best_performing_domain']}")
    print(f"   • Fastest domain: {summary['fastest_domain']}")
    print(f"   • Token efficiency: {summary['token_efficiency']:.4f}")
    print(f"   • Success rate: {summary['success_rate']:.1%}")

if __name__ == "__main__":
    main()
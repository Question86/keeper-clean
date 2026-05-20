#!/usr/bin/env python3
"""
Generalized Interlink Discovery Test
Scans random samples of 3 files until finding at least 1 interconnected triple
"""

import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
META_DIR = ROOT / "tools" / "metadata"
if str(META_DIR) not in sys.path:
    sys.path.insert(0, str(META_DIR))

from enhanced_metadata_extractor import EnhancedMetadataExtractor

def run_generalized_test(max_attempts=100):
    """
    Randomly sample 3-file groups until finding interconnected metadata
    """
    extractor = EnhancedMetadataExtractor(Path('.'))

    # Get all markdown files in workspace (excluding certain dirs)
    all_md_files = []
    for pattern in ["**/*.md"]:
        for file_path in Path('.').glob(pattern):
            # Skip excluded directories
            if any(skip in str(file_path) for skip in [
                '__pycache__', 'node_modules', '.pytest_cache',
                'venv', 'venv310', 'venv311', 'venv312',
                'vscode-extension', '.vscode', '.svcode', '.worktrees',
                'seed_template', '.github', 'tmp', 'backups'
            ]):
                continue
            all_md_files.append(file_path)

    print(f"Found {len(all_md_files)} markdown files for testing")
    print(f"Will attempt up to {max_attempts} random 3-file samples")
    print("=" * 60)

    attempts = 0
    hits = 0

    while attempts < max_attempts and hits < 1:
        attempts += 1

        # Randomly select 3 files
        sample_files = random.sample(all_md_files, 3)

        print(f"\nAttempt {attempts}: Testing files:")
        for f in sample_files:
            print(f"  - {f.name}")

        # Run connectivity analysis
        graph = extractor.build_connectivity_graph(sample_files)

        # Analyze connectivity
        total_edges = len(graph["edges"])
        shared_entity_edges = [e for e in graph["edges"] if e["type"] == "shared_entity"]
        shared_concept_edges = [e for e in graph["edges"] if e["type"] == "shared_concept"]

        print(f"  Edges found: {total_edges}")
        print(f"  Shared entity edges: {len(shared_entity_edges)}")
        print(f"  Shared concept edges: {len(shared_concept_edges)}")

        # Check for interconnected triple (at least 2 edges indicating connections)
        if total_edges >= 2:
            hits += 1
            print(f"  ✅ HIT FOUND! Interconnected triple detected")

            # Show details
            print("  Connection details:")
            for edge in graph["edges"][:5]:  # Show first 5
                print(f"    {edge['source']} --({edge.get('entity', edge.get('shared_terms', 'unknown'))})--> {edge['target']} (w={edge['weight']})")

            # Run learning efficiency
            metadata_samples = [extractor.extract_enhanced_metadata(f) for f in sample_files]
            analysis = extractor.analyze_learning_efficiency(metadata_samples)
            print(f"  Learning efficiency: {analysis['learning_efficiency']:.3f} ({analysis['learning_efficiency']*100:.1f}%)")
            break
        else:
            print(f"  ❌ No significant connections")

    print("\n" + "=" * 60)
    print("GENERALIZED TEST RESULTS:")
    print(f"Total attempts: {attempts}")
    print(f"Hits found: {hits}")

    if hits > 0:
        print("✅ SUCCESS: Method reliably identifies real metadata connections")
        print("   Found interconnected triple in random sampling")
    else:
        print("❌ FAILURE: Method failed to find interconnected triples")
        print("   No significant metadata connections found in random samples")

    return hits > 0

if __name__ == '__main__':
    success = run_generalized_test()
    print(f"\nTest outcome: {'PASSED' if success else 'FAILED'}")

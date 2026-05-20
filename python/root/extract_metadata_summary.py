#!/usr/bin/env python3
"""
Extract metadata from the connected files
"""

from enhanced_metadata_extractor import EnhancedMetadataExtractor
from pathlib import Path

extractor = EnhancedMetadataExtractor(Path('.'))
files = [
    Path('reports/report_INCIDENT_L23_v01.md'),
    Path('reports/report_TASK_0043_L27_v01.md'),
    Path('reports/report_TASK_0005_L03_v01.md')
]

print('=== Metadata Found in the Connected Files ===')
for f in files:
    print(f'\nFile: {f.name}')
    metadata = extractor.extract_enhanced_metadata(f)
    quality = metadata.get('quality_scores', {}).get('overall_quality', 0)
    print(f'  Quality Score: {quality:.3f}')
    patterns = metadata.get('learning_patterns', {})
    print(f'  Problem Indicators: {len(patterns.get("problem_indicators", []))}')
    print(f'  Solution Indicators: {len(patterns.get("solution_indicators", []))}')
    entities = metadata.get('semantic_analysis', {}).get('entity_mentions', [])[:5]
    print(f'  Key Entities: {entities}')
    clusters = len(metadata.get('semantic_analysis', {}).get('concept_clusters', []))
    print(f'  Concept Clusters: {clusters}')
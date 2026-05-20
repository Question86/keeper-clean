#!/usr/bin/env python3
"""
Validation test for enhanced metadata extractor
"""

from enhanced_metadata_extractor import EnhancedMetadataExtractor
from pathlib import Path

extractor = EnhancedMetadataExtractor(Path('.'))
reports = list(Path('reports').glob('report_*.md'))[:5]
print('=== Enhanced Metadata Validation Test ===')

for report in reports:
    print(f'\nAnalyzing: {report.name}')
    metadata = extractor.extract_enhanced_metadata(report)
    quality = metadata.get('quality_scores', {})
    print(f'  Quality Score: {quality.get("overall_quality", 0):.3f}')
    print(f'  Connectivity: {quality.get("connectivity_score", 0):.3f}')
    print(f'  Depth: {quality.get("depth_score", 0):.3f}')

metadata_samples = [extractor.extract_enhanced_metadata(r) for r in reports]
analysis = extractor.analyze_learning_efficiency(metadata_samples)
print(f'\n=== Validation Results ===')
print(f'Total Samples: {analysis["total_samples"]}')
print(f'Average Quality: {analysis["average_quality_score"]:.3f}')
print(f'Learning Efficiency: {analysis["learning_efficiency"]:.3f} ({analysis["learning_efficiency"]*100:.1f}%)')
print(f'Recommendations: {len(analysis["recommendations"])}')
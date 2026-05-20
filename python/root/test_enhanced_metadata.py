#!/usr/bin/env python3
"""
Test script for enhanced metadata extractor
"""

from enhanced_metadata_extractor import EnhancedMetadataExtractor
from pathlib import Path

def test_enhanced_metadata():
    # Test enhanced metadata extraction
    extractor = EnhancedMetadataExtractor(Path('.'))

    # Test on a sample report
    reports = list(Path('reports').glob('report_*.md'))[:2]
    print('=== Enhanced Metadata Extraction Test ===')

    for report in reports:
        print(f'\nAnalyzing: {report.name}')
        metadata = extractor.extract_enhanced_metadata(report)

        # Show key metrics
        quality = metadata.get('quality_scores', {})
        context_depth = metadata.get('context_depth', {})
        learning_patterns = metadata.get('learning_patterns', {})

        print(f'  Quality Score: {quality.get("overall_quality", 0):.3f}')
        print(f'  Connectivity: {quality.get("connectivity_score", 0):.3f}')
        print(f'  Depth: {quality.get("depth_score", 0):.3f}')
        print(f'  Reference Depth: {context_depth.get("reference_depth", 0)}')
        print(f'  Technical Density: {context_depth.get("technical_density", 0):.3f}')
        print(f'  Learning Indicators: {len(learning_patterns.get("learning_indicators", []))}')

    # Test learning efficiency analysis
    print('\n=== Learning Efficiency Analysis ===')
    metadata_samples = [extractor.extract_enhanced_metadata(r) for r in reports]
    analysis = extractor.analyze_learning_efficiency(metadata_samples)

    print(f'Total Samples: {analysis["total_samples"]}')
    print(f'Average Quality: {analysis["average_quality_score"]:.3f}')
    print(f'Learning Efficiency: {analysis["learning_efficiency"]:.3f} ({analysis["learning_efficiency"]*100:.1f}%)')
    print(f'Recommendations: {len(analysis["recommendations"])}')
    for rec in analysis['recommendations']:
        print(f'  - {rec}')

if __name__ == '__main__':
    test_enhanced_metadata()
#!/usr/bin/env python3
"""
Analyze the bug report and code documentation for significant relevance
"""

from enhanced_metadata_extractor import EnhancedMetadataExtractor
from pathlib import Path

def analyze_incident_documents():
    extractor = EnhancedMetadataExtractor(Path('.'))

    # Analyze the two files
    files_to_analyze = [
        Path('bugs/BUG_0084_ARCHIVE_CHAIN_BREAK.md'),
        Path('code/CODE_0084_ARCHIVE_CHAIN_RECOVERY.md')
    ]

    print('=== ENHANCED METADATA ANALYSIS ===')
    print('Analyzing Bug Report and Code Documentation for Archive Chain Incident')
    print('=' * 70)

    for file_path in files_to_analyze:
        print(f'\n📄 Analyzing: {file_path.name}')
        print('-' * 50)

        metadata = extractor.extract_enhanced_metadata(file_path)

        # Show key metrics
        quality = metadata.get('quality_scores', {})
        context_depth = metadata.get('context_depth', {})
        learning_patterns = metadata.get('learning_patterns', {})

        print(f'🎯 Overall Quality Score: {quality.get("overall_quality", 0):.3f}')
        print(f'🔗 Connectivity Score: {quality.get("connectivity_score", 0):.3f}')
        print(f'📚 Depth Score: {quality.get("depth_score", 0):.3f}')
        print(f'📖 Reference Depth: {context_depth.get("reference_depth", 0)}')
        print(f'⚙️  Technical Density: {context_depth.get("technical_density", 0):.3f}')
        print(f'🧠 Learning Indicators: {len(learning_patterns.get("learning_indicators", []))}')

        # Show architectural insights
        arch_insights = learning_patterns.get('architectural_insights', [])
        if arch_insights:
            print(f'🏗️  Architectural Insights: {len(arch_insights)}')
            for insight in arch_insights[:3]:
                print(f'   - {insight}')

        # Show technical depth indicators
        tech_depth = learning_patterns.get('technical_depth_indicators', [])
        if tech_depth:
            print(f'🔧 Technical Depth Indicators: {len(tech_depth)}')
            for indicator in tech_depth[:3]:
                print(f'   - {indicator}')

        # Show top learning indicators
        indicators = learning_patterns.get('learning_indicators', [])[:5]
        if indicators:
            print(f'💡 Top Learning Indicators:')
            for indicator in indicators:
                print(f'   - {indicator}')

        # Show semantic relationships
        semantic_rels = metadata.get('semantic_relationships', {})
        if semantic_rels:
            print(f'🔍 Key Semantic Relationships:')
            for rel_type, targets in list(semantic_rels.items())[:3]:
                if targets:
                    print(f'   {rel_type}: {len(targets)} connections')

    print('\n' + '=' * 70)
    print('=== LEARNING EFFICIENCY ANALYSIS ===')

    # Analyze learning efficiency across both documents
    metadata_samples = [extractor.extract_enhanced_metadata(f) for f in files_to_analyze]
    analysis = extractor.analyze_learning_efficiency(metadata_samples)

    print(f'📊 Total Samples: {analysis["total_samples"]}')
    print(f'📈 Average Quality: {analysis["average_quality_score"]:.3f}')
    print(f'🚀 Learning Efficiency: {analysis["learning_efficiency"]:.3f} ({analysis["learning_efficiency"]*100:.1f}%)')
    print(f'💡 Recommendations: {len(analysis["recommendations"])}')

    for rec in analysis['recommendations'][:5]:
        print(f'   - {rec}')

    print('\n' + '=' * 70)
    print('=== SIGNIFICANT RELEVANCE ASSESSMENT ===')

    # Calculate significance scores
    total_quality = sum(m.get('quality_scores', {}).get('overall_quality', 0) for m in metadata_samples)
    avg_quality = total_quality / len(metadata_samples)

    total_connectivity = sum(m.get('quality_scores', {}).get('connectivity_score', 0) for m in metadata_samples)
    avg_connectivity = total_connectivity / len(metadata_samples)

    total_learning_indicators = sum(len(m.get('learning_patterns', {}).get('learning_indicators', [])) for m in metadata_samples)
    total_arch_insights = sum(len(m.get('learning_patterns', {}).get('architectural_insights', [])) for m in metadata_samples)
    total_tech_depth = sum(len(m.get('learning_patterns', {}).get('technical_depth_indicators', [])) for m in metadata_samples)

    print(f'⭐ Average Quality Score: {avg_quality:.3f}')
    print(f'🔗 Average Connectivity: {avg_connectivity:.3f}')
    print(f'🧠 Total Learning Indicators: {total_learning_indicators}')
    print(f'🏗️  Total Architectural Insights: {total_arch_insights}')
    print(f'🔧 Total Technical Depth Indicators: {total_tech_depth}')
    print(f'📚 Combined Technical Depth: {sum(m.get("context_depth", {}).get("technical_density", 0) for m in metadata_samples):.3f}')

    # Significance assessment (enhanced with new metrics)
    base_score = (avg_quality * 0.3) + (avg_connectivity * 0.2) + (min(total_learning_indicators / 20, 1) * 0.2)
    arch_bonus = min(total_arch_insights * 0.05, 0.15)  # Architectural insights are valuable
    tech_bonus = min(total_tech_depth * 0.03, 0.15)   # Technical depth is valuable
    significance_score = base_score + arch_bonus + tech_bonus
    print(f'🎯 SIGNIFICANCE SCORE: {significance_score:.3f} ({significance_score*100:.1f}%)')

    if significance_score > 0.8:
        print('🏆 HIGH SIGNIFICANCE: Exceptional learning value and connectivity')
    elif significance_score > 0.6:
        print('✅ SIGNIFICANT: Strong learning value with good connectivity')
    elif significance_score > 0.4:
        print('📈 MODERATE: Decent learning value')
    else:
        print('📉 LOW: Limited learning value')

if __name__ == '__main__':
    analyze_incident_documents()
#!/usr/bin/env python3
"""
Test enhanced metadata extraction on BUG_0084 and CODE_0084
"""

from enhanced_metadata_extractor import EnhancedMetadataExtractor
from pathlib import Path

extractor = EnhancedMetadataExtractor(Path('.'))

# Test on the specific problem-solution pair
files_to_test = [
    Path('bugs/BUG_0084_ARCHIVE_CHAIN_BREAK.md'),
    Path('code/CODE_0084_ARCHIVE_CHAIN_RECOVERY.md')
]

print('=== TASK_0174: Problem-Solution Connectivity Test ===')

for file_path in files_to_test:
    print(f'\nAnalyzing: {file_path.name}')
    metadata = extractor.extract_enhanced_metadata(file_path)
    quality = metadata.get('quality_scores', {})
    learning_patterns = metadata.get('learning_patterns', {})
    
    print(f'  Overall Quality: {quality.get("overall_quality", 0):.3f}')
    print(f'  Connectivity: {quality.get("connectivity_score", 0):.3f}')
    print(f'  Depth: {quality.get("depth_score", 0):.3f}')
    print(f'  Learning Potential: {quality.get("learning_potential", 0):.3f}')
    print(f'  Problem Indicators: {len(learning_patterns.get("problem_indicators", []))}')
    print(f'  Solution Indicators: {len(learning_patterns.get("solution_indicators", []))}')
    print(f'  Architectural Insights: {len(learning_patterns.get("architectural_insights", []))}')
    print(f'  Technical Depth: {len(learning_patterns.get("technical_depth_indicators", []))}')

# Test learning efficiency on this pair
metadata_samples = [extractor.extract_enhanced_metadata(f) for f in files_to_test]
analysis = extractor.analyze_learning_efficiency(metadata_samples)
print(f'\n=== Problem-Solution Pair Analysis ===')
print(f'Samples: {analysis["total_samples"]}')
print(f'Average Quality: {analysis["average_quality_score"]:.3f}')
print(f'Learning Efficiency: {analysis["learning_efficiency"]:.3f} ({analysis["learning_efficiency"]*100:.1f}%)')
print(f'Recommendations: {len(analysis["recommendations"])}')
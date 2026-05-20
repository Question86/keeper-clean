#!/usr/bin/env python3
"""
Test metadata connections between three related documents
"""

from enhanced_metadata_extractor import EnhancedMetadataExtractor
from pathlib import Path

extractor = EnhancedMetadataExtractor(Path('.'))

# The three documents related to archive chain incident
files_to_test = [
    Path('docs/VIOLATIONS/INCIDENT_0084_ARCHIVE_CHAIN_BREAK.md'),  # Archive-like incident report
    Path('bugs/BUG_0084_ARCHIVE_CHAIN_BREAK.md'),  # Bug report
    Path('code/CODE_0084_ARCHIVE_CHAIN_RECOVERY.md')  # Code fix
]

print('=== ARCHITECTURAL TEST: Hidden Interlinks Discovery ===')
print('Testing metadata connections between three documents that do not directly reference each other')
print('Expected: Strong semantic connections through "archive chain" incident context')
print()

for file_path in files_to_test:
    print(f'Analyzing: {file_path.name}')
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
    print()

# Test cross-document connectivity
print('=== CROSS-DOCUMENT CONNECTIVITY ANALYSIS ===')
graph = extractor.build_connectivity_graph(files_to_test)
print(f'Nodes: {len(graph["nodes"])}')
print(f'Edges: {len(graph["edges"])}')

# Check for semantic connections
semantic_edges = [e for e in graph["edges"] if e["type"] == "semantic"]
print(f'Semantic Edges: {len(semantic_edges)}')
for edge in semantic_edges:
    print(f'  {edge["source"]} --({edge["terms"]})--> {edge["target"]} (weight: {edge["weight"]})')

# Check for shared entity connections
entity_edges = [e for e in graph["edges"] if e["type"] == "shared_entity"]
print(f'Shared Entity Edges: {len(entity_edges)}')
for edge in entity_edges[:5]:  # Show first 5
    print(f'  {edge["source"]} --({edge["entity"]})--> {edge["target"]} (weight: {edge["weight"]})')

# Check for shared concept connections
concept_edges = [e for e in graph["edges"] if e["type"] == "shared_concept"]
print(f'Shared Concept Edges: {len(concept_edges)}')
for edge in concept_edges[:5]:  # Show first 5
    print(f'  {edge["source"]} --({edge["shared_terms"]})--> {edge["target"]} (weight: {edge["weight"]})')

# Overall learning efficiency
metadata_samples = [extractor.extract_enhanced_metadata(f) for f in files_to_test]
analysis = extractor.analyze_learning_efficiency(metadata_samples)
print(f'\n=== TRILATERAL CONNECTION EFFICIENCY ===')
print(f'Samples: {analysis["total_samples"]}')
print(f'Average Quality: {analysis["average_quality_score"]:.3f}')
print(f'Learning Efficiency: {analysis["learning_efficiency"]:.3f} ({analysis["learning_efficiency"]*100:.1f}%)')
print(f'Recommendations: {len(analysis["recommendations"])}')
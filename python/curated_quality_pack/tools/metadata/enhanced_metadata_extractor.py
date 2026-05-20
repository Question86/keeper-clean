#!/usr/bin/env python3
"""
Enhanced Metadata Extractor for TASK_0167

Implements deeper metadata extraction and connectivity enhancement
to improve learning efficiency from 0.0% to >5%.

Enhancements:
- Semantic relationship mapping
- Context depth analysis
- Learning pattern recognition
- Cross-document connectivity
- Quality scoring for learning relevance
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime, timezone
from collections import defaultdict, Counter
import math

class EnhancedMetadataExtractor:
    """
    Enhanced metadata extraction for deeper connectivity and learning.

    TASK_0167: Improve learning efficiency through richer metadata
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.semantic_cache = {}
        self.connectivity_graph = defaultdict(set)

    def extract_enhanced_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract enhanced metadata with deeper connectivity analysis.

        Returns enriched metadata dictionary with:
        - Basic metadata (existing)
        - Semantic relationships
        - Context depth metrics
        - Learning patterns
        - Quality scores
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            return {"error": f"Failed to read {file_path}: {e}"}

        # Start with basic metadata
        metadata = self._extract_basic_metadata(file_path, content)

        # Add enhanced features
        metadata.update(self._extract_semantic_relationships(content))
        metadata.update(self._extract_context_depth_metrics(content))
        metadata.update(self._extract_learning_patterns(content))
        metadata.update(self._calculate_quality_scores(metadata))

        return metadata

    def _extract_basic_metadata(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract basic metadata (existing functionality)."""
        metadata = {
            "file_path": str(file_path.relative_to(self.workspace_root)),
            "file_size": len(content),
            "line_count": len(content.split('\n')),
            "word_count": len(content.split()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # File type specific extraction
        if file_path.suffix == '.md':
            metadata.update(self._extract_markdown_metadata(content))
        elif file_path.suffix == '.py':
            metadata.update(self._extract_python_metadata(content))
        elif file_path.suffix == '.json':
            metadata.update(self._extract_json_metadata(content))

        return metadata

    def _extract_markdown_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata specific to markdown files."""
        metadata = {}

        # Headers analysis
        headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        metadata["headers"] = headers
        metadata["header_count"] = len(headers)
        metadata["max_header_depth"] = max([len(re.match(r'^#+', line).group()) for line in content.split('\n') if re.match(r'^#+', line)] or [0])

        # Code blocks
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', content, re.DOTALL)
        metadata["code_block_count"] = len(code_blocks)
        metadata["total_code_lines"] = sum(len(block.split('\n')) for block in code_blocks)

        # Links and references
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        metadata["link_count"] = len(links)

        # Citations and references
        citations = re.findall(r'\[ref:([^\]]+)\]', content)
        metadata["citation_count"] = len(citations)
        metadata["citations"] = citations

        # Task/Report specific patterns
        if 'TASK_' in content:
            task_ids = re.findall(r'TASK_(\d+)', content)
            metadata["referenced_tasks"] = sorted(set(task_ids))

        return metadata

    def _extract_python_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata specific to Python files."""
        metadata = {}

        # Function definitions
        functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
        metadata["function_count"] = len(functions)
        metadata["functions"] = functions

        # Class definitions
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        metadata["class_count"] = len(classes)
        metadata["classes"] = classes

        # Imports
        imports = re.findall(r'^(?:from\s+\w+\s+)?import\s+(.+)$', content, re.MULTILINE)
        metadata["import_count"] = len(imports)

        # Comments and docstrings
        docstrings = re.findall(r'""".*?"""', content, re.DOTALL)
        metadata["docstring_count"] = len(docstrings)

        return metadata

    def _extract_json_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata specific to JSON files."""
        metadata = {}
        try:
            data = json.loads(content)
            metadata["json_valid"] = True
            metadata["json_keys"] = list(data.keys()) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            metadata["json_depth"] = self._calculate_json_depth(data)
        except json.JSONDecodeError:
            metadata["json_valid"] = False

        return metadata

    def _calculate_json_depth(self, data: Any, current_depth: int = 0) -> int:
        """Calculate maximum depth of JSON structure."""
        if isinstance(data, dict):
            return max([self._calculate_json_depth(v, current_depth + 1) for v in data.values()] or [current_depth])
        elif isinstance(data, list):
            return max([self._calculate_json_depth(item, current_depth + 1) for item in data] or [current_depth])
        else:
            return current_depth

    def _extract_semantic_relationships(self, content: str) -> Dict[str, Any]:
        """Extract semantic relationships and connections."""
        relationships = {
            "semantic_relationships": {},
            "entity_mentions": [],
            "concept_clusters": []
        }

        # Extract entities (enhanced patterns)
        entities = set()
        
        # Code references
        entities.update(re.findall(r'`([^`]+)`', content))
        
        # Proper nouns and technical terms (exclude common words)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        raw_entities = re.findall(r'\b[A-Z][a-zA-Z]+\b', content)
        filtered_entities = [e for e in raw_entities if e.lower() not in common_words]
        entities.update(filtered_entities)
        
        # File references
        entities.update(re.findall(r'\b[\w\-]+\.(md|py|js|ts|json|yml|yaml)\b', content))
        
        # Task references
        entities.update(re.findall(r'\bTASK_\d+\b', content))
        
        relationships["entity_mentions"] = list(entities)

        # Extract concept clusters (improved)
        sentences = re.split(r'[.!?]+', content)
        concept_clusters = []
        for sentence in sentences:
            words = re.findall(r'\b[a-z]{3,}\b', sentence.lower())
            if len(words) >= 3:
                # Find groups of related technical terms (expanded)
                tech_terms = [w for w in words if any(term in w for term in [
                    'data', 'learn', 'model', 'system', 'process', 'analysis', 'validation',
                    'algorithm', 'function', 'class', 'method', 'variable', 'parameter',
                    'connection', 'network', 'graph', 'node', 'edge', 'metadata',
                    'extraction', 'enhancement', 'optimization', 'performance', 'efficiency',
                    'quality', 'depth', 'complexity', 'relationship', 'semantic'
                ])]
                if len(tech_terms) >= 2:
                    concept_clusters.append(tech_terms[:5])  # Max 5 terms per cluster

        relationships["concept_clusters"] = concept_clusters[:15]  # Increased limit

        # Build semantic graph connections (improved weighting)
        semantic_graph = defaultdict(list)
        for cluster in concept_clusters:
            for i, term1 in enumerate(cluster):
                for term2 in cluster[i+1:]:
                    if term1 not in semantic_graph[term2]:  # Avoid duplicates
                        semantic_graph[term1].append(term2)
                    if term2 not in semantic_graph[term1]:
                        semantic_graph[term2].append(term1)

        relationships["semantic_relationships"] = dict(semantic_graph)

        return {"semantic_analysis": relationships}

    def _extract_context_depth_metrics(self, content: str) -> Dict[str, Any]:
        """Extract context depth and complexity metrics."""
        metrics = {}

        # Context depth based on reference chains (enhanced)
        refs = re.findall(r'\[ref:([^\]]+)\]', content)
        metrics["reference_depth"] = len(refs)
        
        # Also count other reference types
        other_refs = re.findall(r'\[([^\]]+)\]\([^\)]+\)', content)  # Markdown links
        metrics["total_references"] = len(refs) + len(other_refs)

        # Complexity based on technical terminology density (expanded)
        tech_terms = len(re.findall(r'\b(?:algorithm|implementation|optimization|efficiency|validation|integration|architecture|framework|infrastructure|scalability|reliability|maintainability|modularity|abstraction|concurrency|parallelization|asynchronous|complexity|performance|memory|resource|allocation|fault|tolerance|resilience|recovery|monitoring|observability|telemetry|metrics|logging|tracing|state|transition|validation|integrity|consistency|robustness|design|pattern|system|analysis|root|cause|technical|path|logic|handling|exception|management|data|flow|control|computational|semantic|relationship|connectivity|metadata|extraction|enhancement|learning|parameter|discovery|matrix|relative|value|context|dreaming|network|graph|node|edge|strength|weight|quality|depth|hierarchical|structural)\b', content, re.IGNORECASE))
        total_words = len(content.split())
        metrics["technical_density"] = tech_terms / max(total_words, 1)

        # Information hierarchy depth (enhanced)
        header_levels = [len(re.match(r'^#+', line).group()) for line in content.split('\n') if re.match(r'^#+', line)]
        metrics["hierarchy_depth"] = max(header_levels) if header_levels else 0
        metrics["hierarchy_complexity"] = len(set(header_levels))  # Number of different levels used
        metrics["hierarchy_balance"] = len(header_levels) / max(metrics["hierarchy_depth"], 1)  # Headers per level

        # Cross-reference density (enhanced)
        cross_refs = len(re.findall(r'\[([^\]]+)\]\[([^\]]+)\]', content))  # Markdown cross-references
        internal_links = len(re.findall(r'\[([^\]]+)\]\(#([^\)]+)\)', content))  # Internal links
        metrics["cross_reference_density"] = (cross_refs + internal_links) / max(len(content.split('\n')), 1)

        # Content structure metrics
        code_blocks = content.count('```')
        list_items = len(re.findall(r'^[\s]*[-\*\+]\s', content, re.MULTILINE))
        numbered_items = len(re.findall(r'^[\s]*\d+\.\s', content, re.MULTILINE))
        metrics["structural_density"] = (code_blocks + list_items + numbered_items) / max(len(content.split('\n')), 1)

        return {"context_depth": metrics}

    def _extract_learning_patterns(self, content: str) -> Dict[str, Any]:
        """Extract patterns that indicate learning opportunities."""
        patterns = {
            "learning_indicators": [],
            "success_patterns": [],
            "failure_patterns": [],
            "improvement_suggestions": [],
            "architectural_insights": [],
            "technical_depth_indicators": [],
            "connection_evidence": [],
            "quality_signals": []
        }

        # Learning indicators (expanded)
        learning_terms = [
            'learned', 'discovered', 'realized', 'understood', 'improved', 'enhanced', 'optimized',
            'achieved', 'succeeded', 'completed', 'resolved', 'fixed', 'implemented', 'developed',
            'created', 'built', 'designed', 'analyzed', 'evaluated', 'tested', 'validated',
            'verified', 'confirmed', 'proven', 'demonstrated', 'established', 'identified'
        ]
        for term in learning_terms:
            if term in content.lower():
                patterns["learning_indicators"].append(term)

        # Success patterns (expanded)
        success_indicators = re.findall(r'(?:✅|success|successful|completed|achieved|resolved|fixed|implemented|working|passed|validated|verified|confirmed|proven|demonstrated)', content, re.IGNORECASE)
        patterns["success_patterns"] = success_indicators

        # Failure patterns (expanded)
        failure_indicators = re.findall(r'(?:❌|failed|failure|error|problem|issue|bug|broken|crash|exception|timeout|rejected|denied|blocked|stuck|failed)', content, re.IGNORECASE)
        patterns["failure_patterns"] = failure_indicators

        # Improvement suggestions (expanded)
        improvement_patterns = re.findall(r'(?:should|could|would|recommend|suggest|improve|enhance|optimize|better|upgrade|refactor|streamline|efficient|effective|robust|reliable|scalable|maintainable)', content, re.IGNORECASE)
        patterns["improvement_suggestions"] = improvement_patterns[:15]  # Increased limit

        # Connection evidence (new)
        connection_terms = [
            'connects', 'links', 'relates', 'references', 'depends', 'requires', 'uses', 'imports',
            'integrates', 'interacts', 'communicates', 'shares', 'exchanges', 'transfers',
            'associates', 'correlates', 'maps', 'binds', 'couples', 'interfaces'
        ]
        for term in connection_terms:
            if term in content.lower():
                patterns["connection_evidence"].append(term)

        # Problem-solution indicators (new for TASK_0174)
        problem_indicators = [
            'problem', 'issue', 'bug', 'error', 'failure', 'broken', 'crash', 'exception',
            'fault', 'defect', 'glitch', 'malfunction', 'breakage', 'interruption',
            'inconsistency', 'violation', 'blockage', 'obstruction', 'hindrance'
        ]
        for indicator in problem_indicators:
            if indicator in content.lower():
                patterns["problem_indicators"] = patterns.get("problem_indicators", []) + [indicator]

        solution_indicators = [
            'solution', 'fix', 'resolve', 'implement', 'recovery', 'correction', 'repair',
            'remedy', 'patch', 'workaround', 'mitigation', 'prevention', 'enhancement',
            'improvement', 'optimization', 'reconstruction', 'restoration', 'stabilization'
        ]
        for indicator in solution_indicators:
            if indicator in content.lower():
                patterns["solution_indicators"] = patterns.get("solution_indicators", []) + [indicator]

        # Quality signals (new)
        quality_terms = [
            'quality', 'excellent', 'superior', 'high', 'low', 'poor', 'good', 'bad', 'best',
            'worst', 'optimal', 'suboptimal', 'efficient', 'inefficient', 'effective', 'ineffective',
            'robust', 'fragile', 'reliable', 'unreliable', 'stable', 'unstable', 'consistent', 'inconsistent'
        ]
        for term in quality_terms:
            if term in content.lower():
                patterns["quality_signals"].append(term)

        # Architectural insights (expanded)
        architectural_terms = [
            'architecture', 'framework', 'infrastructure', 'design pattern', 'system design',
            'scalability', 'reliability', 'maintainability', 'modularity', 'abstraction',
            'state management', 'validation', 'integrity', 'consistency', 'robustness',
            'resilience', 'fault tolerance', 'recovery', 'self-healing', 'monitoring',
            'observability', 'telemetry', 'metrics', 'logging', 'tracing',
            'microservices', 'distributed', 'cloud', 'container', 'orchestration',
            'asynchronous', 'event-driven', 'reactive', 'serverless', 'edge computing'
        ]
        for term in architectural_terms:
            if term.lower() in content.lower():
                patterns["architectural_insights"].append(term)

        # Technical depth indicators (expanded)
        depth_indicators = [
            'root cause', 'technical analysis', 'code path', 'state transition',
            'validation logic', 'error handling', 'exception management',
            'performance optimization', 'memory management', 'resource allocation',
            'concurrency', 'parallelization', 'asynchronous', 'event-driven',
            'data flow', 'control flow', 'algorithm complexity', 'space complexity',
            'time complexity', 'computational efficiency', 'big o', 'asymptotic',
            'scalability analysis', 'bottleneck identification', 'profiling', 'benchmarking',
            'load testing', 'stress testing', 'integration testing', 'unit testing',
            'continuous integration', 'continuous deployment', 'devops', 'infrastructure as code'
        ]
        for indicator in depth_indicators:
            if indicator.lower() in content.lower():
                patterns["technical_depth_indicators"].append(indicator)

        return {"learning_patterns": patterns}

        # Architectural insights (deep technical analysis)
        architectural_terms = [
            'architecture', 'framework', 'infrastructure', 'design pattern', 'system design',
            'scalability', 'reliability', 'maintainability', 'modularity', 'abstraction',
            'state management', 'validation', 'integrity', 'consistency', 'robustness',
            'resilience', 'fault tolerance', 'recovery', 'self-healing', 'monitoring',
            'observability', 'telemetry', 'metrics', 'logging', 'tracing'
        ]
        for term in architectural_terms:
            if term.lower() in content.lower():
                patterns["architectural_insights"].append(term)

        # Technical depth indicators (complex analysis patterns)
        depth_indicators = [
            'root cause', 'technical analysis', 'code path', 'state transition',
            'validation logic', 'error handling', 'exception management',
            'performance optimization', 'memory management', 'resource allocation',
            'concurrency', 'parallelization', 'asynchronous', 'event-driven',
            'data flow', 'control flow', 'algorithm complexity', 'space complexity',
            'time complexity', 'computational efficiency'
        ]
        for indicator in depth_indicators:
            if indicator.lower() in content.lower():
                patterns["technical_depth_indicators"].append(indicator)

        return {"learning_patterns": patterns}

    def _calculate_quality_scores(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality scores for learning relevance."""
        scores = {}

        # Connectivity score (enhanced)
        ref_score = min(len(metadata.get("citations", [])) / 10, 1.0)
        semantic_score = min(len(metadata.get("semantic_analysis", {}).get("semantic_relationships", {})) / 30, 1.0)  # Increased threshold
        connection_evidence = len(metadata.get("learning_patterns", {}).get("connection_evidence", []))
        connection_score = min(connection_evidence / 5, 1.0)
        scores["connectivity_score"] = (ref_score + semantic_score + connection_score) / 3

        # Depth score (enhanced)
        depth_metrics = metadata.get("context_depth", {})
        hierarchy_score = min(depth_metrics.get("hierarchy_depth", 0) / 6, 1.0)
        technical_score = min(depth_metrics.get("technical_density", 0) * 15, 1.0)  # Increased multiplier
        structural_score = min(depth_metrics.get("structural_density", 0) * 20, 1.0)  # New structural factor
        scores["depth_score"] = (hierarchy_score + technical_score + structural_score) / 3

        # Learning potential score (enhanced)
        learning_patterns = metadata.get("learning_patterns", {})
        learning_indicators = len(learning_patterns.get("learning_indicators", []))
        success_failure_ratio = len(learning_patterns.get("success_patterns", [])) / max(len(learning_patterns.get("failure_patterns", [])), 1)
        quality_signals = len(learning_patterns.get("quality_signals", []))
        
        # Problem-solution bonus (new for TASK_0174)
        problem_count = len(learning_patterns.get("problem_indicators", []))
        solution_count = len(learning_patterns.get("solution_indicators", []))
        problem_solution_ratio = min(problem_count, solution_count) / max(max(problem_count, solution_count), 1)  # Balance bonus
        problem_solution_bonus = min(problem_solution_ratio * 0.4, 0.4)  # Up to 0.4 bonus for balanced problem-solution

        # Add architectural and technical depth bonuses (increased)
        architectural_insights = len(learning_patterns.get("architectural_insights", []))
        technical_depth = len(learning_patterns.get("technical_depth_indicators", []))

        # Weight architectural insights heavily
        architectural_bonus = min(architectural_insights * 0.3, 0.6)  # Increased to 0.6
        technical_bonus = min(technical_depth * 0.2, 0.4)  # Increased to 0.4
        quality_bonus = min(quality_signals * 0.1, 0.2)  # New quality bonus

        scores["learning_potential"] = min((learning_indicators + success_failure_ratio + architectural_bonus + technical_bonus + quality_bonus + problem_solution_bonus) / 18, 1.0)  # Increased denominator

        # Overall quality score (weighted average)
        scores["overall_quality"] = (
            scores["connectivity_score"] * 0.35 +  # Slightly adjusted weights
            scores["depth_score"] * 0.35 +
            scores["learning_potential"] * 0.3
        )

        return {"quality_scores": scores}

    def build_connectivity_graph(self, files: List[Path]) -> Dict[str, Any]:
        """Build a connectivity graph across all files."""
        graph = {
            "nodes": [],
            "edges": [],
            "communities": [],
            "centrality_scores": {}
        }

        # Extract metadata for all files
        file_metadata = {}
        for file_path in files:
            metadata = self.extract_enhanced_metadata(file_path)
            file_metadata[str(file_path)] = metadata

            # Add node
            graph["nodes"].append({
                "id": str(file_path),
                "type": file_path.suffix,
                "quality_score": metadata.get("quality_scores", {}).get("overall_quality", 0),
                "connectivity": metadata.get("quality_scores", {}).get("connectivity_score", 0)
            })

        # Build edges based on citations and semantic relationships
        for file_path, metadata in file_metadata.items():
            citations = metadata.get("citations", [])
            semantic_rels = metadata.get("semantic_analysis", {}).get("semantic_relationships", {})
            entity_mentions = metadata.get("semantic_analysis", {}).get("entity_mentions", [])
            concept_clusters = metadata.get("semantic_analysis", {}).get("concept_clusters", [])

            # Citation edges
            for citation in citations:
                # Find files that match citation pattern
                for other_file in files:
                    if citation in str(other_file):
                        graph["edges"].append({
                            "source": file_path,
                            "target": str(other_file),
                            "type": "citation",
                            "weight": 1.0
                        })

            # Semantic edges (existing)
            for term, related_terms in semantic_rels.items():
                for related_term in related_terms:
                    # Find files that contain both terms
                    for other_file in files:
                        if other_file != Path(file_path):
                            other_content = file_metadata[str(other_file)].get("content", "")
                            if term in other_content.lower() and related_term in other_content.lower():
                                graph["edges"].append({
                                    "source": file_path,
                                    "target": str(other_file),
                                    "type": "semantic",
                                    "terms": [term, related_term],
                                    "weight": 0.5
                                })

            # Shared entity edges (new for interlink discovery)
            for entity in entity_mentions:
                for other_file in files:
                    if other_file != Path(file_path):
                        other_entities = file_metadata[str(other_file)].get("semantic_analysis", {}).get("entity_mentions", [])
                        if entity in other_entities:
                            # Avoid duplicate edges
                            edge_exists = any(e["source"] == file_path and e["target"] == str(other_file) and e["type"] == "shared_entity" for e in graph["edges"])
                            if not edge_exists:
                                graph["edges"].append({
                                    "source": file_path,
                                    "target": str(other_file),
                                    "type": "shared_entity",
                                    "entity": entity,
                                    "weight": 0.3
                                })

            # Shared concept cluster edges (new for interlink discovery)
            for cluster in concept_clusters:
                for other_file in files:
                    if other_file != Path(file_path):
                        other_clusters = file_metadata[str(other_file)].get("semantic_analysis", {}).get("concept_clusters", [])
                        for other_cluster in other_clusters:
                            # Check for significant overlap (at least 2 shared terms)
                            shared_terms = set(cluster) & set(other_cluster)
                            if len(shared_terms) >= 2:
                                edge_exists = any(e["source"] == file_path and e["target"] == str(other_file) and e["type"] == "shared_concept" for e in graph["edges"])
                                if not edge_exists:
                                    graph["edges"].append({
                                        "source": file_path,
                                        "target": str(other_file),
                                        "type": "shared_concept",
                                        "shared_terms": list(shared_terms),
                                        "weight": 0.4
                                    })

        return graph

    def analyze_learning_efficiency(self, metadata_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze current learning efficiency across metadata samples."""
        analysis = {
            "total_samples": len(metadata_samples),
            "average_quality_score": 0,
            "learning_efficiency": 0,
            "connectivity_distribution": {},
            "depth_distribution": {},
            "recommendations": []
        }

        if not metadata_samples:
            return analysis

        # Calculate averages
        quality_scores = [m.get("quality_scores", {}).get("overall_quality", 0) for m in metadata_samples]
        analysis["average_quality_score"] = sum(quality_scores) / len(quality_scores)

        # Learning efficiency (simplified metric)
        # Based on quality scores and connectivity
        connectivity_scores = [m.get("quality_scores", {}).get("connectivity_score", 0) for m in metadata_samples]
        depth_scores = [m.get("quality_scores", {}).get("depth_score", 0) for m in metadata_samples]

        # Learning efficiency = quality * (connectivity + depth) / 2
        efficiencies = []
        for i, score in enumerate(quality_scores):
            conn = connectivity_scores[i]
            depth = depth_scores[i]
            efficiency = score * (conn + depth) / 2
            efficiencies.append(efficiency)

        analysis["learning_efficiency"] = sum(efficiencies) / len(efficiencies)

        # Distributions
        analysis["connectivity_distribution"] = self._calculate_distribution(connectivity_scores)
        analysis["depth_distribution"] = self._calculate_distribution(depth_scores)

        # Generate recommendations
        if analysis["learning_efficiency"] < 0.05:  # Target is >5%
            analysis["recommendations"].append("Learning efficiency below target (5%). Enhance metadata depth.")
        if analysis["average_quality_score"] < 0.3:
            analysis["recommendations"].append("Low quality scores. Improve semantic relationship extraction.")
        if max(connectivity_scores) < 0.5:
            analysis["recommendations"].append("Poor connectivity. Add more cross-references and citations.")

        return analysis

    def _calculate_distribution(self, values: List[float]) -> Dict[str, Any]:
        """Calculate distribution statistics."""
        if not values:
            return {}

        return {
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "median": sorted(values)[len(values) // 2],
            "quartiles": {
                "25": sorted(values)[len(values) // 4],
                "75": sorted(values)[3 * len(values) // 4]
            }
        }
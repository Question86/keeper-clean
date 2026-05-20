# MODE: LIBRARY

"""
Search Synergy - Mega.md Methodology Integration

Implements mega.md methodology for search optimization:
- Depth-first metadata network expansion
- Reference chain analysis and optimization
- Token budget allocation for search operations
- Quality scoring based on connectivity metrics
- Proactive knowledge discovery

Integrates mega.md principles with the advanced search system.
"""

from __future__ import annotations

import json
import re
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict, Counter

from advanced_search_engine import AdvancedSearchEngine, EnhancedSearchResult
from intelligent_tagger import IntelligentTagger


@dataclass
class ReferenceNode:
    """A node in the reference graph."""
    id: str
    type: str  # 'report', 'task', 'lesson', 'archive'
    title: str
    outgoing_refs: List[str]
    incoming_refs: List[str]
    token_cost: int
    quality_score: float
    loop_num: int
    created_at: datetime


@dataclass
class ReferenceChain:
    """A chain of references following mega.md methodology."""
    nodes: List[ReferenceNode]
    total_depth: int
    total_tokens: int
    connectivity_score: float
    knowledge_density: float


@dataclass
class MegaSearchResult:
    """Search result enhanced with mega.md synergy."""
    base_result: EnhancedSearchResult
    reference_chains: List[ReferenceChain]
    synergy_score: float
    knowledge_context: Dict[str, Any]
    recommended_exploration: List[str]


class SearchSynergy:
    """
    Mega.md methodology integration for search optimization.

    Implements depth-first metadata network principles:
    - Reference chain analysis
    - Token budget optimization
    - Quality-based ranking
    - Proactive knowledge discovery
    """

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.search_engine = AdvancedSearchEngine(workspace_path)
        self.tagger = IntelligentTagger(workspace_path)

        # Mega.md parameters
        self.target_branching_factor = 5  # Minimum 5 refs per document
        self.max_token_budget = 200000  # 200k tokens per loop
        self.min_reference_depth = 3
        self.quality_weight = 0.7
        self.connectivity_weight = 0.3

        # Build reference graph
        self.reference_graph: Dict[str, ReferenceNode] = {}
        self._build_reference_graph()

    def _build_reference_graph(self) -> None:
        """Build the reference graph from workspace content."""
        # Scan reports, tasks, and other documents for references
        self._scan_reports_for_references()
        self._scan_tasks_for_references()
        self._scan_lessons_for_references()

        # Calculate connectivity metrics
        self._calculate_connectivity_scores()

    def _scan_reports_for_references(self) -> None:
        """Scan report files for reference patterns."""
        reports_dir = self.workspace / "reports"
        if not reports_dir.exists():
            return

        for report_file in reports_dir.glob("*.md"):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract metadata
                metadata = self._extract_report_metadata(content, str(report_file))

                # Find references
                references = self._extract_references(content)

                # Create node
                node = ReferenceNode(
                    id=metadata.get('id', str(report_file.name)),
                    type='report',
                    title=metadata.get('title', report_file.stem),
                    outgoing_refs=references,
                    incoming_refs=[],  # Will be populated later
                    token_cost=self._estimate_token_cost(content),
                    quality_score=self._calculate_quality_score(content, references),
                    loop_num=metadata.get('loop_num', 0),
                    created_at=metadata.get('created_at', datetime.now(timezone.utc))
                )

                self.reference_graph[node.id] = node

            except (IOError, UnicodeDecodeError):
                continue

    def _scan_tasks_for_references(self) -> None:
        """Scan task files for references."""
        tasks_dir = self.workspace / "tasks"
        if not tasks_dir.exists():
            return

        for task_file in tasks_dir.glob("*.md"):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                references = self._extract_references(content)
                metadata = self._extract_task_metadata(content, str(task_file))

                node = ReferenceNode(
                    id=metadata.get('id', str(task_file.name)),
                    type='task',
                    title=metadata.get('title', task_file.stem),
                    outgoing_refs=references,
                    incoming_refs=[],
                    token_cost=self._estimate_token_cost(content),
                    quality_score=self._calculate_quality_score(content, references),
                    loop_num=metadata.get('loop_num', 0),
                    created_at=metadata.get('created_at', datetime.now(timezone.utc))
                )

                self.reference_graph[node.id] = node

            except (IOError, UnicodeDecodeError):
                continue

    def _scan_lessons_for_references(self) -> None:
        """Scan lesson files for references."""
        # Look for lesson files in various locations
        lesson_patterns = [
            "lessons_learned_*.md",
            "*lesson*.md",
            "*learning*.md"
        ]

        for pattern in lesson_patterns:
            for lesson_file in self.workspace.glob(f"**/{pattern}"):
                try:
                    with open(lesson_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    references = self._extract_references(content)

                    node = ReferenceNode(
                        id=str(lesson_file.name),
                        type='lesson',
                        title=lesson_file.stem,
                        outgoing_refs=references,
                        incoming_refs=[],
                        token_cost=self._estimate_token_cost(content),
                        quality_score=self._calculate_quality_score(content, references),
                        loop_num=0,  # Lessons may not have loop numbers
                        created_at=datetime.now(timezone.utc)
                    )

                    self.reference_graph[node.id] = node

                except (IOError, UnicodeDecodeError):
                    continue

    def _extract_references(self, content: str) -> List[str]:
        """Extract reference IDs from content using various patterns."""
        references = []

        # Pattern 1: [TASK_XXXX] or (TASK_XXXX)
        task_refs = re.findall(r'\b(TASK_\w+)\b', content, re.IGNORECASE)
        references.extend(task_refs)

        # Pattern 2: report_LXXX_...
        report_refs = re.findall(r'\b(report_L\d+_\w+)\b', content, re.IGNORECASE)
        references.extend(report_refs)

        # Pattern 3: See also: XXXX
        see_also_refs = re.findall(r'see also:\s*([^\n]+)', content, re.IGNORECASE)
        for ref_block in see_also_refs:
            # Extract IDs from the block
            ids = re.findall(r'\b(\w+_\w+)\b', ref_block)
            references.extend(ids)

        # Pattern 4: References section
        ref_section = re.search(r'#+\s*references?\s*\n(.*?)(?=\n#|\Z)', content, re.IGNORECASE | re.DOTALL)
        if ref_section:
            ref_content = ref_section.group(1)
            ids = re.findall(r'\b(\w+_\w+)\b', ref_content)
            references.extend(ids)

        return list(set(references))  # Remove duplicates

    def _extract_report_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """Extract metadata from report content."""
        metadata = {}

        # Extract ID from filename
        filename = Path(file_path).name
        if 'report_' in filename:
            metadata['id'] = filename

        # Extract loop number
        loop_match = re.search(r'_L(\d+)_', filename)
        if loop_match:
            metadata['loop_num'] = int(loop_match.group(1))

        # Extract title
        title_match = re.search(r'#+\s*(.+?)\n', content)
        if title_match:
            metadata['title'] = title_match.group(1).strip()

        return metadata

    def _extract_task_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """Extract metadata from task content."""
        metadata = {}

        filename = Path(file_path).name
        if 'task_' in filename:
            metadata['id'] = filename

        # Extract loop number if present
        loop_match = re.search(r'_L(\d+)', filename)
        if loop_match:
            metadata['loop_num'] = int(loop_match.group(1))

        return metadata

    def _estimate_token_cost(self, content: str) -> int:
        """Estimate token cost for processing content."""
        # Rough estimation: ~4 characters per token
        char_count = len(content)
        return char_count // 4

    def _calculate_quality_score(self, content: str, references: List[str]) -> float:
        """Calculate quality score based on mega.md criteria."""
        score = 0.0

        # Reference count (target: 5+)
        ref_score = min(1.0, len(references) / 5.0)
        score += ref_score * 0.4

        # Content length (reasonable depth)
        content_length = len(content.split())
        length_score = min(1.0, content_length / 500.0)  # Target: 500+ words
        score += length_score * 0.3

        # Structure score (has sections, lists, etc.)
        structure_indicators = [
            bool(re.search(r'#+\s+', content)),  # Headers
            bool(re.search(r'-\s+', content)),   # Lists
            bool(re.search(r'\d+\.', content)),  # Numbered lists
            len(references) > 0                   # Has references
        ]
        structure_score = sum(structure_indicators) / len(structure_indicators)
        score += structure_score * 0.3

        return score

    def _calculate_connectivity_scores(self) -> None:
        """Calculate incoming references for all nodes."""
        for node in self.reference_graph.values():
            for ref_id in node.outgoing_refs:
                if ref_id in self.reference_graph:
                    self.reference_graph[ref_id].incoming_refs.append(node.id)

    def search_with_synergy(
        self,
        query: str,
        *,
        max_depth: int = 3,
        token_budget: Optional[int] = None,
        prioritize_quality: bool = True
    ) -> List[MegaSearchResult]:
        """
        Perform search with mega.md synergy optimization.

        Args:
            query: Search query
            max_depth: Maximum reference chain depth to explore
            token_budget: Token budget for exploration
            prioritize_quality: Prioritize quality over connectivity

        Returns:
            List of results enhanced with synergy analysis
        """
        # Perform base search
        base_results, _ = self.search_engine.search(query, limit=10)

        synergy_results = []

        for result in base_results:
            # Find reference chains
            chains = self._find_reference_chains(result, max_depth, token_budget or self.max_token_budget)

            # Calculate synergy score
            synergy_score = self._calculate_synergy_score(result, chains, prioritize_quality)

            # Generate knowledge context
            knowledge_context = self._build_knowledge_context(chains)

            # Recommend exploration paths
            recommendations = self._recommend_exploration(chains, query)

            synergy_result = MegaSearchResult(
                base_result=result,
                reference_chains=chains,
                synergy_score=synergy_score,
                knowledge_context=knowledge_context,
                recommended_exploration=recommendations
            )

            synergy_results.append(synergy_result)

        # Sort by synergy score
        synergy_results.sort(key=lambda x: x.synergy_score, reverse=True)

        return synergy_results

    def _find_reference_chains(
        self,
        result: EnhancedSearchResult,
        max_depth: int,
        token_budget: int
    ) -> List[ReferenceChain]:
        """Find reference chains starting from a search result."""
        chains = []
        visited = set()
        current_tokens = 0

        # Start with the result itself
        start_node = self._result_to_node(result)
        if not start_node:
            return chains

        # Explore chains using depth-first approach
        self._explore_chains(
            start_node,
            [],
            visited,
            max_depth,
            token_budget,
            current_tokens,
            chains
        )

        return chains

    def _result_to_node(self, result: EnhancedSearchResult) -> Optional[ReferenceNode]:
        """Convert search result to reference node."""
        result_id = result.base_result.id

        # Try direct match
        if result_id in self.reference_graph:
            return self.reference_graph[result_id]

        # Try fuzzy matching
        for node in self.reference_graph.values():
            if result_id in node.id or node.id in result_id:
                return node

        return None

    def _explore_chains(
        self,
        current_node: ReferenceNode,
        current_chain: List[ReferenceNode],
        visited: Set[str],
        max_depth: int,
        token_budget: int,
        current_tokens: int,
        chains: List[ReferenceChain]
    ) -> None:
        """Recursively explore reference chains."""
        # Check depth and token limits
        if len(current_chain) >= max_depth or current_tokens >= token_budget:
            return

        # Avoid cycles
        if current_node.id in visited:
            return

        # Add current node to chain
        new_chain = current_chain + [current_node]
        new_tokens = current_tokens + current_node.token_cost
        new_visited = visited | {current_node.id}

        # Create chain if we have minimum depth
        if len(new_chain) >= 2:
            chain = ReferenceChain(
                nodes=new_chain,
                total_depth=len(new_chain),
                total_tokens=new_tokens,
                connectivity_score=self._calculate_chain_connectivity(new_chain),
                knowledge_density=self._calculate_chain_density(new_chain)
            )
            chains.append(chain)

        # Explore outgoing references
        for ref_id in current_node.outgoing_refs:
            if ref_id in self.reference_graph:
                ref_node = self.reference_graph[ref_id]
                self._explore_chains(
                    ref_node,
                    new_chain,
                    new_visited,
                    max_depth,
                    token_budget,
                    new_tokens,
                    chains
                )

    def _calculate_chain_connectivity(self, chain: List[ReferenceNode]) -> float:
        """Calculate connectivity score for a reference chain."""
        if len(chain) < 2:
            return 0.0

        total_connections = 0
        for i in range(len(chain) - 1):
            current = chain[i]
            next_node = chain[i + 1]

            # Check if next node is referenced by current
            if next_node.id in current.outgoing_refs:
                total_connections += 1

            # Bonus for bidirectional references
            if current.id in next_node.incoming_refs:
                total_connections += 0.5

        return total_connections / (len(chain) - 1)

    def _calculate_chain_density(self, chain: List[ReferenceNode]) -> float:
        """Calculate knowledge density for a reference chain."""
        if not chain:
            return 0.0

        # Average quality score
        avg_quality = sum(node.quality_score for node in chain) / len(chain)

        # Branching factor bonus
        total_refs = sum(len(node.outgoing_refs) for node in chain)
        avg_branching = total_refs / len(chain)
        branching_bonus = min(1.0, avg_branching / self.target_branching_factor)

        return (avg_quality + branching_bonus) / 2

    def _calculate_synergy_score(
        self,
        result: EnhancedSearchResult,
        chains: List[ReferenceChain],
        prioritize_quality: bool
    ) -> float:
        """Calculate overall synergy score."""
        base_score = result.combined_score

        if not chains:
            return base_score

        # Best chain metrics
        best_chain = max(chains, key=lambda c: c.knowledge_density)

        quality_component = best_chain.knowledge_density
        connectivity_component = best_chain.connectivity_score

        # Weight components based on preference
        if prioritize_quality:
            synergy_boost = (quality_component * self.quality_weight +
                           connectivity_component * self.connectivity_weight)
        else:
            synergy_boost = (quality_component * self.connectivity_weight +
                           connectivity_component * self.quality_weight)

        # Combine with base score
        return base_score * 0.6 + synergy_boost * 0.4

    def _build_knowledge_context(self, chains: List[ReferenceChain]) -> Dict[str, Any]:
        """Build knowledge context from reference chains."""
        if not chains:
            return {}

        # Aggregate information from all chains
        all_nodes = []
        for chain in chains:
            all_nodes.extend(chain.nodes)

        # Remove duplicates while preserving order
        seen = set()
        unique_nodes = []
        for node in all_nodes:
            if node.id not in seen:
                unique_nodes.append(node)
                seen.add(node.id)

        # Calculate context metrics
        context = {
            'total_nodes': len(unique_nodes),
            'node_types': Counter(node.type for node in unique_nodes),
            'avg_quality': sum(node.quality_score for node in unique_nodes) / len(unique_nodes),
            'total_references': sum(len(node.outgoing_refs) for node in unique_nodes),
            'loop_coverage': sorted(set(node.loop_num for node in unique_nodes if node.loop_num > 0)),
            'temporal_span': self._calculate_temporal_span(unique_nodes)
        }

        return context

    def _calculate_temporal_span(self, nodes: List[ReferenceNode]) -> Optional[int]:
        """Calculate temporal span in days."""
        if not nodes:
            return None

        timestamps = [node.created_at for node in nodes if node.created_at]
        if len(timestamps) < 2:
            return None

        earliest = min(timestamps)
        latest = max(timestamps)
        span_days = (latest - earliest).days

        return span_days

    def _recommend_exploration(
        self,
        chains: List[ReferenceChain],
        original_query: str
    ) -> List[str]:
        """Recommend exploration paths based on chains."""
        recommendations = []

        if not chains:
            return recommendations

        # Find unexplored references
        explored_ids = set()
        for chain in chains:
            explored_ids.update(node.id for node in chain.nodes)

        unexplored_refs = set()
        for chain in chains:
            for node in chain.nodes:
                for ref_id in node.outgoing_refs:
                    if ref_id not in explored_ids:
                        unexplored_refs.add(ref_id)

        # Convert to readable recommendations
        for ref_id in list(unexplored_refs)[:5]:  # Limit to 5
            if ref_id in self.reference_graph:
                node = self.reference_graph[ref_id]
                recommendations.append(f"Explore {node.type}: {node.title}")

        # Add methodology-based suggestions
        if len(chains[0].nodes) < self.min_reference_depth:
            recommendations.append("Deepen reference chain (target: 3+ levels)")

        total_refs = sum(len(chain.nodes[0].outgoing_refs) for chain in chains)
        if total_refs < self.target_branching_factor:
            recommendations.append(f"Increase branching factor (current: {total_refs}, target: {self.target_branching_factor}+)")

        return recommendations

    def get_synergy_metrics(self) -> Dict[str, Any]:
        """Get overall synergy metrics for the knowledge base."""
        if not self.reference_graph:
            return {}

        nodes = list(self.reference_graph.values())

        metrics = {
            'total_nodes': len(nodes),
            'node_types': dict(Counter(node.type for node in nodes)),
            'avg_quality_score': sum(node.quality_score for node in nodes) / len(nodes),
            'avg_references_per_node': sum(len(node.outgoing_refs) for node in nodes) / len(nodes),
            'branching_factor_achievement': sum(
                1 for node in nodes if len(node.outgoing_refs) >= self.target_branching_factor
            ) / len(nodes),
            'total_reference_loops': len(set(node.loop_num for node in nodes if node.loop_num > 0)),
            'connectivity_density': self._calculate_global_connectivity()
        }

        return metrics

    def _calculate_global_connectivity(self) -> float:
        """Calculate global connectivity density."""
        if not self.reference_graph:
            return 0.0

        total_possible_connections = len(self.reference_graph) ** 2
        actual_connections = sum(len(node.incoming_refs) + len(node.outgoing_refs)
                               for node in self.reference_graph.values())

        return actual_connections / total_possible_connections if total_possible_connections > 0 else 0.0

    def optimize_token_budget(self, query_complexity: str) -> int:
        """
        Optimize token budget allocation based on query complexity.

        Args:
            query_complexity: 'simple', 'medium', 'complex'

        Returns:
            Recommended token budget
        """
        base_budget = self.max_token_budget

        complexity_multipliers = {
            'simple': 0.3,
            'medium': 0.6,
            'complex': 1.0
        }

        multiplier = complexity_multipliers.get(query_complexity, 0.6)
        return int(base_budget * multiplier)
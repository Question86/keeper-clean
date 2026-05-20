#!/usr/bin/env python3
# MODE: SCRIPT
"""Chain Cost Analyzer - Automatic token cost estimation for reference chains.

Phase 2 of TASK_0153: Analyze reference chains to estimate token costs,
calculate value scores, and compute ROI metrics.

Features:
- Parse [ref:...] tags from markdown files
- Build reference chains (depth-first traversal)
- Estimate token costs (4 chars ≈ 1 token)
- Calculate value scores based on connection graph
- Store results in KnowledgeDB chain_costs table
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

# Fix Windows console encoding for Unicode characters (TASK_0155)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from loop_guardrails import parse_ref, read_text
from knowledge_db import KnowledgeDB


REF_RE = re.compile(r"\[ref:([^\]]+)\]")


@dataclass
class ChainNode:
    """Represents a node in a reference chain."""
    path: str
    depth: int
    estimated_tokens: int
    outbound_refs: List[str]
    inbound_refs: List[str]
    
    def __hash__(self):
        return hash(self.path)


class ChainAnalyzer:
    """Analyzes reference chains and calculates token costs + ROI."""
    
    def __init__(self, workspace_root: Path, knowledge_db: Optional[KnowledgeDB] = None):
        self.workspace = workspace_root
        self.db = knowledge_db or KnowledgeDB(workspace_root)
        
        # Cache for parsed files
        self._file_cache: Dict[str, str] = {}
        self._ref_cache: Dict[str, List[str]] = {}
        
    def estimate_file_tokens(self, file_path: Path) -> int:
        """Estimate token count for a file (4 chars ≈ 1 token)."""
        try:
            content = read_text(file_path)
            return len(content) // 4
        except Exception:
            return 0
    
    def extract_references(self, file_path: Path) -> List[str]:
        """Extract all [ref:...] references from a file."""
        cache_key = str(file_path)
        if cache_key in self._ref_cache:
            return self._ref_cache[cache_key]
        
        try:
            content = read_text(file_path)
            refs = []
            
            for match in REF_RE.finditer(content):
                ref_text = match.group(1).strip()
                parsed = parse_ref(ref_text)
                target = parsed.target
                
                # Normalize path (remove leading ./ or /)
                if target.startswith('./'):
                    target = target[2:]
                elif target.startswith('/'):
                    target = target[1:]
                
                refs.append(target)
            
            self._ref_cache[cache_key] = refs
            return refs
            
        except Exception:
            return []
    
    def build_chain(
        self, 
        root_path: str, 
        max_depth: int = 3,
        visited: Optional[Set[str]] = None
    ) -> Dict[str, ChainNode]:
        """Build reference chain from root file (depth-first)."""
        if visited is None:
            visited = set()
        
        chain: Dict[str, ChainNode] = {}
        queue: List[Tuple[str, int]] = [(root_path, 0)]
        
        while queue:
            current_path, depth = queue.pop(0)
            
            if current_path in visited or depth > max_depth:
                continue
            
            visited.add(current_path)
            
            # Resolve full path
            full_path = self.workspace / current_path
            if not full_path.exists():
                continue
            
            # Extract references
            outbound = self.extract_references(full_path)
            
            # Estimate tokens
            tokens = self.estimate_file_tokens(full_path)
            
            # Create node
            node = ChainNode(
                path=current_path,
                depth=depth,
                estimated_tokens=tokens,
                outbound_refs=outbound,
                inbound_refs=[]  # Will be populated later
            )
            
            chain[current_path] = node
            
            # Add outbound refs to queue
            for ref in outbound:
                if ref not in visited:
                    queue.append((ref, depth + 1))
        
        # Build inbound reference map
        for path, node in chain.items():
            for ref in node.outbound_refs:
                if ref in chain:
                    chain[ref].inbound_refs.append(path)
        
        return chain
    
    def calculate_value_score(self, node: ChainNode, chain: Dict[str, ChainNode]) -> float:
        """Calculate value score based on connection topology.
        
        Formula:
        - Outbound connections: +0.05 per connection (up to 0.5)
        - Inbound connections: +0.10 per connection (up to 0.5)
        - Base value: 0.2 (every file has some value)
        """
        outbound_score = min(len(node.outbound_refs) * 0.05, 0.5)
        inbound_score = min(len(node.inbound_refs) * 0.10, 0.5)
        base_score = 0.2
        
        total = base_score + outbound_score + inbound_score
        return min(total, 1.0)  # Cap at 1.0
    
    def analyze_chain(self, root_path: str, max_depth: int = 3) -> Dict[str, any]:
        """Analyze a reference chain and return metrics."""
        chain = self.build_chain(root_path, max_depth)
        
        if not chain:
            return {
                'root': root_path,
                'depth': 0,
                'nodes': 0,
                'total_tokens': 0,
                'value_score': 0.0,
                'roi': 0.0
            }
        
        # Calculate total tokens
        total_tokens = sum(node.estimated_tokens for node in chain.values())
        
        # Calculate value score for root node
        root_node = chain.get(root_path)
        if root_node:
            value_score = self.calculate_value_score(root_node, chain)
            connection_count = len(root_node.outbound_refs) + len(root_node.inbound_refs)
        else:
            value_score = 0.2
            connection_count = 0
        
        # Calculate ROI
        roi = value_score / total_tokens if total_tokens > 0 else 0.0
        
        return {
            'root': root_path,
            'depth': max_depth,
            'nodes': len(chain),
            'total_tokens': total_tokens,
            'value_score': value_score,
            'connection_count': connection_count,
            'roi': roi,
            'chain': chain
        }
    
    def analyze_and_store(self, root_path: str, max_depth: int = 3) -> bool:
        """Analyze a chain and store results in KnowledgeDB."""
        metrics = self.analyze_chain(root_path, max_depth)
        
        success = self.db.record_chain_cost(
            chain_root=metrics['root'],
            depth=metrics['depth'],
            estimated_tokens=metrics['total_tokens'],
            actual_tokens=None,  # Not measured yet
            value_score=metrics['value_score'],
            connection_count=metrics['connection_count']
        )
        
        return success
    
    def analyze_workspace(
        self,
        patterns: List[str] = None,
        max_depth: int = 3
    ) -> Dict[str, any]:
        """Analyze all files matching patterns in workspace."""
        if patterns is None:
            patterns = ['reports/*.md', 'tasks/*.md', 'docs/*.md']
        
        results = {
            'analyzed': 0,
            'stored': 0,
            'failed': 0,
            'total_tokens': 0,
            'avg_roi': 0.0,
            'files': []
        }
        
        files_to_analyze = []
        for pattern in patterns:
            files_to_analyze.extend(self.workspace.glob(pattern))
        
        roi_scores = []
        
        for file_path in sorted(files_to_analyze):
            relative_path = str(file_path.relative_to(self.workspace))
            
            try:
                metrics = self.analyze_chain(relative_path, max_depth)
                results['analyzed'] += 1
                results['total_tokens'] += metrics['total_tokens']
                
                if metrics['roi'] > 0:
                    roi_scores.append(metrics['roi'])
                
                # Store in DB
                success = self.db.record_chain_cost(
                    chain_root=metrics['root'],
                    depth=metrics['depth'],
                    estimated_tokens=metrics['total_tokens'],
                    actual_tokens=None,
                    value_score=metrics['value_score'],
                    connection_count=metrics['connection_count']
                )
                
                if success:
                    results['stored'] += 1
                else:
                    results['failed'] += 1
                
                results['files'].append({
                    'path': relative_path,
                    'tokens': metrics['total_tokens'],
                    'value': metrics['value_score'],
                    'roi': metrics['roi'],
                    'stored': success
                })
                
            except Exception as e:
                results['failed'] += 1
                results['files'].append({
                    'path': relative_path,
                    'error': str(e)
                })
        
        if roi_scores:
            results['avg_roi'] = sum(roi_scores) / len(roi_scores)
        
        return results


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze reference chains and calculate ROI")
    parser.add_argument('--root', type=str, help='Root file to analyze')
    parser.add_argument('--depth', type=int, default=3, help='Max chain depth (default: 3)')
    parser.add_argument('--workspace', action='store_true', help='Analyze entire workspace')
    parser.add_argument('--patterns', nargs='+', help='File patterns to analyze')
    parser.add_argument('--top', type=int, default=10, help='Show top N by ROI')
    
    args = parser.parse_args()
    
    workspace = Path('.')
    analyzer = ChainAnalyzer(workspace)
    
    if args.workspace:
        print("=== Analyzing Workspace ===\n")
        patterns = args.patterns or ['reports/*.md', 'tasks/*.md', 'docs/*.md']
        results = analyzer.analyze_workspace(patterns, args.depth)
        
        print(f"Files analyzed: {results['analyzed']}")
        print(f"Stored in DB: {results['stored']}")
        print(f"Failed: {results['failed']}")
        print(f"Total tokens: {results['total_tokens']:,}")
        print(f"Average ROI: {results['avg_roi']:.6f}\n")
        
        # Show top files by ROI
        files_with_roi = [f for f in results['files'] if 'roi' in f and f['roi'] > 0]
        files_with_roi.sort(key=lambda x: x['roi'], reverse=True)
        
        print(f"Top {args.top} files by ROI:")
        for i, f in enumerate(files_with_roi[:args.top], 1):
            print(f"{i:2}. {f['path']}")
            print(f"    Tokens: {f['tokens']:,}, Value: {f['value']:.2f}, ROI: {f['roi']:.6f}")
        
    elif args.root:
        print(f"=== Analyzing Chain: {args.root} ===\n")
        metrics = analyzer.analyze_chain(args.root, args.depth)
        
        print(f"Root: {metrics['root']}")
        print(f"Depth: {metrics['depth']}")
        print(f"Nodes: {metrics['nodes']}")
        print(f"Total tokens: {metrics['total_tokens']:,}")
        print(f"Value score: {metrics['value_score']:.2f}")
        print(f"Connections: {metrics['connection_count']}")
        print(f"ROI: {metrics['roi']:.6f}\n")
        
        # Store
        success = analyzer.analyze_and_store(args.root, args.depth)
        print(f"Stored in DB: {'✓' if success else '✗'}")
    
    else:
        parser.print_help()
    
    analyzer.db.close()


if __name__ == '__main__':
    main()

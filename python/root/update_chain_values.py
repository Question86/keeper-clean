#!/usr/bin/env python3
"""Update chain value scores using global reference graph analysis."""

from pathlib import Path
from collections import defaultdict
from knowledge_db import KnowledgeDB
from chain_analyzer import ChainAnalyzer

def build_global_reference_graph(workspace: Path) -> tuple:
    """Build a global reference graph from all markdown files."""
    analyzer = ChainAnalyzer(workspace)
    
    outbound_refs = defaultdict(list)
    inbound_refs = defaultdict(list)
    
    # Scan all markdown files
    patterns = ['reports/*.md', 'tasks/*.md', 'docs/*.md', 'archive/*.md']
    all_files = []
    for pattern in patterns:
        all_files.extend(workspace.glob(pattern))
    
    print(f"Scanning {len(all_files)} files for references...")
    
    for file_path in all_files:
        relative_path = str(file_path.relative_to(workspace))
        refs = analyzer.extract_references(file_path)
        
        if refs:
            outbound_refs[relative_path] = refs
            for ref in refs:
                inbound_refs[ref].append(relative_path)
    
    return outbound_refs, inbound_refs

def calculate_enhanced_value_score(
    path: str,
    outbound: dict,
    inbound: dict
) -> tuple:
    """Calculate enhanced value score with proper inbound/outbound counts."""
    out_count = len(outbound.get(path, []))
    in_count = len(inbound.get(path, []))
    
    # Enhanced formula:
    # - Base: 0.2
    # - Outbound: +0.03 per ref (max +0.4 at 13 refs)
    # - Inbound: +0.08 per ref (max +0.4 at 5 refs)
    
    out_score = min(out_count * 0.03, 0.4)
    in_score = min(in_count * 0.08, 0.4)
    base = 0.2
    
    value = base + out_score + in_score
    connection_count = out_count + in_count
    
    return min(value, 1.0), connection_count

def main():
    workspace = Path('.')
    db = KnowledgeDB(workspace)
    
    # Build global graph
    print("=== Building Global Reference Graph ===")
    outbound, inbound = build_global_reference_graph(workspace)
    
    print(f"\nFiles with outbound refs: {len(outbound)}")
    print(f"Files with inbound refs: {len(inbound)}")
    
    # Get all chains from DB
    print("\n=== Updating Chain Values ===")
    chains = db.get_chain_costs(order_by='tokens', limit=10000)
    print(f"Found {len(chains)} chains in DB")
    
    updated = 0
    for chain in chains:
        path = chain['chain_root']
        
        # Calculate new value score
        new_value, new_connections = calculate_enhanced_value_score(
            path, outbound, inbound
        )
        
        # Update if different
        old_value = chain.get('value_score', 0.0)
        old_connections = chain.get('connection_count', 0)
        
        if abs(new_value - old_value) > 0.01 or new_connections != old_connections:
            success = db.record_chain_cost(
                chain_root=path,
                depth=chain['depth'],
                estimated_tokens=chain['estimated_tokens'],
                actual_tokens=chain.get('actual_tokens'),
                value_score=new_value,
                connection_count=new_connections
            )
            
            if success:
                updated += 1
    
    print(f"Updated {updated} chains")
    
    # Show top chains by new ROI
    print("\n=== Top 20 Chains by ROI (Updated) ===")
    top_chains = db.get_chain_costs(order_by='roi', limit=20)
    
    for i, c in enumerate(top_chains, 1):
        print(f"{i:2}. {c['chain_root']}")
        print(f"    ROI={c['roi']:.6f}, Value={c['value_score']:.2f}, "
              f"Connections={c['connection_count']}, Tokens={c['estimated_tokens']:,}")
    
    # Show most connected files
    print("\n=== Top 20 Most Connected Files ===")
    top_connected = db.get_chain_costs(order_by='value', limit=20)
    
    for i, c in enumerate(top_connected, 1):
        print(f"{i:2}. {c['chain_root']}")
        print(f"    Value={c['value_score']:.2f}, Connections={c['connection_count']}, "
              f"ROI={c['roi']:.6f}, Tokens={c['estimated_tokens']:,}")
    
    db.close()

if __name__ == '__main__':
    main()

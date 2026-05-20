#!/usr/bin/env python3
"""
AI Breadcrumb Trail Analysis

Extracts and analyzes AI decision paths from breadcrumb trails.
Provides insights into the AI's logical navigation through the codebase.

Usage:
    python analyze_breadcrumb_trails.py [--file FILE] [--context CONTEXT] [--limit N]
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone
from typing import Dict, List, Any

from ai_breadcrumb_tracker import get_breadcrumb_tracker


def analyze_breadcrumb_trails(workspace_root: Path, target_file: str = None, source_context: str = None, limit: int = 100):
    """Analyze breadcrumb trails and provide insights."""

    tracker = get_breadcrumb_tracker(workspace_root)
    breadcrumbs = tracker.get_breadcrumb_trail(target_file=target_file, limit=limit)

    if not breadcrumbs:
        print("No breadcrumb trails found.")
        return

    print("🗺️  AI Breadcrumb Trail Analysis")
    print("=" * 50)
    print(f"Total breadcrumbs: {len(breadcrumbs)}")
    print()

    # Filter by source context if specified
    if source_context:
        breadcrumbs = [bc for bc in breadcrumbs if bc.source_context == source_context]
        print(f"Filtered by context '{source_context}': {len(breadcrumbs)} breadcrumbs")
        print()

    # Basic statistics
    operations = Counter(bc.operation for bc in breadcrumbs)
    contexts = Counter(bc.source_context for bc in breadcrumbs)
    files = Counter(bc.target_file for bc in breadcrumbs)

    print("📊 Operation Breakdown:")
    for op, count in operations.most_common():
        print(f"  {op}: {count}")
    print()

    print("🎯 Top Source Contexts:")
    for context, count in contexts.most_common(10):
        print(f"  {context}: {count}")
    print()

    print("📁 Most Accessed Files:")
    for file, count in files.most_common(10):
        print(f"  {file}: {count}")
    print()

    # Decision path analysis
    print("🔍 Decision Path Analysis:")

    # Group by source context to see navigation patterns
    context_flows = defaultdict(lambda: defaultdict(int))
    for bc in breadcrumbs:
        context_flows[bc.source_context][bc.target_file] += 1

    print("Top navigation patterns (Context → File):")
    for context, targets in context_flows.items():
        if len(targets) > 1:  # Only show contexts that access multiple files
            top_targets = sorted(targets.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"  {context}:")
            for file, count in top_targets:
                print(f"    → {file} ({count} times)")

    print()

    # Temporal analysis
    print("⏰ Temporal Analysis:")
    timestamps = [datetime.fromisoformat(bc.timestamp.replace('Z', '+00:00')) for bc in breadcrumbs]
    if timestamps:
        earliest = min(timestamps)
        latest = max(timestamps)
        duration = latest - earliest

        print(f"  Time span: {duration}")
        print(f"  From: {earliest}")
        print(f"  To: {latest}")

        # Activity by hour
        hours = Counter(ts.hour for ts in timestamps)
        peak_hour = hours.most_common(1)[0]
        print(f"  Peak activity hour: {peak_hour[0]:02d}:00 ({peak_hour[1]} operations)")

    print()

    # Recent activity
    print("🕐 Recent Breadcrumb Trail (last 10):")
    for bc in breadcrumbs[:10]:
        print(f"  {bc.timestamp} | {bc.operation} | {bc.target_file}")
        print(f"    ← {bc.source_context}")
    print()

    # Extract unique decision paths
    print("🧭 Unique Decision Paths:")
    paths = []
    current_path = []

    # Sort breadcrumbs by timestamp
    sorted_bc = sorted(breadcrumbs, key=lambda x: x.timestamp)

    for bc in sorted_bc:
        if not current_path or bc.source_context != current_path[-1]['target']:
            if current_path:
                paths.append(current_path)
            current_path = []

        current_path.append({
            'source': bc.source_context,
            'target': bc.target_file,
            'operation': bc.operation,
            'time': bc.timestamp
        })

    if current_path:
        paths.append(current_path)

    # Show longest paths
    if paths:
        longest_path = max(paths, key=len)
        print(f"Longest decision path ({len(longest_path)} steps):")
        for i, step in enumerate(longest_path):
            print(f"  {i+1}. {step['source']} →[{step['operation']}]→ {step['target']}")
            print(f"     at {step['time']}")

    return {
        'total_breadcrumbs': len(breadcrumbs),
        'operations': dict(operations),
        'contexts': dict(contexts),
        'files': dict(files),
        'paths': len(paths)
    }


def extract_breadcrumbs_from_files(workspace_root: Path):
    """Extract breadcrumbs embedded in files."""

    tracker = get_breadcrumb_tracker(workspace_root)

    print("📂 Extracting breadcrumbs from files...")

    extracted = []
    for file_path in workspace_root.rglob('*'):
        if file_path.is_file() and file_path.suffix in ['.py', '.md', '.json']:
            try:
                file_breadcrumbs = tracker.extract_breadcrumbs_from_file(file_path)
                if file_breadcrumbs:
                    extracted.extend(file_breadcrumbs)
                    print(f"  {file_path.relative_to(workspace_root)}: {len(file_breadcrumbs)} breadcrumbs")
            except Exception as e:
                print(f"  Error reading {file_path}: {e}")

    print(f"\n✅ Extracted {len(extracted)} breadcrumbs from files")

    # Save to analysis file
    analysis_file = workspace_root / "breadcrumb_analysis.json"
    with open(analysis_file, 'w') as f:
        json.dump({
            'extracted_at': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            'total_extracted': len(extracted),
            'breadcrumbs': [bc.to_dict() for bc in extracted]
        }, f, indent=2)

    print(f"💾 Analysis saved to: {analysis_file}")
    return extracted


def main():
    parser = argparse.ArgumentParser(description="Analyze AI breadcrumb trails")
    parser.add_argument('--workspace', type=Path, default=Path.cwd(),
                       help='Workspace root directory')
    parser.add_argument('--file', help='Filter by target file')
    parser.add_argument('--context', help='Filter by source context')
    parser.add_argument('--limit', type=int, default=100,
                       help='Limit number of breadcrumbs to analyze')
    parser.add_argument('--extract-from-files', action='store_true',
                       help='Extract breadcrumbs embedded in files')

    args = parser.parse_args()

    if args.extract_from_files:
        extract_breadcrumbs_from_files(args.workspace)
    else:
        analyze_breadcrumb_trails(
            workspace_root=args.workspace,
            target_file=args.file,
            source_context=args.context,
            limit=args.limit
        )


if __name__ == "__main__":
    main()
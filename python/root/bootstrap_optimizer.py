#!/usr/bin/env python3
"""Bootstrap Optimizer - Identify files to exclude based on ROI analysis.

Phase 2-3 bridge for TASK_0153: Analyze which files can be safely excluded
from bootstrap to reduce token usage while maintaining knowledge quality.
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple
import json

# Fix Windows console encoding for Unicode characters (TASK_0155)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from knowledge_db import KnowledgeDB


class BootstrapOptimizer:
    """Optimize bootstrap file selection using ROI and relevance metrics."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.db = KnowledgeDB(workspace)
        
    def get_bootstrap_candidates(self) -> List[Dict]:
        """Get all files that might be loaded during bootstrap."""
        # Typical bootstrap patterns
        patterns = [
            'reports/report_*.md',
            'tasks/task_*.md',
            'docs/*.md',
            'archive/ARCHIV_*.md'
        ]
        
        candidates = []
        for pattern in patterns:
            for file in self.workspace.glob(pattern):
                rel_path = str(file.relative_to(self.workspace))
                candidates.append(rel_path)
        
        return candidates
    
    def analyze_exclusion_candidates(
        self,
        roi_threshold: float = 0.000010,
        token_threshold: int = 100000
    ) -> Dict:
        """Identify files that are good candidates for exclusion.
        
        Exclusion criteria:
        - Low ROI (< threshold)
        - High token cost (> threshold)
        - Low connection count (< 2)
        """
        all_chains = self.db.get_chain_costs(order_by='tokens', limit=10000)
        
        exclusion_candidates = []
        keep_files = []
        huge_files = []
        
        total_tokens = 0
        excluded_tokens = 0
        
        for chain in all_chains:
            total_tokens += chain['estimated_tokens']
            
            roi = chain.get('roi') or 0.0
            tokens = chain['estimated_tokens']
            connections = chain.get('connection_count', 0)
            value = chain.get('value_score', 0.2)
            
            # Criteria for exclusion
            is_low_roi = roi < roi_threshold
            is_huge = tokens > token_threshold
            is_disconnected = connections < 2
            
            if is_low_roi and (is_huge or is_disconnected):
                exclusion_candidates.append({
                    'path': chain['chain_root'],
                    'tokens': tokens,
                    'roi': roi,
                    'value': value,
                    'connections': connections,
                    'reason': self._get_exclusion_reason(is_low_roi, is_huge, is_disconnected)
                })
                excluded_tokens += tokens
            else:
                keep_files.append(chain['chain_root'])
            
            if tokens > token_threshold:
                huge_files.append({
                    'path': chain['chain_root'],
                    'tokens': tokens,
                    'roi': roi,
                    'connections': connections
                })
        
        # Calculate savings
        savings_percent = (excluded_tokens / total_tokens * 100) if total_tokens > 0 else 0
        
        return {
            'total_files': len(all_chains),
            'excluded_count': len(exclusion_candidates),
            'keep_count': len(keep_files),
            'total_tokens': total_tokens,
            'excluded_tokens': excluded_tokens,
            'savings_percent': savings_percent,
            'exclusion_candidates': exclusion_candidates,
            'huge_files': huge_files[:20],  # Top 20 huge files
            'criteria': {
                'roi_threshold': roi_threshold,
                'token_threshold': token_threshold
            }
        }
    
    def _get_exclusion_reason(
        self,
        low_roi: bool,
        huge: bool,
        disconnected: bool
    ) -> str:
        """Generate human-readable exclusion reason."""
        reasons = []
        if low_roi:
            reasons.append('low ROI')
        if huge:
            reasons.append('huge file')
        if disconnected:
            reasons.append('poorly connected')
        return ' + '.join(reasons)
    
    def generate_exclusion_report(
        self,
        output_path: Path = None
    ) -> Dict:
        """Generate comprehensive exclusion analysis report."""
        if output_path is None:
            output_path = self.workspace / 'reports' / 'bootstrap_exclusion_analysis.json'
        
        # Run analysis with multiple thresholds
        analyses = []
        
        thresholds = [
            (0.000005, 200000, "Conservative (5e-6 ROI, 200k tokens)"),
            (0.000010, 150000, "Moderate (1e-5 ROI, 150k tokens)"),
            (0.000020, 100000, "Aggressive (2e-5 ROI, 100k tokens)"),
        ]
        
        for roi_thresh, token_thresh, desc in thresholds:
            result = self.analyze_exclusion_candidates(roi_thresh, token_thresh)
            result['description'] = desc
            analyses.append(result)
        
        report = {
            'generated_at': Path('.').resolve().name,
            'analyses': analyses,
            'recommendations': self._generate_recommendations(analyses)
        }
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2))
        
        return report
    
    def _generate_recommendations(self, analyses: List[Dict]) -> Dict:
        """Generate actionable recommendations from analyses."""
        # Use moderate strategy as baseline
        moderate = analyses[1] if len(analyses) > 1 else analyses[0]
        
        recommendations = {
            'primary_strategy': 'Moderate',
            'expected_savings': f"{moderate['savings_percent']:.1f}%",
            'files_to_exclude': moderate['excluded_count'],
            'token_reduction': f"{moderate['excluded_tokens']:,} tokens",
            'actions': []
        }
        
        # Add specific actions
        if moderate['savings_percent'] > 30:
            recommendations['actions'].append(
                'Implement exclusion list in session pack generation'
            )
        
        if moderate['huge_files']:
            recommendations['actions'].append(
                'Consider lazy-loading for huge files (>100k tokens)'
            )
        
        if moderate['excluded_count'] > 50:
            recommendations['actions'].append(
                'Create .bootstrap_exclude file with exclusion patterns'
            )
        
        return recommendations
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimize bootstrap file selection")
    parser.add_argument('--report', action='store_true', help='Generate full report')
    parser.add_argument('--roi', type=float, default=0.000010, help='ROI threshold')
    parser.add_argument('--tokens', type=int, default=150000, help='Token threshold')
    parser.add_argument('--top', type=int, default=30, help='Show top N exclusion candidates')
    
    args = parser.parse_args()
    
    optimizer = BootstrapOptimizer(Path('.'))
    
    if args.report:
        print("=== Generating Bootstrap Exclusion Report ===\n")
        report = optimizer.generate_exclusion_report()
        
        for analysis in report['analyses']:
            print(f"\n{analysis['description']}:")
            print(f"  Files to exclude: {analysis['excluded_count']}/{analysis['total_files']}")
            print(f"  Token savings: {analysis['excluded_tokens']:,} / {analysis['total_tokens']:,}")
            print(f"  Savings: {analysis['savings_percent']:.1f}%")
        
        print(f"\n=== Recommendations ===")
        recs = report['recommendations']
        print(f"Strategy: {recs['primary_strategy']}")
        print(f"Expected savings: {recs['expected_savings']}")
        print(f"Files to exclude: {recs['files_to_exclude']}")
        print(f"Token reduction: {recs['token_reduction']}")
        print(f"\nActions:")
        for action in recs['actions']:
            print(f"  - {action}")
        
        print(f"\nReport saved to: reports/bootstrap_exclusion_analysis.json")
    
    else:
        print(f"=== Bootstrap Exclusion Analysis ===")
        print(f"ROI threshold: {args.roi}")
        print(f"Token threshold: {args.tokens:,}\n")
        
        result = optimizer.analyze_exclusion_candidates(args.roi, args.tokens)
        
        print(f"Total files: {result['total_files']}")
        print(f"Files to exclude: {result['excluded_count']} ({result['excluded_count']/result['total_files']*100:.1f}%)")
        print(f"Files to keep: {result['keep_count']}")
        print(f"\nTotal tokens: {result['total_tokens']:,}")
        print(f"Excluded tokens: {result['excluded_tokens']:,}")
        print(f"Token savings: {result['savings_percent']:.1f}%\n")
        
        print(f"Top {args.top} Exclusion Candidates:")
        for i, candidate in enumerate(result['exclusion_candidates'][:args.top], 1):
            print(f"{i:2}. {candidate['path']}")
            print(f"    Tokens: {candidate['tokens']:,}, ROI: {candidate['roi']:.6f}, "
                  f"Connections: {candidate['connections']}")
            print(f"    Reason: {candidate['reason']}")
        
        if result['huge_files']:
            print(f"\n=== Top 10 Huge Files ===")
            for i, huge in enumerate(result['huge_files'][:10], 1):
                print(f"{i:2}. {huge['path']}")
                print(f"    Tokens: {huge['tokens']:,}, ROI: {huge['roi']:.6f}, "
                      f"Connections: {huge['connections']}")
    
    optimizer.close()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
FILE RELEVANCE SCORER
TASK: TASK_0149 Phase 1
PURPOSE: Calculate file relevance scores for token optimization

Design: docs/CONTEXTUAL_RELEVANCE_GATEWAY.md
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass
import math


@dataclass
class FileRelevance:
    """Relevance score components for a single file."""
    path: str
    ref_count: int
    ref_popularity_score: float
    recency_score: float
    semantic_similarity_score: float
    structural_importance_score: float
    final_score: float
    
    def to_dict(self) -> dict:
        return {
            'path': self.path,
            'ref_count': self.ref_count,
            'ref_popularity_score': self.ref_popularity_score,
            'recency_score': self.recency_score,
            'semantic_similarity_score': self.semantic_similarity_score,
            'structural_importance_score': self.structural_importance_score,
            'final_score': self.final_score,
        }


class FileRelevanceScorer:
    """Calculate relevance scores for workspace files."""
    
    # Files that MUST always be included (structural importance = 1.0)
    SKELETON_FILES = {
        "PROJECT_TECH_BASELINE.md",
        "NEURAL_CORTEX.md",
        "NEU.md",
        "Alt.md",
        "current.json",
        "_LOOP_GATE.md",
        "docs/OPS_PROTOCOLS.md",
        "mega.md",  # Core methodology
    }
    
    # Recency decay constant (days)
    RECENCY_DECAY_DAYS = 30
    
    def __init__(self, workspace_root: Path, verbose: bool = False):
        self.workspace_root = Path(workspace_root)
        self.ref_pattern = re.compile(r'\[ref:([^\|\]]+)')
        self.verbose = verbose
    
    def count_references(self) -> Dict[str, int]:
        """Count incoming [ref:...] pointers to each file."""
        ref_counts = defaultdict(int)
        
        # Scan all markdown files
        for md_file in self.workspace_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                refs = self.ref_pattern.findall(content)
                
                for ref_path in refs:
                    # Normalize path (remove leading ./ or /)
                    ref_path = ref_path.strip().lstrip('./')
                    ref_counts[ref_path] += 1
            
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Error reading {md_file}: {e}")
                continue
        
        return dict(ref_counts)
    
    def normalize_ref_counts(self, ref_counts: Dict[str, int]) -> Dict[str, float]:
        """Normalize reference counts to 0.0-1.0 scale."""
        if not ref_counts:
            return {}
        
        max_refs = max(ref_counts.values())
        if max_refs == 0:
            return {path: 0.0 for path in ref_counts}
        
        return {
            path: count / max_refs
            for path, count in ref_counts.items()
        }
    
    def calculate_recency_scores(self, file_paths: List[str]) -> Dict[str, float]:
        """Calculate recency scores based on modification time."""
        recency_scores = {}
        now = datetime.now(timezone.utc)
        
        for path_str in file_paths:
            file_path = self.workspace_root / path_str
            
            if not file_path.exists():
                recency_scores[path_str] = 0.0
                continue
            
            # Get modification time
            mtime = datetime.fromtimestamp(
                file_path.stat().st_mtime,
                tz=timezone.utc
            )
            
            # Calculate age in days
            age_days = (now - mtime).total_seconds() / 86400
            
            # Exponential decay: score = exp(-age / decay_constant)
            recency_score = math.exp(-age_days / self.RECENCY_DECAY_DAYS)
            recency_scores[path_str] = recency_score
        
        return recency_scores
    
    def calculate_structural_importance(self, file_paths: List[str]) -> Dict[str, float]:
        """Calculate structural importance scores."""
        importance = {}
        
        for path in file_paths:
            # SKELETON files always get 1.0
            if any(skeleton in path for skeleton in self.SKELETON_FILES):
                importance[path] = 1.0
            
            # Task/report files get medium importance
            elif path.startswith('tasks/') or path.startswith('reports/'):
                importance[path] = 0.5
            
            # Archive files get low importance (historical)
            elif path.startswith('archive/'):
                importance[path] = 0.2
            
            # Default: neutral
            else:
                importance[path] = 0.3
        
        return importance
    
    def calculate_final_scores(
        self,
        ref_scores: Dict[str, float],
        recency_scores: Dict[str, float],
        semantic_scores: Optional[Dict[str, float]] = None,
        structural_scores: Optional[Dict[str, float]] = None
    ) -> Dict[str, FileRelevance]:
        """Combine all score components into final relevance scores."""
        
        # Get all unique file paths
        all_files = set(ref_scores.keys()) | set(recency_scores.keys())
        if semantic_scores:
            all_files |= set(semantic_scores.keys())
        if structural_scores:
            all_files |= set(structural_scores.keys())
        
        # If structural scores not provided, calculate them
        if structural_scores is None:
            structural_scores = self.calculate_structural_importance(list(all_files))
        
        # If semantic scores not provided, use neutral (0.5)
        if semantic_scores is None:
            semantic_scores = {path: 0.5 for path in all_files}
        
        # Get reference counts (for metadata)
        ref_counts_raw = self.count_references()
        
        # Calculate final scores
        file_relevances = {}
        
        for file_path in all_files:
            ref_score = ref_scores.get(file_path, 0.0)
            recency = recency_scores.get(file_path, 0.0)
            semantic = semantic_scores.get(file_path, 0.5)
            structural = structural_scores.get(file_path, 0.3)
            
            # Weighted combination
            final_score = (
                0.40 * ref_score +
                0.30 * recency +
                0.20 * semantic +
                0.10 * structural
            )
            
            # SKELETON override: force 1.0
            if any(skeleton in file_path for skeleton in self.SKELETON_FILES):
                final_score = 1.0
            
            file_relevances[file_path] = FileRelevance(
                path=file_path,
                ref_count=ref_counts_raw.get(file_path, 0),
                ref_popularity_score=ref_score,
                recency_score=recency,
                semantic_similarity_score=semantic,
                structural_importance_score=structural,
                final_score=final_score
            )
        
        return file_relevances
    
    def generate_relevance_report(
        self,
        file_relevances: Dict[str, FileRelevance],
        output_path: Optional[Path] = None
    ) -> str:
        """Generate markdown report of relevance scores."""
        
        # Sort by final score (descending)
        sorted_files = sorted(
            file_relevances.values(),
            key=lambda x: x.final_score,
            reverse=True
        )
        
        report = ["# FILE RELEVANCE REPORT", ""]
        report.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        report.append(f"Total files: {len(sorted_files)}")
        report.append("")
        
        # Statistics
        scores = [f.final_score for f in sorted_files]
        avg_score = sum(scores) / len(scores) if scores else 0
        report.append(f"Average relevance: {avg_score:.3f}")
        report.append("")
        
        # Top files
        report.append("## TOP 20 FILES BY RELEVANCE")
        report.append("")
        report.append("| Rank | Score | Refs | File |")
        report.append("|------|-------|------|------|")
        
        for i, file_rel in enumerate(sorted_files[:20], 1):
            report.append(
                f"| {i:2d} | {file_rel.final_score:.3f} | "
                f"{file_rel.ref_count:3d} | {file_rel.path} |"
            )
        
        report.append("")
        
        # Low relevance files (candidates for filtering)
        low_relevance = [f for f in sorted_files if f.final_score < 0.4]
        report.append(f"## LOW RELEVANCE FILES (< 0.4): {len(low_relevance)}")
        report.append("")
        
        if low_relevance:
            report.append("| Score | Refs | File |")
            report.append("|-------|------|------|")
            
            for file_rel in low_relevance[:30]:  # Show first 30
                report.append(
                    f"| {file_rel.final_score:.3f} | "
                    f"{file_rel.ref_count:3d} | {file_rel.path} |"
                )
        
        report_text = "\n".join(report)
        
        # Write to file if path provided
        if output_path:
            output_path.write_text(report_text, encoding='utf-8')
        
        return report_text
    
    def run_analysis(self) -> Dict[str, FileRelevance]:
        """Run complete relevance analysis."""
        if self.verbose:
            print("Counting file references...")
        ref_counts = self.count_references()
        if self.verbose:
            print(f"   Found {len(ref_counts)} referenced files")
        
        if self.verbose:
            print("Normalizing reference counts...")
        ref_scores = self.normalize_ref_counts(ref_counts)
        
        if self.verbose:
            print("Calculating recency scores...")
        all_files = list(ref_counts.keys())
        recency_scores = self.calculate_recency_scores(all_files)
        
        if self.verbose:
            print("Calculating structural importance...")
        structural_scores = self.calculate_structural_importance(all_files)
        
        if self.verbose:
            print("Computing final scores...")
        file_relevances = self.calculate_final_scores(
            ref_scores,
            recency_scores,
            None,  # No semantic scores yet (Phase 3)
            structural_scores
        )
        
        if self.verbose:
            print(f"Analysis complete: {len(file_relevances)} files scored")
        return file_relevances


if __name__ == "__main__":
    workspace = Path(r"D:\Keeper-Clean-Loop1")
    scorer = FileRelevanceScorer(workspace, verbose=True)
    
    print("FILE RELEVANCE SCORER - TASK_0149 Phase 1")
    print("=" * 60)
    print()
    
    relevances = scorer.run_analysis()
    
    print()
    print("Generating report...")
    report_path = workspace / "reports" / "file_relevance_scores_L80.md"
    report_text = scorer.generate_relevance_report(relevances, report_path)
    
    print(f"Report saved: {report_path}")
    print()
    print("=" * 60)

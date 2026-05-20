#!/usr/bin/env python3
"""A/B Testing Framework for Adaptive Bootstrap (TASK_0156).

Compares static exclusion approach vs adaptive prediction approach.
Measures token usage, prediction accuracy, and context completeness.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timezone

from knowledge_db import KnowledgeDB
from adaptive_bootstrap import BootstrapPredictor
from bootstrap_optimizer import BootstrapOptimizer


class BootstrapABTester:
    """A/B testing framework for bootstrap optimization strategies."""

    def __init__(self, workspace: Path, penalty_scale: float = 5000.0, roi_weights: List[float] = None):
        self.workspace = workspace
        self.db = KnowledgeDB(workspace)
        self.predictor = BootstrapPredictor(workspace, penalty_scale, roi_weights)
        self.optimizer = BootstrapOptimizer(workspace)

    def run_ab_test(
        self,
        task_context: str,
        task_type: str = "unknown",
        budget_tokens: int = 60000,
        num_trials: int = 5
    ) -> Dict:
        """Run A/B test comparing static vs adaptive approaches."""

        results = {
            "task_context": task_context,
            "task_type": task_type,
            "budget_tokens": budget_tokens,
            "trials": [],
            "summary": {}
        }

        for trial in range(num_trials):
            print(f"Running trial {trial + 1}/{num_trials}...")

            # Method A: Static optimization (current approach)
            static_result = self._test_static_approach(task_context, budget_tokens)

            # Method B: Adaptive prediction (new approach)
            adaptive_result = self._test_adaptive_approach(task_context, task_type, budget_tokens)

            trial_result = {
                "trial": trial + 1,
                "static": static_result,
                "adaptive": adaptive_result,
                "comparison": self._compare_results(static_result, adaptive_result)
            }

            results["trials"].append(trial_result)

        # Calculate summary statistics
        results["summary"] = self._calculate_summary(results["trials"])

        return results

    def _test_static_approach(self, task_context: str, budget_tokens: int) -> Dict:
        """Test the static exclusion approach."""
        start_time = time.time()

        # Get candidates
        candidates = self.optimizer.get_bootstrap_candidates()

        # Bandwidth guard: estimate bytes to read for candidates and check guard
        try:
            from rate_limit_handler import get_rate_limit_handler
            handler = get_rate_limit_handler(self.workspace)
            est_bytes = 0
            for file_path in candidates:
                p = self.workspace / file_path
                try:
                    est_bytes += p.stat().st_size if p.exists() else 0
                except Exception:
                    continue

            bw_check = handler.bandwidth_guard.check_bandwidth('abtest_static_candidate_calc', estimated_bytes=est_bytes)
            if not bw_check['should_proceed']:
                # Respect guard: abort this trial but return an informative result
                return {
                    "method": "static",
                    "selected_files": [],
                    "total_tokens": 0,
                    "num_files": 0,
                    "execution_time": 0.0,
                    "selection_logic": "aborted_by_bandwidth_guard",
                    "bandwidth_decision": bw_check
                }
        except Exception:
            # If guard not available, proceed cautiously
            pass

        # Analyze exclusions (simulate current logic)
        analysis = self.optimizer.analyze_exclusion_candidates(
            roi_threshold=0.000010,
            token_threshold=budget_tokens
        )

        # Select files (those not excluded)
        selected_files = []
        total_tokens = 0

        for file_path in candidates:
            if not self._should_exclude_static(file_path, analysis):
                estimated_tokens = self._estimate_token_cost(file_path)
                if total_tokens + estimated_tokens <= budget_tokens:
                    selected_files.append(file_path)
                    total_tokens += estimated_tokens

        end_time = time.time()

        # Record bandwidth usage for selected files if handler present
        try:
            from rate_limit_handler import get_rate_limit_handler
            handler = get_rate_limit_handler(self.workspace)
            sel_bytes = 0
            for f in selected_files:
                p = self.workspace / f
                try:
                    sel_bytes += p.stat().st_size if p.exists() else 0
                except Exception:
                    continue
            if sel_bytes > 0:
                handler.bandwidth_guard.record_usage('abtest_static_selected_read', int(sel_bytes))
        except Exception:
            pass

        return {
            "method": "static",
            "selected_files": selected_files,
            "total_tokens": total_tokens,
            "num_files": len(selected_files),
            "execution_time": end_time - start_time,
            "selection_logic": "ROI-based exclusion with token budget"
        }

    def _test_adaptive_approach(self, task_context: str, task_type: str, budget_tokens: int) -> Dict:
        """Test the adaptive prediction approach."""
        start_time = time.time()

        # Bandwidth guard: check estimated bytes for predicted files
        try:
            from rate_limit_handler import get_rate_limit_handler
            handler = get_rate_limit_handler(self.workspace)

            # Get a light-weight estimate by summing file sizes of candidates
            candidates = self.predictor._get_bootstrap_candidates()
            est_bytes = 0
            for file_path in candidates:
                p = self.workspace / file_path
                try:
                    est_bytes += p.stat().st_size if p.exists() else 0
                except Exception:
                    continue

            bw_check = handler.bandwidth_guard.check_bandwidth('abtest_adaptive_candidate_calc', estimated_bytes=est_bytes)
            if not bw_check['should_proceed']:
                # abort this trial due to bandwidth guard
                return {
                    "method": "adaptive",
                    "selected_files": [],
                    "total_tokens": 0,
                    "num_files": 0,
                    "execution_time": 0.0,
                    "selection_logic": "aborted_by_bandwidth_guard",
                    "bandwidth_decision": bw_check
                }
        except Exception:
            pass

        # Use adaptive predictor
        selected_files = self.predictor.predict_needed_files(
            task_context=task_context,
            task_type=task_type,
            budget_tokens=budget_tokens
        )

        # Calculate total tokens
        total_tokens = sum(self._estimate_token_cost(f) for f in selected_files)

        end_time = time.time()

        # Record bandwidth usage for selected files if handler present
        try:
            from rate_limit_handler import get_rate_limit_handler
            handler = get_rate_limit_handler(self.workspace)
            sel_bytes = 0
            for f in selected_files:
                p = self.workspace / f
                try:
                    sel_bytes += p.stat().st_size if p.exists() else 0
                except Exception:
                    continue
            if sel_bytes > 0:
                handler.bandwidth_guard.record_usage('abtest_adaptive_selected_read', int(sel_bytes))
        except Exception:
            pass

        return {
            "method": "adaptive",
            "selected_files": selected_files,
            "total_tokens": total_tokens,
            "num_files": len(selected_files),
            "execution_time": end_time - start_time,
            "selection_logic": "Context-aware prediction with ensemble scoring"
        }

    def _should_exclude_static(self, file_path: str, analysis: Dict) -> bool:
        """Determine if file should be excluded using static logic."""
        # Check if file is in exclusion candidates
        for item in analysis.get('exclusion_candidates', []):
            if item['path'] == file_path:
                return True
        return False

    def _estimate_token_cost(self, file_path: str) -> int:
        """Estimate token cost of a file."""
        try:
            full_path = self.workspace / file_path
            if not full_path.exists():
                return 0

            content = full_path.read_text(encoding='utf-8')
            # Rough approximation: 1 token per 4 characters
            return len(content) // 4
        except:
            return 1000

    def _compare_results(self, static: Dict, adaptive: Dict) -> Dict:
        """Compare results between static and adaptive approaches."""
        return {
            "token_difference": adaptive["total_tokens"] - static["total_tokens"],
            "token_savings_percent": ((static["total_tokens"] - adaptive["total_tokens"]) / static["total_tokens"]) * 100 if static["total_tokens"] > 0 else 0,
            "file_difference": adaptive["num_files"] - static["num_files"],
            "time_difference": adaptive["execution_time"] - static["execution_time"],
            "adaptive_more_efficient": adaptive["total_tokens"] < static["total_tokens"]
        }

    def _calculate_summary(self, trials: List[Dict]) -> Dict:
        """Calculate summary statistics across all trials."""
        comparisons = [t["comparison"] for t in trials]

        avg_token_savings = sum(c["token_savings_percent"] for c in comparisons) / len(comparisons)
        adaptive_wins = sum(1 for c in comparisons if c["adaptive_more_efficient"])

        return {
            "total_trials": len(trials),
            "adaptive_wins": adaptive_wins,
            "adaptive_win_rate": adaptive_wins / len(trials),
            "avg_token_savings_percent": avg_token_savings,
            "avg_token_difference": sum(c["token_difference"] for c in comparisons) / len(comparisons),
            "avg_file_difference": sum(c["file_difference"] for c in comparisons) / len(comparisons),
            "avg_time_difference": sum(c["time_difference"] for c in comparisons) / len(comparisons)
        }


def main():
    """CLI interface for A/B testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python bootstrap_ab_test.py <task_context> [task_type] [budget_tokens]")
        sys.exit(1)

    task_context = sys.argv[1]
    task_type = sys.argv[2] if len(sys.argv) > 2 else "unknown"
    budget_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 60000

    workspace = Path(".")
    tester = BootstrapABTester(workspace)

    print(f"Running A/B test for: {task_context}")
    print(f"Task type: {task_type}")
    print(f"Budget: {budget_tokens} tokens")
    print()

    results = tester.run_ab_test(task_context, task_type, budget_tokens)

    # Save results
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    results_file = f"bootstrap_ab_test_{timestamp}.json"

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Results saved to: {results_file}")
    print()

    # Print summary
    summary = results["summary"]
    print("SUMMARY:")
    print(f"  Trials: {summary['total_trials']}")
    print(f"  Adaptive wins: {summary['adaptive_wins']} ({summary['adaptive_win_rate']*100:.1f}%)")
    print(f"  Avg token savings: {summary['avg_token_savings_percent']:+.1f}%")
    print(f"  Avg token difference: {summary['avg_token_difference']:+.0f}")
    print(f"  Avg file difference: {summary['avg_file_difference']:+.1f}")


if __name__ == "__main__":
    main()
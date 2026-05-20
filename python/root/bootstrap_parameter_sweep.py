#!/usr/bin/env python3
"""Parameter Sweep for Adaptive Bootstrap Stabilization (TASK_0207 Phase A)."""

import json
from pathlib import Path
from datetime import datetime, timezone
import statistics
from bootstrap_ab_test import BootstrapABTester

def run_sweep():
    """Run the parameter sweep."""

    workspace = Path.cwd()

    # Parameter grids
    penalty_scales = [3000.0, 5000.0, 7000.0]
    roi_weights = [
        [0.4, 0.05, 0.30, 0.20, 0.05],
        [0.35, 0.10, 0.30, 0.20, 0.05],
        [0.25, 0.20, 0.30, 0.20, 0.05],
    ]

    results = {
        "sweep_started": datetime.now(timezone.utc).isoformat(),
        "trials": []
    }

    trial_id = 0
    total_trials = len(penalty_scales) * len(roi_weights) * 10

    for penalty_scale in penalty_scales:
        for roi_weight_set in roi_weights:
            print(f"Testing penalty_scale={penalty_scale}, roi_weights={roi_weight_set}")

            for trial in range(10):
                trial_id += 1
                print(f"  Trial {trial_id}/{total_trials}...")

                tester = BootstrapABTester(workspace, penalty_scale, roi_weight_set)
                test_result = tester.run_ab_test(
                    task_context=f"Trial {trial_id}",
                    task_type="parameter_sweep",
                    budget_tokens=60000,
                    num_trials=1
                )

                trial_data = test_result["trials"][0] if test_result["trials"] else {}

                results["trials"].append({
                    "trial_id": trial_id,
                    "parameters": {"penalty_scale": penalty_scale, "roi_weights": roi_weight_set},
                    "static": trial_data.get("static", {}),
                    "adaptive": trial_data.get("adaptive", {}),
                    "comparison": trial_data.get("comparison", {})
                })

    # Simple summary
    adaptive_wins = sum(1 for t in results["trials"]
                       if t["adaptive"].get("total_tokens", 0) < t["static"].get("total_tokens", 0)
                       and t["adaptive"].get("selection_logic") != "aborted_by_bandwidth_guard")

    results["summary"] = {
        "total_trials": len(results["trials"]),
        "adaptive_wins": adaptive_wins,
        "win_rate": adaptive_wins / len(results["trials"]) if results["trials"] else 0
    }

    # Save results
    output_file = workspace / "bootstrap_parameter_sweep_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Sweep completed. Results saved to {output_file}")
    print(f"Adaptive wins: {adaptive_wins}/{len(results['trials'])}")

if __name__ == "__main__":
    run_sweep()
#!/usr/bin/env python3
"""
Mathematical Testing Framework for Deep Field Piercing Exploration

This framework provides systematic testing of mathematical axioms for stability
and convergence in optimization and neural network dynamics.

Axioms Tested:
- Axiom 2: Timescale Separation (Borkar's Two-Timescale Convergence)
- Axiom 3: Contraction Stability (ISS - Input-to-State Stability)
- Axiom 4: Mutual Information Finiteness (PAC-Bayes Bounds)
- Stability Valve: Active Stability Recovery

The framework explores parameter spaces to identify stable regions and
failure boundaries for deep field optimization.
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
import os
from pathlib import Path
import sys

# Add the first_scripts directory to path to import axioms
sys.path.append(str(Path(__file__).parent / "docs" / "First_research_mega.md" / "first_scripts"))

# Import axiom functions
from axio2_py import verify_timescale_separation
from axio3_py import assert_contraction_stability
from axio_4 import assert_mi_finiteness
# from The_Stability_Capped_Optimizer_Wrapper import StabilityValve  # TODO: Implement complete StabilityValve

class MathematicalTestingFramework:
    """Framework for testing mathematical stability axioms across parameter spaces."""

    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.results_dir = self.workspace / "mathematical_testing_results"
        self.results_dir.mkdir(exist_ok=True)

    def define_parameter_spaces(self) -> Dict[str, List[float]]:
        """Define parameter ranges for deep field exploration."""
        return {
            'learning_rates': [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1],
            'spectral_radii': [0.1, 0.5, 0.8, 0.95, 0.99, 1.01, 1.1],
            'noise_scales': [1e-12, 1e-8, 1e-4, 0.01, 0.1, 1.0],
            'contraction_thresholds': [0.5, 0.8, 0.95, 0.99, 1.0, 1.05],
            'snr_thresholds': [1e3, 1e4, 1e5, 1e6, 1e7]
        }

    def test_timescale_separation(self, lr_theta: float, lr_lambda: float) -> Dict:
        """Test Axiom 2: Timescale separation between optimizers."""
        try:
            model = torch.nn.Linear(10, 10)
            opt_theta = torch.optim.Adam(model.parameters(), lr=lr_theta)
            opt_lambda = torch.optim.Adam(model.parameters(), lr=lr_lambda)

            verify_timescale_separation(opt_theta, opt_lambda, 0)

            return {
                'passed': True,
                'ratio': lr_lambda / lr_theta,
                'error': None
            }
        except AssertionError as e:
            return {
                'passed': False,
                'ratio': lr_lambda / lr_theta,
                'error': str(e)
            }

    def test_contraction_stability(self, spectral_radius: float, c_max: float = 0.99) -> Dict:
        """Test Axiom 3: Contraction stability of operators."""
        try:
            class SimpleOp(torch.nn.Module):
                def __init__(self, scale):
                    super().__init__()
                    self.W = torch.nn.Parameter(torch.eye(2) * scale)
                def forward(self, z, x=None):
                    return z @ self.W

            op = SimpleOp(spectral_radius)
            z_init = torch.randn(1, 2)

            assert_contraction_stability(op, z_init, None, c_max)

            return {
                'passed': True,
                'spectral_radius': spectral_radius,
                'c_max': c_max,
                'error': None
            }
        except AssertionError as e:
            return {
                'passed': False,
                'spectral_radius': spectral_radius,
                'c_max': c_max,
                'error': str(e)
            }

    def test_mi_finiteness(self, z_magnitude: float, noise_std: float) -> Dict:
        """Test Axiom 4: Mutual information finiteness."""
        try:
            z_mean = torch.ones(10) * z_magnitude
            assert_mi_finiteness(z_mean, noise_std)

            snr = torch.norm(z_mean) / (noise_std + 1e-8)

            return {
                'passed': True,
                'snr': snr.item(),
                'z_magnitude': z_magnitude,
                'noise_std': noise_std,
                'error': None
            }
        except AssertionError as e:
            snr = torch.norm(z_mean) / (noise_std + 1e-8)
            return {
                'passed': False,
                'snr': snr.item(),
                'z_magnitude': z_magnitude,
                'noise_std': noise_std,
                'error': str(e)
            }

    def test_stability_valve(self, initial_rho: float, gradient_scale: float, c_max: float = 0.99) -> Dict:
        """Test Stability Valve recovery mechanism. (TODO: Implement when StabilityValve is complete)"""
        return {
            'passed': False,
            'error': 'StabilityValve not implemented'
        }

    def run_comprehensive_tests(self) -> Dict:
        """Run comprehensive testing across all parameter spaces."""
        params = self.define_parameter_spaces()
        results = {
            'timescale_separation': [],
            'contraction_stability': [],
            'mi_finiteness': [],
            # 'stability_valve': [],  # TODO: Implement when StabilityValve is complete
            'summary': {}
        }

        # Test Timescale Separation
        print("Testing Timescale Separation...")
        for lr_theta in params['learning_rates'][:3]:  # Subset for efficiency
            for lr_lambda in params['learning_rates']:
                if lr_lambda >= lr_theta:
                    continue
                result = self.test_timescale_separation(lr_theta, lr_lambda)
                results['timescale_separation'].append(result)

        # Test Contraction Stability
        print("Testing Contraction Stability...")
        for rho in params['spectral_radii']:
            for c_max in params['contraction_thresholds'][:3]:
                result = self.test_contraction_stability(rho, c_max)
                results['contraction_stability'].append(result)

        # Test MI Finiteness
        print("Testing MI Finiteness...")
        for noise in params['noise_scales']:
            for snr_thresh in params['snr_thresholds'][:3]:
                z_mag = snr_thresh * noise
                result = self.test_mi_finiteness(z_mag, noise)
                results['mi_finiteness'].append(result)

        # Test Stability Valve
        # print("Testing Stability Valve...")
        # for rho in [0.95, 0.98, 0.99]:
        #     for grad_scale in [0.1, 0.5, 1.0]:
        #         result = self.test_stability_valve(rho, grad_scale)
        #         results['stability_valve'].append(result)

        # Generate summary
        results['summary'] = self.generate_summary(results)

        return results

    def generate_summary(self, results: Dict) -> Dict:
        """Generate summary statistics from test results."""
        summary = {}

        for test_name, test_results in results.items():
            if test_name == 'summary':
                continue

            passed = sum(1 for r in test_results if r.get('passed', False))
            total = len(test_results)
            pass_rate = passed / total if total > 0 else 0

            summary[test_name] = {
                'total_tests': total,
                'passed': passed,
                'failed': total - passed,
                'pass_rate': pass_rate
            }

        return summary

    def save_results(self, results: Dict, filename: str = "comprehensive_test_results.json"):
        """Save test results to file."""
        output_path = self.results_dir / filename
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {output_path}")

    def identify_stable_regions(self, results: Dict) -> Dict:
        """Identify parameter regions that consistently pass tests."""
        stable_regions = {
            'timescale_separation': {
                'max_safe_ratio': 0.0,
                'stable_lr_combinations': []
            },
            'contraction_stability': {
                'max_stable_spectral_radius': 0.0,
                'stable_cmax_values': []
            },
            'mi_finiteness': {
                'min_safe_noise': float('inf'),
                'stable_snr_ranges': []
            },
            # 'stability_valve': {
            #     'effective_recovery_rate': 0.0
            # }
        }

        # Analyze timescale separation
        for result in results['timescale_separation']:
            if result['passed']:
                ratio = result['ratio']
                stable_regions['timescale_separation']['max_safe_ratio'] = max(
                    stable_regions['timescale_separation']['max_safe_ratio'], ratio
                )
                stable_regions['timescale_separation']['stable_lr_combinations'].append(
                    (result.get('lr_theta'), result.get('lr_lambda'))
                )

        # Analyze contraction stability
        for result in results['contraction_stability']:
            if result['passed']:
                rho = result['spectral_radius']
                c_max = result['c_max']
                stable_regions['contraction_stability']['max_stable_spectral_radius'] = max(
                    stable_regions['contraction_stability']['max_stable_spectral_radius'], rho
                )
                if c_max not in stable_regions['contraction_stability']['stable_cmax_values']:
                    stable_regions['contraction_stability']['stable_cmax_values'].append(c_max)

        # Analyze MI finiteness
        for result in results['mi_finiteness']:
            if result['passed']:
                noise = result['noise_std']
                stable_regions['mi_finiteness']['min_safe_noise'] = min(
                    stable_regions['mi_finiteness']['min_safe_noise'], noise
                )
                snr = result['snr']
                stable_regions['mi_finiteness']['stable_snr_ranges'].append(snr)

        # Analyze stability valve
        # valve_results = results['stability_valve']
        # if valve_results:
        #     recovery_count = sum(1 for r in valve_results if r.get('passed', False))
        #     stable_regions['stability_valve']['effective_recovery_rate'] = recovery_count / len(valve_results)

        return stable_regions

def main():
    """Main execution function."""
    framework = MathematicalTestingFramework()

    print("Starting Mathematical Testing Framework for Deep Field Piercing Exploration")
    print("=" * 80)

    # Run comprehensive tests
    results = framework.run_comprehensive_tests()

    # Identify stable regions
    stable_regions = framework.identify_stable_regions(results)

    # Save results
    framework.save_results(results)
    framework.save_results(stable_regions, "stable_regions_analysis.json")

    # Print summary
    print("\nTest Summary:")
    for test_name, stats in results['summary'].items():
        print("{}: {}/{} passed ({:.1%})".format(test_name, stats['passed'], stats['total_tests'], stats['pass_rate']))

    print("\nStable Regions Identified:")
    print("- Max safe LR ratio: {:.3f}".format(stable_regions['timescale_separation']['max_safe_ratio']))
    print("- Max stable spectral radius: {:.3f}".format(stable_regions['contraction_stability']['max_stable_spectral_radius']))
    print("- Min safe noise scale: {:.2e}".format(stable_regions['mi_finiteness']['min_safe_noise']))
    # print("- Stability valve recovery rate: {:.1%}".format(stable_regions['stability_valve']['effective_recovery_rate']))

    print("\nFramework execution completed successfully.")

if __name__ == "__main__":
    main()

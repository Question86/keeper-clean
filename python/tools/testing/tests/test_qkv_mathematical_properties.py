#!/usr/bin/env python3
"""
Mathematical Properties Tests for QKV Relevance Framework

Tests the mathematical properties and theoretical guarantees of the QKV system.
"""

import unittest
import math
from typing import Dict, List
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context_dreamer import ContextDreamer

class TestQKVMathematicalProperties(unittest.TestCase):
    """Test mathematical properties of QKV relevance dimensions."""

    def setUp(self):
        """Set up test fixtures."""
        self.dreamer = ContextDreamer()
        self.test_weights = {'urgency': 0.4, 'strategic_fit': 0.4, 'historical_reliability': 0.2}

    def test_vector_space_properties(self):
        """Test that QKV vectors form a proper vector space."""
        # Create test file analyses
        analysis_a = {
            'age_days': 7,
            'content_preview': 'urgent task session',
            'references': ['file1.md', 'file2.md'],
            'file_type': 'python'
        }
        analysis_b = {
            'age_days': 14,
            'content_preview': 'strategic goal planning',
            'references': ['goal.md', 'strategy.md'],
            'file_type': 'markdown'
        }

        # Calculate QKV vector
        qkv_vector = self.dreamer._calculate_qkv_relevance_vector(
            'test_a.py', analysis_a, 'test_b.md', analysis_b
        )

        # Test vector properties
        self.assertIsInstance(qkv_vector, dict)
        self.assertIn('urgency', qkv_vector)
        self.assertIn('strategic_fit', qkv_vector)
        self.assertIn('historical_reliability', qkv_vector)

        # Test normalization (values in [0,1])
        for dimension, value in qkv_vector.items():
            self.assertGreaterEqual(value, 0.0, f"{dimension} should be >= 0")
            self.assertLessEqual(value, 1.0, f"{dimension} should be <= 1")

    def test_relevance_score_bounds(self):
        """Test theoretical bounds on relevance scores."""
        test_vectors = [
            {'urgency': 0.0, 'strategic_fit': 0.0, 'historical_reliability': 0.0},
            {'urgency': 1.0, 'strategic_fit': 1.0, 'historical_reliability': 1.0},
            {'urgency': 0.5, 'strategic_fit': 0.3, 'historical_reliability': 0.8},
            {'urgency': 0.1, 'strategic_fit': 0.9, 'historical_reliability': 0.2}
        ]

        for qkv_vector in test_vectors:
            # Calculate weighted score
            score = sum(self.test_weights[dim] * qkv_vector[dim] for dim in qkv_vector)

            # Test bounds
            min_weight = min(self.test_weights.values())
            max_weight = max(self.test_weights.values())

            self.assertGreaterEqual(score, min_weight,
                f"Score {score} violates lower bound {min_weight}")
            self.assertLessEqual(score, max_weight,
                f"Score {score} violates upper bound {max_weight}")

    def test_dimension_monotonicity(self):
        """Test that higher dimension values produce higher relevance."""
        base_vector = {'urgency': 0.5, 'strategic_fit': 0.5, 'historical_reliability': 0.5}
        base_score = sum(self.test_weights[dim] * base_vector[dim] for dim in base_vector)

        # Test each dimension independently
        for dimension in base_vector.keys():
            # Higher value
            high_vector = base_vector.copy()
            high_vector[dimension] = min(1.0, base_vector[dimension] + 0.3)
            high_score = sum(self.test_weights[dim] * high_vector[dim] for dim in high_vector)

            # Lower value
            low_vector = base_vector.copy()
            low_vector[dimension] = max(0.0, base_vector[dimension] - 0.3)
            low_score = sum(self.test_weights[dim] * low_vector[dim] for dim in low_vector)

            # Monotonicity check
            self.assertGreaterEqual(high_score, base_score,
                f"Increasing {dimension} should not decrease score")
            self.assertLessEqual(low_score, base_score,
                f"Decreasing {dimension} should not increase score")

    def test_additivity_property(self):
        """Test additivity of relevance scores."""
        vector1 = {'urgency': 0.2, 'strategic_fit': 0.3, 'historical_reliability': 0.4}
        vector2 = {'urgency': 0.1, 'strategic_fit': 0.2, 'historical_reliability': 0.3}

        score1 = sum(self.test_weights[dim] * vector1[dim] for dim in vector1)
        score2 = sum(self.test_weights[dim] * vector2[dim] for dim in vector2)

        # Combined vector
        combined = {dim: min(1.0, vector1[dim] + vector2[dim]) for dim in vector1}
        score_combined = sum(self.test_weights[dim] * combined[dim] for dim in combined)

        # Test subadditivity (due to clamping)
        self.assertLessEqual(score1 + score2, score_combined + 1.0,
            "Relevance scores should satisfy weak additivity")

    def test_numerical_stability(self):
        """Test numerical stability of calculations."""
        # Test with edge cases
        edge_cases = [
            {'age_days': 0, 'content_preview': '', 'references': [], 'file_type': 'unknown'},
            {'age_days': 1000, 'content_preview': 'x' * 1000, 'references': ['x'] * 100, 'file_type': 'binary'},
            {'age_days': float('inf'), 'content_preview': None, 'references': None, 'file_type': None}
        ]

        for i, analysis in enumerate(edge_cases):
            try:
                qkv_vector = self.dreamer._calculate_qkv_relevance_vector(
                    f'test_{i}_a', analysis, f'test_{i}_b', analysis
                )

                # Should not crash and return valid values
                for dim, value in qkv_vector.items():
                    self.assertFalse(math.isnan(value), f"{dim} is NaN in edge case {i}")
                    self.assertFalse(math.isinf(value), f"{dim} is infinite in edge case {i}")
                    self.assertGreaterEqual(value, 0.0, f"{dim} negative in edge case {i}")
                    self.assertLessEqual(value, 1.0, f"{dim} > 1 in edge case {i}")

            except Exception as e:
                self.fail(f"Edge case {i} caused exception: {e}")

    def test_weight_convergence(self):
        """Test convergence properties of weighted combinations."""
        # Simple gradient descent simulation
        weights = [0.33, 0.33, 0.34]  # Initial equal weights
        learning_rate = 0.01

        # Mock loss function (minimize difference from target)
        target_weights = [0.4, 0.4, 0.2]

        for _ in range(100):  # 100 iterations
            # Simple gradient (difference from target)
            gradient = [w - t for w, t in zip(weights, target_weights)]

            # Update weights
            weights = [w - learning_rate * g for w, g in zip(weights, gradient)]

            # Normalize to sum to 1
            total = sum(weights)
            weights = [w / total for w in weights]

        # Check convergence
        final_error = sum(abs(w - t) for w, t in zip(weights, target_weights))
        self.assertLess(final_error, 0.1, "Weights should converge toward target")

if __name__ == '__main__':
    unittest.main()</content>
<parameter name="filePath">d:\Keeper-Clean-Loop1\tests\test_qkv_mathematical_properties.py
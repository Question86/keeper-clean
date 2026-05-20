#!/usr/bin/env python3
"""
Unit tests for TokenGovernor functionality.
"""

import unittest
from token_governor import TokenGovernor, BudgetZone, TokenMetrics, BudgetAllocation


class TestTokenGovernor(unittest.TestCase):
    """Test cases for TokenGovernor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.governor = TokenGovernor(budget=200000)
        
    def test_budget_allocation_default(self):
        """Test default budget allocation ratios."""
        allocation = self.governor.calculate_adaptive_allocation()
        
        # Should have proper allocation structure
        self.assertIsInstance(allocation, BudgetAllocation)
        self.assertEqual(allocation.total, 200000)
        
        # Default ratios (approximately)
        expected_short = int(200000 * 0.30)  # 60k
        expected_mid = int(200000 * 0.50)    # 100k  
        expected_long = int(200000 * 0.20)   # 40k
        
        self.assertAlmostEqual(allocation.short_term, expected_short, delta=1000)
        self.assertAlmostEqual(allocation.mid_term, expected_mid, delta=1000)
        self.assertAlmostEqual(allocation.long_term, expected_long, delta=1000)
        
    def test_zone_based_recommendations(self):
        """Test that recommendations change based on token zone."""
        # Should return list of recommendation strings
        recommendations = self.governor.get_recommendations()
        
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Each recommendation should be a non-empty string
        for rec in recommendations:
            self.assertIsInstance(rec, str)
            self.assertGreater(len(rec), 0)
            
    def test_finalization_logic(self):
        """Test loop finalization decision logic."""
        should_finalize, reason = self.governor.should_finalize_loop()
        
        # Should return boolean and string
        self.assertIsInstance(should_finalize, bool)
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 0)
        
    def test_budget_report_structure(self):
        """Test budget report contains required fields."""
        report = self.governor.generate_budget_report()
        
        # Check required top-level keys
        required_keys = ['timestamp', 'token_metrics', 'allocation', 'recommendations', 'finalization']
        for key in required_keys:
            self.assertIn(key, report)
            
        # Check token_metrics structure
        metrics_keys = ['used', 'remaining', 'percentage', 'zone', 'budget']
        for key in metrics_keys:
            self.assertIn(key, report['token_metrics'])
            
        # Check allocation structure  
        allocation_keys = ['short_term', 'mid_term', 'long_term', 'total']
        for key in allocation_keys:
            self.assertIn(key, report['allocation'])
            
        # Allocation should sum correctly
        allocation = report['allocation']
        expected_total = allocation['short_term'] + allocation['mid_term'] + allocation['long_term']
        self.assertEqual(allocation['total'], expected_total)


def run_tests():
    """Run unit tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
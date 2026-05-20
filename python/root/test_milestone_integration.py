#!/usr/bin/env python3
"""
Unit tests for MilestoneKnowledgeIntegrator functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from milestone_knowledge_integration import (
    MilestoneKnowledgeIntegrator, 
    PlanningHorizon, 
    PriorityWeights,
    EnhancedSearchResult
)
from knowledge_db import SearchResult
from token_governor import BudgetZone


class TestMilestoneKnowledgeIntegrator(unittest.TestCase):
    """Test cases for MilestoneKnowledgeIntegrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('milestone_knowledge_integration.KnowledgeDB'), \
             patch('milestone_knowledge_integration.TokenGovernor'):
            self.integrator = MilestoneKnowledgeIntegrator(
                workspace_root=Path("."),
                token_budget=200000
            )
        
    def test_classify_planning_horizon_by_loop(self):
        """Test planning horizon classification based on loop numbers."""
        # Mock context
        self.integrator.get_current_loop_context = Mock(return_value={
            "loop_number": 10,
            "status": "ACTIVE",
            "token_usage": 50.0,
            "token_zone": BudgetZone.SAFE
        })
        
        # Test short-term (current loop)
        result_current = Mock()
        result_current.loop_num = 10
        result_current.content = "current task work"
        
        horizon = self.integrator.classify_planning_horizon(result_current)
        self.assertEqual(horizon, PlanningHorizon.SHORT_TERM)
        
        # Test mid-term (recent loops)
        result_recent = Mock()
        result_recent.loop_num = 7
        result_recent.content = "milestone implementation"
        
        horizon = self.integrator.classify_planning_horizon(result_recent)
        self.assertEqual(horizon, PlanningHorizon.MID_TERM)
        
        # Test long-term (older loops)
        result_old = Mock() 
        result_old.loop_num = 1
        result_old.content = "architecture foundation"
        
        horizon = self.integrator.classify_planning_horizon(result_old)
        self.assertEqual(horizon, PlanningHorizon.LONG_TERM)
        
    def test_classify_planning_horizon_by_content(self):
        """Test planning horizon classification based on content patterns."""
        self.integrator.get_current_loop_context = Mock(return_value={
            "loop_number": 10,
            "status": "ACTIVE", 
            "token_usage": 50.0,
            "token_zone": BudgetZone.SAFE
        })
        
        # Test short-term patterns
        result_urgent = Mock()
        result_urgent.loop_num = None
        result_urgent.content = "urgent task needs immediate attention"
        
        horizon = self.integrator.classify_planning_horizon(result_urgent)
        self.assertEqual(horizon, PlanningHorizon.SHORT_TERM)
        
        # Test mid-term patterns
        result_milestone = Mock()
        result_milestone.loop_num = None
        result_milestone.content = "milestone goal implementation planned"
        
        horizon = self.integrator.classify_planning_horizon(result_milestone)
        self.assertEqual(horizon, PlanningHorizon.MID_TERM)
        
        # Test long-term patterns
        result_strategic = Mock()
        result_strategic.loop_num = None 
        result_strategic.content = "strategic architecture future roadmap"
        
        horizon = self.integrator.classify_planning_horizon(result_strategic)
        self.assertEqual(horizon, PlanningHorizon.LONG_TERM)
        
    def test_calculate_priority_score(self):
        """Test priority score calculation with different factors."""
        self.integrator.get_current_loop_context = Mock(return_value={
            "loop_number": 10,
            "status": "ACTIVE",
            "token_usage": 50.0,
            "token_zone": BudgetZone.SAFE
        })
        
        # Test high-relevance short-term result
        result = Mock()
        result.relevance = 0.9
        result.loop_num = 10
        result.content = "test content"
        
        priority = self.integrator.calculate_priority_score(
            result, PlanningHorizon.SHORT_TERM
        )
        
        # Should be weighted by short-term factor (0.6) plus recency boost
        expected = 0.9 * 0.6  # Base calculation
        self.assertGreater(priority, expected)  # Should have recency boost
        self.assertLessEqual(priority, 1.0)    # Should be clamped
        
    def test_estimate_token_cost(self):
        """Test token cost estimation."""
        result = Mock()
        result.content = "This is test content " * 20  # ~100 characters
        
        cost = self.integrator.estimate_token_cost(result)
        
        # Should be roughly 25 tokens (100 chars / 4) + 50 overhead = 75
        self.assertGreater(cost, 50)
        self.assertLess(cost, 200)  # More generous upper bound
        
    def test_priority_weights_configuration(self):
        """Test that priority weights are configurable and sum logically."""
        weights = PriorityWeights()
        
        # Test default values
        self.assertEqual(weights.short_term, 0.6)
        self.assertEqual(weights.mid_term, 0.3) 
        self.assertEqual(weights.long_term, 0.1)
        
        # Test sum adds up to 1.0 (roughly)
        total = weights.short_term + weights.mid_term + weights.long_term
        self.assertAlmostEqual(total, 1.0, places=1)
        
    def test_acquisition_recommendation_logic(self):
        """Test acquisition recommendation generation."""
        # Mock enhanced result
        enhanced_result = Mock()
        enhanced_result.priority_score = 0.85
        enhanced_result.token_cost_estimate = 100
        
        recommendation = self.integrator.get_acquisition_recommendation(enhanced_result)
        
        # Should recommend high priority acquisition
        self.assertIn("HIGH", recommendation)
        self.assertIn("🟢", recommendation)


def run_tests():
    """Run unit tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
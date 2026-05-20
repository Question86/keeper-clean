#!/usr/bin/env python3
"""
Test suite for Global Events Observer and Prediction System

Tests the mathematical scoring algorithms, data persistence, and API integration.
"""

import pytest
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import shutil

# Import the modules to test
from global_events_observer import GlobalEventsObserver, observe_global_event, create_event_prediction, get_global_events_report
from prediction_scorer import PredictionScorer

class TestPredictionScorer:
    """Test the mathematical scoring system."""

    def setup_method(self):
        self.scorer = PredictionScorer()
        self.project_context = {
            'strategic_keywords': ['ai', 'automation', 'technology', 'security'],
            'risk_keywords': ['crisis', 'threat', 'disruption'],
            'opportunity_keywords': ['breakthrough', 'innovation', 'growth']
        }

    def test_reliability_scoring(self):
        """Test reliability score calculation."""
        # Trusted source
        score = self.scorer.calculate_reliability_score('trusted_news', 0.8, 0.9)
        assert 0.7 <= score <= 1.0

        # Unknown source
        score = self.scorer.calculate_reliability_score('unknown', 0.5, 0.5)
        assert 0.3 <= score <= 0.7

    def test_urgency_scoring(self):
        """Test urgency score calculation."""
        # High urgency event
        score = self.scorer.calculate_urgency_score('geopolitical_crisis', 'global', 0.8)
        assert 0.8 <= score <= 1.0

        # Low urgency event
        score = self.scorer.calculate_urgency_score('scientific_discovery', 'local', 0.2)
        assert 0.0 <= score <= 0.4

    def test_strategic_relevance(self):
        """Test strategic relevance calculation."""
        # High relevance tags
        score = self.scorer.calculate_strategic_relevance(['ai', 'automation', 'security'], self.project_context)
        assert score > 0.5

        # Low relevance tags
        score = self.scorer.calculate_strategic_relevance(['sports', 'entertainment'], self.project_context)
        assert score < 0.3

    def test_composite_scoring(self):
        """Test composite score calculation."""
        composite = self.scorer.calculate_composite_score(0.8, 0.7, 0.6)
        expected = (0.8 * 0.4) + (0.7 * 0.3) + (0.6 * 0.3)  # 0.32 + 0.21 + 0.18 = 0.71
        assert abs(composite - expected) < 0.001

class TestGlobalEventsObserver:
    """Test the main observer system."""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.observer = GlobalEventsObserver(str(self.temp_dir))

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_observe_event(self):
        """Test event observation."""
        event_id = self.observer.observe_event(
            title="Test Event",
            description="A test global event",
            category="technological",
            source="trusted_news",
            tags=["ai", "automation"],
            impact_scale="regional"
        )

        assert event_id.startswith("event_")

        # Check event was saved
        events = self.observer._load_events()
        assert len(events) == 1
        assert events[0].title == "Test Event"
        assert events[0].composite_score > 0

    def test_create_prediction(self):
        """Test prediction creation."""
        # First create an event
        event_id = self.observer.observe_event(
            title="Base Event",
            description="Foundation event",
            category="economic",
            source="government",
            tags=["economy"]
        )

        # Create prediction
        prediction_id = self.observer.create_prediction(
            title="Test Prediction",
            description="A test prediction",
            related_event_ids=[event_id],
            predicted_outcome="Positive outcome expected",
            confidence_level=0.8,
            timeframe_days=30
        )

        assert prediction_id.startswith("pred_")

        # Check prediction was saved
        predictions = self.observer._load_predictions()
        assert len(predictions) == 1
        assert predictions[0].title == "Test Prediction"
        assert predictions[0].event_ids == [event_id]

    def test_get_high_priority_events(self):
        """Test filtering high priority events."""
        # Create events with different scores
        self.observer.observe_event(
            title="High Priority",
            description="Important event",
            category="geopolitical",
            source="trusted_news",
            tags=["ai", "security"],
            impact_scale="global"
        )

        self.observer.observe_event(
            title="Low Priority",
            description="Minor event",
            category="scientific_discovery",
            source="unknown",
            tags=["science"],
            impact_scale="local"
        )

        high_priority = self.observer.get_high_priority_events(0.7)
        assert len(high_priority) >= 1  # At least the high priority one

    def test_generate_report(self):
        """Test report generation."""
        # Create some test data
        self.observer.observe_event(
            title="Report Test Event",
            description="For report testing",
            category="technological",
            source="academic",
            tags=["ai"]
        )

        report = self.observer.generate_report()
        assert "Global Events Observation Report" in report
        assert "Report Test Event" in report

def test_api_functions():
    """Test the API wrapper functions."""
    # These would need a proper test environment, but we can test the imports
    from global_events_observer import observe_global_event, create_event_prediction, get_global_events_report

    # Test that functions are callable (would need temp workspace in real test)
    assert callable(observe_global_event)
    assert callable(create_event_prediction)
    assert callable(get_global_events_report)

if __name__ == "__main__":
    # Run basic tests
    scorer = PredictionScorer()
    project_context = {
        'strategic_keywords': ['ai', 'automation', 'technology'],
        'risk_keywords': ['crisis', 'threat'],
        'opportunity_keywords': ['breakthrough', 'innovation']
    }

    # Test scoring
    scores = scorer.score_prediction({
        'source': 'trusted_news',
        'category': 'technological',
        'impact_scale': 'global',
        'tags': ['ai', 'automation'],
        'time_sensitivity': 0.8,
        'evidence_strength': 0.9,
        'historical_accuracy': 0.85
    }, project_context)

    print("Scoring Test Results:")
    print(f"Reliability: {scores['reliability']:.3f}")
    print(f"Urgency: {scores['urgency']:.3f}")
    print(f"Strategic Relevance: {scores['strategic_relevance']:.3f}")
    print(f"Composite: {scores['composite']:.3f}")

    explanation = scorer.get_scoring_explanation(scores)
    print(f"Explanation: {explanation}")

    print("Basic tests completed successfully!")
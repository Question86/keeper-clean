#!/usr/bin/env python3
"""
Prediction Scoring System

Mathematical scoring for global event predictions based on:
- Reliability: Source credibility and historical accuracy
- Urgency: Time-sensitive impact assessment
- Strategic Relevance: Alignment with project goals

Composite Score Formula: C = (R × 0.4) + (U × 0.3) + (S × 0.3)
"""

from typing import Dict, List, Any
import math

class PredictionScorer:
    """Mathematical scoring system for event predictions and observations."""

    def __init__(self):
        # Weight factors for composite scoring
        self.weights = {
            'reliability': 0.4,
            'urgency': 0.3,
            'strategic_relevance': 0.3
        }

        # Source credibility mapping
        self.source_credibility = {
            'trusted_news': 0.9,
            'government_official': 0.8,
            'academic_research': 0.85,
            'industry_expert': 0.7,
            'social_media': 0.3,
            'anonymous': 0.2,
            'unknown': 0.5
        }

        # Event category urgency mapping
        self.category_urgency = {
            'geopolitical_crisis': 0.95,
            'economic_disruption': 0.85,
            'technological_breakthrough': 0.75,
            'environmental_disaster': 0.90,
            'health_pandemic': 0.95,
            'social_unrest': 0.80,
            'cyber_attack': 0.85,
            'market_crash': 0.88,
            'regulatory_change': 0.70,
            'scientific_discovery': 0.65
        }

        # Impact scale multipliers
        self.impact_multipliers = {
            'global': 1.0,
            'continental': 0.9,
            'regional': 0.7,
            'national': 0.5,
            'local': 0.3,
            'sector_specific': 0.4
        }

    def calculate_reliability_score(self, source: str, historical_accuracy: float = 0.5,
                                  evidence_strength: float = 0.5) -> float:
        """
        Calculate reliability score based on source credibility and evidence.

        Args:
            source: Source identifier
            historical_accuracy: Historical accuracy of source (0-1)
            evidence_strength: Strength of supporting evidence (0-1)

        Returns:
            Reliability score (0-1)
        """
        base_credibility = self.source_credibility.get(source.lower(), 0.5)

        # Weighted combination of credibility, historical accuracy, and evidence
        reliability = (base_credibility * 0.5) + (historical_accuracy * 0.3) + (evidence_strength * 0.2)

        return min(1.0, max(0.0, reliability))

    def calculate_urgency_score(self, event_category: str, impact_scale: str,
                               time_sensitivity: float = 0.5) -> float:
        """
        Calculate urgency score based on category, impact, and time sensitivity.

        Args:
            event_category: Type of event
            impact_scale: Scale of impact
            time_sensitivity: How time-critical the event is (0-1)

        Returns:
            Urgency score (0-1)
        """
        base_urgency = self.category_urgency.get(event_category.lower(), 0.5)
        impact_multiplier = self.impact_multipliers.get(impact_scale.lower(), 0.5)

        # Apply impact scale and time sensitivity
        urgency = base_urgency * impact_multiplier * (0.7 + 0.3 * time_sensitivity)

        return min(1.0, max(0.0, urgency))

    def calculate_strategic_relevance(self, tags: List[str], project_context: Dict[str, Any]) -> float:
        """
        Calculate strategic relevance based on alignment with project goals.

        Args:
            tags: Event tags/keywords
            project_context: Project strategic context

        Returns:
            Strategic relevance score (0-1)
        """
        strategic_keywords = project_context.get('strategic_keywords', [
            'ai', 'automation', 'technology', 'innovation', 'security',
            'intelligence', 'prediction', 'analysis', 'development'
        ])

        risk_keywords = project_context.get('risk_keywords', [
            'disruption', 'crisis', 'threat', 'vulnerability', 'competition'
        ])

        opportunity_keywords = project_context.get('opportunity_keywords', [
            'breakthrough', 'advancement', 'growth', 'efficiency', 'optimization'
        ])

        # Count matches across different categories
        strategic_matches = sum(1 for tag in tags if any(kw in tag.lower() for kw in strategic_keywords))
        risk_matches = sum(1 for tag in tags if any(kw in tag.lower() for kw in risk_keywords))
        opportunity_matches = sum(1 for tag in tags if any(kw in tag.lower() for kw in opportunity_keywords))

        # Calculate weighted relevance
        total_keywords = len(strategic_keywords) + len(risk_keywords) + len(opportunity_keywords)
        total_matches = strategic_matches + risk_matches + opportunity_matches

        if total_keywords == 0:
            return 0.5

        base_relevance = total_matches / total_keywords

        # Boost for risk/opportunity signals
        risk_boost = min(0.2, risk_matches * 0.1)
        opportunity_boost = min(0.2, opportunity_matches * 0.1)

        relevance = base_relevance + risk_boost + opportunity_boost

        return min(1.0, max(0.0, relevance))

    def calculate_composite_score(self, reliability: float, urgency: float, strategic_relevance: float) -> float:
        """
        Calculate weighted composite score from individual dimensions.

        Args:
            reliability: Reliability score (0-1)
            urgency: Urgency score (0-1)
            strategic_relevance: Strategic relevance score (0-1)

        Returns:
            Composite score (0-1)
        """
        composite = (reliability * self.weights['reliability'] +
                    urgency * self.weights['urgency'] +
                    strategic_relevance * self.weights['strategic_relevance'])

        return min(1.0, max(0.0, composite))

    def score_prediction(self, event_data: Dict[str, Any], project_context: Dict[str, Any]) -> Dict[str, float]:
        """
        Score a prediction based on event data and project context.

        Args:
            event_data: Dictionary containing event information
            project_context: Project strategic context

        Returns:
            Dictionary with individual and composite scores
        """
        source = event_data.get('source', 'unknown')
        category = event_data.get('category', 'unknown')
        impact_scale = event_data.get('impact_scale', 'regional')
        tags = event_data.get('tags', [])
        time_sensitivity = event_data.get('time_sensitivity', 0.5)
        evidence_strength = event_data.get('evidence_strength', 0.5)
        historical_accuracy = event_data.get('historical_accuracy', 0.5)

        reliability = self.calculate_reliability_score(source, historical_accuracy, evidence_strength)
        urgency = self.calculate_urgency_score(category, impact_scale, time_sensitivity)
        strategic = self.calculate_strategic_relevance(tags, project_context)
        composite = self.calculate_composite_score(reliability, urgency, strategic)

        return {
            'reliability': reliability,
            'urgency': urgency,
            'strategic_relevance': strategic,
            'composite': composite
        }

    def get_scoring_explanation(self, scores: Dict[str, float]) -> str:
        """Generate human-readable explanation of scoring."""
        explanation = f"Reliability: {scores['reliability']:.2f}, Urgency: {scores['urgency']:.2f}, Strategic: {scores['strategic_relevance']:.2f}, Composite: {scores['composite']:.2f}"

        if scores['composite'] >= 0.8:
            explanation += " (HIGH PRIORITY - Immediate attention required)"
        elif scores['composite'] >= 0.6:
            explanation += " (MEDIUM PRIORITY - Monitor closely)"
        else:
            explanation += " (LOW PRIORITY - Track for trends)"

        return explanation
#!/usr/bin/env python3
"""
Global Events Observer and Prediction System

Monitors global events and develops mid-to-long-term predictions with mathematical scoring.
Provides structured observation capabilities and predictive analytics for real-world events.

Scoring Dimensions:
- Reliability (R): Source credibility and historical accuracy (0-1)
- Urgency (U): Time-sensitive impact assessment (0-1)
- Strategic Relevance (S): Alignment with project goals (0-1)

Composite Score: C = (R * 0.4) + (U * 0.3) + (S * 0.3)
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import math
from collections import defaultdict

@dataclass
class GlobalEvent:
    """Represents a global event observation."""
    event_id: str
    title: str
    description: str
    category: str
    timestamp: str
    source: str
    reliability_score: float
    urgency_score: float
    strategic_relevance: float
    composite_score: float
    tags: List[str]
    metadata: Dict[str, Any]

@dataclass
class Prediction:
    """Represents a prediction based on observed events."""
    prediction_id: str
    title: str
    description: str
    event_ids: List[str]  # Related events
    predicted_outcome: str
    confidence_level: float
    timeframe_days: int
    timestamp: str
    status: str  # 'active', 'realized', 'failed'
    validation_date: Optional[str] = None

class PredictionScorer:
    """Mathematical scoring system for predictions."""

    def __init__(self):
        # Weight factors for composite scoring
        self.weights = {
            'reliability': 0.4,
            'urgency': 0.3,
            'strategic_relevance': 0.3
        }

    def calculate_reliability_score(self, source: str, historical_accuracy: float = 0.5) -> float:
        """Calculate reliability based on source credibility and track record."""
        source_credibility = {
            'trusted_news': 0.9,
            'government': 0.8,
            'academic': 0.85,
            'industry': 0.7,
            'social_media': 0.3,
            'unknown': 0.5
        }

        base_credibility = source_credibility.get(source.lower(), 0.5)
        return min(1.0, (base_credibility + historical_accuracy) / 2)

    def calculate_urgency_score(self, event_category: str, impact_scale: str) -> float:
        """Calculate urgency based on category and impact scale."""
        category_urgency = {
            'geopolitical': 0.9,
            'economic': 0.8,
            'technological': 0.7,
            'environmental': 0.8,
            'social': 0.6,
            'health': 0.9
        }

        impact_multiplier = {
            'global': 1.0,
            'regional': 0.7,
            'national': 0.5,
            'local': 0.3
        }

        base_urgency = category_urgency.get(event_category.lower(), 0.5)
        multiplier = impact_multiplier.get(impact_scale.lower(), 0.5)

        return min(1.0, base_urgency * multiplier)

    def calculate_strategic_relevance(self, tags: List[str], project_context: Dict[str, Any]) -> float:
        """Calculate strategic relevance based on project alignment."""
        relevance_keywords = project_context.get('strategic_keywords', [
            'ai', 'technology', 'development', 'innovation', 'security',
            'automation', 'intelligence', 'prediction', 'analysis'
        ])

        tag_matches = sum(1 for tag in tags if any(kw in tag.lower() for kw in relevance_keywords))
        relevance_score = min(1.0, tag_matches / len(relevance_keywords))

        return relevance_score

    def calculate_composite_score(self, reliability: float, urgency: float, strategic: float) -> float:
        """Calculate weighted composite score."""
        return (reliability * self.weights['reliability'] +
                urgency * self.weights['urgency'] +
                strategic * self.weights['strategic_relevance'])

class GlobalEventsObserver:
    """Main system for observing global events and making predictions."""

    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.data_dir = self.workspace / "data" / "global_events"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.events_file = self.data_dir / "events.jsonl"
        self.predictions_file = self.data_dir / "predictions.jsonl"

        self.scorer = PredictionScorer()
        self.project_context = self._load_project_context()

    def _load_project_context(self) -> Dict[str, Any]:
        """Load project context for strategic relevance scoring."""
        return {
            'strategic_keywords': [
                'ai', 'automation', 'development', 'technology', 'innovation',
                'security', 'intelligence', 'prediction', 'analysis', 'coding',
                'software', 'data', 'machine learning', 'neural networks'
            ]
        }

    def observe_event(self, title: str, description: str, category: str,
                     source: str, tags: List[str], impact_scale: str = 'regional') -> str:
        """Observe and record a new global event."""

        event_id = f"event_{int(datetime.now(timezone.utc).timestamp())}"

        # Calculate scores
        reliability = self.scorer.calculate_reliability_score(source)
        urgency = self.scorer.calculate_urgency_score(category, impact_scale)
        strategic = self.scorer.calculate_strategic_relevance(tags, self.project_context)
        composite = self.scorer.calculate_composite_score(reliability, urgency, strategic)

        event = GlobalEvent(
            event_id=event_id,
            title=title,
            description=description,
            category=category,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            reliability_score=reliability,
            urgency_score=urgency,
            strategic_relevance=strategic,
            composite_score=composite,
            tags=tags,
            metadata={'impact_scale': impact_scale}
        )

        # Save event
        with open(self.events_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(event)) + '\n')

        return event_id

    def create_prediction(self, title: str, description: str, related_event_ids: List[str],
                         predicted_outcome: str, confidence_level: float, timeframe_days: int) -> str:
        """Create a new prediction based on observed events."""

        prediction_id = f"pred_{int(datetime.now(timezone.utc).timestamp())}"

        prediction = Prediction(
            prediction_id=prediction_id,
            title=title,
            description=description,
            event_ids=related_event_ids,
            predicted_outcome=predicted_outcome,
            confidence_level=confidence_level,
            timeframe_days=timeframe_days,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status='active'
        )

        # Save prediction
        with open(self.predictions_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(prediction)) + '\n')

        return prediction_id

    def get_high_priority_events(self, threshold: float = 0.7) -> List[GlobalEvent]:
        """Get events with composite score above threshold."""
        events = self._load_events()
        return [e for e in events if e.composite_score >= threshold]

    def get_active_predictions(self) -> List[Prediction]:
        """Get all active predictions."""
        predictions = self._load_predictions()
        return [p for p in predictions if p.status == 'active']

    def validate_prediction(self, prediction_id: str, realized: bool) -> bool:
        """Validate a prediction as realized or failed."""
        predictions = self._load_predictions()
        for i, pred in enumerate(predictions):
            if pred.prediction_id == prediction_id:
                pred.status = 'realized' if realized else 'failed'
                pred.validation_date = datetime.now(timezone.utc).isoformat()

                # Rewrite predictions file
                self._save_predictions(predictions)
                return True
        return False

    def _load_events(self) -> List[GlobalEvent]:
        """Load all events from storage."""
        events = []
        if self.events_file.exists():
            with open(self.events_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        events.append(GlobalEvent(**data))
        return events

    def _load_predictions(self) -> List[Prediction]:
        """Load all predictions from storage."""
        predictions = []
        if self.predictions_file.exists():
            with open(self.predictions_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        predictions.append(Prediction(**data))
        return predictions

    def _save_predictions(self, predictions: List[Prediction]):
        """Save predictions to storage."""
        with open(self.predictions_file, 'w', encoding='utf-8') as f:
            for pred in predictions:
                f.write(json.dumps(asdict(pred)) + '\n')

    def generate_report(self) -> str:
        """Generate a summary report of observations and predictions."""
        events = self._load_events()
        predictions = self._load_predictions()

        report = f"""# Global Events Observation Report

Generated: {datetime.now(timezone.utc).isoformat()}

## Summary
- Total Events Observed: {len(events)}
- Active Predictions: {len([p for p in predictions if p.status == 'active'])}
- Realized Predictions: {len([p for p in predictions if p.status == 'realized'])}
- Failed Predictions: {len([p for p in predictions if p.status == 'failed'])}

## High Priority Events (Score > 0.7)
"""

        high_priority = self.get_high_priority_events(0.7)
        for event in high_priority[-10:]:  # Last 10
            report += f"- **{event.title}** (Score: {event.composite_score:.2f}) - {event.category}\n"

        report += "\n## Recent Predictions\n"
        active_preds = self.get_active_predictions()
        for pred in active_preds[-5:]:  # Last 5
            report += f"- **{pred.title}** (Confidence: {pred.confidence_level:.1%}) - {pred.timeframe_days} days\n"

        return report

# API Integration functions for loop_cockpit.py
def observe_global_event(title: str, description: str, category: str, source: str, tags: List[str]) -> str:
    """API function to observe a global event."""
    observer = GlobalEventsObserver()
    return observer.observe_event(title, description, category, source, tags)

def create_event_prediction(title: str, description: str, event_ids: List[str],
                           outcome: str, confidence: float, timeframe: int) -> str:
    """API function to create a prediction."""
    observer = GlobalEventsObserver()
    return observer.create_prediction(title, description, event_ids, outcome, confidence, timeframe)

def get_global_events_report() -> str:
    """API function to get observation report."""
    observer = GlobalEventsObserver()
    return observer.generate_report()
#!/usr/bin/env python3
"""
Self-Reflective Analysis Framework

TASK_0179: Implements self-awareness and reflective capabilities for AI system.
Captures AI decisions, analyzes behavior patterns, and enables self-improvement.

Components:
- ReflectiveLogger: Captures AI decisions and outcomes
- PatternAnalyzer: Identifies behavior patterns
- QualityAssessor: Evaluates task completion quality
- CorrectionEngine: Automated self-improvement
- MetaDashboard: Visualization and insights
"""

import json
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from collections import defaultdict, Counter
import statistics
import re

from ai_breadcrumb_tracker import Breadcrumb


@dataclass
class DecisionRecord:
    """Records a single AI decision with context and outcome."""
    decision_id: str
    timestamp: str
    task_id: str
    decision_type: str  # 'task_selection', 'implementation_choice', 'validation', etc.
    context: Dict[str, Any]
    reasoning: str
    confidence: float  # 0.0 to 1.0
    alternatives: List[str]
    chosen_action: str
    expected_outcome: str
    actual_outcome: Optional[str] = None
    success: Optional[bool] = None
    lessons_learned: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'decision_id': self.decision_id,
            'timestamp': self.timestamp,
            'task_id': self.task_id,
            'decision_type': self.decision_type,
            'context': self.context,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'alternatives': self.alternatives,
            'chosen_action': self.chosen_action,
            'expected_outcome': self.expected_outcome,
            'actual_outcome': self.actual_outcome,
            'success': self.success,
            'lessons_learned': self.lessons_learned,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecisionRecord':
        return cls(**data)


class ReflectiveLogger:
    """Captures and logs AI decisions for self-reflection."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.log_file = workspace_root / 'ai_reflective_log.jsonl'
        self._lock = threading.Lock()
        self.decision_counter = 0

    def log_decision(self, task_id: str, decision_type: str, context: Dict[str, Any],
                    reasoning: str, confidence: float, alternatives: List[str],
                    chosen_action: str, expected_outcome: str) -> str:
        """Log a new decision."""
        with self._lock:
            self.decision_counter += 1
            decision_id = f"decision_{self.decision_counter}_{int(time.time())}"

            record = DecisionRecord(
                decision_id=decision_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                task_id=task_id,
                decision_type=decision_type,
                context=context,
                reasoning=reasoning,
                confidence=confidence,
                alternatives=alternatives,
                chosen_action=chosen_action,
                expected_outcome=expected_outcome
            )

            # Append to log file
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record.to_dict()) + '\n')

            return decision_id

    def update_decision_outcome(self, decision_id: str, actual_outcome: str,
                               success: Optional[bool], lessons_learned: Optional[List[str]] = None):
        """Update a decision record with actual outcome."""
        if lessons_learned is None:
            lessons_learned = []

        # Read all records and update the matching one
        records = self._load_all_records()
        updated = False

        for record in records:
            if record.decision_id == decision_id:
                record.actual_outcome = actual_outcome
                record.success = success
                record.lessons_learned = lessons_learned
                updated = True
                break

        if updated:
            self._save_all_records(records)

    def _load_all_records(self) -> List[DecisionRecord]:
        """Load all decision records from file."""
        records = []
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            records.append(DecisionRecord.from_dict(data))
                        except json.JSONDecodeError:
                            continue
        return records

    def _save_all_records(self, records: List[DecisionRecord]):
        """Save all records back to file."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record.to_dict()) + '\n')


class PatternAnalyzer:
    """Analyzes behavior patterns from decision records."""

    def __init__(self, logger: ReflectiveLogger):
        self.logger = logger

    def analyze_success_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in successful vs failed decisions."""
        records = self.logger._load_all_records()
        if not records:
            return {"error": "No decision records available"}

        successful = [r for r in records if r.success is True]
        failed = [r for r in records if r.success is False]

        analysis = {
            'total_decisions': len(records),
            'success_rate': len(successful) / len(records) if records else 0,
            'patterns': {}
        }

        # Analyze confidence vs success
        if successful and failed:
            success_confidence = [r.confidence for r in successful]
            failed_confidence = [r.confidence for r in failed]

            analysis['patterns']['confidence_correlation'] = {
                'success_avg_confidence': statistics.mean(success_confidence),
                'failed_avg_confidence': statistics.mean(failed_confidence),
                'correlation': self._calculate_confidence_success_correlation(successful, failed)
            }

        # Analyze decision types
        decision_types = Counter(r.decision_type for r in records)
        success_by_type = Counter(r.decision_type for r in successful)

        analysis['patterns']['decision_type_performance'] = {}
        for dt, total in decision_types.items():
            success_count = success_by_type[dt]
            analysis['patterns']['decision_type_performance'][dt] = {
                'total': total,
                'success_rate': success_count / total if total > 0 else 0
            }

        # Analyze reasoning patterns
        analysis['patterns']['reasoning_patterns'] = self._analyze_reasoning_patterns(records)

        return analysis

    def _calculate_confidence_success_correlation(self, successful: List[DecisionRecord],
                                                failed: List[DecisionRecord]) -> float:
        """Calculate correlation between confidence and success."""
        # Simple correlation calculation
        all_records = successful + failed
        if len(all_records) < 2:
            return 0.0

        confidences = [r.confidence for r in all_records]
        successes = [1.0 if r.success else 0.0 for r in all_records]

        try:
            return statistics.correlation(confidences, successes)
        except:
            return 0.0

    def _analyze_reasoning_patterns(self, records: List[DecisionRecord]) -> Dict[str, Any]:
        """Analyze patterns in reasoning text."""
        successful_reasoning = [r.reasoning for r in records if r.success]
        failed_reasoning = [r.reasoning for r in records if r.success is False]

        patterns = {
            'common_success_keywords': self._extract_common_keywords(successful_reasoning),
            'common_failure_keywords': self._extract_common_keywords(failed_reasoning),
            'reasoning_length_analysis': self._analyze_reasoning_length(records)
        }

        return patterns

    def _extract_common_keywords(self, reasoning_texts: List[str]) -> List[Tuple[str, int]]:
        """Extract most common keywords from reasoning texts."""
        if not reasoning_texts:
            return []

        all_words = []
        for text in reasoning_texts:
            words = re.findall(r'\b[a-z]{4,}\b', text.lower())
            all_words.extend(words)

        word_counts = Counter(all_words)
        return word_counts.most_common(10)

    def _analyze_reasoning_length(self, records: List[DecisionRecord]) -> Dict[str, Any]:
        """Analyze reasoning text length patterns."""
        successful_lengths = [len(r.reasoning) for r in records if r.success]
        failed_lengths = [len(r.reasoning) for r in records if r.success is False]

        analysis = {}
        if successful_lengths:
            analysis['successful_avg_length'] = statistics.mean(successful_lengths)
        if failed_lengths:
            analysis['failed_avg_length'] = statistics.mean(failed_lengths)

        return analysis


class QualityAssessor:
    """Assesses quality of task completion and AI performance."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def assess_task_quality(self, task_id: str) -> Dict[str, Any]:
        """Assess the quality of a completed task."""
        # Check if task report exists
        report_file = self.workspace_root / 'reports' / f'report_{task_id}_L104_v01.md'
        task_file = self.workspace_root / 'tasks' / f'task_{task_id}.md'

        assessment = {
            'task_id': task_id,
            'has_report': report_file.exists(),
            'has_task_spec': task_file.exists(),
            'quality_score': 0.0,
            'criteria': {}
        }

        if not report_file.exists():
            assessment['criteria']['missing_report'] = -0.5
            return assessment

        if not task_file.exists():
            assessment['criteria']['missing_task_spec'] = -0.3
            return assessment

        # Read and analyze report
        try:
            report_content = report_file.read_text(encoding='utf-8')
            task_content = task_file.read_text(encoding='utf-8')

            assessment['criteria'] = self._evaluate_report_quality(report_content, task_content)
            assessment['quality_score'] = sum(assessment['criteria'].values())

        except Exception as e:
            assessment['error'] = str(e)

        return assessment

    def _evaluate_report_quality(self, report_content: str, task_content: str) -> Dict[str, float]:
        """Evaluate the quality of a task report."""
        criteria = {}

        # Check for required sections
        required_sections = ['STATUS: COMPLETED', 'SUCCESS CRITERIA', 'IMPLEMENTATION SUMMARY']
        for section in required_sections:
            if section in report_content:
                criteria[f'has_{section.lower().replace(" ", "_")}'] = 0.2
            else:
                criteria[f'missing_{section.lower().replace(" ", "_")}'] = -0.2

        # Check for performance metrics
        if 'Performance Results' in report_content or 'Benchmark Results' in report_content:
            criteria['has_performance_metrics'] = 0.3
        else:
            criteria['missing_performance_metrics'] = -0.1

        # Check for file references
        if 'Files Modified/Created' in report_content:
            criteria['has_file_references'] = 0.2
        else:
            criteria['missing_file_references'] = -0.1

        # Check for success criteria alignment
        success_criteria = self._extract_success_criteria(task_content)
        addressed_criteria = 0
        for criterion in success_criteria:
            if criterion.lower() in report_content.lower():
                addressed_criteria += 1

        if success_criteria:
            criteria['success_criteria_coverage'] = 0.3 * (addressed_criteria / len(success_criteria))
        else:
            criteria['success_criteria_coverage'] = 0.1

        return criteria

    def _extract_success_criteria(self, task_content: str) -> List[str]:
        """Extract success criteria from task specification."""
        criteria = []
        lines = task_content.split('\n')
        in_criteria = False

        for line in lines:
            if 'SUCCESS CRITERIA' in line:
                in_criteria = True
                continue
            elif in_criteria and line.strip().startswith('##'):
                break
            elif in_criteria and line.strip().startswith('- ['):
                # Extract the criterion text
                match = re.search(r'- \[ \] (.+)', line)
                if match:
                    criteria.append(match.group(1))

        return criteria


class CorrectionEngine:
    """Automated self-improvement system."""

    def __init__(self, analyzer: PatternAnalyzer, assessor: QualityAssessor):
        self.analyzer = analyzer
        self.assessor = assessor
        self.corrections_applied = []

    def generate_corrections(self) -> List[Dict[str, Any]]:
        """Generate self-improvement recommendations."""
        corrections = []

        # Analyze patterns
        pattern_analysis = self.analyzer.analyze_success_patterns()

        # Generate corrections based on patterns
        if 'patterns' in pattern_analysis:
            patterns = pattern_analysis['patterns']

            # Confidence correlation correction
            if 'confidence_correlation' in patterns:
                corr = patterns['confidence_correlation']
                if corr.get('correlation', 0) < 0.3:
                    corrections.append({
                        'type': 'confidence_calibration',
                        'description': 'Improve confidence assessment accuracy',
                        'impact': 'medium',
                        'action': 'Review confidence scoring methodology'
                    })

            # Decision type performance correction
            if 'decision_type_performance' in patterns:
                dt_perf = patterns['decision_type_performance']
                for dt, perf in dt_perf.items():
                    if perf['success_rate'] < 0.7 and perf['total'] > 3:
                        corrections.append({
                            'type': 'decision_type_improvement',
                            'description': f'Improve {dt} decision making',
                            'impact': 'high',
                            'action': f'Analyze failures in {dt} decisions'
                        })

        return corrections

    def apply_correction(self, correction: Dict[str, Any]) -> bool:
        """Apply a specific correction."""
        # For now, just log the correction
        self.corrections_applied.append({
            'correction': correction,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'logged'
        })
        return True


class MetaDashboard:
    """Visualization and insights for self-reflective data."""

    def __init__(self, workspace_root: Path, logger: ReflectiveLogger,
                 analyzer: PatternAnalyzer, assessor: QualityAssessor):
        self.workspace_root = workspace_root
        self.logger = logger
        self.analyzer = analyzer
        self.assessor = assessor

    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate comprehensive dashboard data."""
        dashboard = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {},
            'charts': {},
            'insights': [],
            'recommendations': []
        }

        # Load decision records
        records = self.logger._load_all_records()

        # Summary statistics
        total_decisions = len(records)
        successful_decisions = len([r for r in records if r.success is True])
        failed_decisions = len([r for r in records if r.success is False])

        dashboard['summary'] = {
            'total_decisions': total_decisions,
            'success_rate': successful_decisions / total_decisions if total_decisions > 0 else 0,
            'avg_confidence': statistics.mean([r.confidence for r in records]) if records else 0,
            'decisions_by_type': dict(Counter(r.decision_type for r in records))
        }

        # Pattern analysis
        pattern_data = self.analyzer.analyze_success_patterns()
        dashboard['charts']['pattern_analysis'] = pattern_data

        # Quality assessment for recent tasks
        recent_tasks = self._get_recent_completed_tasks()
        quality_scores = []
        for task_id in recent_tasks[:5]:  # Last 5 tasks
            assessment = self.assessor.assess_task_quality(task_id)
            quality_scores.append(assessment.get('quality_score', 0))

        dashboard['charts']['quality_trends'] = {
            'recent_tasks': recent_tasks[:5],
            'quality_scores': quality_scores,
            'avg_quality': statistics.mean(quality_scores) if quality_scores else 0
        }

        # Generate insights
        dashboard['insights'] = self._generate_insights(dashboard)

        return dashboard

    def _get_recent_completed_tasks(self) -> List[str]:
        """Get recently completed task IDs."""
        alt_file = self.workspace_root / 'Alt.md'
        if not alt_file.exists():
            return []

        content = alt_file.read_text(encoding='utf-8')
        # Extract task IDs from completed tasks section
        task_refs = re.findall(r'\[ref:tasks/task_(TASK_\d+)\.md', content)
        return task_refs[-10:]  # Last 10 completed tasks

    def _generate_insights(self, dashboard: Dict[str, Any]) -> List[str]:
        """Generate insights from dashboard data."""
        insights = []

        summary = dashboard.get('summary', {})
        success_rate = summary.get('success_rate', 0)

        if success_rate > 0.8:
            insights.append("High success rate indicates effective decision making")
        elif success_rate < 0.6:
            insights.append("Low success rate suggests need for improved decision processes")

        # Pattern insights
        pattern_analysis = dashboard.get('charts', {}).get('pattern_analysis', {})
        if 'patterns' in pattern_analysis:
            patterns = pattern_analysis['patterns']
            if 'confidence_correlation' in patterns:
                corr = patterns['confidence_correlation'].get('correlation', 0)
                if corr > 0.5:
                    insights.append("Strong correlation between confidence and success")
                elif corr < 0:
                    insights.append("Overconfidence detected - review confidence calibration")

        return insights


# Convenience function for logging decisions
_reflective_logger = None

def get_reflective_logger(workspace_root: Path = None) -> ReflectiveLogger:
    """Get or create the global reflective logger."""
    global _reflective_logger
    if _reflective_logger is None:
        if workspace_root is None:
            workspace_root = Path(__file__).parent.parent
        _reflective_logger = ReflectiveLogger(workspace_root)
    return _reflective_logger

def log_ai_decision(task_id: str, decision_type: str, context: Dict[str, Any],
                   reasoning: str, confidence: float, alternatives: List[str],
                   chosen_action: str, expected_outcome: str) -> str:
    """Convenience function to log AI decisions."""
    logger = get_reflective_logger()
    return logger.log_decision(task_id, decision_type, context, reasoning,
                              confidence, alternatives, chosen_action, expected_outcome)

def update_decision_outcome(decision_id: str, actual_outcome: str, success: Optional[bool], lessons_learned: Optional[List[str]] = None):
    """Convenience function to update decision outcomes."""
    if lessons_learned is None:
        lessons_learned = []
    logger = get_reflective_logger()
    logger.update_decision_outcome(decision_id, actual_outcome, success, lessons_learned)
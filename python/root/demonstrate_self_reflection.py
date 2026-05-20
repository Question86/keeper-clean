#!/usr/bin/env python3
"""
Simple Self-Reflective Analysis Demo
"""

from pathlib import Path
from ai_self_reflective_framework import (
    ReflectiveLogger, PatternAnalyzer, QualityAssessor
)

def demo():
    workspace_root = Path(__file__).parent

    print("AI Self-Reflective Framework Demo")
    print("=" * 40)

    # Initialize components
    logger = ReflectiveLogger(workspace_root)
    analyzer = PatternAnalyzer(logger)
    assessor = QualityAssessor(workspace_root)

    # Log a decision
    decision_id = logger.log_decision(
        task_id="TASK_0179",
        decision_type="implementation_choice",
        context={"framework": "self_reflective"},
        reasoning="Building self-awareness improves AI effectiveness",
        confidence=0.9,
        alternatives=["skip_self_reflection", "basic_logging"],
        chosen_action="implement_full_framework",
        expected_outcome="Better decision making"
    )

    print(f"Logged decision: {decision_id}")

    # Update outcome
    logger.update_decision_outcome(
        decision_id,
        actual_outcome="Framework implemented successfully",
        success=True,
        lessons_learned=["Self-reflection valuable", "Pattern analysis useful"]
    )

    # Analyze patterns
    analysis = analyzer.analyze_success_patterns()
    print(f"Analysis: {analysis.get('total_decisions', 0)} decisions, success rate: {analysis.get('success_rate', 0):.1%}")

    # Assess quality
    quality = assessor.assess_task_quality("TASK_0178")
    print(f"Task 0178 quality score: {quality.get('quality_score', 0):.2f}")

    print("Demo completed!")

if __name__ == '__main__':
    demo()
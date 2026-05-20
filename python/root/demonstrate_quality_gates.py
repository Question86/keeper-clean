#!/usr/bin/env python3
"""
Demonstration script for strategic task planner quality gates.
Shows the complete pipeline from recommendation generation to task creation.
"""

import sys
import os
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from scripts.strategic_task_planner import StrategicTaskPlanner

def main():
    print("🚀 Starting Strategic Task Planner Quality Gate Demonstration")
    print("=" * 60)

    # Initialize the strategic planner
    planner = StrategicTaskPlanner()

    # For demonstration, use manually crafted high-quality recommendations
    # that are specific and actionable - focused on high-value improvements
    recommendations = [
        {
            'id': 'demo_task_001',
            'type': 'gap_filling',
            'title': 'Implement automated dependency conflict resolution',
            'description': 'Develop a system to automatically detect and resolve package dependency conflicts in Python projects, reducing manual intervention time by 80%',
            'categories': ['automation', 'python', 'dependencies'],
            'priority': 'high',
            'estimated_effort': 'medium',
            'prerequisites': ['python_packaging', 'dependency_analysis'],
            'rationale': 'Dependency conflicts waste significant developer time and cause deployment failures',
            'expected_impact': 'Faster project setup and more reliable deployments',
            'frequency': 'one_time'
        },
        {
            'id': 'demo_task_002',
            'type': 'gap_filling',
            'title': 'Add comprehensive error handling to API endpoints',
            'description': 'Implement structured error handling with proper HTTP status codes and error messages for all REST API endpoints in the Flask application',
            'categories': ['api', 'error_handling', 'flask'],
            'priority': 'high',
            'estimated_effort': 'low',
            'prerequisites': ['flask', 'api_design'],
            'rationale': 'Poor error handling leads to confusing user experiences and debugging difficulties',
            'expected_impact': 'Better user experience and easier debugging',
            'frequency': 'one_time'
        },
        {
            'id': 'demo_task_003',
            'type': 'maintenance',
            'title': 'Refactor duplicate code in data processing modules',
            'description': 'Identify and eliminate duplicate code patterns in data processing functions across the codebase, creating reusable utilities',
            'categories': ['refactoring', 'code_quality', 'data_processing'],
            'priority': 'high',  # Changed to high
            'estimated_effort': 'medium',
            'prerequisites': ['code_analysis', 'refactoring'],
            'rationale': 'Duplicate code increases maintenance burden and bug risk',
            'expected_impact': 'Easier maintenance and reduced bug surface area',
            'frequency': 'one_time'
        },
        {
            'id': 'demo_task_004',
            'type': 'gap_filling',
            'title': 'Add automated testing framework for API endpoints',
            'description': 'Implement comprehensive automated testing suite for all API endpoints with unit tests, integration tests, and performance benchmarks',
            'categories': ['testing', 'api', 'automation'],
            'priority': 'high',
            'estimated_effort': 'medium',
            'prerequisites': ['pytest', 'api_testing'],
            'rationale': 'Manual testing is time-consuming and error-prone',
            'expected_impact': 'Faster development cycles and higher code quality',
            'frequency': 'one_time'
        }
    ]

    print(f"✅ Using {len(recommendations)} manually crafted high-quality recommendations for demonstration")

    print(f"\n🎯 Step 2: Processing through quality gates (threshold: low)...")
    print("This will show the 5-gate pipeline for each recommendation:")
    print("  1. Chaosbox Quality Scoring")
    print("  2. Validation Engine")
    print("  3. Formal Consistency Checker")
    print("  4. Task File Creation")
    print("  5. Knowledge Database Registration")

    # Process recommendations through quality gates
    created_tasks = planner.create_task_files_from_recommendations(recommendations, priority_threshold='low')

    print("\n" + "=" * 60)
    print("🎉 DEMONSTRATION COMPLETE")
    print(f"📈 Results: {len(created_tasks)} tasks successfully created through ALL quality gates")

    if created_tasks:
        print("\n✅ Successfully created tasks:")
        for task_id in created_tasks:
            print(f"  - {task_id}")
            # Show the task file path
            task_file = Path(__file__).parent / 'tasks' / f'task_{task_id}.md'
            if task_file.exists():
                print(f"    📄 File: {task_file}")
    else:
        print("\n❌ No tasks were created - all recommendations were rejected by quality gates")

if __name__ == "__main__":
    main()
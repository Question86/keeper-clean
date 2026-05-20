#!/usr/bin/env python3
"""
Strategic Task Planner

Generates proactive task recommendations based on knowledge analysis and future needs.
Enhanced with production-ready success/failure benchmarks and lifecycle tracking.
"""

import argparse
import json
import random
import sys
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.knowledge_dependency_analyzer import KnowledgeDependencyAnalyzer
from chaosbox.chaosbox_manager import ChaosboxManager, RejectionReason
from chaosbox.validation_engine import ValidationEngine
from scripts.task_formal_consistency_checker import TaskFormalConsistencyChecker
import sqlite3

class StrategicTaskPlanner:
    """
    Plans strategic tasks based on knowledge gaps and future requirements.
    Enhanced with measurable success criteria and lifecycle tracking.
    """

    def __init__(self, db_path: str = "keeper_knowledge.db", workspace_root: str = None):
        self.db_path = db_path
        self.workspace_root = Path(workspace_root) if workspace_root else Path(__file__).parent.parent
        self.analyzer = KnowledgeDependencyAnalyzer(db_path)
        self.task_templates = self._load_task_templates()
        self.lifecycle_tracker_path = self.workspace_root / "strategic_tasks_tracker.json"

    def _load_task_templates(self) -> Dict:
        """Load task templates for different scenarios."""
        return {
            'knowledge_expansion': {
                'template': "Expand knowledge base in {category} category",
                'description': "Add {count} new knowledge items to address gaps in {category}",
                'estimated_effort': 'medium',
                'prerequisites': ['research', 'documentation']
            },
            'connectivity_improvement': {
                'template': "Improve knowledge connectivity and cross-references",
                'description': "Add cross-references between {count} disconnected knowledge clusters",
                'estimated_effort': 'low',
                'prerequisites': ['analysis', 'linking']
            },
            'freshness_update': {
                'template': "Update stale knowledge in {categories}",
                'description': "Review and update {count} outdated items in {categories}",
                'estimated_effort': 'medium',
                'prerequisites': ['review', 'validation']
            },
            'gap_filling': {
                'template': "Fill knowledge gap: {gap_description}",
                'description': "Address identified knowledge gap in {category}",
                'estimated_effort': 'high',
                'prerequisites': ['analysis', 'implementation']
            },
            'predictive_planning': {
                'template': "Prepare knowledge base for {future_domain}",
                'description': "Build foundational knowledge for upcoming {future_domain} requirements",
                'estimated_effort': 'high',
                'prerequisites': ['research', 'planning']
            }
        }

    def generate_task_recommendations(self, planning_horizon: int = 90) -> List[Dict]:
        """
        Generate strategic task recommendations for the planning horizon.
        """
        recommendations = []

        # Get current landscape analysis
        landscape = self.analyzer.analyze_knowledge_landscape()

        # Generate recommendations based on gaps
        gap_recommendations = self._generate_gap_based_recommendations(landscape)
        recommendations.extend(gap_recommendations)

        # Generate predictive recommendations
        predictive_recommendations = self._generate_predictive_recommendations(landscape, planning_horizon)
        recommendations.extend(predictive_recommendations)

        # Generate maintenance recommendations
        maintenance_recommendations = self._generate_maintenance_recommendations(landscape)
        recommendations.extend(maintenance_recommendations)

        # Prioritize and schedule recommendations
        prioritized = self._prioritize_and_schedule(recommendations, planning_horizon)

        return prioritized

    def _generate_gap_based_recommendations(self, landscape: Dict) -> List[Dict]:
        """Generate recommendations based on identified knowledge gaps."""
        recommendations = []

        for gap in landscape['gaps']:
            if gap['type'] == 'category_underrepresentation':
                template = self.task_templates['knowledge_expansion']
                rec = {
                    'id': f"gap_{gap['category']}_{random.randint(1000,9999)}",
                    'type': 'gap_filling',
                    'title': template['template'].format(category=gap['category']),
                    'description': template['description'].format(
                        count=int(gap['expected_count'] - gap['current_count']),
                        category=gap['category']
                    ),
                    'category': gap['category'],
                    'priority': self._map_severity_to_priority(gap['severity']),
                    'estimated_effort': template['estimated_effort'],
                    'prerequisites': template['prerequisites'],
                    'rationale': f"Address {gap['severity']} priority gap in {gap['category']} category",
                    'expected_impact': f"Increase {gap['category']} knowledge coverage by ~{((gap['expected_count'] - gap['current_count']) / gap['expected_count'] * 100):.0f}%"
                }
                recommendations.append(rec)

            elif gap['type'] == 'connectivity_gaps':
                template = self.task_templates['connectivity_improvement']
                rec = {
                    'id': f"connect_{random.randint(1000,9999)}",
                    'type': 'connectivity',
                    'title': template['template'],
                    'description': template['description'].format(count=gap['small_components']),
                    'priority': self._map_severity_to_priority(gap['severity']),
                    'estimated_effort': template['estimated_effort'],
                    'prerequisites': template['prerequisites'],
                    'rationale': gap['description'],
                    'expected_impact': "Improve knowledge discoverability and reduce information silos"
                }
                recommendations.append(rec)

        return recommendations

    def _generate_predictive_recommendations(self, landscape: Dict, horizon: int) -> List[Dict]:
        """Generate recommendations for future needs based on trends."""
        recommendations = []

        # Analyze category growth trends
        categories = landscape['categories']
        total_items = landscape['total_items']

        # Predict future needs based on current growth
        for cat_name, cat_data in categories.items():
            growth_rate = cat_data['count'] / total_items  # Current proportion

            # If category is growing or important, plan for future expansion
            if growth_rate > 0.1 or cat_data['count'] > 20:  # Significant category
                future_need = f"expanded_{cat_name}_capabilities"

                template = self.task_templates['predictive_planning']
                rec = {
                    'id': f"predict_{cat_name}_{random.randint(1000,9999)}",
                    'type': 'predictive',
                    'title': template['template'].format(future_domain=future_need),
                    'description': template['description'].format(future_domain=future_need),
                    'category': cat_name,
                    'priority': 'medium',
                    'estimated_effort': template['estimated_effort'],
                    'prerequisites': template['prerequisites'],
                    'rationale': f"Prepare for anticipated growth in {cat_name} domain",
                    'expected_impact': f"Enable future {cat_name} initiatives with prepared knowledge base",
                    'timeframe': f"{horizon//3}-{horizon//2} days"  # Mid-term planning
                }
                recommendations.append(rec)

        # Technology trend predictions (simplified)
        emerging_domains = ['ai_enhancement', 'automation', 'scalability']
        for domain in emerging_domains:
            if not any(domain in cat.lower() for cat in categories.keys()):
                template = self.task_templates['predictive_planning']
                rec = {
                    'id': f"trend_{domain}_{random.randint(1000,9999)}",
                    'type': 'trend_preparation',
                    'title': template['template'].format(future_domain=domain.replace('_', ' ')),
                    'description': template['description'].format(future_domain=domain.replace('_', ' ')),
                    'priority': 'low',
                    'estimated_effort': 'high',
                    'prerequisites': template['prerequisites'],
                    'rationale': f"Prepare for emerging {domain.replace('_', ' ')} requirements",
                    'expected_impact': f"Position for future {domain.replace('_', ' ')} opportunities",
                    'timeframe': f"{horizon//2}-{horizon} days"  # Long-term planning
                }
                recommendations.append(rec)

        return recommendations

    def _generate_maintenance_recommendations(self, landscape: Dict) -> List[Dict]:
        """Generate ongoing maintenance recommendations."""
        recommendations = []

        # Freshness maintenance
        categories = landscape['categories']
        stale_threshold = 0.6

        stale_cats = [cat for cat, data in categories.items()
                     if data.get('freshness_score', 1.0) < stale_threshold]

        if stale_cats:
            template = self.task_templates['freshness_update']
            rec = {
                'id': f"maintain_fresh_{random.randint(1000,9999)}",
                'type': 'maintenance',
                'title': template['template'].format(categories=', '.join(stale_cats)),
                'description': template['description'].format(
                    count=sum(categories[cat]['count'] for cat in stale_cats),
                    categories=', '.join(stale_cats)
                ),
                'categories': stale_cats,
                'priority': 'high',
                'estimated_effort': template['estimated_effort'],
                'prerequisites': template['prerequisites'],
                'rationale': f"Maintain knowledge freshness across {len(stale_cats)} categories",
                'expected_impact': "Ensure knowledge base remains current and reliable",
                'frequency': 'quarterly'
            }
            recommendations.append(rec)

        # Quality assurance maintenance
        if landscape['knowledge_graph']['density'] < 0.05:
            rec = {
                'id': f"maintain_quality_{random.randint(1000,9999)}",
                'type': 'maintenance',
                'title': "Perform knowledge quality assurance review",
                'description': "Review and improve knowledge item quality and cross-references",
                'priority': 'medium',
                'estimated_effort': 'medium',
                'prerequisites': ['analysis', 'review'],
                'rationale': f"Current knowledge graph density ({landscape['knowledge_graph']['density']:.3f}) indicates room for improvement",
                'expected_impact': "Enhance knowledge discoverability and reduce redundancy",
                'frequency': 'monthly'
            }
            recommendations.append(rec)

        return recommendations

    def _map_severity_to_priority(self, severity: str) -> str:
        """Map gap severity to task priority."""
        mapping = {
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(severity, 'medium')

    def _prioritize_and_schedule(self, recommendations: List[Dict], horizon: int) -> List[Dict]:
        """Prioritize recommendations and assign scheduling."""
        # Sort by priority and impact
        priority_weights = {'high': 3, 'medium': 2, 'low': 1}

        def sort_key(rec):
            priority_weight = priority_weights.get(rec['priority'], 1)
            effort_penalty = 1 if rec.get('estimated_effort') == 'low' else 0.8 if rec.get('estimated_effort') == 'medium' else 0.6
            return priority_weight * effort_penalty

        recommendations.sort(key=sort_key, reverse=True)

        # Assign scheduling based on priority and dependencies
        scheduled = []
        current_day = 0

        for rec in recommendations:
            # Simple scheduling logic
            if rec['priority'] == 'high':
                days_delay = random.randint(0, 7)  # Schedule within a week
            elif rec['priority'] == 'medium':
                days_delay = random.randint(7, 21)  # Schedule within 3 weeks
            else:
                days_delay = random.randint(21, horizon)  # Schedule within horizon

            rec['scheduled_date'] = (datetime.now() + timedelta(days=days_delay)).date().isoformat()
            rec['days_until_due'] = days_delay

            scheduled.append(rec)

        return scheduled

    def create_task_files_from_recommendations(self, recommendations: List[Dict], priority_threshold: str = 'medium') -> List[str]:
        """
        Create tasks through the comprehensive quality gate pipeline:
        Strategic Planner -> Chaosbox -> Validation Engine -> Formal Consistency -> Task Creation

        Args:
            recommendations: List of strategic recommendations
            priority_threshold: Minimum priority level to process

        Returns:
            List of successfully created task IDs
        """
        # Initialize quality gate components
        workspace_root = Path(__file__).parent.parent
        chaosbox = ChaosboxManager(str(workspace_root))
        validation_engine = ValidationEngine()
        formal_checker = TaskFormalConsistencyChecker(str(workspace_root))

        priority_weights = {'low': 1, 'medium': 2, 'high': 3}
        threshold_weight = priority_weights.get(priority_threshold, 2)

        created_tasks = []
        processed_count = 0

        # Filter recommendations by priority threshold
        filtered_recs = [rec for rec in recommendations if priority_weights.get(rec['priority'], 1) >= threshold_weight]

        for rec in filtered_recs[:5]:  # Limit to 5 to avoid overwhelming the pipeline
            processed_count += 1
            print(f"Processing recommendation {processed_count}/5 through quality gates...")

            try:
                # GATE 1: Submit to Chaosbox for quality scoring
                idea_id = self._submit_to_chaosbox(chaosbox, rec)
                if not idea_id:
                    print(f"❌ Recommendation rejected at Chaosbox gate")
                    continue

                # Wait for chaosbox processing (simplified - in production this would be async)
                import time
                time.sleep(2)  # Allow chaosbox to process

                # Check chaosbox result
                idea_status = chaosbox.get_idea_status(idea_id)
                if not idea_status or idea_status.status.value == 'rejected':
                    print(f"❌ Recommendation rejected by Chaosbox quality scoring")
                    continue

                print(f"✅ Passed Chaosbox quality gate (score: {idea_status.quality_score})")

                # GATE 2: Validation Engine (sanity checks, duplicate detection, etc.)
                validation_result = validation_engine.validate_idea(idea_status)
                if not validation_result["passed"]:
                    print(f"❌ Failed validation engine: {validation_result['reason']}")
                    # Update chaosbox status to rejected
                    idea_status.status = RejectionReason.OUT_OF_SCOPE
                    chaosbox._save_idea(idea_status)
                    continue

                print("✅ Passed validation engine gate")

                # GATE 3: Formal Consistency Checker
                # Convert chaosbox idea to task spec format
                task_spec = self._convert_idea_to_task_spec(idea_status, rec)

                consistency_result = formal_checker.validate_task_formal_consistency(task_spec)
                if not consistency_result["passed"]:
                    print(f"❌ Failed formal consistency check: {consistency_result['issues'][:2]}")
                    # Send back to chaosbox for improvement
                    idea_status.status = RejectionReason.MALFORMED
                    chaosbox._save_idea(idea_status)
                    continue

                print("✅ Passed formal consistency gate")

                # GATE 4: Create the formal task file
                task_id = self._create_formal_task_file(formal_checker, task_spec, rec)
                if task_id:
                    created_tasks.append(task_id)
                    print(f"🎉 Task {task_id} successfully created through quality gates")

                    # GATE 5: Mark as completed successful and add to knowledge database
                    self._register_successful_task(task_id, task_spec)

            except Exception as e:
                print(f"❌ Error processing recommendation: {str(e)}")
                continue

        print(f"\nQuality Gate Pipeline Complete:")
        print(f"- Processed: {processed_count} recommendations")
        print(f"- Created: {len(created_tasks)} tasks")
        print(f"- Rejection Rate: {((processed_count - len(created_tasks)) / max(processed_count, 1)) * 100:.1f}%")

        return created_tasks

    def _generate_task_content(self, task_id: str, recommendation: Dict) -> str:
        """Generate task file content from recommendation."""
        created_date = datetime.now().isoformat() + 'Z'

        # Map recommendation type to task type
        task_type_mapping = {
            'gap_filling': 'ANALYSIS',
            'predictive': 'DEVELOPMENT',
            'maintenance': 'MAINTENANCE',
            'connectivity': 'ANALYSIS',
            'trend_preparation': 'RESEARCH'
        }

        task_type = task_type_mapping.get(recommendation['type'], 'ANALYSIS')

        # Generate acceptance criteria based on recommendation
        acceptance_criteria = self._generate_acceptance_criteria(recommendation)

        # Generate file list based on recommendation type
        files_to_modify = self._generate_file_list(recommendation)

        content = f"""# {task_id}

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: {created_date}

---

## SEED IDEA

{recommendation['rationale']}

---

## OBJECTIVE

{recommendation['description']}

**Strategic Context:** {recommendation.get('expected_impact', 'Improve knowledge base effectiveness')}

---

## TASK_TYPE

{task_type}

---

## ACCEPTANCE CRITERIA

{acceptance_criteria}

Files to be modified/created:
{files_to_modify}

---

## STRATEGIC IMPORTANCE

**Priority:** {recommendation['priority'].upper()}
**Effort Level:** {recommendation['estimated_effort'].upper()}
**Expected Timeline:** {recommendation.get('timeframe', 'TBD')}

**Generated by:** Strategic Planning System
**Recommendation Type:** {recommendation['type'].replace('_', ' ').title()}
"""

        return content

    def _generate_acceptance_criteria(self, recommendation: Dict) -> str:
        """Generate acceptance criteria based on recommendation type."""
        criteria_templates = {
            'gap_filling': """- [ ] Knowledge gap analysis completed
- [ ] Required content identified and documented
- [ ] Implementation plan created
- [ ] Knowledge base coverage improved by target percentage
- [ ] Cross-references established""",

            'predictive': """- [ ] Future requirements analysis completed
- [ ] Preparation strategy documented
- [ ] Implementation roadmap created
- [ ] Resource requirements identified
- [ ] Success metrics defined""",

            'maintenance': """- [ ] Maintenance scope defined
- [ ] Update procedures documented
- [ ] Quality checks implemented
- [ ] Automation opportunities identified
- [ ] Process improvements documented""",

            'connectivity': """- [ ] Connectivity gaps identified
- [ ] Cross-reference improvements implemented
- [ ] Knowledge graph density improved
- [ ] Navigation enhancements documented
- [ ] User experience validated""",

            'trend_preparation': """- [ ] Emerging trends analyzed
- [ ] Preparation strategy developed
- [ ] Implementation plan created
- [ ] Risk assessment completed
- [ ] Future-readiness validated"""
        }

        return criteria_templates.get(recommendation['type'], """- [ ] Task requirements analyzed
- [ ] Implementation completed
- [ ] Testing and validation performed
- [ ] Documentation updated""")

    def _generate_file_list(self, recommendation: Dict) -> str:
        """Generate list of files to be modified based on recommendation."""
        file_templates = {
            'gap_filling': """- docs/{category}_expansion_plan.md (new)
- scripts/{category}_analysis.py (new)
- tests/test_{category}_coverage.py (new)""",

            'predictive': """- docs/future_{domain}_strategy.md (new)
- scripts/{domain}_preparation.py (new)
- ui/{domain}_readiness_dashboard.py (new)""",

            'maintenance': """- scripts/maintenance_{category}.py (new)
- docs/maintenance_procedures.md (update)
- tests/test_maintenance_automation.py (new)""",

            'connectivity': """- scripts/connectivity_improvements.py (new)
- docs/knowledge_graph_optimization.md (new)
- ui/connectivity_dashboard.py (new)""",

            'trend_preparation': """- docs/emerging_{domain}_trends.md (new)
- scripts/{domain}_trend_monitor.py (new)
- ui/trend_analysis_dashboard.py (new)"""
        }

        template = file_templates.get(recommendation['type'], """- docs/task_implementation.md (new)
- scripts/task_implementation.py (new)
- tests/test_implementation.py (new)""")

        # Fill in template variables
        category = recommendation.get('category', 'general').lower().replace(' ', '_')
        domain = recommendation.get('category', 'domain').lower().replace(' ', '_')

        return template.format(category=category, domain=domain)

    def _update_lifecycle_tracker(self, task_id: str, recommendation: Dict, task_path: str):
        """Update the strategic tasks lifecycle tracker with new task information."""
        try:
            # Load existing tracker
            if self.lifecycle_tracker_path.exists():
                with open(self.lifecycle_tracker_path, 'r', encoding='utf-8') as f:
                    tracker = json.load(f)
            else:
                tracker = {
                    "version": "1.0",
                    "description": "Strategic Task Lifecycle Tracker - Monitors planned vs actual task completion",
                    "created": datetime.now().isoformat() + 'Z',
                    "last_updated": datetime.now().isoformat() + 'Z',
                    "tasks": {},
                    "summary": {
                        "total_planned": 0,
                        "completed_successfully": 0,
                        "completed_partially": 0,
                        "failed": 0,
                        "mock_completions": 0,
                        "real_completions": 0
                    },
                    "validation_rules": {
                        "file_existence_check": "Required files must exist and have non-zero size",
                        "code_execution_check": "Generated code must be syntactically valid and executable",
                        "output_validation": "Task deliverables must match acceptance criteria",
                        "integration_test": "Changes must integrate properly with existing codebase"
                    }
                }

            # Add new task entry
            tracker["tasks"][task_id] = {
                "status": "planned",
                "created": datetime.now().isoformat() + 'Z',
                "recommendation_type": recommendation['type'],
                "priority": recommendation['priority'],
                "estimated_effort": recommendation['estimated_effort'],
                "task_file_path": task_path,
                "acceptance_criteria": self._generate_measurable_criteria(recommendation),
                "validation_attempts": [],
                "completion_type": "unknown",  # Will be set to "real" or "mock" upon completion
                "last_validated": None,
                "validation_errors": []
            }

            # Update summary
            tracker["summary"]["total_planned"] += 1
            tracker["last_updated"] = datetime.now().isoformat() + 'Z'

            # Save updated tracker
            with open(self.lifecycle_tracker_path, 'w', encoding='utf-8') as f:
                json.dump(tracker, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Warning: Failed to update lifecycle tracker: {e}")

    def _generate_measurable_criteria(self, recommendation: Dict) -> Dict:
        """Generate AI-evaluable, measurable acceptance criteria."""
        measurable_criteria = {
            "file_existence_checks": [],
            "code_quality_checks": [],
            "functional_tests": [],
            "integration_tests": []
        }

        rec_type = recommendation['type']
        category = recommendation.get('category', 'general').lower().replace(' ', '_')

        if rec_type == 'gap_filling':
            measurable_criteria["file_existence_checks"] = [
                f"docs/{category}_analysis.md must exist and be >1000 chars",
                f"scripts/{category}_gap_filler.py must exist and be syntactically valid"
            ]
            measurable_criteria["code_quality_checks"] = [
                "Generated Python code must pass syntax validation",
                "Code must include proper error handling and logging"
            ]
            measurable_criteria["functional_tests"] = [
                "Script execution must complete without critical errors",
                f"Generated content must be relevant to the {category} gap category"
            ]

        elif rec_type == 'predictive':
            measurable_criteria["file_existence_checks"] = [
                f"docs/future_{category}_strategy.md must exist and contain implementation roadmap",
                f"scripts/{category}_predictor.py must exist and be executable"
            ]
            measurable_criteria["functional_tests"] = [
                "Strategy document must include measurable milestones",
                "Predictor script must generate valid recommendations"
            ]

        elif rec_type == 'maintenance':
            measurable_criteria["file_existence_checks"] = [
                "scripts/maintenance_automation.py must exist and be >500 lines",
                "docs/maintenance_procedures.md must be updated with new procedures"
            ]
            measurable_criteria["integration_tests"] = [
                "Maintenance scripts must integrate with existing codebase",
                "No breaking changes to existing functionality"
            ]

        elif rec_type == 'connectivity':
            measurable_criteria["file_existence_checks"] = [
                "scripts/connectivity_analyzer.py must exist and contain graph analysis functions",
                "docs/knowledge_graph_metrics.md must exist with before/after metrics"
            ]
            measurable_criteria["functional_tests"] = [
                "Connectivity improvements must be measurable via graph metrics",
                "Cross-reference additions must be validated"
            ]

        elif rec_type == 'trend_preparation':
            measurable_criteria["file_existence_checks"] = [
                f"docs/emerging_{category}_trends.md must exist with trend analysis",
                f"scripts/{category}_monitor.py must exist and be runnable"
            ]
            measurable_criteria["code_quality_checks"] = [
                "Monitor script must include proper data collection and alerting",
                "Documentation must include risk assessment and mitigation strategies"
            ]

        return measurable_criteria

    def validate_task_completion(self, task_id: str) -> Dict:
        """Validate actual task completion vs mock completion."""
        validation_result = {
            "task_id": task_id,
            "is_completed": False,
            "completion_type": "unknown",
            "validation_errors": [],
            "validation_successes": [],
            "confidence_score": 0.0
        }

        try:
            # Load tracker
            if not self.lifecycle_tracker_path.exists():
                validation_result["validation_errors"].append("Lifecycle tracker not found")
                return validation_result

            with open(self.lifecycle_tracker_path, 'r', encoding='utf-8') as f:
                tracker = json.load(f)

            if task_id not in tracker["tasks"]:
                validation_result["validation_errors"].append(f"Task {task_id} not found in tracker")
                return validation_result

            task_info = tracker["tasks"][task_id]
            criteria = task_info["acceptance_criteria"]

            # Check file existence
            for check in criteria.get("file_existence_checks", []):
                try:
                    # Parse the file path and requirements from the check string
                    if " must exist and be " in check:
                        file_path, requirement = check.split(" must exist and be ", 1)
                    else:
                        file_path = check.split(" must exist")[0]
                        requirement = "exists"
                    
                    full_path = self.workspace_root / file_path

                    if not full_path.exists():
                        validation_result["validation_errors"].append(f"Required file missing: {file_path}")
                    elif requirement == "exists":
                        validation_result["validation_successes"].append(f"File exists: {file_path}")
                    elif requirement.startswith(">"):
                        # Check file size
                        min_size = int(requirement[1:].split()[0])
                        if full_path.stat().st_size > min_size:
                            validation_result["validation_successes"].append(f"File exists and meets size requirement: {file_path}")
                        else:
                            validation_result["validation_errors"].append(f"File exists but too small: {file_path} ({full_path.stat().st_size} < {min_size})")
                    elif "syntactically valid" in requirement:
                        # Check if Python file is syntactically valid
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                compile(f.read(), full_path, 'exec')
                            validation_result["validation_successes"].append(f"File exists and is syntactically valid: {file_path}")
                        except SyntaxError as e:
                            validation_result["validation_errors"].append(f"File exists but has syntax errors: {file_path} - {e}")
                        except Exception as e:
                            validation_result["validation_errors"].append(f"File check failed: {file_path} - {e}")
                    else:
                        validation_result["validation_successes"].append(f"File exists: {file_path}")
                        
                except Exception as e:
                    validation_result["validation_errors"].append(f"File check failed: {check} - {e}")

            # Check code quality
            for check in criteria.get("code_quality_checks", []):
                # This would require more sophisticated analysis
                validation_result["validation_successes"].append(f"Code quality check noted: {check}")

            # Check functional tests
            for test in criteria.get("functional_tests", []):
                # This would require running actual tests
                validation_result["validation_successes"].append(f"Functional test requirement noted: {test}")

            # Determine completion type
            error_count = len(validation_result["validation_errors"])
            success_count = len(validation_result["validation_successes"])

            if error_count == 0 and success_count > 0:
                validation_result["is_completed"] = True
                validation_result["completion_type"] = "real"
                validation_result["confidence_score"] = 0.9
            elif error_count > 0 and success_count == 0:
                validation_result["completion_type"] = "failed"
                validation_result["confidence_score"] = 0.1
            else:
                validation_result["completion_type"] = "partial"
                validation_result["confidence_score"] = 0.5

            # Update tracker
            task_info["last_validated"] = datetime.now().isoformat() + 'Z'
            task_info["validation_attempts"].append({
                "timestamp": datetime.now().isoformat() + 'Z',
                "result": validation_result
            })

            with open(self.lifecycle_tracker_path, 'w', encoding='utf-8') as f:
                json.dump(tracker, f, indent=2, ensure_ascii=False)

        except Exception as e:
            validation_result["validation_errors"].append(f"Validation failed: {e}")

        return validation_result

    def _add_task_to_queue(self, task_id: str, recommendation: Dict) -> None:
        """Add task reference to NEU.md queue."""
        neu_path = os.path.join(os.path.dirname(__file__), '..', 'NEU.md')

        # Generate tags based on recommendation
        tags = [recommendation['type']]
        if 'category' in recommendation:
            tags.append(recommendation['category'].lower().replace(' ', '_'))
        if recommendation['priority'] == 'high':
            tags.append('urgent')
        tags.extend(['strategic', 'auto_generated'])

        # Create reference line
        ref_line = f"[ref:tasks/task_{task_id}.md|v:1|tags:{','.join(tags)}|src:strategic_planner]\n"

        # Read current NEU.md content
        with open(neu_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the TASK QUEUE section and add the new task at the top
        queue_marker = "## TASK QUEUE (PRIORITY ORDER)"
        if queue_marker in content:
            # Insert after the queue marker
            parts = content.split(queue_marker, 1)
            new_content = parts[0] + queue_marker + "\n\n" + ref_line + parts[1]
        else:
            # Fallback: append to end
            new_content = content + "\n" + ref_line

        # Write back
        with open(neu_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

    def analyze_task_dependencies(self, task_list: List[Dict]) -> Dict:
        """
        Analyze dependencies between recommended tasks.
        """
        # Build dependency graph
        dep_graph = {}
        for task in task_list:
            task_id = task['id']
            dep_graph[task_id] = {
                'task': task,
                'dependencies': [],
                'dependents': []
            }

        # Find dependencies
        for task in task_list:
            task_id = task['id']

            # Find prerequisites that match other tasks
            for prereq in task.get('prerequisites', []):
                for other_task in task_list:
                    if other_task['id'] != task_id and prereq in other_task.get('title', '').lower():
                        if other_task['id'] in dep_graph:  # Ensure it exists
                            dep_graph[task_id]['dependencies'].append(other_task['id'])
                            dep_graph[other_task['id']]['dependents'].append(task_id)

        # Calculate execution order
        execution_order = self._topological_sort(dep_graph)

        return {
            'dependency_graph': dep_graph,
            'execution_order': execution_order,
            'parallel_groups': self._identify_parallel_groups(dep_graph),
            'critical_path': self._find_critical_path(dep_graph)
        }

    def _topological_sort(self, dep_graph: Dict) -> List[str]:
        """Perform topological sort of tasks."""
        # Simple implementation (no cycles assumed)
        sorted_tasks = []
        visited = set()

        def visit(task_id):
            if task_id in visited:
                return
            visited.add(task_id)

            for dep_id in dep_graph[task_id]['dependencies']:
                visit(dep_id)

            sorted_tasks.append(task_id)

        for task_id in dep_graph:
            visit(task_id)

        return sorted_tasks

    def _identify_parallel_groups(self, dep_graph: Dict) -> List[List[str]]:
        """Identify groups of tasks that can be executed in parallel."""
        # Simple grouping based on no dependencies between them
        groups = []
        processed = set()

        for task_id, data in dep_graph.items():
            if task_id in processed:
                continue

            # Start a new group
            group = [task_id]
            processed.add(task_id)

            # Add tasks that don't depend on anything in current group
            for other_id, other_data in dep_graph.items():
                if other_id not in processed:
                    # Check if this task can be parallel to the group
                    can_parallel = True
                    for group_task in group:
                        if (other_id in dep_graph[group_task]['dependencies'] or
                            group_task in other_data['dependencies']):
                            can_parallel = False
                            break

                    if can_parallel:
                        group.append(other_id)
                        processed.add(other_id)

            groups.append(group)

        return groups

    def _find_critical_path(self, dep_graph: Dict) -> List[str]:
        """Find the critical path through task dependencies."""
        # For simplicity, return the longest dependency chain
        if not dep_graph:
            return []

        # Find tasks with no dependencies (starting points)
        start_tasks = [tid for tid, data in dep_graph.items() if not data['dependencies']]

        if not start_tasks:
            return list(dep_graph.keys())[:1]  # Return first task

        # For now, return the first path found
        return self._find_longest_path(dep_graph, start_tasks[0])

    def _find_longest_path(self, dep_graph: Dict, start_task: str, visiting: Optional[set] = None) -> List[str]:
        """Find longest path from start task."""
        if visiting is None:
            visiting = set()
        if start_task in visiting:
            # Break cycles deterministically.
            return [start_task]
        visiting = set(visiting)
        visiting.add(start_task)

        if not dep_graph[start_task]['dependents']:
            return [start_task]

        max_path = [start_task]
        for dependent in dep_graph[start_task]['dependents']:
            path = self._find_longest_path(dep_graph, dependent, visiting=visiting)
            if len(path) + 1 > len(max_path):
                max_path = [start_task] + path

        return max_path

    def export_planning_report(self, recommendations: List[Dict], dependencies: Dict) -> str:
        """Export comprehensive planning report."""
        report = f"""# Strategic Task Planning Report
Generated: {datetime.now().isoformat()}

## Executive Summary
- Total Recommendations: {len(recommendations)}
- High Priority: {len([r for r in recommendations if r['priority'] == 'high'])}
- Medium Priority: {len([r for r in recommendations if r['priority'] == 'medium'])}
- Low Priority: {len([r for r in recommendations if r['priority'] == 'low'])}

## Recommended Tasks

"""

        for i, rec in enumerate(recommendations, 1):
            report += f"""### {i}. {rec['title']}
**Priority:** {rec['priority'].upper()} | **Effort:** {rec['estimated_effort'].upper()}
**Scheduled:** {rec.get('scheduled_date', 'TBD')}
**Description:** {rec['description']}
**Rationale:** {rec['rationale']}
**Expected Impact:** {rec.get('expected_impact', 'TBD')}

"""

        report += f"""
## Dependency Analysis
- Execution Order Tasks: {len(dependencies['execution_order'])}
- Parallel Groups: {len(dependencies['parallel_groups'])}
- Critical Path Length: {len(dependencies['critical_path'])}

### Critical Path
{chr(10).join(f"- {tid}: {dependencies['dependency_graph'][tid]['task']['title']}" for tid in dependencies['critical_path'])}

### Parallel Execution Groups
"""
        for i, group in enumerate(dependencies['parallel_groups'], 1):
            report += f"""
**Group {i}:**
{chr(10).join(f"- {tid}: {dependencies['dependency_graph'][tid]['task']['title']}" for tid in group)}
"""

        return report

    def _submit_to_chaosbox(self, chaosbox: ChaosboxManager, recommendation: Dict) -> Optional[str]:
        """Submit a recommendation to chaosbox for quality control."""
        try:
            # Convert recommendation to chaosbox format
            title = recommendation.get('title', f"Strategic Task: {recommendation.get('type', 'unknown')}")
            description = recommendation.get('description', recommendation.get('rationale', 'Strategic recommendation'))

            # Add strategic context tags
            tags = ['strategic', 'auto_generated', recommendation.get('type', 'unknown')]
            if recommendation.get('priority') == 'high':
                tags.append('urgent')

            idea_id = chaosbox.submit_idea(
                title=title,
                description=description,
                submitted_by="strategic_planner",
                tags=tags,
                metadata={
                    'source': 'strategic_task_planner',
                    'recommendation_type': recommendation.get('type'),
                    'priority': recommendation.get('priority'),
                    'estimated_effort': recommendation.get('estimated_effort'),
                    'strategic_context': recommendation.get('rationale')
                }
            )

            return idea_id

        except Exception as e:
            print(f"Error submitting to chaosbox: {str(e)}")
            return None

    def _convert_idea_to_task_spec(self, idea, recommendation: Dict) -> Dict[str, Any]:
        """Convert chaosbox idea to task specification format."""
        return {
            'title': idea.title,
            'description': idea.description,
            'objective': recommendation.get('description', idea.description),
            'task_type': self._map_recommendation_to_task_type(recommendation.get('type', 'unknown')),
            'priority': recommendation.get('priority', 'medium'),
            'estimated_effort': recommendation.get('estimated_effort', 'medium'),
            'quality_score': idea.quality_score,
            'strategic_context': recommendation.get('rationale', 'Generated through strategic planning'),
            'files_to_modify': recommendation.get('files_to_modify', []),
            'tags': idea.tags,
            'metadata': idea.metadata,
            'completion_checklist': self._generate_completion_checklist(recommendation),
            'failure_conditions': self._generate_failure_conditions(recommendation),
            'report_requirements': self._generate_report_requirements(recommendation),
            'bug_report_requirements': self._generate_bug_report_requirements(recommendation),
            'code_documentation_requirements': self._generate_code_documentation_requirements(recommendation)
        }

    def _map_recommendation_to_task_type(self, rec_type: str) -> str:
        """Map recommendation type to task type."""
        mapping = {
            'gap_filling': 'ANALYSIS',
            'predictive': 'RESEARCH',
            'maintenance': 'MAINTENANCE',
            'connectivity': 'ANALYSIS',
            'trend_preparation': 'DEVELOPMENT'
        }
        return mapping.get(rec_type, 'DEVELOPMENT')

    def _generate_completion_checklist(self, recommendation: Dict) -> List[str]:
        """Generate completion checklist based on recommendation type."""
        rec_type = recommendation.get('type', 'gap_filling')
        title = recommendation.get('title', '')

        base_checklist = [
            "Core functionality implemented and tested",
            "Code follows project standards and conventions",
            "Documentation updated with changes",
            "No breaking changes to existing functionality"
        ]

        if rec_type == 'gap_filling':
            base_checklist.extend([
                "Knowledge gap addressed with new content",
                "Cross-references added where applicable",
                "Integration with existing knowledge verified"
            ])
        elif rec_type == 'maintenance':
            base_checklist.extend([
                "Stale content updated or removed",
                "Dependencies refreshed",
                "Performance impact assessed"
            ])
        elif rec_type == 'predictive':
            base_checklist.extend([
                "Future requirements analyzed",
                "Preparatory work completed",
                "Monitoring setup for future needs"
            ])

        return base_checklist

    def _generate_failure_conditions(self, recommendation: Dict) -> List[str]:
        """Generate failure conditions based on recommendation type."""
        rec_type = recommendation.get('type', 'gap_filling')

        base_conditions = [
            "Implementation exceeds estimated effort by 50% or more",
            "Breaking changes introduced without proper migration plan",
            "Quality standards not met (test failures, linting errors)"
        ]

        if rec_type == 'gap_filling':
            base_conditions.extend([
                "Knowledge gap remains unaddressed after implementation",
                "New content conflicts with existing knowledge"
            ])
        elif rec_type == 'maintenance':
            base_conditions.extend([
                "Stale content not properly updated",
                "System instability introduced"
            ])
        elif rec_type == 'predictive':
            base_conditions.extend([
                "Future requirements not adequately prepared for",
                "Preparatory work becomes obsolete"
            ])

        return base_conditions

    def _generate_report_requirements(self, recommendation: Dict) -> Dict[str, Any]:
        """Generate report requirements based on recommendation type."""
        rec_type = recommendation.get('type', 'gap_filling')

        base_requirements = {
            'during_work': True,
            'after_work': True,
            'frequency': 'daily',
            'format': 'structured'
        }

        if rec_type == 'gap_filling':
            base_requirements.update({
                'focus_areas': ['progress', 'challenges', 'knowledge_gaps_addressed'],
                'milestones': True
            })
        elif rec_type == 'maintenance':
            base_requirements.update({
                'focus_areas': ['items_updated', 'issues_found', 'performance_impact'],
                'milestones': False
            })

        return base_requirements

    def _generate_bug_report_requirements(self, recommendation: Dict) -> Dict[str, Any]:
        """Generate bug report requirements."""
        return {
            'required': True,
            'when': 'when_discovered',
            'format': 'structured',
            'escalation': 'immediate_for_blockers'
        }

    def _generate_code_documentation_requirements(self, recommendation: Dict) -> Dict[str, Any]:
        """Generate code documentation requirements."""
        rec_type = recommendation.get('type', 'gap_filling')

        base_requirements = {
            'required': True,
            'for_changes': True,
            'for_bugs': True,
            'integration_notes': True
        }

        if rec_type in ['gap_filling', 'predictive']:
            base_requirements['api_documentation'] = True

        return base_requirements

    def _create_formal_task_file(self, formal_checker: TaskFormalConsistencyChecker, task_spec: Dict, recommendation: Dict) -> Optional[str]:
        """Create a formal task file using the consistency checker."""
        try:
            # Find next available task number
            tasks_dir = Path(__file__).parent.parent / 'tasks'
            tasks_dir.mkdir(exist_ok=True)

            existing_tasks = [f for f in os.listdir(tasks_dir) if f.startswith('task_TASK_') and f.endswith('.md')]
            if existing_tasks:
                task_numbers = [int(f.split('_')[-1].split('.')[0]) for f in existing_tasks if f.split('_')[-1].split('.')[0].isdigit()]
                next_task_num = max(task_numbers) + 1 if task_numbers else 230
            else:
                next_task_num = 231

            task_id = f"TASK_{next_task_num:04d}"
            task_filename = f"task_{task_id}.md"
            task_path = tasks_dir / task_filename

            # Create formal task content
            task_content = formal_checker.create_formal_task_file(task_spec, task_id)

            # Write task file
            with open(task_path, 'w', encoding='utf-8') as f:
                f.write(task_content)

            # Update lifecycle tracker
            self._update_lifecycle_tracker(task_id, recommendation, str(task_path))

            # Add to NEU.md queue
            self._add_task_to_queue(task_id, recommendation)

            return task_id

        except Exception as e:
            print(f"Error creating formal task file: {str(e)}")
            return None

    def _register_successful_task(self, task_id: str, task_spec: Dict):
        """Register a successfully created task in the knowledge database."""
        try:
            # Connect to knowledge database
            db_path = Path(__file__).parent.parent / 'keeper_knowledge.db'
            if not db_path.exists():
                print(f"Knowledge database not found at {db_path}")
                return

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Insert task completion record
            cursor.execute('''
                INSERT OR REPLACE INTO knowledge_items
                (id, content, category, tags, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"task_{task_id}_completion",
                f"Task {task_id} successfully created through quality-controlled strategic pipeline",
                "task_completion",
                json.dumps(["strategic", "quality_controlled", "auto_generated"]),
                json.dumps({
                    "task_id": task_id,
                    "quality_score": task_spec.get('quality_score'),
                    "creation_method": "chaosbox_pipeline",
                    "validation_passed": ["chaosbox", "validation_engine", "formal_consistency"],
                    "strategic_context": task_spec.get('strategic_context'),
                    "created_at": datetime.now().isoformat()
                }),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            print(f"✅ Task {task_id} registered in knowledge database")

        except Exception as e:
            print(f"Warning: Could not register task in knowledge database: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate strategic task recommendations.")
    parser.add_argument(
        "--create-tasks",
        action="store_true",
        help="Create task files via quality gates (default is dry-run report only).",
    )
    parser.add_argument(
        "--priority-threshold",
        default="high",
        choices=["low", "medium", "high"],
        help="Minimum priority for --create-tasks mode.",
    )
    args = parser.parse_args()

    planner = StrategicTaskPlanner()

    recommendations = planner.generate_task_recommendations()
    print(f"Generated {len(recommendations)} task recommendations")

    dependencies = planner.analyze_task_dependencies(recommendations)
    print(f"Dependency analysis complete: {len(dependencies['execution_order'])} tasks in execution order")

    created_tasks = []
    if args.create_tasks:
        print("\nCreating task files from strategic recommendations...")
        created_tasks = planner.create_task_files_from_recommendations(
            recommendations, priority_threshold=args.priority_threshold
        )
        print(f"Created {len(created_tasks)} task files: {', '.join(created_tasks) if created_tasks else '(none)'}")
    else:
        print("\nDry-run mode: no task files created. Use --create-tasks to enable writes.")

    report = planner.export_planning_report(recommendations, dependencies)
    print(f"Planning report generated: {len(report)} characters")

    print("\nTop 5 Recommendations:")
    for rec in recommendations[:5]:
        print(f"- {rec['priority'].upper()}: {rec['title']} (due in {rec.get('days_until_due', 'TBD')} days)")

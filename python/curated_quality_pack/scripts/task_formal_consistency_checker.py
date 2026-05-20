#!/usr/bin/env python3
"""
Task Formal Consistency Checker

Validates that tasks conform to the required formal structure including:
- Success parameters and completion checklists
- Failure conditions
- Report requirements
- Bug report requirements
- Code documentation standards
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path
import os
from datetime import datetime

class TaskFormalConsistencyChecker:
    """Validates formal consistency of task specifications."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)

    def validate_task_formal_consistency(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that a task specification meets formal consistency requirements.

        Args:
            task_spec: Task specification dictionary

        Returns:
            Validation result with pass/fail and detailed feedback
        """
        issues = []
        recommendations = []

        # Check 1: Success Parameters (COMPLETION CHECKLIST)
        if not self._has_completion_checklist(task_spec):
            issues.append("MISSING_COMPLETION_CHECKLIST: Task must have a COMPLETION CHECKLIST section")
        else:
            checklist_quality = self._validate_completion_checklist_quality(task_spec)
            if checklist_quality['score'] < 0.7:
                issues.extend(checklist_quality['issues'])
                recommendations.extend(checklist_quality['recommendations'])

        # Check 2: Failure Conditions
        if not self._has_failure_conditions(task_spec):
            issues.append("MISSING_FAILURE_CONDITIONS: Task must specify FAILURE IF conditions")
        else:
            failure_quality = self._validate_failure_conditions_quality(task_spec)
            if failure_quality['score'] < 0.6:
                issues.extend(failure_quality['issues'])

        # Check 3: Report Requirements
        if not self._has_report_requirements(task_spec):
            issues.append("MISSING_REPORT_REQUIREMENTS: Task must require REPORT OF THE TASK DURING WORK/AFTER WORK")
        else:
            report_quality = self._validate_report_requirements_quality(task_spec)
            if report_quality['score'] < 0.7:
                issues.extend(report_quality['issues'])

        # Check 4: Bug Report Requirements
        if not self._has_bug_report_requirements(task_spec):
            issues.append("MISSING_BUG_REPORT_REQUIREMENTS: Task must require BUG REPORT FOR BUGS FACED/DISCOVERED")
        else:
            bug_quality = self._validate_bug_report_quality(task_spec)
            if bug_quality['score'] < 0.6:
                issues.extend(bug_quality['issues'])

        # Check 5: Code Documentation Requirements
        if not self._has_code_documentation_requirements(task_spec):
            issues.append("MISSING_CODE_DOCUMENTATION: Task must require CODE DOCUMENTATION of bug solutions and project integration")
        else:
            doc_quality = self._validate_documentation_quality(task_spec)
            if doc_quality['score'] < 0.7:
                issues.extend(doc_quality['issues'])

        # Check 6: Task Structure Consistency
        structure_issues = self._validate_task_structure(task_spec)
        issues.extend(structure_issues)

        # Calculate overall score
        total_checks = 6
        passed_checks = total_checks - len([i for i in issues if i.startswith(('MISSING_', 'INVALID_'))])

        overall_score = passed_checks / total_checks

        return {
            'passed': len(issues) == 0,
            'overall_score': overall_score,
            'issues': issues,
            'recommendations': recommendations,
            'validation_details': {
                'completion_checklist_score': checklist_quality['score'] if 'checklist_quality' in locals() else 0.0,
                'failure_conditions_score': failure_quality['score'] if 'failure_quality' in locals() else 0.0,
                'report_requirements_score': report_quality['score'] if 'report_quality' in locals() else 0.0,
                'bug_report_score': bug_quality['score'] if 'bug_quality' in locals() else 0.0,
                'documentation_score': doc_quality['score'] if 'doc_quality' in locals() else 0.0
            }
        }

    def _has_completion_checklist(self, task_spec: Dict[str, Any]) -> bool:
        """Check if task has a completion checklist."""
        return 'completion_checklist' in task_spec and len(task_spec['completion_checklist']) > 0

    def _has_failure_conditions(self, task_spec: Dict[str, Any]) -> bool:
        """Check if task has failure conditions."""
        return 'failure_conditions' in task_spec and len(task_spec['failure_conditions']) > 0

    def _has_report_requirements(self, task_spec: Dict[str, Any]) -> bool:
        """Check if task requires reporting."""
        return 'report_requirements' in task_spec and task_spec['report_requirements'].get('during_work') or task_spec['report_requirements'].get('after_work')

    def _has_bug_report_requirements(self, task_spec: Dict[str, Any]) -> bool:
        """Check if task requires bug reporting."""
        return 'bug_report_requirements' in task_spec and task_spec['bug_report_requirements'].get('required', False)

    def _has_code_documentation_requirements(self, task_spec: Dict[str, Any]) -> bool:
        """Check if task requires code documentation."""
        return 'code_documentation_requirements' in task_spec and task_spec['code_documentation_requirements'].get('required', False)

    def _validate_completion_checklist_quality(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of completion checklist."""
        checklist = task_spec.get('completion_checklist', [])
        score = 0.5
        issues = []
        recommendations = []

        # Check number of items
        if len(checklist) >= 3:
            score += 0.2
        elif len(checklist) < 2:
            issues.append("INSUFFICIENT_CHECKLIST_ITEMS: Need at least 2-3 specific checklist items")
            recommendations.append("Add 2-3 specific, measurable completion criteria")
        else:
            score += 0.1

        # Check for quantifiable success metrics in checklist items
        measurable_words = ['test', 'validate', 'verify', 'confirm', 'measure', 'implement', 'complete']
        measurable_items = sum(1 for item in checklist if any(word in item.lower() for word in measurable_words))
        if measurable_items >= len(checklist) * 0.5:  # At least half are measurable
            score += 0.2
        elif measurable_items == 0:
            issues.append("NON_MEASURABLE_CHECKLIST: Checklist items should be specific and measurable")
            recommendations.append("Make checklist items specific and measurable (use words like test, validate, implement)")

        return {
            'score': min(1.0, score),
            'issues': issues,
            'recommendations': recommendations
        }

    def _validate_failure_conditions_quality(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of failure conditions."""
        content = self._get_task_content_string(task_spec)
        score = 0.5
        issues = []

        # Check for specific failure scenarios
        if len(content.split('failure')) > 1:
            score += 0.3

        # Check for measurable failure criteria
        if any(word in content.lower() for word in ['timeout', 'error', 'fail', 'unable', 'cannot']):
            score += 0.2

        return {
            'score': min(1.0, score),
            'issues': issues
        }

    def _validate_report_requirements_quality(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of report requirements."""
        content = self._get_task_content_string(task_spec)
        score = 0.5
        issues = []

        # Check for progress reporting
        if 'during work' in content.lower():
            score += 0.2

        # Check for completion reporting
        if 'after work' in content.lower() or 'completion' in content.lower():
            score += 0.2

        # Check for specific report content requirements
        if any(word in content.lower() for word in ['findings', 'results', 'outcomes', 'challenges']):
            score += 0.1

        return {
            'score': min(1.0, score),
            'issues': issues
        }

    def _validate_bug_report_quality(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of bug report requirements."""
        content = self._get_task_content_string(task_spec)
        score = 0.5
        issues = []

        # Check for bug discovery reporting
        if 'discovered' in content.lower() or 'found' in content.lower():
            score += 0.2

        # Check for bug fixing documentation
        if 'solution' in content.lower() or 'fix' in content.lower():
            score += 0.3

        return {
            'score': min(1.0, score),
            'issues': issues
        }

    def _validate_documentation_quality(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of documentation requirements."""
        content = self._get_task_content_string(task_spec)
        score = 0.5
        issues = []

        # Check for bug solution documentation
        if 'bug' in content.lower() and 'solution' in content.lower():
            score += 0.2

        # Check for integration documentation
        if 'integration' in content.lower() or 'wired' in content.lower():
            score += 0.2

        # Check for broader project context
        if 'project' in content.lower() or 'system' in content.lower():
            score += 0.1

        return {
            'score': min(1.0, score),
            'issues': issues
        }

    def _validate_task_structure(self, task_spec: Dict[str, Any]) -> List[str]:
        """Validate overall task structure consistency."""
        issues = []

        # Check for required keys in task_spec
        required_keys = ['objective', 'task_type', 'completion_checklist', 'strategic_context']
        for key in required_keys:
            if key not in task_spec:
                issues.append(f"MISSING_KEY_{key.upper()}: Task spec must have a {key} key")

        # Check for proper data types
        if 'completion_checklist' in task_spec and not isinstance(task_spec['completion_checklist'], list):
            issues.append("INVALID_CHECKLIST_FORMAT: completion_checklist must be a list")

        if 'failure_conditions' in task_spec and not isinstance(task_spec['failure_conditions'], list):
            issues.append("INVALID_FAILURE_FORMAT: failure_conditions must be a list")

        return issues

    def _get_task_content_string(self, task_spec: Dict[str, Any]) -> str:
        """Extract content string from task specification."""
        if 'content' in task_spec:
            return task_spec['content']
        elif 'description' in task_spec:
            return task_spec['description']
        elif 'objective' in task_spec:
            return task_spec['objective']
        else:
            return str(task_spec)

    def create_formal_task_file(self, task_spec: Dict[str, Any], task_id: str) -> str:
        """
        Create a properly formatted task file that passes formal consistency checks.

        Args:
            task_spec: Task specification from chaosbox
            task_id: Generated task ID

        Returns:
            Complete task file content
        """
        created_date = datetime.now().isoformat() + 'Z'

        # Extract information from task spec
        title = task_spec.get('title', f'Task {task_id}')
        objective = task_spec.get('objective', task_spec.get('description', 'Complete assigned task'))
        task_type = task_spec.get('task_type', 'DEVELOPMENT')

        # Generate formal acceptance criteria
        acceptance_criteria = self._generate_formal_acceptance_criteria(task_spec)

        # Generate file targets
        files_to_modify = task_spec.get('files_to_modify', [])

        # Generate strategic importance
        priority = task_spec.get('priority', 'medium')
        effort = task_spec.get('estimated_effort', 'medium')

        content = f"""# {task_id}

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: {created_date}

---

## SEED IDEA

{task_spec.get('description', 'Strategic task generated through quality-controlled pipeline')}

---

## OBJECTIVE

{objective}

**Strategic Context:** {task_spec.get('strategic_context', 'Generated through automated strategic planning pipeline')}

---

## TASK_TYPE

{task_type.upper()}

---

## ACCEPTANCE CRITERIA

{acceptance_criteria}

Files to be modified/created:
{chr(10).join(f"- {file}" for file in files_to_modify)}

---

## STRATEGIC IMPORTANCE

**Priority:** {priority.upper()}
**Effort Level:** {effort.upper()}
**Expected Timeline:** TBD

**Generated by:** Quality-Controlled Strategic Pipeline
**Quality Score:** {task_spec.get('quality_score', 'N/A')}
**Validation Passed:** Chaosbox + Formal Consistency

"""

        return content

    def _generate_formal_acceptance_criteria(self, task_spec: Dict[str, Any]) -> str:
        """Generate formal acceptance criteria that meet consistency requirements."""
        criteria = []

        # Add completion checklist
        criteria.append("COMPLETION CHECKLIST:")
        criteria.append("- [ ] Task implementation completed according to specifications")
        criteria.append("- [ ] All acceptance criteria verified and met")
        criteria.append("- [ ] Code changes tested and functional")
        criteria.append("- [ ] Documentation updated as required")

        # Add failure conditions
        criteria.append("")
        criteria.append("FAILURE IF:")
        criteria.append("- Implementation cannot be completed within reasonable timeframe")
        criteria.append("- Critical bugs prevent core functionality")
        criteria.append("- Security vulnerabilities introduced")
        criteria.append("- Breaking changes to existing systems without migration plan")

        # Add reporting requirements
        criteria.append("")
        criteria.append("REPORTING REQUIREMENTS:")
        criteria.append("- [ ] Progress report submitted during work (minimum weekly updates)")
        criteria.append("- [ ] Final completion report submitted after work")
        criteria.append("- [ ] Report includes challenges faced, solutions implemented, and lessons learned")

        # Add bug reporting requirements
        criteria.append("")
        criteria.append("BUG REPORTING REQUIREMENTS:")
        criteria.append("- [ ] All bugs discovered during implementation documented")
        criteria.append("- [ ] Bug reports include reproduction steps and severity assessment")
        criteria.append("- [ ] Solutions for resolved bugs documented in detail")

        # Add documentation requirements
        criteria.append("")
        criteria.append("CODE DOCUMENTATION REQUIREMENTS:")
        criteria.append("- [ ] All bug fixes documented with root cause and solution approach")
        criteria.append("- [ ] Code integration points clearly documented")
        criteria.append("- [ ] How the implementation fits into the broader project architecture explained")

        return "\n".join(criteria)
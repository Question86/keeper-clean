#!/usr/bin/env python3
"""
Transformation Pipeline - Convert Raw Ideas to Standardized Task Specifications

Transforms validated seed ideas into well-structured task specifications
following the project's task format and conventions.
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from chaosbox.chaosbox_manager import SeedIdea

class TransformationPipeline:
    """Pipeline for transforming raw ideas into standardized task specs."""

    def __init__(self, workspace_root: str = "."):
        self.task_id_pattern = re.compile(r'TASK_(\d{4})')
        self.workspace = Path(workspace_root)
        self.next_task_id = self._get_next_task_id()

    def _get_next_task_id(self) -> int:
        """Get the next available task ID."""
        tasks_dir = self.workspace / "tasks"
        if not tasks_dir.exists():
            return 1

        max_id = 0
        for task_file in tasks_dir.glob("task_TASK_*.md"):
            m = re.search(r"TASK_(\d{4})", task_file.name)
            if not m:
                continue
            max_id = max(max_id, int(m.group(1)))
        return max_id + 1 if max_id > 0 else 1

    def transform_idea(self, idea: SeedIdea) -> Dict[str, Any]:
        """
        Transform a validated idea into a standardized task specification.

        Args:
            idea: The validated seed idea

        Returns:
            Task specification dictionary
        """
        task_id = f"TASK_{self.next_task_id:04d}"
        self.next_task_id += 1

        # Extract components from idea
        objective = self._extract_objective(idea)
        task_type = self._determine_task_type(idea)
        acceptance_criteria = self._generate_acceptance_criteria(idea, task_type)
        technical_details = self._extract_technical_details(idea)
        files_to_modify = self._identify_files_to_modify(idea)

        # Generate task spec
        task_spec = {
            "task_id": task_id,
            "title": idea.title,
            "objective": objective,
            "task_type": task_type,
            "acceptance_criteria": acceptance_criteria,
            "technical_details": technical_details,
            "files_to_modify": files_to_modify,
            "priority": self._determine_priority(idea),
            "estimated_effort": self._estimate_effort(idea, task_type),
            "dependencies": self._identify_dependencies(idea),
            "created_from_idea": idea.idea_id,
            "quality_score": idea.quality_score,
            "tags": idea.tags,
            "metadata": {
                "submitted_by": idea.submitted_by,
                "submitted_at": idea.submitted_at,
                "transformed_at": datetime.now(timezone.utc).isoformat(),
                "chaosbox_quality_score": idea.quality_score
            }
        }

        return {
            "success": True,
            "task_spec": task_spec,
            "task_id": task_id
        }

    def _extract_objective(self, idea: SeedIdea) -> str:
        """Extract and refine the core objective from the idea."""
        description = idea.description

        # Look for explicit objective statements
        objective_patterns = [
            r'(?:objective|goal|aim|purpose)[\s:]+(.+?)(?:\n|$)',
            r'(?:implement|create|build|develop|add)[\s:]+(.+?)(?:\n|$)',
            r'(?:to\s+.+?\s+(?:implement|create|build|develop|add|improve|fix))(.+?)(?:\n|$)'
        ]

        for pattern in objective_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                objective = match.group(1).strip()
                if len(objective) > 20:  # Ensure it's substantial
                    return self._clean_objective(objective)

        # Fallback: Use first substantial sentence
        sentences = re.split(r'[.!?]+', description)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30 and len(sentence) < 200:
                return self._clean_objective(sentence)

        # Last resort: Truncate description
        return self._clean_objective(description[:150] + "...")

    def _clean_objective(self, text: str) -> str:
        """Clean and standardize objective text."""
        # Capitalize first letter
        text = text[0].upper() + text[1:] if text else ""

        # Remove trailing punctuation except periods
        text = re.sub(r'[,;:]$', '', text)

        # Ensure ends with period
        if not text.endswith('.'):
            text += '.'

        return text

    def _determine_task_type(self, idea: SeedIdea) -> str:
        """Determine the appropriate task type based on idea content."""
        text = f"{idea.title} {idea.description}".lower()

        # Implementation indicators
        implementation_keywords = [
            'implement', 'create', 'build', 'develop', 'add', 'integrate',
            'code', 'algorithm', 'api', 'framework', 'library', 'module'
        ]

        # Analysis indicators
        analysis_keywords = [
            'analyze', 'assess', 'evaluate', 'review', 'audit', 'benchmark',
            'research', 'investigate', 'study', 'examine'
        ]

        # Maintenance indicators
        maintenance_keywords = [
            'fix', 'resolve', 'optimize', 'improve', 'refactor', 'update',
            'maintain', 'clean', 'organize', 'document'
        ]

        impl_score = sum(1 for kw in implementation_keywords if kw in text)
        analysis_score = sum(1 for kw in analysis_keywords if kw in text)
        maint_score = sum(1 for kw in maintenance_keywords if kw in text)

        max_score = max(impl_score, analysis_score, maint_score)

        if max_score == 0:
            return "ANALYSIS"  # Default

        if impl_score == max_score:
            return "IMPLEMENTATION"
        elif analysis_score == max_score:
            return "ANALYSIS"
        else:
            return "MAINTENANCE"

    def _generate_acceptance_criteria(self, idea: SeedIdea, task_type: str) -> List[str]:
        """Generate acceptance criteria based on idea and task type."""
        criteria = []

        # Task-type specific criteria
        if task_type == "IMPLEMENTATION":
            criteria.extend([
                f"[ ] Create functional {self._extract_main_component(idea)}",
                "[ ] Implement comprehensive error handling",
                "[ ] Add unit tests with >80% coverage",
                "[ ] Update documentation and usage examples",
                "[ ] Validate integration with existing systems"
            ])
        elif task_type == "ANALYSIS":
            criteria.extend([
                "[ ] Complete comprehensive analysis report",
                "[ ] Identify key findings and recommendations",
                "[ ] Validate analysis methodology",
                "[ ] Document assumptions and limitations",
                "[ ] Present actionable insights"
            ])
        else:  # MAINTENANCE
            criteria.extend([
                "[ ] Resolve identified issues",
                "[ ] Improve code quality metrics",
                "[ ] Maintain backward compatibility",
                "[ ] Update tests and documentation",
                "[ ] Validate no regressions introduced"
            ])

        # Idea-specific criteria
        main_component = self._extract_main_component(idea)
        if main_component:
            criteria.append(f"[ ] Successfully {task_type.lower()} {main_component}")

        return criteria[:6]  # Limit to 6 criteria

    def _extract_main_component(self, idea: SeedIdea) -> str:
        """Extract the main component or feature from the idea."""
        text = f"{idea.title} {idea.description}"

        # Look for nouns that might be components
        component_patterns = [
            r'(?:create|implement|build|add|develop)\s+(?:a|an|the)?\s*([a-zA-Z][a-zA-Z\s]+?)(?:\s+that|\s+to|\s+for|\s+with|$)',
            r'([A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]+)*)'  # CamelCase or TitleCase words
        ]

        for pattern in component_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                component = match.strip()
                if 3 < len(component) < 50 and not component.lower() in ['system', 'module', 'component', 'feature']:
                    return component.lower()

        return "specified functionality"

    def _extract_technical_details(self, idea: SeedIdea) -> str:
        """Extract technical details and requirements."""
        text = idea.description

        # Look for technical sections or requirements
        technical_indicators = [
            'requirements', 'technical', 'implementation', 'architecture',
            'dependencies', 'constraints', 'considerations'
        ]

        details = []
        sentences = re.split(r'[.!?]+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if any(indicator in sentence.lower() for indicator in technical_indicators):
                details.append(sentence)

        if details:
            return " ".join(details)
        else:
            # Generate basic technical details
            task_type = self._determine_task_type(idea)
            if task_type == "IMPLEMENTATION":
                return "Implementation requires following project coding standards, error handling patterns, and integration with existing architecture."
            elif task_type == "ANALYSIS":
                return "Analysis should use appropriate methodologies, document assumptions, and provide actionable recommendations."
            else:
                return "Maintenance work should preserve existing functionality while improving code quality and performance."

    def _identify_files_to_modify(self, idea: SeedIdea) -> List[str]:
        """Identify files that would likely need modification."""
        # This is a simplified heuristic - in practice would use more sophisticated analysis
        files = []

        text = f"{idea.title} {idea.description}".lower()

        # Common file patterns based on content
        if 'api' in text or 'endpoint' in text:
            files.append("loop_cockpit.py - Add API endpoints")
        if 'ui' in text or 'interface' in text or 'dashboard' in text:
            files.append("HTML/CSS/JS files - Update user interface")
        if 'database' in text or 'storage' in text:
            files.append("knowledge_db.py or relevant data storage")
        if 'test' in text:
            files.append("test_*.py - Add test cases")
        if 'config' in text:
            files.append("config.json - Update configuration")

        # Default files
        if not files:
            files.append("Relevant module files - Implementation")
            files.append("test_*.py - Add tests")
            files.append("README.md - Update documentation")

        return files

    def _determine_priority(self, idea: SeedIdea) -> str:
        """Determine task priority based on idea content and quality."""
        if idea.quality_score and idea.quality_score > 0.8:
            return "HIGH"
        elif idea.quality_score and idea.quality_score > 0.6:
            return "MEDIUM"
        else:
            return "LOW"

    def _estimate_effort(self, idea: SeedIdea, task_type: str) -> str:
        """Estimate effort level based on idea complexity."""
        text = f"{idea.title} {idea.description}"

        # Simple complexity heuristics
        word_count = len(text.split())
        has_multiple_components = len(re.findall(r'(?:and|or|also|additionally)', text)) > 2
        has_technical_terms = len(re.findall(r'\b(?:api|database|algorithm|framework|integration)\b', text, re.IGNORECASE)) > 1

        complexity_score = 0
        if word_count > 100:
            complexity_score += 1
        if has_multiple_components:
            complexity_score += 1
        if has_technical_terms:
            complexity_score += 1

        if task_type == "IMPLEMENTATION":
            complexity_score += 1  # Implementation is generally more effort

        if complexity_score >= 3:
            return "HIGH"
        elif complexity_score >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def _identify_dependencies(self, idea: SeedIdea) -> List[str]:
        """Identify potential task dependencies."""
        # Simplified dependency identification
        dependencies = []

        text = f"{idea.title} {idea.description}".lower()

        if 'database' in text and 'api' in text:
            dependencies.append("Database schema and API design")
        if 'ui' in text and 'backend' in text:
            dependencies.append("Backend API implementation")
        if 'test' in text:
            dependencies.append("Core functionality implementation")

# MODE: SCRIPT\n\n"""Comprehensive Knowledge Extraction System for MD Files

This module implements TASK_0058: Extract structured knowledge from all reports, tasks,
archives, and documentation MD files to maximize learning effectiveness and enable
deep context-aware search capabilities.

Specialized parsers for different file types:
- Reports: Task completion reports with structured sections
- Tasks: Task definitions with objectives, criteria, deliverables
- Archives: Historical loop data with lessons learned
- Docs: Architecture and operational documentation
- Root files: Core project documentation

Integration with existing knowledge_db.py for storage and search.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from knowledge_db import KnowledgeDB
from loop_guardrails import read_text


@dataclass
class ExtractionResult:
    """Result of knowledge extraction from a single file."""
    file_path: Path
    file_type: str  # 'report', 'task', 'archive', 'doc', 'root'
    entities_extracted: int
    confidence_score: float  # 0.0 to 1.0
    metadata: Dict[str, Any]
    extraction_errors: List[str]
    entities: List[Dict[str, Any]] = None  # Add this field


class ComprehensiveExtractor:
    """Comprehensive knowledge extraction system for all MD file types."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.knowledge_db = KnowledgeDB(workspace_root)

        # File type patterns
        self.file_patterns = {
            'report': re.compile(r'reports[/\\]report_TASK_\d+_L\d+_v\d+\.md$'),
            'task': re.compile(r'tasks[/\\]task_TASK_\d+\.md$'),
            'archive': re.compile(r'archive[/\\]ARCHIV_\d+\.md$'),
            'doc': re.compile(r'docs[/\\].*\.md$'),
            'root': re.compile(r'(?!.*/).*\.md$')  # Files in root directory
        }

        # Section patterns for different file types
        self.section_patterns = {
            'report': {
                'executive_summary': re.compile(r'^## EXECUTIVE SUMMARY', re.MULTILINE | re.IGNORECASE),
                'knowledge_usage': re.compile(r'^## KNOWLEDGE DATABASE USAGE', re.MULTILINE | re.IGNORECASE),
                'issues_resolved': re.compile(r'^## ISSUES RESOLVED', re.MULTILINE | re.IGNORECASE),
                'validation_results': re.compile(r'^## VALIDATION RESULTS', re.MULTILINE | re.IGNORECASE),
                'technical_approach': re.compile(r'^## TECHNICAL APPROACH', re.MULTILINE | re.IGNORECASE),
                'implementation_details': re.compile(r'^## IMPLEMENTATION DETAILS', re.MULTILINE | re.IGNORECASE)
            },
            'task': {
                'objective': re.compile(r'^\*\*OBJECTIVE:\*\*', re.MULTILINE | re.IGNORECASE),
                'acceptance_criteria': re.compile(r'^\*\*ACCEPTANCE CRITERIA:\*\*', re.MULTILINE | re.IGNORECASE),
                'scope': re.compile(r'^\*\*SCOPE:\*\*', re.MULTILINE | re.IGNORECASE),
                'deliverables': re.compile(r'^\*\*DELIVERABLES:\*\*', re.MULTILINE | re.IGNORECASE),
                'technical_approach': re.compile(r'^\*\*TECHNICAL APPROACH:\*\*', re.MULTILINE | re.IGNORECASE)
            },
            'archive': {
                'loop_summary': re.compile(r'^## LOOP SUMMARY', re.MULTILINE | re.IGNORECASE),
                'tasks_finalization': re.compile(r'^## TASKS AT FINALIZATION', re.MULTILINE | re.IGNORECASE),
                'lessons_learned': re.compile(r'^## LESSONS LEARNED', re.MULTILINE | re.IGNORECASE)
            },
            'doc': {
                'purpose': re.compile(r'^## PURPOSE', re.MULTILINE | re.IGNORECASE),
                'core_concepts': re.compile(r'^## CORE CONCEPTS', re.MULTILINE | re.IGNORECASE),
                'architecture': re.compile(r'^## ARCHITECTURE', re.MULTILINE | re.IGNORECASE),
                'operations': re.compile(r'^## OPERATIONS', re.MULTILINE | re.IGNORECASE)
            }
        }

    def extract_from_all_files(self) -> Dict[str, List[ExtractionResult]]:
        """Extract knowledge from all MD files in the workspace.

        Returns:
            Dictionary mapping file types to lists of extraction results.
        """
        results = {
            'report': [],
            'task': [],
            'archive': [],
            'doc': [],
            'root': []
        }

        # Scan all directories
        scan_dirs = ['reports', 'tasks', 'archive', 'docs', '.']

        for dir_name in scan_dirs:
            dir_path = self.workspace_root / dir_name
            if not dir_path.exists():
                continue

            for md_file in dir_path.glob('*.md'):
                file_type = self._classify_file(md_file)
                if file_type:
                    result = self.extract_from_file(md_file, file_type)
                    results[file_type].append(result)

        return results

    def _classify_file(self, file_path: Path) -> Optional[str]:
        """Classify a file path into its type based on location and naming."""
        relative_path = file_path.relative_to(self.workspace_root)

        for file_type, pattern in self.file_patterns.items():
            if pattern.match(str(relative_path)):
                return file_type

        return None

    def extract_from_file(self, file_path: Path, file_type: str) -> ExtractionResult:
        """Extract knowledge from a single MD file."""
        try:
            content = read_text(file_path)
            metadata = self._extract_metadata(content, file_type)

            # Use specialized parser based on file type
            if file_type == 'report':
                entities = self._extract_report_entities(content, metadata)
            elif file_type == 'task':
                entities = self._extract_task_entities(content, metadata)
            elif file_type == 'archive':
                entities = self._extract_archive_entities(content, metadata)
            elif file_type == 'doc':
                entities = self._extract_doc_entities(content, metadata)
            else:  # root files
                entities = self._extract_root_entities(content, metadata)

            # Calculate confidence score based on extraction quality
            confidence = self._calculate_confidence(entities, content)

            return ExtractionResult(
                file_path=file_path,
                file_type=file_type,
                entities_extracted=len(entities),
                confidence_score=confidence,
                metadata=metadata,
                extraction_errors=[],
                entities=entities  # Store the entities
            )

        except Exception as e:
            return ExtractionResult(
                file_path=file_path,
                file_type=file_type,
                entities_extracted=0,
                confidence_score=0.0,
                metadata={},
                extraction_errors=[str(e)],
                entities=[]
            )

    def _extract_metadata(self, content: str, file_type: str) -> Dict[str, Any]:
        """Extract basic metadata from file content."""
        metadata = {
            'title': self._extract_title(content),
            'word_count': len(content.split()),
            'has_code_blocks': '```' in content,
            'has_references': '[ref:' in content,
            'sections': []
        }

        # Extract sections based on file type
        if file_type in self.section_patterns:
            for section_name, pattern in self.section_patterns[file_type].items():
                if pattern.search(content):
                    metadata['sections'].append(section_name)

        return metadata

    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content."""
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled"

    def _extract_report_entities(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract knowledge entities from report files."""
        entities = []

        # Extract executive summary insights
        summary_match = re.search(r'## EXECUTIVE SUMMARY(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary_text = summary_match.group(1).strip()
            entities.append({
                'type': 'executive_summary',
                'content': summary_text,
                'category': 'summary',
                'confidence': 0.9
            })

        # Extract knowledge database usage
        knowledge_match = re.search(r'## KNOWLEDGE DATABASE USAGE(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if knowledge_match:
            knowledge_text = knowledge_match.group(1).strip()
            entities.append({
                'type': 'knowledge_usage',
                'content': knowledge_text,
                'category': 'methodology',
                'confidence': 0.95
            })

        # Extract issues resolved
        issues_match = re.search(r'## ISSUES RESOLVED(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if issues_match:
            issues_text = issues_match.group(1).strip()
            # Split into individual issues
            issue_items = re.findall(r'### ✅ (.*?)(?=###|\Z)', issues_text, re.DOTALL)
            for issue in issue_items:
                entities.append({
                    'type': 'issue_resolution',
                    'content': issue.strip(),
                    'category': 'solution',
                    'confidence': 0.85
                })

        # Extract validation results
        validation_match = re.search(r'## VALIDATION RESULTS(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if validation_match:
            validation_text = validation_match.group(1).strip()
            entities.append({
                'type': 'validation_result',
                'content': validation_text,
                'category': 'validation',
                'confidence': 0.9
            })

        return entities

    def _extract_task_entities(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract knowledge entities from task files."""
        entities = []

        # Extract objective
        obj_match = re.search(r'\*\*OBJECTIVE:\*\*(.*?)(?=\*\*|\Z)', content, re.DOTALL | re.IGNORECASE)
        if obj_match:
            entities.append({
                'type': 'task_objective',
                'content': obj_match.group(1).strip(),
                'category': 'goal',
                'confidence': 0.95
            })

        # Extract acceptance criteria
        criteria_match = re.search(r'\*\*ACCEPTANCE CRITERIA:\*\*(.*?)(?=\*\*|\Z)', content, re.DOTALL | re.IGNORECASE)
        if criteria_match:
            criteria_text = criteria_match.group(1).strip()
            # Split into individual criteria
            criteria_items = re.findall(r'- (.*?)(?=-|\Z)', criteria_text)
            for criterion in criteria_items:
                entities.append({
                    'type': 'acceptance_criterion',
                    'content': criterion.strip(),
                    'category': 'requirement',
                    'confidence': 0.9
                })

        # Extract scope
        scope_match = re.search(r'\*\*SCOPE:\*\*(.*?)(?=\*\*|\Z)', content, re.DOTALL | re.IGNORECASE)
        if scope_match:
            entities.append({
                'type': 'task_scope',
                'content': scope_match.group(1).strip(),
                'category': 'scope',
                'confidence': 0.85
            })

        # Extract deliverables
        deliverables_match = re.search(r'\*\*DELIVERABLES:\*\*(.*?)(?=\*\*|\Z)', content, re.DOTALL | re.IGNORECASE)
        if deliverables_match:
            deliverables_text = deliverables_match.group(1).strip()
            deliverable_items = re.findall(r'- (.*?)(?=-|\Z)', deliverables_text)
            for deliverable in deliverable_items:
                entities.append({
                    'type': 'deliverable',
                    'content': deliverable.strip(),
                    'category': 'output',
                    'confidence': 0.9
                })

        # Extract technical approach
        approach_match = re.search(r'\*\*TECHNICAL APPROACH:\*\*(.*?)(?=\*\*|\Z)', content, re.DOTALL | re.IGNORECASE)
        if approach_match:
            entities.append({
                'type': 'technical_approach',
                'content': approach_match.group(1).strip(),
                'category': 'methodology',
                'confidence': 0.9
            })

        return entities

    def _extract_archive_entities(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract knowledge entities from archive files."""
        entities = []

        # Extract loop summary
        summary_match = re.search(r'## LOOP SUMMARY(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if summary_match:
            entities.append({
                'type': 'loop_summary',
                'content': summary_match.group(1).strip(),
                'category': 'summary',
                'confidence': 0.9
            })

        # Extract tasks at finalization
        tasks_match = re.search(r'## TASKS AT FINALIZATION(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if tasks_match:
            tasks_text = tasks_match.group(1).strip()
            entities.append({
                'type': 'finalization_tasks',
                'content': tasks_text,
                'category': 'state',
                'confidence': 0.85
            })

        # Extract lessons learned (if present)
        lessons_match = re.search(r'## LESSONS LEARNED(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if lessons_match:
            lessons_text = lessons_match.group(1).strip()
            lesson_items = re.findall(r'- (.*?)(?=-|\Z)', lessons_text)
            for lesson in lesson_items:
                entities.append({
                    'type': 'lesson_learned',
                    'content': lesson.strip(),
                    'category': 'wisdom',
                    'confidence': 0.8
                })

        return entities

    def _extract_doc_entities(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract knowledge entities from documentation files."""
        entities = []

        # Extract purpose
        purpose_match = re.search(r'## PURPOSE(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if purpose_match:
            entities.append({
                'type': 'purpose_statement',
                'content': purpose_match.group(1).strip(),
                'category': 'purpose',
                'confidence': 0.95
            })

        # Extract core concepts
        concepts_match = re.search(r'## CORE CONCEPTS(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if concepts_match:
            concepts_text = concepts_match.group(1).strip()
            # Extract subsections as individual concepts
            concept_sections = re.findall(r'### (.*?)(?=###|\Z)', concepts_text, re.DOTALL)
            for concept in concept_sections:
                entities.append({
                    'type': 'core_concept',
                    'content': concept.strip(),
                    'category': 'concept',
                    'confidence': 0.9
                })

        # Extract architecture information
        arch_match = re.search(r'## ARCHITECTURE(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if arch_match:
            entities.append({
                'type': 'architecture_info',
                'content': arch_match.group(1).strip(),
                'category': 'architecture',
                'confidence': 0.9
            })

        # Extract operations information
        ops_match = re.search(r'## OPERATIONS(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if ops_match:
            entities.append({
                'type': 'operations_info',
                'content': ops_match.group(1).strip(),
                'category': 'operations',
                'confidence': 0.85
            })

        return entities

    def _extract_root_entities(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract knowledge entities from root-level files."""
        entities = []

        # Root files are more varied - extract general sections
        sections = re.findall(r'^## (.*?)(?=^##|\Z)', content, re.MULTILINE | re.DOTALL)
        for section in sections:
            section_title, section_content = section.split('\n', 1)
            entities.append({
                'type': 'root_section',
                'content': f"{section_title.strip()}: {section_content.strip()[:500]}",
                'category': 'general',
                'confidence': 0.7
            })

        return entities

    def _calculate_confidence(self, entities: List[Dict[str, Any]], content: str) -> float:
        """Calculate confidence score for extraction quality."""
        if not entities:
            return 0.0

        # Base confidence from number of entities
        entity_score = min(len(entities) / 10, 1.0)  # Max at 10 entities

        # Content quality factors
        content_length = len(content)
        length_score = min(content_length / 2000, 1.0)  # Max at 2000 chars

        # Structure quality (presence of expected sections)
        structure_score = 0.8 if '## ' in content else 0.4

        # Average entity confidence
        avg_entity_confidence = sum(e.get('confidence', 0.5) for e in entities) / len(entities)

        # Weighted average
        confidence = (
            entity_score * 0.3 +
            length_score * 0.2 +
            structure_score * 0.2 +
            avg_entity_confidence * 0.3
        )

        return round(confidence, 2)

    def integrate_with_knowledge_db(self, extraction_results: Dict[str, List[ExtractionResult]]) -> Dict[str, int]:
        """Integrate extracted knowledge with the knowledge database.

        Returns:
            Dictionary with integration statistics.
        """
        stats = {
            'files_processed': 0,
            'entities_added': 0,
            'errors': 0
        }

        for file_type, results in extraction_results.items():
            for result in results:
                stats['files_processed'] += 1

                if result.extraction_errors:
                    stats['errors'] += 1
                    continue

                try:
                    # Add entities to appropriate knowledge database tables
                    entities_added = self._add_entities_to_db(result)
                    stats['entities_added'] += entities_added

                except Exception as e:
                    stats['errors'] += 1
                    print(f"Error integrating {result.file_path}: {e}")

        # Rebuild search indexes after bulk addition
        try:
            self.knowledge_db.rebuild()
        except Exception as e:
            print(f"Error rebuilding database: {e}")

        return stats

    def _add_entities_to_db(self, result: ExtractionResult) -> int:
        """Add extracted entities to the knowledge database."""
        entities_added = 0

        # Store entities as lessons with appropriate categorization
        for entity in getattr(result, 'entities', []):
            try:
                # Map entity types to lesson categories
                category_map = {
                    'executive_summary': 'summary',
                    'knowledge_usage': 'methodology',
                    'issue_resolution': 'solution',
                    'validation_result': 'validation',
                    'task_objective': 'goal',
                    'acceptance_criterion': 'requirement',
                    'task_scope': 'scope',
                    'deliverable': 'output',
                    'technical_approach': 'methodology',
                    'loop_summary': 'summary',
                    'finalization_tasks': 'state',
                    'lesson_learned': 'wisdom',
                    'purpose_statement': 'purpose',
                    'core_concept': 'concept',
                    'architecture_info': 'architecture',
                    'operations_info': 'operations',
                    'root_section': 'general'
                }

                category = category_map.get(entity.get('type', ''), 'general')

                # Add as lesson learned
                self.knowledge_db.conn.execute("""
                    INSERT INTO lessons (source_type, source_id, loop_num, lesson_text, category, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    result.file_type,
                    str(result.file_path.name),
                    48,  # Current loop
                    entity.get('content', ''),
                    category,
                    datetime.now(timezone.utc).isoformat()
                ))
                entities_added += 1

            except Exception as e:
                print(f"Error adding entity to DB: {e}")

        self.knowledge_db.conn.commit()
        return entities_added

    def generate_extraction_report(self, extraction_results: Dict[str, List[ExtractionResult]],
                                 integration_stats: Dict[str, int]) -> str:
        """Generate a comprehensive extraction report."""
        report_lines = []

        report_lines.append("# TASK_0058: Comprehensive Knowledge Extraction Report")
        report_lines.append("")

        # Summary statistics
        total_files = sum(len(results) for results in extraction_results.values())
        total_entities = sum(sum(r.entities_extracted for r in results) for results in extraction_results.values())
        avg_confidence = 0.0

        if total_files > 0:
            confidences = []
            for results in extraction_results.values():
                confidences.extend(r.confidence_score for r in results)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        report_lines.append("## EXECUTIVE SUMMARY")
        report_lines.append("")
        report_lines.append(f"- **Files Processed:** {total_files}")
        report_lines.append(f"- **Entities Extracted:** {total_entities}")
        report_lines.append(f"- **Average Confidence:** {avg_confidence:.2%}")
        report_lines.append(f"- **Integration Success:** {integration_stats.get('entities_added', 0)} entities added")
        report_lines.append(f"- **Errors:** {integration_stats.get('errors', 0)}")
        report_lines.append("")

        # File type breakdown
        report_lines.append("## EXTRACTION BY FILE TYPE")
        report_lines.append("")

        for file_type, results in extraction_results.items():
            if not results:
                continue

            file_count = len(results)
            entity_count = sum(r.entities_extracted for r in results)
            avg_conf = sum(r.confidence_score for r in results) / file_count if file_count > 0 else 0.0
            error_count = sum(1 for r in results if r.extraction_errors)

            report_lines.append(f"### {file_type.title()} Files")
            report_lines.append(f"- Files: {file_count}")
            report_lines.append(f"- Entities: {entity_count}")
            report_lines.append(f"- Avg Confidence: {avg_conf:.2%}")
            report_lines.append(f"- Errors: {error_count}")
            report_lines.append("")

        # Quality assessment
        report_lines.append("## QUALITY ASSESSMENT")
        report_lines.append("")

        if avg_confidence > 0.8:
            quality = "EXCELLENT"
        elif avg_confidence > 0.6:
            quality = "GOOD"
        elif avg_confidence > 0.4:
            quality = "FAIR"
        else:
            quality = "NEEDS IMPROVEMENT"

        report_lines.append(f"**Overall Quality:** {quality}")
        report_lines.append("")
        report_lines.append("**Assessment Criteria:**")
        report_lines.append("- EXCELLENT: >80% confidence, structured extraction")
        report_lines.append("- GOOD: 60-80% confidence, good entity identification")
        report_lines.append("- FAIR: 40-60% confidence, basic extraction working")
        report_lines.append("- NEEDS IMPROVEMENT: <40% confidence, requires parser tuning")
        report_lines.append("")

        # Recommendations
        report_lines.append("## RECOMMENDATIONS")
        report_lines.append("")

        if avg_confidence < 0.6:
            report_lines.append("- Tune extraction patterns for better section recognition")
            report_lines.append("- Add more specialized parsers for complex file types")
            report_lines.append("- Implement confidence scoring improvements")

        report_lines.append("- Validate extracted knowledge through semantic search testing")
        report_lines.append("- Monitor knowledge database growth and search performance")
        report_lines.append("- Consider adding entity relationship mapping for advanced queries")
        report_lines.append("")

        return "\n".join(report_lines)


def main():
    """Main execution function for comprehensive knowledge extraction."""
    workspace_root = Path(".")

    print("Starting comprehensive knowledge extraction (TASK_0058)...")

    # Initialize extractor
    extractor = ComprehensiveExtractor(workspace_root)

    # Extract from all files
    print("Extracting knowledge from all MD files...")
    extraction_results = extractor.extract_from_all_files()

    # Display extraction summary
    total_files = sum(len(results) for results in extraction_results.values())
    total_entities = sum(sum(r.entities_extracted for r in results) for results in extraction_results.values())

    print(f"Extraction complete: {total_files} files processed, {total_entities} entities extracted")

    # Integrate with knowledge database
    print("Integrating with knowledge database...")
    integration_stats = extractor.integrate_with_knowledge_db(extraction_results)

    print(f"Integration complete: {integration_stats['entities_added']} entities added to database")

    # Generate report
    report = extractor.generate_extraction_report(extraction_results, integration_stats)

    # Save report
    report_path = workspace_root / "reports" / "report_TASK_0058_L48_v01.md"
    report_path.write_text(report)

    print(f"Report saved to: {report_path}")
    print("TASK_0058 implementation complete!")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Lessons Learned Extractor
Automatically extracts lessons learned from reports and archives
"""

import re
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Allow script execution from scripts/ without requiring PYTHONPATH setup.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge_redundancy_db import KnowledgeRedundancyDB

class LessonsLearnedExtractor:
    """Extracts lessons learned from various sources"""

    def __init__(self, db_path: str = "keeper_knowledge_redundancy.db"):
        self.db = KnowledgeRedundancyDB(db_path)

    def extract_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract lessons from a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

        # Extract knowledge from file
        knowledge_key = f"file_{Path(file_path).name}"
        file_data = {
            "filename": Path(file_path).name,
            "path": str(file_path),
            "content_type": "text",
            "size": len(content)
        }

        knowledge_id = self.db.add_knowledge(knowledge_key, file_data, str(file_path))

        # Extract lessons
        lessons = self._extract_lessons_from_content(content)

        # Store lessons
        for lesson in lessons:
            self.db.extract_lessons_learned(knowledge_id, lesson['source_text'])

        return lessons

    def extract_from_directory(self, dir_path: str, pattern: str = "*.md") -> Dict[str, List[Dict[str, Any]]]:
        """Extract lessons from all files in directory"""
        path = Path(dir_path)
        results = {}

        for file_path in path.rglob(pattern):
            if file_path.is_file():
                lessons = self.extract_from_file(str(file_path))
                if lessons:
                    results[str(file_path)] = lessons

        return results

    def _extract_lessons_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract lessons learned from text content"""
        lessons = []

        # Define patterns for lesson extraction
        patterns = [
            {
                'pattern': r'(?:lesson learned|key lesson|important lesson):\s*([^.\n]+)',
                'category': 'lesson_learned',
                'confidence': 0.9
            },
            {
                'pattern': r'(?:best practice|recommended practice):\s*([^.\n]+)',
                'category': 'best_practice',
                'confidence': 0.8
            },
            {
                'pattern': r'(?:avoid|do not|never):\s*([^.\n]+)',
                'category': 'pitfall',
                'confidence': 0.7
            },
            {
                'pattern': r'(?:critical|essential|must):\s*([^.\n]+)',
                'category': 'critical',
                'confidence': 0.8
            },
            {
                'pattern': r'(?:improvement|enhancement|optimization):\s*([^.\n]+)',
                'category': 'improvement',
                'confidence': 0.6
            }
        ]

        for pattern_info in patterns:
            matches = re.findall(pattern_info['pattern'], content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                lesson = {
                    'text': match.strip(),
                    'category': pattern_info['category'],
                    'confidence': pattern_info['confidence'],
                    'source_text': match.strip(),
                    'pattern': pattern_info['pattern']
                }
                lessons.append(lesson)

        # Extract from structured sections
        lessons.extend(self._extract_from_sections(content))

        return lessons

    def _extract_from_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract lessons from structured sections"""
        lessons = []

        # Look for sections with lessons
        section_patterns = [
            r'## Lessons Learned\s*\n(.*?)(?=\n##|\n---|\Z)',
            r'## Key Insights\s*\n(.*?)(?=\n##|\n---|\Z)',
            r'## Summary\s*\n(.*?)(?=\n##|\n---|\Z)'
        ]

        for pattern in section_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Extract bullet points or numbered items
                items = re.findall(r'(?:^|\n)[-*]\s*([^.\n]+)', match)
                for item in items:
                    lesson = {
                        'text': item.strip(),
                        'category': 'section_extracted',
                        'confidence': 0.7,
                        'source_text': item.strip(),
                        'pattern': 'section_extraction'
                    }
                    lessons.append(lesson)

        return lessons

    def get_lessons_summary(self) -> Dict[str, Any]:
        """Get summary of extracted lessons"""
        # This would query the database for summary statistics
        # Placeholder implementation
        return {
            'total_lessons': 0,
            'categories': {},
            'avg_confidence': 0.0
        }

def main():
    parser = argparse.ArgumentParser(description="Extract lessons learned from a file or directory")
    parser.add_argument("target", nargs="?", help="File or directory to process")
    args = parser.parse_args()
    if not args.target:
        parser.print_help()
        return

    target = args.target
    extractor = LessonsLearnedExtractor()

    path = Path(target)
    if path.is_file():
        lessons = extractor.extract_from_file(target)
        print(f"Extracted {len(lessons)} lessons from {target}")
        for lesson in lessons[:5]:  # Show first 5
            print(f"- {lesson['category']}: {lesson['text']}")
    elif path.is_dir():
        results = extractor.extract_from_directory(target)
        total_lessons = sum(len(lessons) for lessons in results.values())
        print(f"Extracted {total_lessons} lessons from {len(results)} files in {target}")
    else:
        print(f"Path {target} not found")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Deep Analysis Interface

Optional comprehensive retrospectives for detailed investigation.
Part of the Loop Retrospective Automation Framework (TASK_0190).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from analysis.loop_insight_extractor import LoopInsightExtractor
from analysis.trend_analyzer import TrendAnalyzer

class DeepAnalysisInterface:
    """Provides comprehensive retrospective analysis when requested."""

    def __init__(self, archive_dir: str = "archive"):
        self.archive_dir = Path(archive_dir)
        self.extractor = LoopInsightExtractor(archive_dir)
        self.trend_analyzer = TrendAnalyzer(archive_dir)

    def perform_deep_analysis(self, loop_number: int, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Perform deep analysis of a completed loop.

        analysis_type options:
        - "comprehensive": Full analysis with all metrics
        - "productivity": Focus on task completion and efficiency
        - "behavioral": Focus on patterns and incidents
        - "complexity": Focus on work volume and documentation
        """
        results = {
            'loop_number': loop_number,
            'analysis_type': analysis_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'sections': {}
        }

        # Load basic archive data
        archive_data = self.extractor._load_archive_data(loop_number)
        if not archive_data:
            results['error'] = f"No archive data found for loop {loop_number}"
            return results

        # Perform analysis based on type
        if analysis_type in ["comprehensive", "productivity"]:
            results['sections']['productivity_analysis'] = self._analyze_productivity_deep(loop_number, archive_data)

        if analysis_type in ["comprehensive", "behavioral"]:
            results['sections']['behavioral_analysis'] = self._analyze_behavioral_deep(loop_number, archive_data)

        if analysis_type in ["comprehensive", "complexity"]:
            results['sections']['complexity_analysis'] = self._analyze_complexity_deep(loop_number, archive_data)

        if analysis_type == "comprehensive":
            results['sections']['trend_context'] = self._analyze_trend_context(loop_number)
            results['sections']['recommendations'] = self._generate_recommendations(results)

        return results

    def _analyze_productivity_deep(self, loop_number: int, archive_data: Dict) -> Dict[str, Any]:
        """Deep productivity analysis."""
        content = archive_data.get('content', '')

        # Task analysis
        task_lines = [line for line in content.split('\n') if '[ref:tasks/task_' in line]
        completed_tasks = [line for line in task_lines if 'tags:completed' in line]
        new_tasks = [line for line in task_lines if 'tags:new' in line]

        # Extract task categories
        categories = []
        priorities = []
        for line in task_lines:
            if 'tags:' in line:
                tags_part = line.split('tags:')[1].split('|')[0]
                tags = [tag.strip() for tag in tags_part.split(',')]

                # Categorize
                if any(tag in ['high-priority', 'medium', 'low'] for tag in ['high-priority', 'medium', 'low']):
                    priorities.extend([tag for tag in tags if tag in ['high-priority', 'medium', 'low']])

                categories.extend([tag for tag in tags if tag not in ['completed', 'new', 'high-priority', 'medium', 'low']])

        # Report analysis
        report_lines = [line for line in content.split('\n') if '[ref:reports/report_' in line]
        report_count = len(report_lines)

        return {
            'total_tasks': len(task_lines),
            'completed_tasks': len(completed_tasks),
            'new_tasks': len(new_tasks),
            'completion_rate': len(completed_tasks) / len(task_lines) if task_lines else 0,
            'top_categories': dict(__import__('collections').Counter(categories).most_common(5)),
            'priority_distribution': dict(__import__('collections').Counter(priorities)),
            'reports_generated': report_count,
            'reports_per_task': report_count / len(task_lines) if task_lines else 0
        }

    def _analyze_behavioral_deep(self, loop_number: int, archive_data: Dict) -> Dict[str, Any]:
        """Deep behavioral analysis."""
        content = archive_data.get('content', '')

        # Incident analysis
        incident_count = content.count('INCIDENT')
        incident_lines = [line for line in content.split('\n') if 'INCIDENT' in line]

        # Transaction analysis
        transactions = self.extractor._load_transaction_data(loop_number)
        transaction_count = len(transactions)

        # File access patterns (if available in transactions)
        file_types_accessed = []
        if transactions:
            for tx in transactions:
                if 'target_file' in tx:
                    file_path = tx['target_file']
                    if 'task_' in file_path:
                        file_types_accessed.append('task')
                    elif 'report_' in file_path:
                        file_types_accessed.append('report')
                    elif '_BOOTSTRAP' in file_path or '_LOOP_GATE' in file_path:
                        file_types_accessed.append('system')
                    else:
                        file_types_accessed.append('other')

        return {
            'incident_count': incident_count,
            'incidents': incident_lines[:5],  # First 5 for brevity
            'transaction_count': transaction_count,
            'file_access_patterns': dict(__import__('collections').Counter(file_types_accessed)),
            'activity_level': 'high' if transaction_count > 200 else 'medium' if transaction_count > 50 else 'low'
        }

    def _analyze_complexity_deep(self, loop_number: int, archive_data: Dict) -> Dict[str, Any]:
        """Deep complexity analysis."""
        content = archive_data.get('content', '')

        # Size metrics
        word_count = len(content.split())
        line_count = len(content.split('\n'))
        char_count = len(content)

        # Content composition
        reference_count = content.count('[ref:')
        code_block_count = content.count('```')
        list_item_count = content.count('- ') + content.count('* ')

        # Documentation density
        documentation_ratio = reference_count / word_count if word_count > 0 else 0

        return {
            'size_metrics': {
                'words': word_count,
                'lines': line_count,
                'characters': char_count
            },
            'content_composition': {
                'references': reference_count,
                'code_blocks': code_block_count,
                'list_items': list_item_count
            },
            'documentation_density': documentation_ratio,
            'complexity_assessment': self._assess_complexity(word_count, reference_count, code_block_count)
        }

    def _assess_complexity(self, word_count: int, references: int, code_blocks: int) -> str:
        """Assess overall complexity level."""
        score = 0

        if word_count > 10000:
            score += 3
        elif word_count > 5000:
            score += 2
        elif word_count > 2000:
            score += 1

        if references > 50:
            score += 2
        elif references > 20:
            score += 1

        if code_blocks > 10:
            score += 2
        elif code_blocks > 5:
            score += 1

        if score >= 5:
            return 'very_high'
        elif score >= 3:
            return 'high'
        elif score >= 2:
            return 'medium'
        else:
            return 'low'

    def _analyze_trend_context(self, loop_number: int) -> Dict[str, Any]:
        """Analyze how this loop fits into broader trends."""
        trends = self.trend_analyzer.analyze_trends()

        if 'error' in trends:
            return {'error': trends['error']}

        # Compare this loop to trends
        prod_trends = trends.get('productivity_trends', {})
        comp_trends = trends.get('complexity_trends', {})
        beh_trends = trends.get('behavioral_trends', {})

        # Get this loop's metrics
        this_loop_data = self.extractor._load_archive_data(loop_number)
        if not this_loop_data:
            return {'error': 'Cannot load current loop data'}

        this_completion = 0
        task_lines = [line for line in this_loop_data['content'].split('\n') if '[ref:tasks/task_' in line]
        completed_lines = [line for line in task_lines if 'tags:completed' in line]
        if task_lines:
            this_completion = len(completed_lines) / len(task_lines)

        return {
            'productivity_context': {
                'this_loop_completion': this_completion,
                'average_completion': prod_trends.get('average_completion_rate', 0),
                'vs_average': this_completion - prod_trends.get('average_completion_rate', 0)
            },
            'complexity_context': {
                'this_loop_words': this_loop_data.get('word_count', 0),
                'average_words': comp_trends.get('average_word_count', 0),
                'vs_average': this_loop_data.get('word_count', 0) - comp_trends.get('average_word_count', 0)
            },
            'behavioral_context': {
                'this_loop_incidents': this_loop_data['content'].count('INCIDENT'),
                'average_incidents': beh_trends.get('average_incidents', 0)
            }
        }

    def _generate_recommendations(self, analysis_results: Dict) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Productivity recommendations
        prod = analysis_results.get('sections', {}).get('productivity_analysis', {})
        completion_rate = prod.get('completion_rate', 0)

        if completion_rate < 0.5:
            recommendations.append({
                'category': 'productivity',
                'priority': 'high',
                'title': 'Improve Task Completion',
                'description': 'Task completion rate is below 50%. Consider smaller task sizes.',
                'actions': ['Break large tasks into smaller units', 'Review task acceptance criteria']
            })

        # Complexity recommendations
        comp = analysis_results.get('sections', {}).get('complexity_analysis', {})
        complexity = comp.get('complexity_assessment', 'low')

        if complexity in ['high', 'very_high']:
            recommendations.append({
                'category': 'complexity',
                'priority': 'medium',
                'title': 'Reduce Documentation Burden',
                'description': 'High complexity detected. Consider streamlining documentation.',
                'actions': ['Consolidate similar reports', 'Use summary formats for routine tasks']
            })

        # Behavioral recommendations
        beh = analysis_results.get('sections', {}).get('behavioral_analysis', {})
        incident_count = beh.get('incident_count', 0)

        if incident_count > 3:
            recommendations.append({
                'category': 'behavioral',
                'priority': 'high',
                'title': 'Address Incident Patterns',
                'description': f'{incident_count} incidents recorded. Investigate root causes.',
                'actions': ['Review incident logs', 'Implement preventive measures']
            })

        return recommendations

def main():
    """Command line interface for deep analysis."""
    import argparse

    parser = argparse.ArgumentParser(description='Perform deep loop analysis')
    parser.add_argument('loop_number', type=int, help='Loop number to analyze')
    parser.add_argument('--type', default='comprehensive',
                       choices=['comprehensive', 'productivity', 'behavioral', 'complexity'],
                       help='Type of analysis to perform')
    parser.add_argument('--output', type=str, help='Output file for results')

    args = parser.parse_args()

    analyzer = DeepAnalysisInterface()
    results = analyzer.perform_deep_analysis(args.loop_number, args.type)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {args.output}")
    else:
        print(json.dumps(results, indent=2, default=str))

if __name__ == "__main__":
    main()
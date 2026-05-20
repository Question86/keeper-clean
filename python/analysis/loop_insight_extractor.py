#!/usr/bin/env python3
"""
Loop Insight Extractor

Automated extraction of 3-5 key behavioral insights per completed loop.
Part of the Loop Retrospective Automation Framework (TASK_0190).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict

class LoopInsightExtractor:
    """Extracts key insights from completed loop data."""

    def __init__(self, archive_dir: str = "archive", transaction_log: str = "_transaction_log.jsonl"):
        self.archive_dir = Path(archive_dir)
        self.transaction_log = Path(transaction_log)

    def extract_insights_for_loop(self, loop_number: int) -> List[Dict[str, Any]]:
        """
        Extract 3-5 key insights for a completed loop.

        Returns list of insight dictionaries with:
        - type: insight category
        - title: brief description
        - description: detailed explanation
        - impact: potential improvement
        - confidence: confidence level (0-1)
        """
        insights = []

        # Get archive data
        archive_data = self._load_archive_data(loop_number)
        if not archive_data:
            return insights

        # Get transaction data for the loop
        transactions = self._load_transaction_data(loop_number)

        # Extract different types of insights
        insights.extend(self._extract_productivity_insights(archive_data, transactions))
        insights.extend(self._extract_behavioral_insights(archive_data))
        insights.extend(self._extract_task_completion_insights(archive_data))
        insights.extend(self._extract_complexity_insights(archive_data))

        # Limit to 3-5 most valuable insights
        insights.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return insights[:5]

    def _load_archive_data(self, loop_number: int) -> Optional[Dict[str, Any]]:
        """Load archive data for the specified loop."""
        archive_file = self.archive_dir / f"ARCHIV_{loop_number:04d}.md"

        if not archive_file.exists():
            return None

        try:
            with open(archive_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract key metrics from archive
            return {
                'content': content,
                'loop_number': loop_number,
                'word_count': len(content.split()),
                'line_count': len(content.split('\n')),
                'has_reports': 'report_' in content,
                'has_tasks': 'task_' in content,
                'has_incidents': 'INCIDENT' in content
            }
        except Exception:
            return None

    def _load_transaction_data(self, loop_number: int) -> List[Dict[str, Any]]:
        """Load transaction data for the specified loop."""
        transactions = []

        if not self.transaction_log.exists():
            return transactions

        try:
            with open(self.transaction_log, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            transaction = json.loads(line)
                            # Check if transaction belongs to this loop
                            if transaction.get('loop') == loop_number:
                                transactions.append(transaction)
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return transactions

    def _extract_productivity_insights(self, archive_data: Dict, transactions: List) -> List[Dict]:
        """Extract productivity-related insights."""
        insights = []

        # Task completion rate
        if archive_data.get('has_tasks'):
            task_count = archive_data['content'].count('[ref:tasks/task_')
            completed_count = archive_data['content'].count('tags:completed')

            if task_count > 0:
                completion_rate = completed_count / task_count
                if completion_rate < 0.5:
                    insights.append({
                        'type': 'productivity',
                        'title': 'Low Task Completion Rate',
                        'description': f'Only {completion_rate:.1%} of tasks were completed this loop.',
                        'impact': 'Consider breaking down tasks into smaller, more achievable units.',
                        'confidence': 0.8
                    })
                elif completion_rate > 0.9:
                    insights.append({
                        'type': 'productivity',
                        'title': 'High Productivity Loop',
                        'description': f'Excellent completion rate of {completion_rate:.1%} achieved.',
                        'impact': 'Analyze successful patterns for replication in future loops.',
                        'confidence': 0.7
                    })

        # Transaction volume
        transaction_count = len(transactions)
        if transaction_count > 100:
            insights.append({
                'type': 'productivity',
                'title': 'High Activity Level',
                'description': f'{transaction_count} operations recorded, indicating high engagement.',
                'impact': 'Monitor for potential over-activity or context switching issues.',
                'confidence': 0.6
            })

        return insights

    def _extract_behavioral_insights(self, archive_data: Dict) -> List[Dict]:
        """Extract behavioral pattern insights."""
        insights = []

        content = archive_data.get('content', '')

        # Incident frequency
        incident_count = content.count('INCIDENT')
        if incident_count > 2:
            insights.append({
                'type': 'behavioral',
                'title': 'Frequent Incidents',
                'description': f'{incident_count} incidents recorded, suggesting potential systemic issues.',
                'impact': 'Review incident patterns and consider preventive measures.',
                'confidence': 0.9
            })

        # Report volume
        report_count = content.count('[ref:reports/report_')
        if report_count > 10:
            insights.append({
                'type': 'behavioral',
                'title': 'High Documentation Burden',
                'description': f'{report_count} reports generated, potentially impacting efficiency.',
                'impact': 'Evaluate if all reports are necessary or if some can be consolidated.',
                'confidence': 0.7
            })

        return insights

    def _extract_task_completion_insights(self, archive_data: Dict) -> List[Dict]:
        """Extract task completion pattern insights."""
        insights = []

        content = archive_data.get('content', '')

        # Task categories
        task_lines = [line for line in content.split('\n') if '[ref:tasks/task_' in line]
        categories = []

        for line in task_lines:
            if 'tags:' in line:
                # Extract tags
                tags_part = line.split('tags:')[1].split('|')[0]
                tags = [tag.strip() for tag in tags_part.split(',')]
                categories.extend(tags)

        if categories:
            category_counts = Counter(categories)
            top_category = category_counts.most_common(1)[0]

            insights.append({
                'type': 'task_completion',
                'title': f'Focus Area: {top_category[0].replace("-", " ").title()}',
                'description': f'Most work concentrated in {top_category[0]} category ({top_category[1]} tasks).',
                'impact': 'Consider if this focus aligns with project priorities.',
                'confidence': 0.6
            })

        return insights

    def _extract_complexity_insights(self, archive_data: Dict) -> List[Dict]:
        """Extract complexity and burden insights."""
        insights = []

        # Archive size as complexity proxy
        word_count = archive_data.get('word_count', 0)
        if word_count > 50000:
            insights.append({
                'type': 'complexity',
                'title': 'Large Archive Size',
                'description': f'Archive contains {word_count:,} words, indicating substantial work volume.',
                'impact': 'Consider if work can be distributed across multiple loops.',
                'confidence': 0.5
            })

        # Line count
        line_count = archive_data.get('line_count', 0)
        if line_count > 2000:
            insights.append({
                'type': 'complexity',
                'title': 'High Detail Level',
                'description': f'Archive spans {line_count:,} lines, suggesting detailed documentation.',
                'impact': 'Balance detail with readability and maintenance overhead.',
                'confidence': 0.4
            })

        return insights

def main():
    """Command line interface for insight extraction."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract loop insights')
    parser.add_argument('loop_number', type=int, help='Loop number to analyze')
    parser.add_argument('--archive-dir', default='archive', help='Archive directory')
    parser.add_argument('--transaction-log', default='_transaction_log.jsonl', help='Transaction log file')

    args = parser.parse_args()

    extractor = LoopInsightExtractor(args.archive_dir, args.transaction_log)
    insights = extractor.extract_insights_for_loop(args.loop_number)

    print(f"Insights for Loop {args.loop_number}:")
    print()

    for i, insight in enumerate(insights, 1):
        print(f"{i}. {insight['title']}")
        print(f"   {insight['description']}")
        print(f"   Impact: {insight['impact']}")
        print(f"   Confidence: {insight['confidence']:.1%}")
        print()

if __name__ == "__main__":
    main()
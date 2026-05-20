#!/usr/bin/env python3
"""
Autonomous Audit System

Performs automated audits of knowledge quality and identifies gaps.
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict
from knowledge_health_monitor import KnowledgeHealthMonitor

class AutonomousAuditSystem:
    """
    System for autonomous auditing of knowledge quality and gap detection.
    """

    def __init__(self, db_path: str = "keeper_knowledge.db"):
        self.db_path = db_path
        self.monitor = KnowledgeHealthMonitor(db_path)
        self.logger = logging.getLogger(__name__)

        # Quality criteria
        self.quality_checks = {
            'completeness': self._check_completeness,
            'accuracy': self._check_accuracy_indicators,
            'consistency': self._check_consistency,
            'relevance': self._check_relevance,
            'structure': self._check_structure
        }

    def perform_full_audit(self) -> Dict:
        """
        Perform comprehensive audit of all knowledge items.
        """
        items = self.monitor.get_knowledge_items()
        audit_results = {
            'total_items': len(items),
            'audit_timestamp': self._get_timestamp(),
            'quality_scores': {},
            'gaps_identified': [],
            'recommendations': [],
            'category_analysis': {},
            'cross_references': self._analyze_cross_references(items)
        }

        # Audit each item
        for item in items:
            item_id = item['id']
            content = self._get_item_content(item_id)
            if content:
                audit_results['quality_scores'][item_id] = self._audit_item_quality(item, content)

        # Analyze categories
        audit_results['category_analysis'] = self._analyze_categories(items)

        # Identify gaps
        audit_results['gaps_identified'] = self._identify_gaps(items, audit_results)

        # Generate recommendations
        audit_results['recommendations'] = self._generate_audit_recommendations(audit_results)

        return audit_results

    def _get_item_content(self, item_id: str) -> Optional[str]:
        """Get full content of a knowledge item."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT content_full FROM docs WHERE id = ?", (item_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Error getting content for {item_id}: {e}")
            return None

    def _audit_item_quality(self, item: Dict, content: str) -> Dict:
        """Audit quality of a single item."""
        scores = {}
        for check_name, check_func in self.quality_checks.items():
            scores[check_name] = check_func(item, content)

        # Overall score (weighted average)
        weights = {
            'completeness': 0.3,
            'accuracy': 0.3,
            'consistency': 0.2,
            'relevance': 0.1,
            'structure': 0.1
        }

        overall_score = sum(scores[check] * weights[check] for check in scores)
        scores['overall'] = overall_score

        return scores

    def _check_completeness(self, item: Dict, content: str) -> float:
        """Check if item has complete information."""
        score = 0.0

        # Check for key sections
        indicators = ['overview', 'description', 'implementation', 'examples', 'references']
        found_indicators = sum(1 for ind in indicators if ind.lower() in content.lower())
        score += (found_indicators / len(indicators)) * 0.6

        # Check content length (reasonable minimum)
        if len(content) > 500:
            score += 0.4

        return min(score, 1.0)

    def _check_accuracy_indicators(self, item: Dict, content: str) -> float:
        """Check for accuracy indicators."""
        score = 0.0

        # Look for citations, references, dates
        if re.search(r'\[.*?\]', content):  # References
            score += 0.3
        if re.search(r'\d{4}-\d{2}-\d{2}', content):  # Dates
            score += 0.3
        if 'version' in content.lower() or 'updated' in content.lower():
            score += 0.4

        return min(score, 1.0)

    def _check_consistency(self, item: Dict, content: str) -> float:
        """Check for internal consistency."""
        score = 1.0

        # Check for contradictory statements (simplified)
        contradictions = ['but', 'however', 'although', 'despite']
        contradiction_count = sum(content.lower().count(word) for word in contradictions)

        if contradiction_count > 5:
            score -= 0.2

        # Check for consistent terminology
        terms = re.findall(r'\b[A-Z][a-z]+\b', content)
        if terms and len(set(terms)) / len(terms) < 0.5:  # High term repetition
            score -= 0.1

        return max(score, 0.0)

    def _check_relevance(self, item: Dict, content: str) -> float:
        """Check relevance to category and tags."""
        score = 0.5  # Base score

        category = item.get('category', '').lower()
        tags = [tag.lower() for tag in item.get('tags', [])]

        content_lower = content.lower()

        # Check if category keywords appear in content
        if category and category in content_lower:
            score += 0.3

        # Check if tags appear in content
        tag_matches = sum(1 for tag in tags if tag in content_lower)
        if tags:
            score += (tag_matches / len(tags)) * 0.2

        return min(score, 1.0)

    def _check_structure(self, item: Dict, content: str) -> float:
        """Check document structure."""
        score = 0.0

        # Check for headings
        if re.search(r'^#+\s', content, re.MULTILINE):
            score += 0.4

        # Check for lists
        if re.search(r'^[\-\*\+]\s', content, re.MULTILINE):
            score += 0.3

        # Check for code blocks
        if '```' in content:
            score += 0.3

        return min(score, 1.0)

    def _analyze_cross_references(self, items: List[Dict]) -> Dict:
        """Analyze cross-references between items."""
        references = defaultdict(list)
        referenced_by = defaultdict(list)

        for item in items:
            item_id = item['id']
            content = self._get_item_content(item_id) or ""

            # Find references in content
            refs = re.findall(r'\[ref:([^]]+)\]', content)
            for ref in refs:
                ref_id = ref.split('|')[0] if '|' in ref else ref
                references[item_id].append(ref_id)
                referenced_by[ref_id].append(item_id)

        return {
            'references': dict(references),
            'referenced_by': dict(referenced_by),
            'orphaned_items': [item['id'] for item in items if item['id'] not in referenced_by],
            'highly_referenced': sorted(referenced_by.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        }

    def _analyze_categories(self, items: List[Dict]) -> Dict:
        """Analyze knowledge distribution across categories."""
        categories = defaultdict(list)

        for item in items:
            cat = item.get('category') or 'uncategorized'
            categories[cat].append(item)

        analysis = {}
        for cat, cat_items in categories.items():
            analysis[cat] = {
                'count': len(cat_items),
                'avg_quality': sum(self._audit_item_quality(item, self._get_item_content(item['id']) or "")['overall']
                                 for item in cat_items) / len(cat_items) if cat_items else 0,
                'tags': list(set(tag for item in cat_items for tag in item['tags']))
            }

        return analysis

    def _identify_gaps(self, items: List[Dict], audit_results: Dict) -> List[Dict]:
        """Identify knowledge gaps."""
        gaps = []

        # Check for categories with low quality
        for cat, analysis in audit_results['category_analysis'].items():
            if analysis['avg_quality'] < 0.6:
                gaps.append({
                    'type': 'quality_gap',
                    'category': cat,
                    'description': f"Category '{cat}' has low average quality ({analysis['avg_quality']:.2f})",
                    'severity': 'high' if analysis['avg_quality'] < 0.4 else 'medium'
                })

        # Check for orphaned items
        orphaned = audit_results['cross_references']['orphaned_items']
        if len(orphaned) > 10:
            gaps.append({
                'type': 'connectivity_gap',
                'description': f"{len(orphaned)} items have no incoming references",
                'severity': 'medium'
            })

        # Check for unbalanced categories
        total_items = len(items)
        for cat, analysis in audit_results['category_analysis'].items():
            ratio = analysis['count'] / total_items
            if ratio > 0.5:  # One category dominates
                gaps.append({
                    'type': 'balance_gap',
                    'category': cat,
                    'description': f"Category '{cat}' represents {ratio:.1f}% of all knowledge",
                    'severity': 'low'
                })

        return gaps

    def _generate_audit_recommendations(self, audit_results: Dict) -> List[Dict]:
        """Generate recommendations based on audit results."""
        recommendations = []

        # Quality improvement recommendations
        low_quality_items = [(item_id, scores) for item_id, scores in audit_results['quality_scores'].items()
                           if scores['overall'] < 0.6]
        if low_quality_items:
            recommendations.append({
                'type': 'quality_improvement',
                'description': f"Improve quality of {len(low_quality_items)} low-quality items",
                'items': [item_id for item_id, _ in low_quality_items]
            })

        # Gap filling recommendations
        for gap in audit_results['gaps_identified']:
            if gap['type'] == 'quality_gap':
                recommendations.append({
                    'type': 'gap_filling',
                    'description': f"Address {gap['description']}",
                    'category': gap['category']
                })

        return recommendations

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        return datetime.now().isoformat()

    def export_audit_report(self, audit_results: Dict, format: str = 'json') -> str:
        """Export audit results."""
        if format == 'json':
            return json.dumps(audit_results, indent=2, default=str)
        elif format == 'markdown':
            return self._format_audit_markdown(audit_results)
        else:
            return str(audit_results)

    def _format_audit_markdown(self, audit_results: Dict) -> str:
        """Format audit results as markdown."""
        md = "# Knowledge Audit Report\n"
        md += f"Generated: {audit_results['audit_timestamp']}\n\n"

        md += f"## Overview\n"
        md += f"- Total Items: {audit_results['total_items']}\n"
        md += f"- Gaps Identified: {len(audit_results['gaps_identified'])}\n"
        md += f"- Recommendations: {len(audit_results['recommendations'])}\n\n"

        md += "## Quality Scores\n"
        avg_quality = sum(scores['overall'] for scores in audit_results['quality_scores'].values()) / len(audit_results['quality_scores']) if audit_results['quality_scores'] else 0
        md += f"Average Quality: {avg_quality:.2f}/1.0\n\n"

        md += "## Identified Gaps\n"
        for gap in audit_results['gaps_identified'][:5]:  # Top 5
            md += f"- **{gap['severity'].upper()}**: {gap['description']}\n"
        md += "\n"

        return md


if __name__ == "__main__":
    # Example usage
    auditor = AutonomousAuditSystem()
    results = auditor.perform_full_audit()

    print(f"Audit completed for {results['total_items']} items")
    print(f"Gaps identified: {len(results['gaps_identified'])}")
    print(f"Recommendations: {len(results['recommendations'])}")

    # Export summary
    md_report = auditor.export_audit_report(results, 'markdown')
    print("\nAudit Report Preview:")
    print(md_report[:1000] + "..." if len(md_report) > 1000 else md_report)
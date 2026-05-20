"""
Quality Scoring and Metrics Calculation

This module provides algorithms for calculating quality scores and metrics
from detected issues and codebase analysis.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict, Counter

from detection_rules import QualityIssue, IssueSeverity, IssueCategory


class QualityScorer:
    """Calculates quality scores and metrics from detected issues"""

    def __init__(self, config: Dict):
        self.config = config
        self.thresholds = config.get("quality_thresholds", {})

    def calculate_file_score(self, issues: List[QualityIssue]) -> Dict[str, Any]:
        """
        Calculate quality score for a single file

        Args:
            issues: List of quality issues for the file

        Returns:
            Dictionary with score and metrics
        """
        if not issues:
            return {
                "score": 100.0,
                "grade": "excellent",
                "issues_count": 0,
                "severity_breakdown": {},
                "category_breakdown": {}
            }

        # Calculate base score (100 - penalty per issue)
        severity_weights = {
            IssueSeverity.CRITICAL: 15,
            IssueSeverity.HIGH: 10,
            IssueSeverity.MEDIUM: 5,
            IssueSeverity.LOW: 2,
            IssueSeverity.INFO: 1
        }

        total_penalty = 0
        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)

        for issue in issues:
            penalty = severity_weights.get(issue.severity, 1)
            total_penalty += penalty
            severity_counts[issue.severity.value] += 1
            category_counts[issue.category.value] += 1

        # Cap penalty at 100 to avoid negative scores
        score = max(0, 100 - total_penalty)

        # Determine grade
        thresholds = self.thresholds.get("overall_score", {})
        if score >= thresholds.get("excellent", 90):
            grade = "excellent"
        elif score >= thresholds.get("good", 80):
            grade = "good"
        elif score >= thresholds.get("acceptable", 70):
            grade = "acceptable"
        elif score >= thresholds.get("poor", 60):
            grade = "poor"
        else:
            grade = "critical"

        return {
            "score": round(score, 1),
            "grade": grade,
            "issues_count": len(issues),
            "severity_breakdown": dict(severity_counts),
            "category_breakdown": dict(category_counts)
        }

    def calculate_project_score(self, file_scores: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Calculate overall project quality score from individual file scores

        Args:
            file_scores: Dictionary mapping file paths to their quality scores

        Returns:
            Project-wide quality metrics
        """
        if not file_scores:
            return {
                "overall_score": 100.0,
                "grade": "excellent",
                "files_analyzed": 0,
                "files_by_grade": {},
                "average_score": 100.0,
                "score_distribution": {}
            }

        total_score = 0
        grade_counts = defaultdict(int)
        scores = []

        for file_path, score_data in file_scores.items():
            score = score_data["score"]
            grade = score_data["grade"]

            total_score += score
            scores.append(score)
            grade_counts[grade] += 1

        files_count = len(file_scores)
        average_score = total_score / files_count

        # Determine overall grade based on average
        thresholds = self.thresholds.get("overall_score", {})
        if average_score >= thresholds.get("excellent", 90):
            overall_grade = "excellent"
        elif average_score >= thresholds.get("good", 80):
            overall_grade = "good"
        elif average_score >= thresholds.get("acceptable", 70):
            overall_grade = "acceptable"
        elif average_score >= thresholds.get("poor", 60):
            overall_grade = "poor"
        else:
            overall_grade = "critical"

        # Calculate score distribution
        score_ranges = {
            "90-100": 0,
            "80-89": 0,
            "70-79": 0,
            "60-69": 0,
            "0-59": 0
        }

        for score in scores:
            if score >= 90:
                score_ranges["90-100"] += 1
            elif score >= 80:
                score_ranges["80-89"] += 1
            elif score >= 70:
                score_ranges["70-79"] += 1
            elif score >= 60:
                score_ranges["60-69"] += 1
            else:
                score_ranges["0-59"] += 1

        return {
            "overall_score": round(average_score, 1),
            "grade": overall_grade,
            "files_analyzed": files_count,
            "files_by_grade": dict(grade_counts),
            "average_score": round(average_score, 1),
            "score_distribution": score_ranges,
            "score_variance": round(sum((x - average_score) ** 2 for x in scores) / len(scores), 2) if scores else 0
        }

    def calculate_trends(self, historical_scores: List[Dict]) -> Dict[str, Any]:
        """
        Calculate quality trends from historical data

        Args:
            historical_scores: List of historical project scores

        Returns:
            Trend analysis metrics
        """
        if len(historical_scores) < 2:
            return {
                "trend": "insufficient_data",
                "change_rate": 0,
                "volatility": 0,
                "improving_files": 0,
                "declining_files": 0
            }

        # Sort by timestamp
        sorted_scores = sorted(historical_scores, key=lambda x: x.get("timestamp", ""))

        # Calculate overall trend
        first_score = sorted_scores[0]["overall_score"]
        last_score = sorted_scores[-1]["overall_score"]
        change_rate = (last_score - first_score) / len(sorted_scores)

        if change_rate > 1:
            trend = "improving"
        elif change_rate < -1:
            trend = "declining"
        else:
            trend = "stable"

        # Calculate volatility (standard deviation of scores)
        scores = [s["overall_score"] for s in sorted_scores]
        mean_score = sum(scores) / len(scores)
        volatility = sum((x - mean_score) ** 2 for x in scores) / len(scores)

        return {
            "trend": trend,
            "change_rate": round(change_rate, 2),
            "volatility": round(volatility, 2),
            "score_range": {
                "min": min(scores),
                "max": max(scores),
                "current": last_score
            }
        }

    def generate_recommendations(self, project_score: Dict, file_scores: Dict) -> List[Dict]:
        """
        Generate actionable recommendations based on quality analysis

        Args:
            project_score: Project-wide quality metrics
            file_scores: Individual file quality scores

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []

        # Overall score recommendations
        if project_score["overall_score"] < 70:
            recommendations.append({
                "priority": "critical",
                "category": "overall_quality",
                "message": f"Overall code quality is {project_score['grade']} ({project_score['overall_score']:.1f}/100)",
                "action": "Schedule code review and refactoring session",
                "impact": "high"
            })

        # File-specific recommendations
        critical_files = []
        for file_path, score_data in file_scores.items():
            if score_data["score"] < 60:
                critical_files.append((file_path, score_data["score"]))

        if critical_files:
            critical_files.sort(key=lambda x: x[1])  # Sort by score ascending
            recommendations.append({
                "priority": "high",
                "category": "file_quality",
                "message": f"{len(critical_files)} files have critical quality issues",
                "action": f"Review files: {', '.join(f'{Path(f[0]).name} ({f[1]:.1f})' for f in critical_files[:3])}",
                "impact": "high"
            })

        # Category-specific recommendations
        grade_counts = project_score.get("files_by_grade", {})
        if grade_counts.get("poor", 0) + grade_counts.get("critical", 0) > grade_counts.get("excellent", 0):
            recommendations.append({
                "priority": "medium",
                "category": "quality_distribution",
                "message": "More files have poor/critical quality than excellent quality",
                "action": "Implement code quality standards and automated checks",
                "impact": "medium"
            })

        # Trend-based recommendations
        # This would require historical data in a real implementation

        return recommendations

    def calculate_coverage_metrics(self, file_scores: Dict) -> Dict[str, Any]:
        """
        Calculate code coverage and analysis coverage metrics

        Args:
            file_scores: Individual file quality scores

        Returns:
            Coverage metrics
        """
        if not file_scores:
            return {
                "analysis_coverage": 0,
                "quality_distribution": {},
                "risk_assessment": "unknown"
            }

        total_files = len(file_scores)
        grade_counts = defaultdict(int)

        for score_data in file_scores.values():
            grade_counts[score_data["grade"]] += 1

        # Calculate risk assessment
        excellent_pct = (grade_counts["excellent"] / total_files) * 100
        poor_pct = ((grade_counts.get("poor", 0) + grade_counts.get("critical", 0)) / total_files) * 100

        if excellent_pct > 50:
            risk = "low"
        elif poor_pct > 30:
            risk = "high"
        else:
            risk = "medium"

        return {
            "analysis_coverage": total_files,
            "quality_distribution": dict(grade_counts),
            "risk_assessment": risk,
            "quality_percentages": {
                grade: round((count / total_files) * 100, 1)
                for grade, count in grade_counts.items()
            }
        }


class QualityReportGenerator:
    """Generates quality reports in various formats"""

    def __init__(self, scorer: QualityScorer):
        self.scorer = scorer

    def generate_json_report(self, project_score: Dict, file_scores: Dict,
                           issues: List[QualityIssue], timestamp: str = None) -> str:
        """Generate JSON quality report"""

        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        report = {
            "timestamp": timestamp,
            "project_score": project_score,
            "file_scores": file_scores,
            "issues": [
                {
                    "file_path": issue.file_path,
                    "line_number": issue.line_number,
                    "category": issue.category.value,
                    "severity": issue.severity.value,
                    "rule_name": issue.rule_name,
                    "message": issue.message,
                    "suggestion": issue.suggestion
                }
                for issue in issues
            ],
            "summary": {
                "total_issues": len(issues),
                "issues_by_category": dict(Counter(i.category.value for i in issues)),
                "issues_by_severity": dict(Counter(i.severity.value for i in issues)),
                "files_with_issues": len(set(i.file_path for i in issues))
            }
        }

        return json.dumps(report, indent=2, ensure_ascii=False)

    def generate_markdown_report(self, project_score: Dict, file_scores: Dict,
                               issues: List[QualityIssue], timestamp: str = None) -> str:
        """Generate Markdown quality report"""

        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        lines = [
            "# Code Quality Report",
            "",
            f"**Generated:** {timestamp}",
            "",
            "## Project Overview",
            "",
            f"- **Overall Score:** {project_score['overall_score']:.1f}/100 ({project_score['grade'].title()})",
            f"- **Files Analyzed:** {project_score['files_analyzed']}",
            f"- **Average Score:** {project_score['average_score']:.1f}",
            "",
            "## Quality Distribution",
            "",
            "| Grade | Count | Percentage |",
            "|-------|-------|------------|"
        ]

        for grade, count in project_score.get("files_by_grade", {}).items():
            pct = (count / project_score["files_analyzed"]) * 100
            lines.append(f"| {grade.title()} | {count} | {pct:.1f}% |")

        lines.extend([
            "",
            "## Top Issues",
            "",
            "| File | Line | Severity | Category | Message |",
            "|------|------|----------|----------|---------|"
        ])

        # Sort issues by severity
        severity_order = {IssueSeverity.CRITICAL: 0, IssueSeverity.HIGH: 1,
                         IssueSeverity.MEDIUM: 2, IssueSeverity.LOW: 3, IssueSeverity.INFO: 4}
        sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.severity, 5))

        for issue in sorted_issues[:20]:  # Top 20 issues
            file_name = Path(issue.file_path).name
            lines.append(f"| {file_name} | {issue.line_number} | {issue.severity.value.title()} | {issue.category.value.replace('_', ' ').title()} | {issue.message} |")

        lines.extend([
            "",
            "## Recommendations",
            ""
        ])

        recommendations = self.scorer.generate_recommendations(project_score, file_scores)
        for rec in recommendations:
            lines.append(f"### {rec['priority'].title()}: {rec['message']}")
            lines.append(f"**Action:** {rec['action']}")
            lines.append("")

        return "\n".join(lines)
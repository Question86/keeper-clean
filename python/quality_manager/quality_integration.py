"""
Quality Manager Integration Script

This script integrates the quality management system with the loop cockpit
and provides command-line interface for quality operations.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add quality_manager to path
sys.path.insert(0, str(Path(__file__).parent))

from quality_scorer import QualityScorer, QualityReportGenerator
from quality_dashboard import create_quality_dashboard, start_dashboard_server, QualityDashboardServer
from quality_scanner import QualityScanner
from detection_rules import QualityIssue


class QualityManagerIntegration:
    """Integration layer for quality management system"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "quality_config.json"

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.scorer = QualityScorer(self.config)
        self.report_generator = QualityReportGenerator(self.scorer)
        self.dashboard = create_quality_dashboard(self.config)

    def _load_config(self) -> Dict:
        """Load quality configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Configuration file not found: {self.config_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in config file: {e}")
            return {}

    def run_quality_scan(self, target_path: str = None, save_report: bool = True) -> Dict[str, Any]:
        """
        Run complete quality scan

        Args:
            target_path: Path to scan (defaults to workspace root)
            save_report: Whether to save JSON report

        Returns:
            Scan results dictionary
        """
        if target_path is None:
            target_path = Path(__file__).parent.parent  # Default to workspace root

        target_path = Path(target_path)

        print(f"Starting quality scan of: {target_path}")

        # Import scanner here to avoid circular imports
        from quality_scanner import QualityScanner

        scanner = QualityScanner(self.config)
        issues = scanner.scan_directory(str(target_path))

        # Calculate scores
        file_scores = {}
        for file_path in set(issue.file_path for issue in issues):
            file_issues = [i for i in issues if i.file_path == file_path]
            file_scores[file_path] = self.scorer.calculate_file_score(file_issues)

        project_score = self.scorer.calculate_project_score(file_scores)

        # Update dashboard
        self.dashboard.update_data(project_score, file_scores, issues)

        # Save report if requested
        if save_report:
            self._save_report(project_score, file_scores, issues)

        # Print summary
        self._print_scan_summary(project_score, issues)

        return {
            "project_score": project_score,
            "file_scores": file_scores,
            "issues": issues,
            "scan_path": str(target_path)
        }

    def _save_report(self, project_score: Dict, file_scores: Dict, issues: List[QualityIssue]):
        """Save quality report to file"""
        report_dir = Path(self.config.get("reporting", {}).get("output_directory", "reports"))
        report_dir.mkdir(exist_ok=True)

        # JSON report
        json_report = self.report_generator.generate_json_report(
            project_score, file_scores, issues
        )

        json_path = report_dir / "quality_report.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_report)

        # Markdown report
        md_report = self.report_generator.generate_markdown_report(
            project_score, file_scores, issues
        )

        md_path = report_dir / "quality_report.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_report)

        print(f"Reports saved to: {report_dir}")

    def _print_scan_summary(self, project_score: Dict, issues: List[QualityIssue]):
        """Print scan summary to console"""
        print("\n" + "="*50)
        print("QUALITY SCAN SUMMARY")
        print("="*50)
        print(f"Overall Score: {project_score['overall_score']:.1f}/100 ({project_score['grade'].title()})")
        print(f"Files Analyzed: {project_score['files_analyzed']}")
        print(f"Total Issues: {len(issues)}")

        # Issues by severity
        severity_counts = {}
        for issue in issues:
            severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1

        print("\nIssues by Severity:")
        for severity, count in severity_counts.items():
            print(f"  {severity.title()}: {count}")

        # Issues by category
        category_counts = {}
        for issue in issues:
            category_counts[issue.category.value] = category_counts.get(issue.category.value, 0) + 1

        print("\nIssues by Category:")
        for category, count in category_counts.items():
            print(f"  {category.replace('_', ' ').title()}: {count}")

        print("\nRecommendations:")
        recommendations = self.scorer.generate_recommendations(project_score, {})
        for rec in recommendations:
            print(f"  {rec['priority'].upper()}: {rec['message']}")
            print(f"    Action: {rec['action']}")

        print("="*50)

    def start_dashboard(self, host: str = "localhost", port: int = 8081):
        """Start the quality dashboard web server"""
        print(f"Starting Quality Dashboard on http://{host}:{port}")
        print("Press Ctrl+C to stop...")

        server = QualityDashboardServer(self.dashboard, host, port)
        server.run()

    def get_quality_status(self) -> Dict[str, Any]:
        """Get current quality status for integration with loop cockpit"""
        data = self.dashboard.get_dashboard_data()

        return {
            "overall_score": data["project_score"].get("overall_score", 0),
            "grade": data["project_score"].get("grade", "unknown"),
            "issues_count": len(data["issues"]),
            "files_analyzed": data["project_score"].get("files_analyzed", 0),
            "last_update": data["last_update"],
            "critical_issues": len([i for i in data["issues"] if i["severity"] == "critical"]),
            "high_issues": len([i for i in data["issues"] if i["severity"] == "high"])
        }

    def export_config(self, output_path: str):
        """Export current configuration to file"""
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"Configuration exported to: {output_path}")

    def validate_config(self) -> bool:
        """Validate current configuration"""
        required_keys = ["scanning", "quality_thresholds", "detection_rules", "reporting"]

        for key in required_keys:
            if key not in self.config:
                print(f"Missing required configuration key: {key}")
                return False

        # Validate detection rules
        rules = self.config.get("detection_rules", {})
        if not isinstance(rules, dict):
            print("detection_rules must be a dictionary")
            return False

        print("Configuration validation passed")
        return True


def main():
    """Command-line interface for quality manager"""
    parser = argparse.ArgumentParser(description="Quality Manager Integration")
    parser.add_argument("action", choices=[
        "scan", "dashboard", "status", "export-config", "validate-config"
    ], help="Action to perform")
    parser.add_argument("--path", help="Path to scan or config file")
    parser.add_argument("--host", default="localhost", help="Dashboard host")
    parser.add_argument("--port", type=int, default=8081, help="Dashboard port")
    parser.add_argument("--no-save", action="store_true", help="Don't save scan reports")

    args = parser.parse_args()

    try:
        integration = QualityManagerIntegration()

        if args.action == "scan":
            scan_path = args.path or str(Path.cwd())
            integration.run_quality_scan(scan_path, save_report=not args.no_save)

        elif args.action == "dashboard":
            integration.start_dashboard(args.host, args.port)

        elif args.action == "status":
            status = integration.get_quality_status()
            print(json.dumps(status, indent=2))

        elif args.action == "export-config":
            output_path = args.path or "quality_config_export.json"
            integration.export_config(output_path)

        elif args.action == "validate-config":
            valid = integration.validate_config()
            sys.exit(0 if valid else 1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Quality Check Script

Command-line tool for manual quality assessment and reporting.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add quality_manager to path
sys.path.insert(0, str(Path(__file__).parent.parent / "quality_manager"))

from quality_integration import QualityManagerIntegration


def main():
    """Main entry point for quality check script"""
    parser = argparse.ArgumentParser(
        description="Manual Quality Assessment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python quality_check.py scan                    # Scan current directory
  python quality_check.py scan --path ../project  # Scan specific path
  python quality_check.py status                  # Show current quality status
  python quality_check.py report --format json    # Generate detailed report
        """
    )

    parser.add_argument("command", choices=[
        "scan", "status", "report", "dashboard", "validate"
    ], help="Command to execute")

    parser.add_argument("--path", "-p", help="Path to scan or analyze")
    parser.add_argument("--format", "-f", choices=["json", "markdown", "text"],
                       default="text", help="Output format for reports")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--threshold", "-t", type=float,
                       help="Quality threshold for pass/fail (0-100)")

    args = parser.parse_args()

    try:
        integration = QualityManagerIntegration()

        if args.command == "scan":
            perform_scan(integration, args)

        elif args.command == "status":
            show_status(integration, args)

        elif args.command == "report":
            generate_report(integration, args)

        elif args.command == "dashboard":
            start_dashboard(integration, args)

        elif args.command == "validate":
            validate_system(integration, args)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def perform_scan(integration: QualityManagerIntegration, args: argparse.Namespace):
    """Perform quality scan"""
    scan_path = args.path or str(Path.cwd())

    if args.verbose:
        print(f"Scanning path: {scan_path}")

    results = integration.run_quality_scan(scan_path, save_report=True)

    # Check threshold if specified
    if args.threshold is not None:
        score = results["project_score"]["overall_score"]
        if score < args.threshold:
            print(f"❌ Quality check FAILED: Score {score:.1f} < threshold {args.threshold}")
            sys.exit(1)
        else:
            print(f"✅ Quality check PASSED: Score {score:.1f} >= threshold {args.threshold}")


def show_status(integration: QualityManagerIntegration, args: argparse.Namespace):
    """Show current quality status"""
    status = integration.get_quality_status()

    if args.format == "json":
        print(json.dumps(status, indent=2))
        return

    print("Current Quality Status")
    print("=" * 30)
    print(f"Overall Score: {status['overall_score']:.1f}/100 ({status['grade'].title()})")
    print(f"Files Analyzed: {status['files_analyzed']}")
    print(f"Total Issues: {status['issues_count']}")
    print(f"Critical Issues: {status['critical_issues']}")
    print(f"High Priority Issues: {status['high_issues']}")

    if status['last_update']:
        from datetime import datetime
        dt = datetime.fromisoformat(status['last_update'].replace('Z', '+00:00'))
        print(f"Last Updated: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    else:
        print("Last Updated: Never")

    # Add quality indicator
    score = status['overall_score']
    if score >= 90:
        indicator = "🟢 EXCELLENT"
    elif score >= 80:
        indicator = "🟡 GOOD"
    elif score >= 70:
        indicator = "🟠 ACCEPTABLE"
    elif score >= 60:
        indicator = "🔴 POOR"
    else:
        indicator = "🔴 CRITICAL"

    print(f"Status: {indicator}")


def generate_report(integration: QualityManagerIntegration, args: argparse.Namespace):
    """Generate detailed quality report"""
    # First perform a scan to get fresh data
    scan_path = args.path or str(Path.cwd())
    results = integration.run_quality_scan(scan_path, save_report=False)

    if args.format == "json":
        report_data = {
            "timestamp": results.get("timestamp"),
            "scan_path": results["scan_path"],
            "project_score": results["project_score"],
            "file_scores": results["file_scores"],
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
                for issue in results["issues"]
            ]
        }

        output = json.dumps(report_data, indent=2, ensure_ascii=False)

    elif args.format == "markdown":
        from quality_scorer import QualityReportGenerator
        scorer = integration.scorer
        generator = QualityReportGenerator(scorer)
        output = generator.generate_markdown_report(
            results["project_score"],
            results["file_scores"],
            results["issues"]
        )

    else:  # text format
        output = generate_text_report(results)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Report saved to: {args.output}")
    else:
        print(output)


def generate_text_report(results: Dict[str, Any]) -> str:
    """Generate text format report"""
    lines = []

    lines.append("CODE QUALITY REPORT")
    lines.append("=" * 50)

    ps = results["project_score"]
    lines.append(f"Scan Path: {results['scan_path']}")
    lines.append(f"Overall Score: {ps['overall_score']:.1f}/100 ({ps['grade'].title()})")
    lines.append(f"Files Analyzed: {ps['files_analyzed']}")
    lines.append(f"Average Score: {ps['average_score']:.1f}")
    lines.append("")

    # Quality distribution
    lines.append("Quality Distribution:")
    for grade, count in ps.get("files_by_grade", {}).items():
        pct = (count / ps["files_analyzed"]) * 100
        lines.append(f"  {grade.title()}: {count} files ({pct:.1f}%)")
    lines.append("")

    # Issues summary
    issues = results["issues"]
    lines.append(f"Total Issues: {len(issues)}")

    from collections import Counter
    severity_counts = Counter(i.severity.value for i in issues)
    lines.append("By Severity:")
    for severity, count in severity_counts.items():
        lines.append(f"  {severity.title()}: {count}")

    category_counts = Counter(i.category.value for i in issues)
    lines.append("By Category:")
    for category, count in category_counts.items():
        lines.append(f"  {category.replace('_', ' ').title()}: {count}")
    lines.append("")

    # Top issues
    if issues:
        lines.append("Top 10 Issues:")
        lines.append("-" * 30)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.severity.value, 5))

        for i, issue in enumerate(sorted_issues[:10], 1):
            file_name = Path(issue.file_path).name
            lines.append(f"{i}. [{issue.severity.value.upper()}] {file_name}:{issue.line_number}")
            lines.append(f"   {issue.message}")
            if issue.suggestion:
                lines.append(f"   → {issue.suggestion}")
            lines.append("")

    return "\n".join(lines)


def start_dashboard(integration: QualityManagerIntegration, args: argparse.Namespace):
    """Start the quality dashboard"""
    print("Starting Quality Dashboard...")
    print("Press Ctrl+C to stop")
    integration.start_dashboard(args.host if hasattr(args, 'host') else "127.0.0.1",
                               args.port if hasattr(args, 'port') else 8082)


def validate_system(integration: QualityManagerIntegration, args: argparse.Namespace):
    """Validate quality system configuration and components"""
    print("Validating Quality Management System...")
    print("-" * 40)

    checks = [
        ("Configuration", integration.validate_config()),
        ("Quality Scorer", validate_scorer(integration.scorer)),
        ("Dashboard", validate_dashboard(integration.dashboard)),
    ]

    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False

    print("-" * 40)
    if all_passed:
        print("✅ All validations passed!")
        return True
    else:
        print("❌ Some validations failed!")
        return False


def validate_scorer(scorer) -> bool:
    """Validate quality scorer functionality"""
    try:
        # Test with empty data
        score = scorer.calculate_file_score([])
        return isinstance(score, dict) and "score" in score
    except Exception:
        return False


def validate_dashboard(dashboard) -> bool:
    """Validate dashboard functionality"""
    try:
        data = dashboard.get_dashboard_data()
        return isinstance(data, dict) and "project_score" in data
    except Exception:
        return False


if __name__ == "__main__":
    main()
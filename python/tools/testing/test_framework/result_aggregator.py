"""
Result Aggregator for Universal Testing Framework

Collects, aggregates, and reports test results in multiple formats.
Supports JSON, HTML, Markdown, XML, and CSV output formats.
"""

import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TestResult:
    """Individual test result data structure."""
    test_id: str
    component: str
    test_name: str
    status: str  # 'pass', 'fail', 'error', 'skip'
    duration: float
    output: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuiteResult:
    """Test suite result data structure."""
    suite_name: str
    component: str
    results: List[TestResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ResultAggregator:
    """
    Aggregates and reports test results in multiple formats.

    Collects test results from various sources, provides summary statistics,
    and generates reports in JSON, HTML, Markdown, XML, and CSV formats.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the result aggregator.

        Args:
            output_dir: Directory to save report files (default: current directory)
        """
        self.output_dir = output_dir or Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[TestSuiteResult] = []
        self.global_summary: Dict[str, Any] = {}

    def add_result(self, suite_name: str, component: str, test_result: TestResult):
        """
        Add a test result to the aggregator.

        Args:
            suite_name: Name of the test suite
            component: Component being tested
            test_result: Individual test result
        """
        # Find or create suite result
        suite_result = None
        for sr in self.results:
            if sr.suite_name == suite_name and sr.component == component:
                suite_result = sr
                break

        if suite_result is None:
            suite_result = TestSuiteResult(
                suite_name=suite_name,
                component=component,
                start_time=datetime.now(timezone.utc)
            )
            self.results.append(suite_result)

        # Add result to suite
        suite_result.results.append(test_result)

        # Update suite end time
        suite_result.end_time = datetime.now(timezone.utc)

    def add_suite_result(self, suite_result: TestSuiteResult):
        """
        Add a complete test suite result.

        Args:
            suite_result: Complete test suite result
        """
        self.results.append(suite_result)

    def generate_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of all test results.

        Returns:
            Dictionary containing summary statistics
        """
        total_tests = 0
        passed = 0
        failed = 0
        errors = 0
        skipped = 0
        total_duration = 0.0

        component_stats = {}
        suite_stats = {}

        for suite_result in self.results:
            suite_total = len(suite_result.results)
            suite_passed = 0
            suite_failed = 0
            suite_errors = 0
            suite_skipped = 0
            suite_duration = 0.0

            for result in suite_result.results:
                total_tests += 1
                total_duration += result.duration
                suite_duration += result.duration

                if result.status == 'pass':
                    passed += 1
                    suite_passed += 1
                elif result.status == 'fail':
                    failed += 1
                    suite_failed += 1
                elif result.status == 'error':
                    errors += 1
                    suite_errors += 1
                elif result.status == 'skip':
                    skipped += 1
                    suite_skipped += 1

            # Component statistics
            if suite_result.component not in component_stats:
                component_stats[suite_result.component] = {
                    'total': 0, 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0, 'duration': 0.0
                }

            comp_stat = component_stats[suite_result.component]
            comp_stat['total'] += suite_total
            comp_stat['passed'] += suite_passed
            comp_stat['failed'] += suite_failed
            comp_stat['errors'] += suite_errors
            comp_stat['skipped'] += suite_skipped
            comp_stat['duration'] += suite_duration

            # Suite statistics
            suite_stats[suite_result.suite_name] = {
                'component': suite_result.component,
                'total': suite_total,
                'passed': suite_passed,
                'failed': suite_failed,
                'errors': suite_errors,
                'skipped': suite_skipped,
                'duration': suite_duration,
                'pass_rate': (suite_passed / suite_total * 100) if suite_total > 0 else 0
            }

        # Calculate pass rates for component stats
        for comp_stats in component_stats.values():
            comp_stats['pass_rate'] = (comp_stats['passed'] / comp_stats['total'] * 100) if comp_stats['total'] > 0 else 0

        self.global_summary = {
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'skipped': skipped,
            'pass_rate': (passed / total_tests * 100) if total_tests > 0 else 0,
            'total_duration': total_duration,
            'component_stats': component_stats,
            'suite_stats': suite_stats,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

        return self.global_summary

    def generate_reports(self, formats: List[str] = None) -> Dict[str, Path]:
        """
        Generate reports in specified formats.

        Args:
            formats: List of formats to generate ('json', 'html', 'markdown', 'xml', 'csv')
                    If None, generates all formats

        Returns:
            Dictionary mapping format names to report file paths
        """
        if formats is None:
            formats = ['json', 'html', 'markdown', 'xml', 'csv']

        # Ensure summary is up to date
        self.generate_summary()

        report_files = {}

        for fmt in formats:
            if fmt == 'json':
                report_files['json'] = self._generate_json_report()
            elif fmt == 'html':
                report_files['html'] = self._generate_html_report()
            elif fmt == 'markdown':
                report_files['markdown'] = self._generate_markdown_report()
            elif fmt == 'xml':
                report_files['xml'] = self._generate_xml_report()
            elif fmt == 'csv':
                report_files['csv'] = self._generate_csv_report()

        return report_files

    def _generate_json_report(self) -> Path:
        """Generate JSON report."""
        report_data = {
            'summary': self.global_summary,
            'suite_results': []
        }

        for suite_result in self.results:
            suite_data = {
                'suite_name': suite_result.suite_name,
                'component': suite_result.component,
                'start_time': suite_result.start_time.isoformat() if suite_result.start_time else None,
                'end_time': suite_result.end_time.isoformat() if suite_result.end_time else None,
                'results': []
            }

            for result in suite_result.results:
                result_data = {
                    'test_id': result.test_id,
                    'test_name': result.test_name,
                    'status': result.status,
                    'duration': result.duration,
                    'output': result.output,
                    'error_message': result.error_message,
                    'timestamp': result.timestamp.isoformat() if result.timestamp else None,
                    'metadata': result.metadata
                }
                suite_data['results'].append(result_data)

            report_data['suite_results'].append(suite_data)

        report_path = self.output_dir / 'test_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return report_path

    def _generate_html_report(self) -> Path:
        """Generate HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; flex-wrap: wrap; }}
        .stat {{ background: white; padding: 10px; border-radius: 3px; text-align: center; }}
        .stat.pass {{ background: #d4edda; color: #155724; }}
        .stat.fail {{ background: #f8d7da; color: #721c24; }}
        .stat.error {{ background: #fff3cd; color: #856404; }}
        .suite {{ margin-bottom: 30px; border: 1px solid #ddd; border-radius: 5px; }}
        .suite-header {{ background: #e9ecef; padding: 10px; font-weight: bold; }}
        .test {{ margin: 5px 0; padding: 5px; border-left: 4px solid; }}
        .test.pass {{ border-left-color: #28a745; background: #d4edda; }}
        .test.fail {{ border-left-color: #dc3545; background: #f8d7da; }}
        .test.error {{ border-left-color: #ffc107; background: #fff3cd; }}
        .test.skip {{ border-left-color: #6c757d; background: #f8f9fa; }}
        .duration {{ font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <h1>Test Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <div class="stats">
            <div class="stat">Total Tests: {self.global_summary['total_tests']}</div>
            <div class="stat pass">Passed: {self.global_summary['passed']}</div>
            <div class="stat fail">Failed: {self.global_summary['failed']}</div>
            <div class="stat error">Errors: {self.global_summary['errors']}</div>
            <div class="stat">Skipped: {self.global_summary['skipped']}</div>
            <div class="stat">Pass Rate: {self.global_summary['pass_rate']:.1f}%</div>
            <div class="stat">Duration: {self.global_summary['total_duration']:.2f}s</div>
        </div>
    </div>
"""

        for suite_result in self.results:
            html_content += f"""
    <div class="suite">
        <div class="suite-header">{suite_result.suite_name} ({suite_result.component})</div>
"""

            for result in suite_result.results:
                status_class = result.status
                html_content += f"""
        <div class="test {status_class}">
            <strong>{result.test_name}</strong>
            <span class="duration">({result.duration:.2f}s)</span>
"""

                if result.error_message:
                    html_content += f"<br><em>Error: {result.error_message}</em>"

                html_content += "</div>"

            html_content += "</div>"

        html_content += """
</body>
</html>
"""

        report_path = self.output_dir / 'test_report.html'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return report_path

    def _generate_markdown_report(self) -> Path:
        """Generate Markdown report."""
        md_content = f"""# Test Report

Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Summary

- **Total Tests**: {self.global_summary['total_tests']}
- **Passed**: {self.global_summary['passed']}
- **Failed**: {self.global_summary['failed']}
- **Errors**: {self.global_summary['errors']}
- **Skipped**: {self.global_summary['skipped']}
- **Pass Rate**: {self.global_summary['pass_rate']:.1f}%
- **Total Duration**: {self.global_summary['total_duration']:.2f}s

## Component Statistics

| Component | Total | Passed | Failed | Errors | Skipped | Pass Rate |
|-----------|-------|--------|--------|--------|---------|-----------|
"""

        for comp, stats in self.global_summary['component_stats'].items():
            md_content += f"| {comp} | {stats['total']} | {stats['passed']} | {stats['failed']} | {stats['errors']} | {stats['skipped']} | {stats['pass_rate']:.1f}% |\n"

        md_content += "\n## Test Suite Results\n\n"

        for suite_result in self.results:
            md_content += f"### {suite_result.suite_name} ({suite_result.component})\n\n"

            for result in suite_result.results:
                status_icon = {
                    'pass': '✅',
                    'fail': '❌',
                    'error': '⚠️',
                    'skip': '⏭️'
                }.get(result.status, '❓')

                md_content += f"- {status_icon} **{result.test_name}** ({result.duration:.2f}s)\n"

                if result.error_message:
                    md_content += f"  - Error: {result.error_message}\n"

            md_content += "\n"

        report_path = self.output_dir / 'test_report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return report_path

    def _generate_xml_report(self) -> Path:
        """Generate XML report."""
        root = ET.Element("test-report")
        root.set("generated", datetime.now(timezone.utc).isoformat())

        # Summary
        summary_elem = ET.SubElement(root, "summary")
        for key, value in self.global_summary.items():
            if key != 'component_stats' and key != 'suite_stats':
                ET.SubElement(summary_elem, key).text = str(value)

        # Component stats
        comp_stats_elem = ET.SubElement(summary_elem, "component-stats")
        for comp, stats in self.global_summary['component_stats'].items():
            comp_elem = ET.SubElement(comp_stats_elem, "component", name=comp)
            for stat_key, stat_value in stats.items():
                ET.SubElement(comp_elem, stat_key).text = str(stat_value)

        # Suite results
        suites_elem = ET.SubElement(root, "suite-results")
        for suite_result in self.results:
            suite_elem = ET.SubElement(suites_elem, "suite",
                                     name=suite_result.suite_name,
                                     component=suite_result.component)

            if suite_result.start_time:
                suite_elem.set("start-time", suite_result.start_time.isoformat())
            if suite_result.end_time:
                suite_elem.set("end-time", suite_result.end_time.isoformat())

            for result in suite_result.results:
                result_elem = ET.SubElement(suite_elem, "test",
                                          id=result.test_id,
                                          name=result.test_name,
                                          status=result.status)
                result_elem.set("duration", str(result.duration))

                if result.output:
                    ET.SubElement(result_elem, "output").text = result.output
                if result.error_message:
                    ET.SubElement(result_elem, "error-message").text = result.error_message
                if result.timestamp:
                    result_elem.set("timestamp", result.timestamp.isoformat())

        # Write XML
        tree = ET.ElementTree(root)
        report_path = self.output_dir / 'test_report.xml'
        tree.write(report_path, encoding='utf-8', xml_declaration=True)

        return report_path

    def _generate_csv_report(self) -> Path:
        """Generate CSV report."""
        report_path = self.output_dir / 'test_report.csv'

        with open(report_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['suite_name', 'component', 'test_id', 'test_name', 'status',
                         'duration', 'error_message', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for suite_result in self.results:
                for result in suite_result.results:
                    writer.writerow({
                        'suite_name': suite_result.suite_name,
                        'component': suite_result.component,
                        'test_id': result.test_id,
                        'test_name': result.test_name,
                        'status': result.status,
                        'duration': result.duration,
                        'error_message': result.error_message or '',
                        'timestamp': result.timestamp.isoformat() if result.timestamp else ''
                    })

        return report_path

    def clear_results(self):
        """Clear all stored results."""
        self.results.clear()
        self.global_summary.clear()
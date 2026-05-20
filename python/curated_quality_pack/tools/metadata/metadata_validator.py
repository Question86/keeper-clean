#!/usr/bin/env python3
"""
Metadata Drift Validator
Checks task specification files for anomalies and inconsistencies.
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Any
import argparse
from datetime import timedelta

class MetadataValidator:
    def __init__(self, tasks_dir: Path):
        self.tasks_dir = tasks_dir
        self.warnings = []

    def validate_all_tasks(self) -> List[str]:
        """Validate all task files in the directory and return structured results.

        Returns a dict mapping filename -> { warnings: [], suggestions: [] }
        """
        results: Dict[str, Any] = {}
        for task_file in sorted(self.tasks_dir.glob("task_TASK_*.md")):
            file_results = { 'warnings': [], 'suggestions': [] }
            # capture current warnings list length and compare after validation
            before = len(self.warnings)
            self.validate_task_file(task_file)
            after = len(self.warnings)
            # collect new warnings for this file
            file_results['warnings'].extend(self.warnings[before:after])
            # generate suggestions (non-destructive) for common issues
            suggestions = self.generate_suggestions(task_file)
            file_results['suggestions'].extend(suggestions)
            results[task_file.name] = file_results

        return results

    def validate_task_file(self, task_file: Path) -> None:
        """Validate a single task file."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.warnings.append(f"ERROR reading {task_file.name}: {e}")
            return

        # Check for placeholder timestamps
        self.check_placeholder_timestamps(content, task_file.name)

        # Check CREATED/COMPLETED ordering
        self.check_date_ordering(content, task_file.name)

        # Check for other anomalies
        self.check_other_anomalies(content, task_file.name)

    def check_placeholder_timestamps(self, content: str, filename: str) -> None:
        """Check for placeholder or suspicious timestamps."""
        # Look for timestamps that might be placeholders
        timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z'
        timestamps = re.findall(timestamp_pattern, content)

        for ts in timestamps:
            # Check if it's a round time (00:00:00) which might be placeholder
            if ts.endswith('T00:00:00Z'):
                self.warnings.append(f"WARNING: {filename} - Possible placeholder timestamp: {ts}")

            # Check if it's in the future (more than 1 hour ahead)
            try:
                ts_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                if ts_dt > now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0):
                    self.warnings.append(f"WARNING: {filename} - Future timestamp: {ts}")
            except:
                pass  # Invalid format, skip

    def check_date_ordering(self, content: str, filename: str) -> None:
        """Check CREATED and COMPLETED date ordering."""
        created_match = re.search(r'CREATED:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', content)
        completed_match = re.search(r'COMPLETED:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', content)

        if created_match and completed_match:
            try:
                created_dt = datetime.fromisoformat(created_match.group(1).replace('Z', '+00:00'))
                completed_dt = datetime.fromisoformat(completed_match.group(1).replace('Z', '+00:00'))

                if completed_dt < created_dt:
                    self.warnings.append(f"WARNING: {filename} - COMPLETED date ({completed_match.group(1)}) is before CREATED date ({created_match.group(1)})")
            except:
                pass  # Invalid format, skip

    def check_other_anomalies(self, content: str, filename: str) -> None:
        """Check for other potential anomalies."""
        # Check for missing STATUS
        if not re.search(r'STATUS:\s*\w+', content):
            self.warnings.append(f"WARNING: {filename} - Missing or invalid STATUS field")

        # Check for TASK_XXXX in filename but not in content
        task_id = filename.replace('task_', '').replace('.md', '')
        if task_id not in content:
            self.warnings.append(f"WARNING: {filename} - Task ID {task_id} not found in content")

    def generate_suggestions(self, task_file: Path) -> List[str]:
        """Generate non-destructive correction suggestions for a task file."""
        suggestions: List[str] = []
        try:
            content = task_file.read_text(encoding='utf-8')
        except Exception as e:
            suggestions.append(f"ERROR reading {task_file.name}: {e}")
            return suggestions

        # Suggest replacing placeholder timestamps (T00:00:00Z) with an actionable note
        placeholder_matches = re.findall(r"(\d{4}-\d{2}-\d{2}T00:00:00Z)", content)
        for m in placeholder_matches:
            suggestions.append(f"SUGGESTION: {task_file.name} - Replace placeholder timestamp {m} with an explicit UTC timestamp or [To be defined]")

        # Suggest correcting CREATED/COMPLETED inversion
        created_match = re.search(r'CREATED:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', content)
        completed_match = re.search(r'COMPLETED:\s*(\d{4}-\d{2}-\d{2})', content)
        if created_match and completed_match:
            try:
                created_dt = datetime.fromisoformat(created_match.group(1).replace('Z', '+00:00'))
                completed_date = datetime.strptime(completed_match.group(1), '%Y-%m-%d')
                if completed_date < created_dt.date():
                    suggestions.append(f"SUGGESTION: {task_file.name} - COMPLETED date appears before CREATED; consider updating COMPLETED or CREATED dates.")
            except Exception:
                pass

        return suggestions

    def apply_corrections(self, apply_placeholders: bool = False) -> List[str]:
        """Apply safe corrections to task files. Returns list of applied edits."""
        edits: List[str] = []
        for task_file in sorted(self.tasks_dir.glob("task_TASK_*.md")):
            try:
                content = task_file.read_text(encoding='utf-8')
            except Exception as e:
                edits.append(f"ERROR reading {task_file.name}: {e}")
                continue

            original = content
            # Safe correction: replace placeholder timestamps T00:00:00Z with current UTC timestamp
            if apply_placeholders:
                now_ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                content = re.sub(r"(\d{4}-\d{2}-\d{2})T00:00:00Z", now_ts, content)

            if content != original:
                try:
                    task_file.write_text(content, encoding='utf-8')
                    edits.append(f"APPLIED: {task_file.name} - placeholder timestamps updated")
                except Exception as e:
                    edits.append(f"ERROR writing {task_file.name}: {e}")

        return edits

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Metadata validator')
    parser.add_argument('--apply', action='store_true', help='Apply safe corrections (placeholder timestamps)')
    args = parser.parse_args()

    workspace_root = Path(__file__).parent
    tasks_dir = workspace_root / "tasks"

    if not tasks_dir.exists():
        print("ERROR: tasks/ directory not found")
        raise SystemExit(1)

    validator = MetadataValidator(tasks_dir)
    results = validator.validate_all_tasks()

    # Print structured output
    any_warnings = False
    for fname, info in results.items():
        if info['warnings'] or info['suggestions']:
            any_warnings = True
            print(f"== {fname} ==")
            for w in info['warnings']:
                print(f"  {w}")
            for s in info['suggestions']:
                print(f"  {s}")
            print('')

    if not any_warnings:
        print("No metadata anomalies detected.")

    if args.apply:
        edits = validator.apply_corrections(apply_placeholders=True)
        if edits:
            print('\nApplied edits:')
            for e in edits:
                print(f'  {e}')
        else:
            print('\nNo edits applied.')

    print(f"\nValidated {len(list(tasks_dir.glob('task_TASK_*.md')))} task files.")

if __name__ == "__main__":
    main()
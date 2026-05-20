#!/usr/bin/env python3
"""
Comprehensive API Audit Script
Uses KnowledgeDB to find task/report references for all APIs in api_inventory.csv
"""

import sys, os, csv
from pathlib import Path
from typing import Dict, List, Set
import re

# Ensure project root on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from knowledge_db import KnowledgeDB

def extract_task_from_report_filename(filename: str) -> str:
    """Extract task ID from report filename like 'report_TASK_XXXX_LYY_vNN.md'"""
    match = re.search(r'report_(TASK_\d+)_L\d+_v\d+\.md', filename)
    return match.group(1) if match else None

def extract_loop_from_report_filename(filename: str) -> int:
    """Extract loop number from report filename"""
    match = re.search(r'report_TASK_\d+_L(\d+)_v\d+\.md', filename)
    return int(match.group(1)) if match else None

def audit_api_references():
    """Audit all APIs in api_inventory.csv for task/report references"""

    # Initialize database
    db = KnowledgeDB(Path(ROOT))

    # Read current CSV
    csv_path = Path(ROOT) / 'api_inventory.csv'
    apis = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            apis.append(row)

    print(f"Loaded {len(apis)} APIs from inventory")

    # Audit each API
    updated_count = 0

    for i, api in enumerate(apis):
        route = api['API Route']
        print(f"\nAuditing API {i+1}/{len(apis)}: {route}")

        # Search for this API route in the knowledge base
        try:
            results = db.search(
                query=f'"{route}"',  # Exact phrase match
                types=['report', 'task', 'doc'],
                limit=50
            )

            print(f"  Found {len(results)} search results")

            # Extract task and report references
            tasks_found = set()
            reports_found = set()
            loops_found = set()

            for result in results:
                if result.type == 'report':
                    # Extract task from report ID
                    task_id = extract_task_from_report_filename(result.id)
                    if task_id:
                        tasks_found.add(task_id)
                        reports_found.add(result.id)
                        loop_num = extract_loop_from_report_filename(result.id)
                        if loop_num:
                            loops_found.add(loop_num)

                elif result.type == 'task':
                    tasks_found.add(result.id)

            # Update CSV if we found references
            current_task = api.get('Corresponding_Task', '').strip()
            current_report = api.get('Implementation_Report', '').strip()

            # Find the most recent task/report
            best_task = None
            best_report = None
            best_loop = 0

            if tasks_found:
                # Sort tasks by number for most recent
                sorted_tasks = sorted(tasks_found, key=lambda x: int(re.search(r'TASK_(\d+)', x).group(1)) if re.search(r'TASK_(\d+)', x) else 0, reverse=True)
                best_task = sorted_tasks[0]

            if reports_found:
                # Sort reports by loop number for most recent
                sorted_reports = sorted(reports_found, key=lambda x: extract_loop_from_report_filename(x) or 0, reverse=True)
                best_report = sorted_reports[0]
                best_loop = extract_loop_from_report_filename(best_report) or 0

            # Update if different from current
            updated = False
            if best_task and best_task != current_task:
                api['Corresponding_Task'] = best_task
                updated = True
                print(f"  Updated task: {current_task} -> {best_task}")

            if best_report and best_report != current_report:
                api['Implementation_Report'] = best_report
                updated = True
                print(f"  Updated report: {current_report} -> {best_report}")

            if updated:
                updated_count += 1

            # Debug info
            if tasks_found or reports_found:
                print(f"  Found tasks: {sorted(tasks_found)}")
                print(f"  Found reports: {sorted(reports_found)}")
                print(f"  Found loops: {sorted(loops_found)}")

        except Exception as e:
            print(f"  Error searching for {route}: {e}")

    # Write updated CSV
    if updated_count > 0:
        print(f"\nUpdated {updated_count} APIs. Writing to CSV...")
        
        # Write to temp file first
        temp_csv = csv_path.with_suffix('.tmp')
        with open(temp_csv, 'w', newline='', encoding='utf-8') as f:
            if apis:
                writer = csv.DictWriter(f, fieldnames=apis[0].keys())
                writer.writeheader()
                writer.writerows(apis)
        
        # Move temp file to replace original
        import shutil
        shutil.move(str(temp_csv), str(csv_path))
        
        print("CSV updated successfully")
    else:
        print("\nNo updates needed")

    # Summary
    orphaned = sum(1 for api in apis if api.get('Corresponding_Task') in ['NONE', ''])
    reported = sum(1 for api in apis if api.get('Implementation_Report', '').endswith('.md'))

    print(f"\nAudit Summary:")
    print(f"Total APIs: {len(apis)}")
    print(f"Orphaned (no task): {orphaned}")
    print(f"With reports: {reported}")
    print(f"Updated this run: {updated_count}")

if __name__ == '__main__':
    audit_api_references()
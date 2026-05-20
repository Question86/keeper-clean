#!/usr/bin/env python3
"""
Simple API Audit Script
"""

import sys, os, csv
from pathlib import Path
import re

# Ensure project root on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from knowledge_db import KnowledgeDB

def extract_task_from_report_filename(filename: str) -> str:
    match = re.search(r'report_(TASK_\d+)_L\d+_v\d+\.md', filename)
    return match.group(1) if match else None

# Initialize database
db = KnowledgeDB(Path(ROOT))

# Read current CSV
csv_path = Path(ROOT) / 'api_inventory.csv'
apis = []

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        apis.append(row)

print(f'Loaded {len(apis)} APIs from inventory')

# Audit each API
updated_count = 0

for i, api in enumerate(apis):
    route = api['API Route']
    print(f'Auditing API {i+1}/{len(apis)}: {route}')

    try:
        results = db.search(query=f'"{route}"', types=['report', 'task'], limit=20)

        tasks_found = set()
        for result in results:
            if result.type == 'report':
                task_id = extract_task_from_report_filename(result.id)
                if task_id:
                    tasks_found.add(task_id)
            elif result.type == 'task':
                tasks_found.add(result.id)

        current_task = api.get('Corresponding_Task', '').strip()
        best_task = None
        if tasks_found:
            sorted_tasks = sorted(tasks_found, key=lambda x: int(re.search(r'TASK_(\d+)', x).group(1)) if re.search(r'TASK_(\d+)', x) else 0, reverse=True)
            best_task = sorted_tasks[0]

        if best_task and best_task != current_task:
            api['Corresponding_Task'] = best_task
            updated_count += 1
            print(f'  Updated: {current_task} -> {best_task}')

    except Exception as e:
        print(f'  Error: {e}')

# Write to new CSV file
new_csv_path = Path(ROOT) / 'api_inventory_updated.csv'
with open(new_csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=apis[0].keys())
    writer.writeheader()
    writer.writerows(apis)

print(f'Updated {updated_count} APIs. Written to api_inventory_updated.csv')
#!/usr/bin/env python3
"""
Comprehensive API Reference Hunter
Finds task references for orphaned APIs using multiple search strategies
"""

import sys, os, csv, re
from pathlib import Path
from typing import Dict, List, Set

# Ensure project root on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from knowledge_db import KnowledgeDB

def extract_task_from_report_filename(filename: str) -> str:
    match = re.search(r'report_(TASK_\d+)_L\d+_v\d+\.md', filename)
    return match.group(1) if match else None

def extract_loop_from_report_filename(filename: str) -> int:
    match = re.search(r'report_TASK_\d+_L(\d+)_v\d+\.md', filename)
    return int(match.group(1)) if match else None

def search_strategies_for_api(api_route: str) -> List[str]:
    """Generate multiple search queries for an API route"""
    strategies = []

    # Exact route
    strategies.append(f'"{api_route}"')

    # Route without leading slash
    if api_route.startswith('/'):
        strategies.append(f'"{api_route[1:]}"')

    # Route components
    parts = api_route.strip('/').split('/')
    if len(parts) > 1:
        # Last part (endpoint name)
        strategies.append(f'"{parts[-1]}"')
        # Second to last part
        if len(parts) > 2:
            strategies.append(f'"{parts[-2]}"')

    # Common variations
    if 'orchestrator' in api_route.lower():
        strategies.append('"orchestrator"')
    if 'session' in api_route.lower():
        strategies.append('"session"')
    if 'agent' in api_route.lower():
        strategies.append('"agent"')
    if 'chaosbox' in api_route.lower():
        strategies.append('"chaosbox"')
    if 'finalization' in api_route.lower():
        strategies.append('"finalization"')
    if 'monitoring' in api_route.lower():
        strategies.append('"monitoring"')

    # Remove duplicates
    return list(set(strategies))

def find_api_references():
    """Find references for orphaned APIs using comprehensive search"""

    # Initialize database
    db = KnowledgeDB(Path(ROOT))

    # Read current CSV
    csv_path = Path(ROOT) / 'api_inventory_new.csv'
    apis = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            apis.append(row)

    # Get orphaned APIs
    orphaned_apis = [api for api in apis if api.get('Corresponding_Task') in ['NONE', '']]

    print(f'Found {len(orphaned_apis)} orphaned APIs to investigate')

    # Search for each orphaned API
    found_references = {}

    for api in orphaned_apis:
        route = api['API Route']
        print(f'\nInvestigating: {route}')

        # Try multiple search strategies
        all_results = []
        tried_queries = set()

        for query in search_strategies_for_api(route):
            if query in tried_queries:
                continue
            tried_queries.add(query)

            try:
                results = db.search(
                    query=query,
                    types=['report', 'task', 'doc'],
                    limit=10
                )

                if results:
                    print(f'  Query "{query}": {len(results)} results')
                    all_results.extend(results)
                else:
                    print(f'  Query "{query}": 0 results')

            except Exception as e:
                print(f'  Query "{query}": Error - {e}')

        # Process results
        tasks_found = set()
        reports_found = set()

        for result in all_results:
            if result.type == 'report':
                task_id = extract_task_from_report_filename(result.id)
                if task_id:
                    tasks_found.add(task_id)
                    reports_found.add(result.id)
            elif result.type == 'task':
                tasks_found.add(result.id)

        # Find best task reference
        best_task = None
        if tasks_found:
            # Sort by task number (most recent)
            sorted_tasks = sorted(tasks_found, key=lambda x: int(re.search(r'TASK_(\d+)', x).group(1)) if re.search(r'TASK_(\d+)', x) else 0, reverse=True)
            best_task = sorted_tasks[0]

        if best_task:
            found_references[route] = best_task
            print(f'  ✓ Found reference: {best_task}')
        else:
            print(f'  ✗ No references found')

    # Update CSV with found references
    updated_count = 0
    for api in apis:
        route = api['API Route']
        if route in found_references and api.get('Corresponding_Task') in ['NONE', '']:
            api['Corresponding_Task'] = found_references[route]
            updated_count += 1
            print(f'Updated {route}: NONE -> {found_references[route]}')

    # Write updated CSV
    if updated_count > 0:
        output_path = Path(ROOT) / 'api_inventory_final.csv'
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=apis[0].keys())
            writer.writeheader()
            writer.writerows(apis)

        print(f'\nUpdated {updated_count} APIs. Written to api_inventory_final.csv')

    # Final summary
    still_orphaned = sum(1 for api in apis if api.get('Corresponding_Task') in ['NONE', ''])
    print(f'\nFinal Status:')
    print(f'Total APIs: {len(apis)}')
    print(f'Still orphaned: {still_orphaned}')
    print(f'Now referenced: {len(apis) - still_orphaned}')

    if still_orphaned > 0:
        print('\nRemaining orphaned APIs:')
        for api in apis:
            if api.get('Corresponding_Task') in ['NONE', '']:
                print(f'  - {api["API Route"]}')

if __name__ == '__main__':
    find_api_references()
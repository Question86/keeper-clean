import csv
import os
import glob
import re

def find_task_for_route(route):
    """Find the task file that mentions this route"""
    task_files = glob.glob('tasks/task_TASK_*.md')
    for task_file in task_files:
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if route in content:
                    # Extract task ID from filename
                    match = re.search(r'task_(TASK_\d+)\.md', task_file)
                    if match:
                        return match.group(1)
        except:
            continue
    return None

def find_report_for_task(task_id):
    """Find the latest report for this task"""
    report_pattern = f'reports/report_{task_id}_L*_v*.md'
    report_files = glob.glob(report_pattern)
    if report_files:
        # Get the latest version
        report_files.sort(reverse=True)
        return report_files[0]
    return None

def check_implementation_status(route, task_id, report_file):
    """Check if implementation matches report"""
    if not report_file:
        return "NO_REPORT"
    
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if route in content:
                # Check if report indicates completion
                if 'COMPLETED' in content or 'SUCCESS' in content:
                    return "REPORTED_COMPLETE"
                else:
                    return "REPORTED_INCOMPLETE"
            else:
                return "NOT_IN_REPORT"
    except:
        return "REPORT_READ_ERROR"
    
    return "UNKNOWN"

def main():
    csv_file = 'api_inventory.csv'
    rows = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Add new columns
    for row in rows:
        route = row['API Route']
        task_id = find_task_for_route(route)
        row['Corresponding_Task'] = task_id or 'NONE'
        
        if task_id:
            report_file = find_report_for_task(task_id)
            row['Implementation_Report'] = os.path.basename(report_file) if report_file else 'NONE'
            row['Consistency_Status'] = check_implementation_status(route, task_id, report_file)
        else:
            row['Implementation_Report'] = 'NONE'
            row['Consistency_Status'] = 'ORPHANED'
    
    # Write updated CSV
    fieldnames = list(rows[0].keys()) if rows else []
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Summary
    total = len(rows)
    orphaned = sum(1 for r in rows if r['Consistency_Status'] == 'ORPHANED')
    consistent = sum(1 for r in rows if r['Consistency_Status'] in ['REPORTED_COMPLETE'])
    inconsistent = total - orphaned - consistent
    
    print(f"Analysis Complete:")
    print(f"Total endpoints: {total}")
    print(f"Orphaned (no task): {orphaned}")
    print(f"Consistent: {consistent}")
    print(f"Inconsistent: {inconsistent}")

if __name__ == '__main__':
    main()
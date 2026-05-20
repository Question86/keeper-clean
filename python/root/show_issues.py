import json

with open('reports/quality_report.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('TOP 20 QUALITY ISSUES FOUND:')
print('=' * 50)

severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
sorted_issues = sorted(data['issues'], key=lambda x: severity_order.get(x['severity'], 5))

for i, issue in enumerate(sorted_issues[:20], 1):
    filename = issue['file_path'].split('\\')[-1]
    print(f'{i}. [{issue["severity"].upper()}] {filename}:{issue["line_number"]}')
    print(f'   {issue["message"]}')
    if 'suggestion' in issue and issue['suggestion']:
        print(f'   → {issue["suggestion"]}')
    print()

print(f'\nTotal issues found: {len(data["issues"])}')
print(f'Files analyzed: {data["project_score"]["files_analyzed"]}')
print(f'Overall score: {data["project_score"]["overall_score"]:.1f}/100 ({data["project_score"]["grade"]})')
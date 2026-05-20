import re
from pathlib import Path

# Read the report
report_path = Path('reports/report_TASK_0089_L63_v01.md')
content = report_path.read_text().lower()

# Check concrete evidence patterns
concrete_patterns = [
    '✅ successfully',
    '✅ added',
    '✅ integrated',
    '✅ implemented',
    'verified working',
    'tested and confirmed',
    'implementation complete',
]

print('=== CONCRETE EVIDENCE PATTERNS ===')
concrete_score = 0
for pattern in concrete_patterns:
    count = content.count(pattern)
    if count > 0:
        concrete_score += 3
        print(f'✓ {pattern}: {count} (score +3)')
    else:
        print(f'✗ {pattern}: 0')

print(f'Concrete score: {min(concrete_score, 6)}/6')

# Check creation patterns
creation_patterns = [
    'created file `',
    'created directory `',
    'generated code in `',
    'added to repository `',
    'committed `',
]

print('\n=== CREATION PATTERNS ===')
creation_score = 0
for pattern in creation_patterns:
    count = content.count(pattern)
    if count > 0:
        creation_score += 4
        print(f'✓ {pattern}: {count} (score +4)')
    else:
        print(f'✗ {pattern}: 0')

print(f'Creation score: {min(creation_score, 8)}/8')

# Check file references
file_refs = re.findall(r'`([^`]+)`', content)
print(f'\n=== FILE REFERENCES ===')
print(f'Found {len(file_refs)} backtick references')
verified = 0
for ref in file_refs[:5]:  # Check first 5
    full_path = Path('d:/Keeper-Clean-Loop1') / ref
    if full_path.exists():
        verified += 1
        print(f'✓ {ref} exists')
    else:
        print(f'✗ {ref} does not exist')

print(f'File verification score: {min(verified * 2, 4)}/4')

# Check technical patterns
technical_patterns = [
    'function `', 'class `', 'def `',
    'API endpoint `/', 'database table',
    'algorithm implemented', 'validation added',
]

print('\n=== TECHNICAL PATTERNS ===')
technical_count = 0
for pattern in technical_patterns:
    count = content.count(pattern)
    if count > 0:
        technical_count += 1
        print(f'✓ {pattern}: {count} (score +1)')
    else:
        print(f'✗ {pattern}: 0')

print(f'Technical score: {min(technical_count, 3)}/3')

total = min(concrete_score, 6) + min(creation_score, 8) + min(verified * 2, 4) + min(technical_count, 3)
print(f'\nTOTAL SCORE: {total}/15')
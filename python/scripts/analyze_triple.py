from pathlib import Path
p=Path('tests/test_task_0022_real_integration.py')
s=p.read_text()
print('len',len(s))
print('occurrences of triple-quote', s.count('"""'))
for i in range(len(s)):
    if s.startswith('"""', i):
        print('triple at', i)
print('\n--- file repr start ---')
print(repr(s[:500]))
print('--- file repr end ---')

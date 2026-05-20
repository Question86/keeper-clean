from pathlib import Path
p=Path('tests/test_task_0022_real_integration.py')
s=p.read_text()
for i,l in enumerate(s.splitlines(), start=1):
    print(f"{i:03}: {l}")

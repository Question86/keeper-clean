from pathlib import Path
p=Path('tests/test_task_0022_real_integration.py')
s=p.read_text()
try:
    compile(s, str(p), 'exec')
    print('compile OK')
except Exception as e:
    import traceback
    print('compile FAILED')
    traceback.print_exc()

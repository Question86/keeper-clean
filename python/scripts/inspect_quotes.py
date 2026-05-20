from pathlib import Path
p=Path('tests/test_task_0022_real_integration.py')
s=p.read_text()
for pos in [0,16,230,240,250,255,260,400]:
    print('pos',pos, repr(s[pos:pos+40]))
print('\nFull content with visible newlines:')
print(s)

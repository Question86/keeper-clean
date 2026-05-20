# MODE: SCRIPT\n\nimport os
from pathlib import Path
p = Path(r'C:/Users/ambas/.ollama/blobs')
if not p.exists():
    print('BLOBS_DIR_NOT_FOUND', p)
else:
    for f in sorted(p.iterdir()):
        try:
            print(f.name, f.stat().st_size)
        except Exception as e:
            print(f.name, 'ERROR', e)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_db import KnowledgeDB

p = Path('archive/ARCHIV_0114.md')
if not p.exists():
    print('archive/ARCHIV_0114.md not found')
    raise SystemExit(1)

db = KnowledgeDB(Path('.'))
try:
    lessons = db._index_archive(p)
    print(f'Indexed archive/ARCHIV_0114.md, lessons extracted: {lessons}')
finally:
    db.close()

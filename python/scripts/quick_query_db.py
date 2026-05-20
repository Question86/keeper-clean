import sys, os
from pathlib import Path
# Ensure project root on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
from knowledge_db import KnowledgeDB
DB = KnowledgeDB(Path(ROOT))
res = DB.search(query='ARCHIV_0112', types=['archive'], loop_min=112, loop_max=112, limit=10)
print('Search result count:', len(res))
print(res[:2])

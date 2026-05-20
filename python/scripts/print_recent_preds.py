from knowledge_db import KnowledgeDB
from pathlib import Path

db = KnowledgeDB(Path('.'))
rows = db.get_bootstrap_prediction_history(limit=5)
for r in rows:
    print(r.get('id'), r.get('task_id'), r.get('timestamp'))

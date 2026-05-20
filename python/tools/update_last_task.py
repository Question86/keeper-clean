# MODE: SCRIPT\n\nimport json
from datetime import datetime, timezone
p = 'current.json'
with open(p,'r',encoding='utf-8') as f:
    cur = json.load(f)
cur['STATE']['lastTaskWorked'] = 'TASK_0023'
cur['STATE']['lastUpdate'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
with open(p,'w',encoding='utf-8') as f:
    json.dump(cur,f,indent=2)
print('Updated lastTaskWorked to TASK_0023')

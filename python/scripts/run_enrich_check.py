from loop_guardrails import enrich_task_with_knowledge
from pathlib import Path

r = enrich_task_with_knowledge('TASK_0081', Path('.'))
print('Result:', r)
if r:
    p = Path(r)
    print('Exists:', p.exists())
    print('Head:', p.read_text()[:200])
    try:
        p.unlink()
    except Exception:
        pass

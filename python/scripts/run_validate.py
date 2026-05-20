from loop_guardrails import validate_all_schemas
from pathlib import Path
import json

r = validate_all_schemas(Path('.'))
print(json.dumps(r, indent=2))
if not r.get('valid'):
    raise SystemExit(1)

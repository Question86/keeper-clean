# MODE: SCRIPT\n\nfrom loop_guardrails import validate_all_schemas
from pathlib import Path
import json
r = validate_all_schemas(Path('.'))
print(json.dumps(r, indent=2))

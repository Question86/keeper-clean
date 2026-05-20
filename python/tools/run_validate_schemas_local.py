# MODE: SCRIPT\n\nimport sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from loop_guardrails import validate_all_schemas
from pathlib import Path
import json
r = validate_all_schemas(Path('.'))
print(json.dumps(r, indent=2))

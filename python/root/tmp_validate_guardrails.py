import json
from pathlib import Path
import loop_guardrails as lg
res = lg.validate_all_schemas(Path.cwd())
print(json.dumps(res, indent=2))

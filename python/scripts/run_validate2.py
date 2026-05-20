import runpy, json
from pathlib import Path

g = runpy.run_path('loop_guardrails.py')
validate = g.get('validate_all_schemas')
if not validate:
    print(json.dumps({'valid': False, 'error': 'validate_all_schemas not found in loop_guardrails.py'}, indent=2))
    raise SystemExit(1)

r = validate(Path('.'))
print(json.dumps(r, indent=2))
if not r.get('valid'):
    raise SystemExit(1)

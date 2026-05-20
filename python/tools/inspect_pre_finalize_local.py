# MODE: SCRIPT\n\nimport sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from loop_cockpit import audit_loop_integrity, check_archive_consistency, metadata_lint
from pathlib import Path
import json

print('audit_loop_integrity:')
ok, issues, warnings = audit_loop_integrity()
print('ok:', ok)
print('issues:', json.dumps(issues, indent=2))
print('warnings:', json.dumps(warnings, indent=2))

print('\ncheck_archive_consistency:')
cons = check_archive_consistency(Path('.'))
print(json.dumps(cons, indent=2))

print('\nmetadata_lint:')
print(json.dumps(metadata_lint(Path('.')), indent=2))

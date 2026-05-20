# MODE: SCRIPT\n\nfrom loop_cockpit import audit_loop_integrity, check_archive_consistency, metadata_lint
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

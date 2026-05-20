from loop_cockpit import audit_loop_integrity, check_archive_consistency, metadata_lint
from pathlib import Path
import json
ok, issues, warnings = audit_loop_integrity()
print('ok:', ok)
print('issues:', json.dumps(issues, indent=2))
print('warnings:', json.dumps(warnings, indent=2))
cons = check_archive_consistency(Path('.'))
print('consistency:', json.dumps(cons, indent=2))
print('lint:', json.dumps(metadata_lint(Path('.')), indent=2))
#!/usr/bin/env python3
"""Generate an ARCHIV preview without modifying workspace state.

Writes ARCHIV_<loop>_PREVIEW.md to workspace root and prints issues/warnings.
"""
import sys
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import loop_cockpit as lc


def main():
    try:
        current = lc.read_json_file(lc.CURRENT_JSON)
    except Exception as e:
        print(f"ERROR: could not read CURRENT_JSON: {e}")
        return 2

    status = current.get('STATE', {}).get('status')
    loop_num = current.get('STATE', {}).get('loop', 0)
    last_task = current.get('STATE', {}).get('lastTaskWorked')

    if status != 'ACTIVE':
        print(f"BLOCKED: current state status='{status}' (must be 'ACTIVE' to preview finalization)")
        return 3

    print("Running pre-finalization audits...")
    ok, issues, warnings = lc.audit_loop_integrity()
    consistency = lc.check_archive_consistency(lc.WORKSPACE_ROOT)
    lint = lc.metadata_lint(lc.WORKSPACE_ROOT)

    print('audit ok:', ok)
    if issues:
        print('audit issues:', json.dumps(issues, indent=2))
    if warnings:
        print('audit warnings:', json.dumps(warnings, indent=2))

    print('consistency:', json.dumps(consistency, indent=2))
    print('lint summary:', json.dumps({'errors': len(lint.get('errors', [])), 'warnings': len(lint.get('warnings', []))}))

    blocked = False
    if not ok:
        print('PREVIEW BLOCKED: audit failed')
        blocked = True
    if not consistency.get('is_consistent', True):
        print('PREVIEW BLOCKED: archive consistency failed')
        blocked = True
    if lint.get('errors'):
        print('PREVIEW BLOCKED: metadata lint errors present')
        blocked = True

    if blocked:
        return 1

    neu = lc.read_text_file(lc.NEU_MD)
    alt = lc.read_text_file(lc.ALT_MD)

    from datetime import datetime, timezone

    preview_name = f"ARCHIV_{loop_num:04d}_PREVIEW.md"
    preview_path = lc.WORKSPACE_ROOT / preview_name

    archiv_content = f"""# ARCHIV_{loop_num:04d}

MODE: PREVIEW
PREVIEW_GENERATED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

---

## LOOP SUMMARY

**Loop ID:** {loop_num}
**Last Task Worked:** {last_task or 'None'}
**Finalization Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

---

## TASKS AT FINALIZATION

### Active Tasks (NEU.md)
```
{neu}
```

### Closed Tasks (Alt.md)
```
{alt}
```

---

## NOTES

Preview generated via scripts/finalize_preview.py — no files were moved and current.json was not modified.

---

END OF DOCUMENT
"""

    preview_path.write_text(archiv_content, encoding='utf-8')

    combined_warnings = []
    if warnings:
        combined_warnings.extend(warnings)
    if consistency.get('warnings'):
        combined_warnings.extend(consistency.get('warnings'))
    if lint.get('warnings'):
        combined_warnings.extend([f"{w.get('code','')}: {w.get('message','')}" for w in lint.get('warnings', [])])

    print(f"PREVIEW WRITTEN: {preview_path}")
    if combined_warnings:
        print('WARNINGS:')
        for w in combined_warnings:
            print('-', w)

    return 0


if __name__ == '__main__':
    rc = main()
    sys.exit(rc or 0)

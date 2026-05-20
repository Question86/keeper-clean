# MODE: SCRIPT\n\n"""Find potential jailbreaks and protocol-bypass events in workspace logs and archives.

Produces JSON output with findings and exits with code 1 when serious events are detected.
"""
import json
from pathlib import Path
import re
import sys

# Use workspace root (one level up from tools/)
WORKSPACE = Path(__file__).resolve().parent.parent
TRANSACTION_LOG = WORKSPACE / "_transaction_log.jsonl"
STATE_TRANSITION_LOG = WORKSPACE / "_state_transition.log"
REPORTS_DIR = WORKSPACE / "reports"
ARCHIVE_DIR = WORKSPACE / "archive"


def load_jsonl(path: Path):
    if not path.exists():
        return []
    res = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            res.append(json.loads(line))
        except Exception:
            continue
    return res


def scan_transaction_log():
    findings = []
    for entry in load_jsonl(TRANSACTION_LOG):
        op = entry.get('operation')
        if op in ('confirm-bootstrap', 'incident_report'):
            findings.append({
                'source': 'transaction_log',
                'op': op,
                'entry': entry
            })
        if op == 'file_delete' and entry.get('target') == '_BOOTSTRAP.md':
            findings.append({
                'source': 'transaction_log',
                'op': 'bootstrap_deleted',
                'entry': entry
            })
    return findings


def scan_state_transitions():
    findings = []
    if not STATE_TRANSITION_LOG.exists():
        return findings
    txt = STATE_TRANSITION_LOG.read_text(encoding='utf-8')
    for line in txt.splitlines():
        if 'IMPLICIT_ACTIVE_TRANSITION' in line or 'FAILED' in line and 'IMPLICIT_ACTIVE_TRANSITION' in line:
            findings.append({'source': 'state_transition_log', 'line': line})
        if 'confirm-bootstrap' in line and 'SUCCESS' in line and 'IDEMPOTENT' not in line:
            findings.append({'source': 'state_transition_log', 'line': line})
    return findings


def scan_reports_for_incidents():
    findings = []
    for p in REPORTS_DIR.glob('report_INCIDENT_*.md'):
        txt = p.read_text(encoding='utf-8')
        if 'BOOTSTRAP PROTOCOL VIOLATION' in txt or 'BOOTSTRAP' in txt:
            findings.append({'source': 'reports', 'file': str(p), 'summary_line': txt.splitlines()[0:10]})
    return findings


def generate_report():
    findings = []
    findings.extend(scan_transaction_log())
    findings.extend(scan_state_transitions())
    findings.extend(scan_reports_for_incidents())

    result = {
        'workspace': str(WORKSPACE),
        'findings_count': len(findings),
        'findings': findings
    }
    print(json.dumps(result, indent=2))
    # Exit non-zero if serious findings exist (any findings)
    return result


if __name__ == '__main__':
    r = generate_report()
    sys.exit(0 if r['findings_count'] == 0 else 1)

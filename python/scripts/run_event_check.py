import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loop_guardrails import write_text, utc_now_iso
from loop_cockpit import KnowledgeDBEventHandler
from knowledge_db import KnowledgeDB

reports_dir = ROOT / 'reports'
reports_dir.mkdir(exist_ok=True)
report_path = reports_dir / 'report_test_EVENT_L99_v01.md'
content = f"""# REPORT: TEST EVENT

MODE: EXECUTION REPORT
STATUS: COMPLETED
CREATED: {utc_now_iso()}

---

## EXECUTIVE SUMMARY

This is a test report for indexing.

---

END OF REPORT
"""
write_text(report_path, content)

KnowledgeDBEventHandler.on_report_created(report_path)

# Query DB
db = KnowledgeDB(ROOT)
try:
    try:
        res = db.search('test report', types=['report'])
        print('Found results:', len(res))
        for r in res[:5]:
            print(r.type, r.id, r.relevance)
    except Exception as e:
        # Keep this script non-crashing even if FTS tables are inconsistent.
        print(f"Search unavailable ({type(e).__name__}): {e}")
finally:
    db.close()

# cleanup
try:
    report_path.unlink()
except Exception:
    pass

import sqlite3
from datetime import datetime, timezone

# Read the full archive content
with open('ARCHIV_0111.md', 'r', encoding='utf-8') as f:
    content_full = f.read()

# Brief summary and artifacts extracted
summary = "Loop 111 finalization: adaptive bootstrap improvements, bandwidth guard, instrumentation, A/B tests."
lessons_learned = "Density-based selection, stronger size penalty, ROI-per-token scoring; BandwidthGuard prevents bandwidth-triggered failures; parameter sweep pending."
# Store tasks as an actual list and serialize to JSON to ensure DB fields are parseable
tasks_completed = ["TASK_0156", "TASK_0207"]
import json
tasks_completed_json = json.dumps(tasks_completed)

infrastructure_created = "adaptive_bootstrap.py, rate_limit_handler.py, scripts/instrument_bootstrap_load.py"

indexed_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# Connect to database and insert
conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

cursor.execute('''
INSERT INTO archives (id, loop_num, path, summary, lessons_learned, tasks_completed, infrastructure_created, content_full, indexed_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    'ARCHIV_0111',
    111,
    'ARCHIV_0111.md',
    summary,
    lessons_learned,
    tasks_completed_json,
    infrastructure_created,
    content_full,
    indexed_at
))

conn.commit()
conn.close()

print('Successfully inserted ARCHIV_0111 into knowledge database')
import sqlite3
from datetime import datetime, timezone
import json

# Read the full archive content
with open('ARCHIV_0113.md', 'r', encoding='utf-8') as f:
    content_full = f.read()

# Extract summary and lessons learned (placeholder, can be improved)
summary = "Loop 113: Backend bug fixes, compliance automation, and finalization workflow validation."
lessons_learned = "1. Backend errors can break UI; always check API responses. 2. Compliance automation is essential for loop finalization. 3. Guardrail and lint checks must be satisfied before archiving."
tasks_completed = ["TASK_0207"]
tasks_completed_json = json.dumps(tasks_completed)
infrastructure_created = "quality_correlator.py fix, pattern_recognizer.py fix, compliance scripts, guardrail automation"
indexed_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# Connect to database and insert
conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

cursor.execute('''
INSERT INTO archives (id, loop_num, path, summary, lessons_learned, tasks_completed, infrastructure_created, content_full, indexed_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    'ARCHIV_0113',
    113,
    'ARCHIV_0113.md',
    summary,
    lessons_learned,
    tasks_completed_json,
    infrastructure_created,
    content_full,
    indexed_at
))

conn.commit()
conn.close()

print('Successfully inserted ARCHIV_0113 into knowledge database')

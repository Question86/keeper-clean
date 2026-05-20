from knowledge_db import KnowledgeDB
from pathlib import Path
import sqlite3
import json
import os

# Connect to database
db = KnowledgeDB(Path('.'))
conn = db.conn

# Check version
try:
    version = conn.execute('SELECT value FROM db_meta WHERE key = "version"').fetchone()
    current_version = int(version[0]) if version else 0
    code_version = getattr(db.__class__, 'DB_VERSION', 7)
    print(f'Current DB version: {current_version}')
    print(f'Code DB_VERSION: {code_version}')
    
    if current_version < code_version:
        print(f'⚠️  Database needs rebuild (version {current_version} < {code_version})')
        print('Starting rebuild...')
        stats = db.rebuild()
        print('Rebuild completed!')
        print(json.dumps(stats, indent=2))
    else:
        print('✅ Database is up to date')
        
except Exception as e:
    print(f'Version check error: {e}')

# Get database schema info
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('\n=== DATABASE TABLES ===')
for table in tables:
    table_name = table[0]
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f'{table_name}: {count} rows')
    except:
        print(f'{table_name}: error counting')

print('\n=== SAMPLE DATA FROM KEY TABLES ===')

# Reports table
try:
    reports = conn.execute('SELECT id, path, task_id, loop_num FROM reports LIMIT 5').fetchall()
    print('\nREPORTS (first 5):')
    for r in reports:
        print(f'  {r[0]} -> {r[1]} (task: {r[2]}, loop: {r[3]})')
except Exception as e:
    print(f'REPORTS error: {e}')

# Tasks table
try:
    tasks = conn.execute('SELECT id, path FROM tasks LIMIT 5').fetchall()
    print('\nTASKS (first 5):')
    for t in tasks:
        print(f'  {t[0]} -> {t[1]}')
except Exception as e:
    print(f'TASKS error: {e}')

# Archives
try:
    archives = conn.execute('SELECT id, path FROM archives LIMIT 5').fetchall()
    print('\nARCHIVES (first 5):')
    for a in archives:
        print(f'  {a[0]} -> {a[1]}')
except Exception as e:
    print(f'ARCHIVES error: {e}')

# Check for new tables
new_tables = ['reference_relationships', 'milestone_index', 'semantic_embeddings', 'quality_scores']
print('\n=== NEW TABLES (TASK_0142) ===')
for table in new_tables:
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f'{table}: {count} rows')
        
        # Show sample data
        if count > 0:
            sample = conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
            print(f'  Sample: {sample[:1]}')
    except Exception as e:
        print(f'{table}: not found or error - {e}')

db.close()
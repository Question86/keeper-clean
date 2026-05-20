import sqlite3
import csv

# Query database for task and report files
conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

cursor.execute("SELECT path FROM docs WHERE path LIKE 'task_%' OR path LIKE 'report_%'")
files = cursor.fetchall()
conn.close()

print(f'Found {len(files)} task/report files in database')
for path, in files[:10]:  # Show first 10
    print(f'{path}')
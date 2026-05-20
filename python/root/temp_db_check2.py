import sqlite3

conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM tasks')
print('Tasks table records:', cursor.fetchone()[0])

cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name LIKE "%_fts"')
fts_tables = cursor.fetchall()
print('FTS tables:')
for table in fts_tables:
    print(f'  {table[0]}')

conn.close()
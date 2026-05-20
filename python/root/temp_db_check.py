import sqlite3

conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

# Get all tables
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables in database:')
for table in tables:
    print(f'  {table[0]}')

# Check FTS tables specifically
fts_tables = ['reports_fts', 'archives_fts', 'docs_fts']
for table in fts_tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'{table}: {count} records')
    except Exception as e:
        print(f'{table}: error - {e}')

conn.close()
import sqlite3

conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

# Get table schemas
cursor.execute('SELECT sql FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
for table in tables:
    print('Table SQL:', table[0])

# Check sections_fts content
cursor.execute('SELECT * FROM sections_fts LIMIT 5')
rows = cursor.fetchall()
print('Sample FTS data:', rows)

conn.close()
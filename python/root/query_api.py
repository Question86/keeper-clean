import sqlite3

conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

cursor.execute("SELECT path FROM docs WHERE content_full LIKE '%/api/status%'")
results = cursor.fetchall()
conn.close()

print(f'Found {len(results)} files')
for path, in results[:50]:
    print(path)
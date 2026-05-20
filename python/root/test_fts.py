import sqlite3
conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

# Test FTS
try:
    cursor.execute('SELECT id FROM reports_fts WHERE content_full MATCH "task" LIMIT 5')
    fts_rows = cursor.fetchall()
    print(f'FTS matches for "task": {len(fts_rows)} results')
    if fts_rows:
        print('Sample FTS IDs:', fts_rows[:3])
except Exception as e:
    print(f'FTS error: {e}')

# Test LIKE
try:
    cursor.execute('SELECT id, substr(content_full, 1, 100) FROM reports WHERE content_full LIKE "%task%" LIMIT 3')
    like_rows = cursor.fetchall()
    print(f'LIKE matches for "%task%": {len(like_rows)} results')
    if like_rows:
        print('Sample LIKE content:', like_rows[0][1][:50])
except Exception as e:
    print(f'LIKE error: {e}')

conn.close()
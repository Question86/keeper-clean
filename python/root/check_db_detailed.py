import sqlite3

conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM archives WHERE id="ARCHIV_0110"')
result = cursor.fetchone()
print('ARCHIV_0110 entry:', result)

cursor.execute('SELECT COUNT(*) FROM archives')
count = cursor.fetchone()[0]
print(f'Total archives: {count}')

# Check if there are any NULL values in the ARCHIV_0110 entry
if result:
    columns = [desc[0] for desc in cursor.description]
    data = dict(zip(columns, result))
    print('ARCHIV_0110 data:')
    for k, v in data.items():
        print(f'  {k}: {repr(v)}')

conn.close()
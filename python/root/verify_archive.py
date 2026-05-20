import sqlite3

conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

cursor.execute('SELECT id, loop_num, path FROM archives WHERE id="ARCHIV_0110"')
result = cursor.fetchone()
print('ARCHIV_0110 entry:', result)

conn.close()
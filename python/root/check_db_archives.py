import sqlite3

conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

# Check archives table structure
cursor.execute('PRAGMA table_info(archives)')
columns_info = cursor.fetchall()
print('Archives table columns:', [col[1] for col in columns_info])

# Check for archive entries
cursor.execute('SELECT COUNT(*) FROM archives')
count = cursor.fetchone()[0]
print(f'Archive entries: {count}')

if count > 0:
    # Get column names
    cursor.execute('SELECT * FROM archives LIMIT 1')
    columns = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    print('Columns:', columns)
    print('Sample archive data:', dict(zip(columns, row)))

    # Check for ARCHIV_0110
    cursor.execute('SELECT * FROM archives WHERE id LIKE "%0110%"')
    arch110 = cursor.fetchall()
    if arch110:
        print('ARCHIV_0110 found:', dict(zip(columns, arch110[0])))
    else:
        print('ARCHIV_0110 NOT found in database')

conn.close()
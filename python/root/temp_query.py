import sqlite3

conn = sqlite3.connect('keeper_knowledge.db')
cursor = conn.cursor()

# Get tables
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables:', tables)

for table in tables:
    table_name = table[0]
    print(f'\nTable: {table_name}')
    
    # Get columns
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    print('Columns:', columns)
    
    # Get sample data
    try:
        cursor.execute(f'SELECT * FROM {table_name} LIMIT 5')
        rows = cursor.fetchall()
        print('Sample data:', rows)
    except:
        print('No data or error')

conn.close()
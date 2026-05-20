import sqlite3
from pprint import pprint

db='keeper_knowledge.db'
conn=sqlite3.connect(db)
c=conn.cursor()

print('PRAGMA table_info(archives)')
for row in c.execute("PRAGMA table_info(archives)"):
    pprint(row)

print('\nSample row for ARCHIV_0111')
for row in c.execute("SELECT * FROM archives WHERE id='ARCHIV_0111'"):
    pprint(row)

# Show column names
cols=[r[1] for r in c.execute("PRAGMA table_info(archives)")]
print('\nColumns:', cols)

# Check for NULLs
row=c.execute("SELECT * FROM archives WHERE id='ARCHIV_0111'").fetchone()
if row is None:
    print('No row found for ARCHIV_0111')
else:
    null_cols=[cols[i] for i,v in enumerate(row) if v is None]
    if null_cols:
        print('NULL columns in ARCHIV_0111:', null_cols)
    else:
        print('No NULL columns')

conn.close()
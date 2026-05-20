import sqlite3, json, sys

db = 'keeper_knowledge.db'
try:
    c = sqlite3.connect(db)
    ic = c.execute('PRAGMA integrity_check').fetchone()
    rows = c.execute('SELECT key,value FROM db_meta').fetchall()
    tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print('integrity_check:', ic)
    print('db_meta:', dict(rows))
    print('tables_count:', len(tables))
    c.close()
except Exception as e:
    print('ERROR:', e)
    sys.exit(2)

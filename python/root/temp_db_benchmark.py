import time
import sqlite3
from pathlib import Path
import json

def benchmark_db():
    db_path = Path("keeper_knowledge.db")
    if not db_path.exists():
        return {"error": "Database not found"}

    results = {}
    try:
        # Direct SQLite connection without importing knowledge_db
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Simple performance tests
        start = time.time()
        cursor.execute("SELECT COUNT(*) FROM knowledge")
        count = cursor.fetchone()[0]
        query_time = time.time() - start

        start = time.time()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        schema_time = time.time() - start

        conn.close()

        results = {
            "total_records": count,
            "query_time_ms": query_time * 1000,
            "schema_time_ms": schema_time * 1000,
            "tables_count": len(tables),
            "success": True
        }
    except Exception as e:
        results = {"error": str(e), "success": False}

    print(json.dumps(results))

if __name__ == "__main__":
    benchmark_db()</content>
<parameter name="filePath">d:\Keeper-Clean-Loop1\temp_db_benchmark.py
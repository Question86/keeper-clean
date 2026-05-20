# MODE: SCRIPT

from pathlib import Path
import sqlite3

from knowledge_db import KnowledgeDB


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return bool(row)


def main() -> int:
    db = KnowledgeDB(Path("."))
    try:
        conn = db.conn
        if not table_exists(conn, "test_knowledge"):
            print("Table test_knowledge not found; nothing to analyze.")
            return 0

        entities = conn.execute(
            """
            SELECT knowledge_type, category, COUNT(*) as count
            FROM test_knowledge
            WHERE id LIKE 'external_%'
            GROUP BY knowledge_type, category
            """
        ).fetchall()

        total = sum(row["count"] for row in entities)
        print("EXTERNAL KNOWLEDGE EXTRACTION SUMMARY")
        print("=" * 50)
        print(f"Total external entities: {total}")
        print()

        if not entities:
            print("No external_* entities found.")
            return 0

        print("By knowledge type:")
        for row in sorted(entities, key=lambda x: x["count"], reverse=True)[:10]:
            print(f'  {row["knowledge_type"]}: {row["count"]}')

        print()
        print("By category:")
        category_counts = {}
        for row in entities:
            category_counts[row["category"]] = category_counts.get(row["category"], 0) + row["count"]
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count}")

        print()
        print("SAMPLE EXTERNAL ENTITIES:")
        sample_entities = conn.execute(
            """
            SELECT id, knowledge_type, description
            FROM test_knowledge
            WHERE id LIKE 'external_%'
            LIMIT 5
            """
        ).fetchall()
        for entity in sample_entities:
            desc = entity["description"] or ""
            if len(desc) > 100:
                desc = desc[:100] + "..."
            print(f'  {entity["id"]}')
            print(f'    Type: {entity["knowledge_type"]}')
            print(f"    Description: {desc}")
            print()

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

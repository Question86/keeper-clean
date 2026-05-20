#!/usr/bin/env python3
"""
Incremental Knowledge Database Update Script

This script updates the existing keeper_knowledge.db with new reports and archives
that haven't been indexed yet, without rebuilding the entire database.

Usage: python update_knowledge_db.py
"""

import sys
from pathlib import Path
from knowledge_db import KnowledgeDB

def main():
    workspace_root = Path(".")
    db_path = workspace_root / "keeper_knowledge.db"

    if not db_path.exists():
        print(f"Error: {db_path} does not exist. Please run --generate-knowledge-db first.")
        sys.exit(1)

    print("Updating existing knowledge database with new content...")

    db = KnowledgeDB(workspace_root)

    # Get existing report IDs from database
    existing_reports = set()
    try:
        cursor = db.conn.execute("SELECT id FROM reports")
        existing_reports = {row[0] for row in cursor.fetchall()}
    except Exception as e:
        print(f"Warning: Could not query existing reports: {e}")

    # Get existing archive IDs
    existing_archives = set()
    try:
        cursor = db.conn.execute("SELECT id FROM archives")
        existing_archives = {row[0] for row in cursor.fetchall()}
    except Exception as e:
        print(f"Warning: Could not query existing archives: {e}")

    # Find new reports
    new_reports = []
    reports_dir = workspace_root / "reports"
    if reports_dir.exists():
        for report_file in sorted(reports_dir.glob("report_*.md")):
            report_id = report_file.stem
            if report_id not in existing_reports:
                new_reports.append(report_file)

    # Find new archives
    new_archives = []
    archive_dir = workspace_root / "archive"
    if archive_dir.exists():
        for archive_file in sorted(archive_dir.glob("ARCHIV_*.md")):
            archive_id = archive_file.stem
            if archive_id not in existing_archives:
                new_archives.append(archive_file)

    print(f"Found {len(new_reports)} new reports and {len(new_archives)} new archives to index")

    # Index new reports
    reports_indexed = 0
    for report_path in new_reports:
        try:
            db._index_report(report_path)
            reports_indexed += 1
            print(f"✓ Indexed report: {report_path.name}")
        except Exception as e:
            print(f"✗ Failed to index report {report_path.name}: {e}")

    # Index new archives
    archives_indexed = 0
    lessons_from_archives = 0
    for archive_path in new_archives:
        try:
            lessons = db._index_archive(archive_path)
            archives_indexed += 1
            lessons_from_archives += lessons
            print(f"✓ Indexed archive: {archive_path.name} ({lessons} lessons)")
        except Exception as e:
            print(f"✗ Failed to index archive {archive_path.name}: {e}")

    # Update semantic data if new content was added
    if new_reports or new_archives:
        try:
            print("Updating semantic relationships...")
            db._mine_relationships()
            db._mine_patterns()
            print("✓ Semantic data updated")
        except Exception as e:
            print(f"Warning: Failed to update semantic data: {e}")

    db.close()

    print("\nKnowledge database update complete!")
    print(f"  New reports indexed: {reports_indexed}")
    print(f"  New archives indexed: {archives_indexed}")
    print(f"  Lessons extracted from archives: {lessons_from_archives}")

    if reports_indexed > 0 or archives_indexed > 0:
        print("\n✓ Database successfully updated with new knowledge")
        print("  You can now search for recent task information using semantic/contextual queries")
    else:
        print("\n✓ No new content found - database is up to date")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Autostart-safe archive indexing wrapper.

Indexes the latest archive in `archive/ARCHIV_*.md`. Exits 0 when nothing to index.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    archive_dir = root / "archive"
    if not archive_dir.exists():
        print("autostart_index_archive: skipping (archive directory missing)")
        return 0

    archive_files = sorted(archive_dir.glob("ARCHIV_*.md"))
    if not archive_files:
        print("autostart_index_archive: skipping (no archive files found)")
        return 0

    latest = archive_files[-1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from knowledge_db import KnowledgeDB  # type: ignore

    db = KnowledgeDB(root)
    try:
        lessons = db._index_archive(latest)
        db.conn.commit()
        print(f"autostart_index_archive: indexed {latest.name} (lessons={lessons})")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

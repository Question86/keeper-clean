import argparse
import os
import sys
from pathlib import Path

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge_db import KnowledgeDB


def resolve_archive(path_arg: str | None) -> Path | None:
    if path_arg:
        candidate = Path(path_arg)
        if not candidate.is_absolute():
            candidate = (ROOT / candidate).resolve()
        return candidate if candidate.exists() else None

    archive_dir = ROOT / "archive"
    archives = sorted(archive_dir.glob("ARCHIV_*.md")) if archive_dir.exists() else []
    return archives[-1] if archives else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Index a single archive file into keeper_knowledge.db")
    parser.add_argument("--archive", help="Archive path (defaults to latest archive/ARCHIV_*.md)")
    args = parser.parse_args()

    archive = resolve_archive(args.archive)
    if not archive:
        print("Archive file not found. Provide --archive <path> or ensure archive/ARCHIV_*.md exists.")
        return 0

    db = KnowledgeDB(ROOT)
    try:
        print("Indexing archive:", archive)
        num_lessons = db._index_archive(archive)
        db.conn.commit()
        print("Indexed lessons:", num_lessons)
        return 0
    except Exception as e:
        print("Indexing failed:", e)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

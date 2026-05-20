"""Repair common knowledge DB integrity issues.

Focus:
- reports.loop_num drift to 0
- reports.version missing/0
- reports.task_id empty when recoverable from id/path
- lessons.source_id empty strings
- archive path normalization and previous-loop archive bootstrap readiness
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path


DB_PATH = Path("keeper_knowledge.db")
CURRENT_JSON_PATH = Path("current.json")
ARCHIVE_DIR = Path("archive")


def _infer_report_fields(report_id: str, report_path: str) -> tuple[str, int, int]:
    text = f"{report_id} {report_path or ''}"

    task_match = re.search(r"(TASK_\d{4})", text)
    loop_match = re.search(r"_L(\d+)(?:_|$)", text)
    if not loop_match:
        loop_match = re.search(r"(?:^|_)LOOP_(\d+)(?:_|$)", text, re.IGNORECASE)
    version_match = re.search(r"_v(\d+)(?:_|$)", text, re.IGNORECASE)

    task_id = task_match.group(1) if task_match else ""
    loop_num = int(loop_match.group(1)) if loop_match else 0
    version = int(version_match.group(1)) if version_match else 1
    return task_id, loop_num, version


def _extract_archive_summary(content: str) -> str:
    summary_match = re.search(
        r"^## (?:SUMMARY|LOOP SUMMARY)\s*$\s*(.*?)(?=^##|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    return (summary_match.group(1).strip()[:1000] if summary_match else "")


def _extract_archive_lessons(content: str) -> str:
    lessons_match = re.search(
        r"^## (?:LESSONS LEARNED|OBSERVATIONS|KEY LEARNINGS)\s*$\s*(.*?)(?=^##|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    return (lessons_match.group(1).strip() if lessons_match else "")


def _extract_archive_tasks(content: str) -> list[str]:
    tasks_match = re.search(
        r"^## (?:TASKS COMPLETED|COMPLETED TASKS|WORK DONE)\s*$\s*(.*?)(?=^##|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not tasks_match:
        return []
    task_ids = re.findall(r"TASK_\d{4}", tasks_match.group(1))
    return sorted(set(task_ids))


def _extract_archive_infra(content: str) -> list[str]:
    infra_match = re.search(
        r"^## (?:INFRASTRUCTURE|FILES CREATED|NEW FILES)\s*$\s*(.*?)(?=^##|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not infra_match:
        return []
    files = re.findall(
        r"[`\[]?([a-zA-Z0-9_/\\]+\.(?:py|md|json|html|sh|bat))[`\]]?",
        infra_match.group(1),
    )
    return sorted(set(files))


def _load_current_loop() -> int:
    if not CURRENT_JSON_PATH.exists():
        return 0
    try:
        payload = json.loads(CURRENT_JSON_PATH.read_text(encoding="utf-8"))
        return int(payload.get("STATE", {}).get("loop", 0) or 0)
    except Exception:
        return 0


def _repair_archives(cur: sqlite3.Cursor) -> dict[str, int]:
    archive_path_updates = 0
    prev_archive_inserted = 0
    prev_archive_path_fixed = 0
    fts_rebuilt = 0

    rows = cur.execute("SELECT id, path FROM archives WHERE id LIKE 'ARCHIV_%'").fetchall()
    for row in rows:
        archive_id = row["id"]
        current_path = row["path"] or ""
        canonical_path = f"archive/{archive_id}.md"
        if current_path == f"{archive_id}.md" or (
            current_path and "/" not in current_path and "\\" not in current_path
        ):
            cur.execute("UPDATE archives SET path = ? WHERE id = ?", (canonical_path, archive_id))
            archive_path_updates += 1

    current_loop = _load_current_loop()
    if current_loop > 1:
        prev_archive_id = f"ARCHIV_{current_loop - 1:04d}"
        prev_archive_rel = f"archive/{prev_archive_id}.md"
        prev_archive_file = ARCHIVE_DIR / f"{prev_archive_id}.md"
        prev_row = cur.execute(
            "SELECT id, path FROM archives WHERE id = ?",
            (prev_archive_id,),
        ).fetchone()

        if prev_row is None and prev_archive_file.exists():
            content = prev_archive_file.read_text(encoding="utf-8", errors="replace")
            now = cur.execute("SELECT datetime('now')").fetchone()[0]
            cur.execute(
                """
                INSERT OR REPLACE INTO archives
                (id, loop_num, path, summary, lessons_learned, tasks_completed,
                 infrastructure_created, content_full, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prev_archive_id,
                    current_loop - 1,
                    prev_archive_rel,
                    _extract_archive_summary(content),
                    _extract_archive_lessons(content),
                    json.dumps(_extract_archive_tasks(content)),
                    json.dumps(_extract_archive_infra(content)),
                    content,
                    now,
                ),
            )
            prev_archive_inserted += 1
        elif prev_row is not None and prev_row["path"] != prev_archive_rel:
            cur.execute("UPDATE archives SET path = ? WHERE id = ?", (prev_archive_rel, prev_archive_id))
            prev_archive_path_fixed += 1

    if archive_path_updates or prev_archive_inserted or prev_archive_path_fixed:
        cur.execute("INSERT INTO archives_fts(archives_fts) VALUES ('rebuild')")
        fts_rebuilt = 1

    return {
        "archive_path_updates": archive_path_updates,
        "prev_archive_inserted": prev_archive_inserted,
        "prev_archive_path_fixed": prev_archive_path_fixed,
        "archives_fts_rebuilt": fts_rebuilt,
    }


def main() -> int:
    if not DB_PATH.exists():
        print(json.dumps({"ok": False, "error": f"DB not found: {DB_PATH}"}))
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    updated_reports = 0
    updated_lessons = 0

    rows = cur.execute(
        "SELECT id, path, task_id, loop_num, version FROM reports"
    ).fetchall()
    for row in rows:
        inferred_task, inferred_loop, inferred_version = _infer_report_fields(
            row["id"], row["path"] or ""
        )

        new_task = row["task_id"] or inferred_task or ""
        new_loop = row["loop_num"] if row["loop_num"] not in (None, 0) else inferred_loop
        new_version = row["version"] if row["version"] not in (None, 0) else inferred_version

        if (
            new_task != row["task_id"]
            or new_loop != row["loop_num"]
            or new_version != row["version"]
        ):
            cur.execute(
                """
                UPDATE reports
                SET task_id = ?, loop_num = ?, version = ?
                WHERE id = ?
                """,
                (new_task, int(new_loop or 0), int(new_version or 1), row["id"]),
            )
            updated_reports += 1

    lesson_rows = cur.execute(
        "SELECT id, source_type, source_id FROM lessons WHERE source_id = ''"
    ).fetchall()
    for row in lesson_rows:
        replacement = f"{row['source_type']}_unknown_{row['id']}"
        cur.execute("UPDATE lessons SET source_id = ? WHERE id = ?", (replacement, row["id"]))
        updated_lessons += 1

    archive_repair_stats = _repair_archives(cur)

    conn.commit()

    summary = {
        "ok": True,
        "db": str(DB_PATH),
        "reports_scanned": len(rows),
        "reports_updated": updated_reports,
        "empty_lesson_source_ids_fixed": updated_lessons,
        **archive_repair_stats,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

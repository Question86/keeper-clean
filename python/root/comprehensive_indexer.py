#!/usr/bin/env python3
"""
Comprehensive Knowledge Database Indexer

This script adds missing FTS tables and indexes all content types that aren't currently
searchable in the knowledge database, including:

- Tasks (add FTS table and indexing)
- Bugs (new table and FTS)
- Code files (new table and FTS)
- JSON files and other content
- Missing documentation files

Usage: python comprehensive_indexer.py
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any

# Import existing utilities
sys.path.append('.')
from knowledge_db import KnowledgeDB

def utc_now_iso() -> str:
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def read_text(path: Path) -> str:
    """Read text file with error handling."""
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        return ""

class ComprehensiveIndexer:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.db_path = workspace_root / "keeper_knowledge.db"
        self.conn = None

    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def add_missing_tables(self):
        """Add FTS tables for tasks, bugs, and code."""
        print("Adding missing FTS tables...")

        # Tasks FTS table
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
                id,
                objective,
                seed_idea,
                content_full,
                content='tasks',
                content_rowid='rowid'
            )
        """)

        # Bugs table and FTS
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bugs (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                title TEXT,
                description TEXT,
                status TEXT,
                severity TEXT,
                loop_num INTEGER,
                task_id TEXT,
                content_full TEXT,
                indexed_at TEXT NOT NULL
            )
        """)

        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS bugs_fts USING fts5(
                id,
                title,
                description,
                content_full,
                content='bugs',
                content_rowid='rowid'
            )
        """)

        # Code table and FTS
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS code (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                title TEXT,
                description TEXT,
                type TEXT,  -- 'implementation', 'fix', 'feature', 'refactor', etc.
                loop_num INTEGER,
                task_id TEXT,
                content_full TEXT,
                indexed_at TEXT NOT NULL
            )
        """)

        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS code_fts USING fts5(
                id,
                title,
                description,
                content_full,
                content='code',
                content_rowid='rowid'
            )
        """)

        # JSON content table and FTS
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS json_content (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                title TEXT,
                content_type TEXT,  -- 'index', 'config', 'data', 'results', etc.
                content_full TEXT,
                indexed_at TEXT NOT NULL
            )
        """)

        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS json_content_fts USING fts5(
                id,
                title,
                content_full,
                content='json_content',
                content_rowid='rowid'
            )
        """)

        # Triggers to keep FTS in sync
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS tasks_ai AFTER INSERT ON tasks BEGIN
                INSERT INTO tasks_fts(rowid, id, objective, seed_idea, content_full)
                VALUES (NEW.rowid, NEW.id, NEW.objective, NEW.seed_idea, NEW.objective || ' ' || COALESCE(NEW.seed_idea, ''));
            END
        """)

        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS bugs_ai AFTER INSERT ON bugs BEGIN
                INSERT INTO bugs_fts(rowid, id, title, description, content_full)
                VALUES (NEW.rowid, NEW.id, NEW.title, NEW.description, NEW.content_full);
            END
        """)

        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS code_ai AFTER INSERT ON code BEGIN
                INSERT INTO code_fts(rowid, id, title, description, content_full)
                VALUES (NEW.rowid, NEW.id, NEW.title, NEW.description, NEW.content_full);
            END
        """)

        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS json_content_ai AFTER INSERT ON json_content BEGIN
                INSERT INTO json_content_fts(rowid, id, title, content_full)
                VALUES (NEW.rowid, NEW.id, NEW.title, NEW.content_full);
            END
        """)

        self.conn.commit()
        print("✓ Missing FTS tables added")

    def index_tasks_fts(self):
        """Add existing tasks to FTS table."""
        print("Indexing existing tasks for FTS...")

        cursor = self.conn.execute("SELECT rowid, id, objective, seed_idea FROM tasks")
        tasks = cursor.fetchall()

        for task in tasks:
            self.conn.execute("""
                INSERT OR IGNORE INTO tasks_fts(rowid, id, objective, seed_idea, content_full)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task['rowid'],
                task['id'],
                task['objective'] or '',
                task['seed_idea'] or '',
                (task['objective'] or '') + ' ' + (task['seed_idea'] or '')
            ))

        self.conn.commit()
        print(f"✓ Indexed {len(tasks)} tasks for FTS")

    def index_bugs(self):
        """Index bug report files."""
        print("Indexing bug reports...")

        bugs_dir = self.workspace_root / "bugs"
        if not bugs_dir.exists():
            print("  Bugs directory not found, skipping")
            return

        indexed = 0
        for bug_file in sorted(bugs_dir.glob("*.md")):
            try:
                content = read_text(bug_file)
                if not content:
                    continue

                # Extract metadata from filename and content
                bug_id = bug_file.stem
                title = self.extract_title(content)
                description = self.extract_description(content)

                # Extract loop number and task ID from filename if present
                loop_num = None
                task_id = None
                if '_L' in bug_id:
                    parts = bug_id.split('_L')
                    if len(parts) > 1:
                        loop_part = parts[1].split('_')[0]
                        try:
                            loop_num = int(loop_part)
                        except ValueError:
                            pass

                if 'TASK_' in bug_id:
                    task_id = bug_id.split('TASK_')[1].split('_')[0]
                    task_id = f"TASK_{task_id}"

                now = utc_now_iso()
                self.conn.execute("""
                    INSERT OR REPLACE INTO bugs
                    (id, path, title, description, status, severity, loop_num, task_id, content_full, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bug_id,
                    str(bug_file.relative_to(self.workspace_root)),
                    title,
                    description,
                    'unknown',  # Could be extracted from content
                    'unknown',  # Could be extracted from content
                    loop_num,
                    task_id,
                    content,
                    now
                ))

                indexed += 1

            except Exception as e:
                print(f"  Error indexing bug {bug_file.name}: {e}")

        self.conn.commit()
        print(f"✓ Indexed {indexed} bug reports")

    def index_code(self):
        """Index code files."""
        print("Indexing code files...")

        code_dir = self.workspace_root / "code"
        if not code_dir.exists():
            print("  Code directory not found, skipping")
            return

        indexed = 0
        for code_file in sorted(code_dir.glob("*.md")):
            try:
                content = read_text(code_file)
                if not content:
                    continue

                # Extract metadata from filename and content
                code_id = code_file.stem
                title = self.extract_title(content)
                description = self.extract_description(content)

                # Extract loop number and task ID from filename if present
                loop_num = None
                task_id = None
                if '_L' in code_id:
                    parts = code_id.split('_L')
                    if len(parts) > 1:
                        loop_part = parts[1].split('_')[0]
                        try:
                            loop_num = int(loop_part)
                        except ValueError:
                            pass

                if 'TASK_' in code_id:
                    task_id = code_id.split('TASK_')[1].split('_')[0]
                    task_id = f"TASK_{task_id}"

                # Determine type from content or filename
                code_type = 'unknown'
                if 'FIX' in code_id.upper() or 'fix' in content.lower():
                    code_type = 'fix'
                elif 'FEATURE' in code_id.upper() or 'feature' in content.lower():
                    code_type = 'feature'
                elif 'REFACTOR' in code_id.upper() or 'refactor' in content.lower():
                    code_type = 'refactor'
                else:
                    code_type = 'implementation'

                now = utc_now_iso()
                self.conn.execute("""
                    INSERT OR REPLACE INTO code
                    (id, path, title, description, type, loop_num, task_id, content_full, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    code_id,
                    str(code_file.relative_to(self.workspace_root)),
                    title,
                    description,
                    code_type,
                    loop_num,
                    task_id,
                    content,
                    now
                ))

                indexed += 1

            except Exception as e:
                print(f"  Error indexing code {code_file.name}: {e}")

        self.conn.commit()
        print(f"✓ Indexed {indexed} code files")

    def index_json_files(self):
        """Index important JSON files."""
        print("Indexing JSON files...")

        json_files = [
            "query.json",
            "query_test_results.json",
            "query_test_results_100.json",
            "docs/HISTORY_INDEX.json",
            "docs/QUERY_INDEX.json",
            "docs/CONTEXT_INDEX.json",
            "bootstrap_ab_test_20260209_035036.json",
            "bootstrap_ab_test_20260210_012254.json",
            "bootstrap_ab_test_20260210_012643_sweep20.json",
            "bootstrap_ab_test_20260210_013138_postpenalty.json",
            "bootstrap_parameter_sweep_results.json",
            "benchmark_results_20260127_172506.json",
            "benchmark_results_metadata.json",
            "benchmark_results_metadata_optimized.json",
            "pytorch_cpu_results.json",
            "pytorch_gpu_results.json",
            "pytorch_gpu_results_adversarial.json",
            "context_dream_20260127_155658.json",
            "parameter_discovery_20260127_185150.json",
            "parameter_discovery_20260127_185648.json",
            "parameter_discovery_20260127_185909.json",
            "parameter_discovery_20260127_190002.json",
            "parameter_discovery_20260127_192003.json",
            "parameter_discovery_20260127_192048.json",
            "parameter_discovery_20260127_192830.json",
            "validation_hashes.json",
            "validation_keys/validation_proofs.jsonl",
            "knownissues.json",
            "lint_output.json",
            "response.json",
            "skl_export_framework.json",
            "skl_export_task.json",
            "query_test_analysis_100.json",
            "finalization_assessment_L84.json",
            "finalization_assessment_L93.json",
            "connectivity_report.json",
            "quality_report.json",
            "assumption_validation_results.json",
            "audit_results.json",
            "bandwidth_settings.json",
            "bootstrap_dry_runs.jsonl",
            "breadcrumb_analysis.json",
            "transaction_log.jsonl",
            "bandwidth_guard_log.jsonl",
            "budget_guardrail_log.jsonl",
            "_transaction_log.jsonl",
            "validation_proofs.jsonl",
            "integrity_log.jsonl",
            "ai_reflective_log.jsonl",
            "bandwidth_usage.jsonl",
        ]

        indexed = 0
        for json_file in json_files:
            json_path = self.workspace_root / json_file
            if not json_path.exists():
                continue

            try:
                content = read_text(json_path)
                if not content:
                    continue

                # Determine content type
                content_type = 'data'
                if 'index' in json_file.lower():
                    content_type = 'index'
                elif 'query' in json_file.lower():
                    content_type = 'query_results'
                elif 'benchmark' in json_file.lower() or 'results' in json_file.lower():
                    content_type = 'benchmark_results'
                elif 'validation' in json_file.lower():
                    content_type = 'validation'
                elif 'config' in json_file.lower():
                    content_type = 'config'
                elif 'log' in json_file.lower():
                    content_type = 'log'

                # Create a title from filename
                title = json_file.replace('.json', '').replace('.jsonl', '').replace('_', ' ').title()

                json_id = json_file.replace('/', '_').replace('\\', '_')

                now = utc_now_iso()
                self.conn.execute("""
                    INSERT OR REPLACE INTO json_content
                    (id, path, title, content_type, content_full, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    json_id,
                    json_file,
                    title,
                    content_type,
                    content,
                    now
                ))

                indexed += 1

            except Exception as e:
                print(f"  Error indexing JSON {json_file}: {e}")

        self.conn.commit()
        print(f"✓ Indexed {indexed} JSON files")

    def index_missing_docs(self):
        """Index documentation files that might be missing."""
        print("Indexing additional documentation files...")

        # Look for docs in various locations
        doc_patterns = [
            "*.md",
            "docs/*.md",
            "docs/**/*.md",
            "*.txt",
            "docs/*.txt",
            "README.md",
            "WORKSPACE_README.md",
            "DOCKER_README.md",
        ]

        indexed = 0
        processed_files = set()

        # Get existing docs to avoid duplicates
        cursor = self.conn.execute("SELECT path FROM docs")
        existing_docs = {row['path'] for row in cursor.fetchall()}

        for pattern in doc_patterns:
            try:
                for doc_file in self.workspace_root.glob(pattern):
                    if doc_file.is_file():
                        rel_path = str(doc_file.relative_to(self.workspace_root))
                        if rel_path in existing_docs or rel_path in processed_files:
                            continue

                        processed_files.add(rel_path)

                        try:
                            content = read_text(doc_file)
                            if not content or len(content.strip()) < 100:  # Skip very small files
                                continue

                            # Extract title from first line or filename
                            title = self.extract_title(content) or doc_file.stem.replace('_', ' ').title()

                            # Determine category
                            category = 'documentation'
                            if 'README' in str(doc_file).upper():
                                category = 'readme'
                            elif 'ARCHITECTURE' in str(doc_file).upper():
                                category = 'architecture'
                            elif 'IMPLEMENTATION' in str(doc_file).upper():
                                category = 'implementation'
                            elif 'AUDIT' in str(doc_file).upper():
                                category = 'audit'
                            elif 'PLAN' in str(doc_file).upper():
                                category = 'planning'

                            doc_id = rel_path.replace('/', '_').replace('\\', '_').replace('.md', '').replace('.txt', '')

                            now = utc_now_iso()
                            self.conn.execute("""
                                INSERT OR REPLACE INTO docs
                                (id, path, title, category, content_full, indexed_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                doc_id,
                                rel_path,
                                title,
                                category,
                                content,
                                now
                            ))

                            indexed += 1

                        except Exception as e:
                            print(f"  Error indexing doc {rel_path}: {e}")

            except Exception as e:
                print(f"  Error processing pattern {pattern}: {e}")

        self.conn.commit()
        print(f"✓ Indexed {indexed} additional documentation files")

    def extract_title(self, content: str) -> str:
        """Extract title from markdown content."""
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return ""

    def extract_description(self, content: str) -> str:
        """Extract description from content."""
        lines = content.split('\n')
        description_lines = []

        for line in lines[1:20]:  # Check next 20 lines after title
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('```') and len(line) > 20:
                description_lines.append(line)
                if len(description_lines) >= 3:  # Get first few substantial lines
                    break

        return ' '.join(description_lines)

    def run_comprehensive_indexing(self):
        """Run all indexing operations."""
        print("Starting comprehensive knowledge database indexing...")
        print("=" * 60)

        try:
            self.connect()
            self.add_missing_tables()
            self.index_tasks_fts()
            self.index_bugs()
            self.index_code()
            self.index_json_files()
            self.index_missing_docs()

            print("=" * 60)
            print("✓ Comprehensive indexing completed successfully!")
            print("\nNew searchable content types added:")
            print("  - Tasks (full-text searchable)")
            print("  - Bug reports")
            print("  - Code files")
            print("  - JSON content files")
            print("  - Additional documentation")
            print("\nYou can now search for content across all these types using:")
            print("  python query_db.py \"your search query\"")

        except Exception as e:
            print(f"✗ Error during indexing: {e}")
            return False
        finally:
            self.close()

        return True

def main():
    workspace_root = Path(".")
    indexer = ComprehensiveIndexer(workspace_root)
    success = indexer.run_comprehensive_indexing()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
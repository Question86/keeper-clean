#!/usr/bin/env python3
"""
Index Extracted Code Sections into Knowledge Database

This script adds all the extracted code section text files from all_snippets_collected/
into the keeper_knowledge.db FTS tables for searchable code content.
"""

import os
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

class SectionIndexer:
    def __init__(self, db_path: str = "keeper_knowledge.db", sections_dir: str = "all_snippets_collected"):
        self.db_path = db_path
        self.sections_dir = Path(sections_dir)
        self.db = None

    def connect_db(self):
        """Connect to the knowledge database"""
        self.db = sqlite3.connect(self.db_path)
        return self.db

    def close_db(self):
        """Close database connection"""
        if self.db:
            self.db.close()

    def ensure_fts_tables(self):
        """Ensure all FTS tables exist"""
        cursor = self.db.cursor()

        # Check if tables exist, create if missing
        tables_to_check = [
            'reports_fts', 'archives_fts', 'docs_fts', 'tasks_fts',
            'bugs_fts', 'code_fts', 'json_content_fts', 'sections_fts'
        ]

        for table in tables_to_check:
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {table} USING fts5(
                    file_path, title, content, metadata,
                    tokenize = 'porter unicode61'
                )
            """)

        self.db.commit()
        print("✓ Ensured FTS tables exist")

    def get_file_hash(self, file_path: Path) -> str:
        """Get SHA256 hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except:
            return "unknown"

    def extract_section_info(self, filename: str) -> Tuple[str, str]:
        """
        Extract section name and source file hash from filename
        Format: Section_Name_Hash.txt
        """
        if not filename.endswith('.txt'):
            return filename, ""

        # Remove .txt extension
        name_without_ext = filename[:-4]

        # Find the last underscore to separate section name from hash
        last_underscore = name_without_ext.rfind('_')
        if last_underscore == -1:
            return name_without_ext.replace('_', ' '), ""

        section_name = name_without_ext[:last_underscore].replace('_', ' ')
        source_hash = name_without_ext[last_underscore + 1:]

        # Validate hash (should be hex)
        try:
            int(source_hash, 16)
            return section_name, source_hash
        except ValueError:
            # Not a valid hash, treat whole thing as section name
            return name_without_ext.replace('_', ' '), ""

    def is_valid_text_file(self, file_path: Path) -> bool:
        """Check if file contains valid text content"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='strict') as f:
                content = f.read(1024)  # Read first 1KB
                # Check for null bytes or very high ratio of non-printable chars
                if '\x00' in content:
                    return False
                printable_ratio = sum(1 for c in content if c.isprintable() or c in '\n\r\t') / len(content)
                return printable_ratio > 0.8
        except (UnicodeDecodeError, IOError):
            return False

    def index_section_file(self, file_path: Path):
        """Index a single section file into the database"""
        try:
            # Skip if not a valid text file
            if not self.is_valid_text_file(file_path):
                print(f"⚠ Skipping binary/non-text file: {file_path.name}")
                return

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()

            if not content or len(content) < 10:
                print(f"⚠ Skipping empty/short file: {file_path.name}")
                return

            # Extract section info from filename
            section_name, source_hash = self.extract_section_info(file_path.name)

            # Create metadata with additional info
            file_hash = self.get_file_hash(file_path)
            metadata = f"section:{section_name}|source_hash:{source_hash}|file_hash:{file_hash}|indexed:code_sections"

            # Insert into sections_fts table (matching existing schema)
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sections_fts (file_path, title, content, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                str(file_path),
                section_name,
                content,
                metadata
            ))

            print(f"✓ Indexed section: {section_name[:50]}... ({len(content)} chars)")

        except Exception as e:
            print(f"✗ Error indexing {file_path.name}: {e}")

    def index_all_sections(self):
        """Index all section files in the directory"""
        if not self.sections_dir.exists():
            print(f"✗ Sections directory not found: {self.sections_dir}")
            return

        section_files = list(self.sections_dir.glob("*.txt"))
        print(f"Found {len(section_files)} section files to index")

        indexed_count = 0
        skipped_count = 0

        for file_path in section_files:
            try:
                self.index_section_file(file_path)
                indexed_count += 1
            except Exception as e:
                print(f"✗ Failed to index {file_path.name}: {e}")
                skipped_count += 1

            # Commit every 50 files to avoid memory issues
            if (indexed_count + skipped_count) % 50 == 0:
                self.db.commit()
                print(f"Committed {indexed_count} sections, skipped {skipped_count}...")

        # Final commit
        self.db.commit()
        print(f"✓ Successfully indexed {indexed_count} code sections into database")
        if skipped_count > 0:
            print(f"⚠ Skipped {skipped_count} problematic files")

    def create_section_search_view(self):
        """Create a view for easy section searching"""
        try:
            cursor = self.db.cursor()

            # Create a view that combines sections with other content
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS searchable_sections AS
                SELECT
                    'section' as content_type,
                    file_path,
                    title as section_name,
                    content,
                    metadata,
                    title || ' ' || content as full_text
                FROM sections_fts
                WHERE metadata LIKE '%indexed:code_sections%'
            """)

            self.db.commit()
            print("✓ Created searchable_sections view")
        except Exception as e:
            print(f"⚠ Failed to create search view: {e}")

    def run_indexing(self):
        """Main indexing process"""
        try:
            self.connect_db()
            self.ensure_fts_tables()
            self.index_all_sections()
            self.create_section_search_view()
            print("✓ Code sections indexing complete!")

        except Exception as e:
            print(f"✗ Indexing failed: {e}")
            raise
        finally:
            self.close_db()

def main():
    indexer = SectionIndexer()
    indexer.run_indexing()

if __name__ == "__main__":
    main()
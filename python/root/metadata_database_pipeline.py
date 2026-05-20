#!/usr/bin/env python3
"""
Database-Metadata Connection Pipeline (ETL Engine)

TASK_0180: Automated pipeline connecting metadata extraction to database ingestion.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone
from dataclasses import dataclass
import sqlite3
import hashlib

from knowledge_db import KnowledgeDB
from tools.metadata.metadata_processor import UnifiedMetadataProcessor

@dataclass
class ETLResult:
    files_processed: int
    metadata_extracted: int
    database_updates: int
    errors: List[str]
    duration_seconds: float

class MetadataDatabasePipeline:
    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.knowledge_db = KnowledgeDB(workspace_root)
        self.metadata_processor = UnifiedMetadataProcessor(workspace_root)
        self.checksum_cache = self._load_checksum_cache()

    def _load_checksum_cache(self) -> Dict[str, str]:
        cache_file = self.workspace_root / ".metadata_etl_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_checksum_cache(self):
        cache_file = self.workspace_root / ".metadata_etl_cache.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(self.checksum_cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save checksum cache: {e}")

    def _get_file_checksum(self, file_path: Path) -> str:
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def _get_files_to_process(self) -> List[Path]:
        files_to_process = []
        patterns = [
            "reports/report_*.md",
            "tasks/task_*.md",
            "archive/ARCHIV_*.md",
            "docs/*.md",
            "*.md"
        ]
        
        for pattern in patterns:
            for file_path in self.workspace_root.glob(pattern):
                if file_path.is_file():
                    current_checksum = self._get_file_checksum(file_path)
                    cached_checksum = self.checksum_cache.get(str(file_path))
                    
                    if current_checksum != cached_checksum:
                        files_to_process.append(file_path)
                        self.checksum_cache[str(file_path)] = current_checksum
                        
        return files_to_process

    def process_file_incremental(self, file_path: Path) -> bool:
        try:
            metadata = self.metadata_processor.process_file(file_path, depth="deep")
            
            if not metadata or "error" in metadata:
                print(f"Failed to extract metadata from {file_path}: {metadata.get('error', 'Unknown error')}")
                return False
                
            file_type = metadata.get("file_type", self._determine_file_type(file_path))
            
            if file_type == "report":
                self._update_report_in_db(file_path, metadata)
            elif file_type == "task":
                self._update_task_in_db(file_path, metadata)
            elif file_type == "archive":
                self._update_archive_in_db(file_path, metadata)
            elif file_type == "doc":
                self._update_doc_in_db(file_path, metadata)
            else:
                self._update_generic_in_db(file_path, metadata)
                
            return True
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False

    def _determine_file_type(self, file_path: Path) -> str:
        path_str = str(file_path)
        if "reports/" in path_str:
            return "report"
        elif "tasks/" in path_str:
            return "task"
        elif "archive/" in path_str:
            return "archive"
        elif "docs/" in path_str:
            return "doc"
        else:
            return "root"

    def _update_report_in_db(self, file_path: Path, metadata: Dict[str, Any]):
        content = file_path.read_text(encoding="utf-8")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        self.knowledge_db.conn.execute("""
            INSERT OR REPLACE INTO reports 
            (id, task_id, loop_num, version, path, goal, files_changed, 
             tags, keywords, refs, validation_passed, date_completed, 
             content_full, indexed_at,
             enhanced_quality_score, enhanced_connectivity_score, enhanced_depth_score,
             enhanced_learning_potential, semantic_relationships, context_depth_metrics, learning_patterns)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get("id", file_path.stem),
            metadata.get("taskId", ""),
            metadata.get("loopNum", 0),
            metadata.get("version", 1),
            metadata.get("path", file_path.name),
            metadata.get("goal", ""),
            json.dumps(metadata.get("filesChanged", [])),
            json.dumps(metadata.get("tags", [])),
            json.dumps(metadata.get("keywords", [])),
            json.dumps(metadata.get("references", [])),
            1 if metadata.get("validationPassed") else (0 if metadata.get("validationPassed") is False else None),
            metadata.get("dateCompleted"),
            content,
            now,
            metadata.get("quality_scores", {}).get("overall_quality", 0),
            metadata.get("quality_scores", {}).get("connectivity_quality", 0),
            metadata.get("quality_scores", {}).get("depth_quality", 0),
            metadata.get("quality_scores", {}).get("learning_potential", 0),
            json.dumps(metadata.get("entities", [])),
            json.dumps(metadata.get("context_depth", {})),
            json.dumps(metadata.get("learning_patterns", {})),
        ))
        
        self._extract_lessons_from_content(content, "report", metadata.get("id"), metadata.get("loopNum", 0))
        self.knowledge_db.conn.commit()

    def _update_task_in_db(self, file_path: Path, metadata: Dict[str, Any]):
        content = file_path.read_text(encoding="utf-8")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        self.knowledge_db.conn.execute("""
            INSERT OR REPLACE INTO tasks 
            (id, path, status, objective, seed_idea, tags, refs, created, completed, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get("id", file_path.stem),
            str(file_path),
            metadata.get("status", ""),
            metadata.get("objective", ""),
            metadata.get("seed_idea", ""),
            json.dumps(metadata.get("tags", [])),
            json.dumps(metadata.get("references", [])),
            metadata.get("created", ""),
            metadata.get("completed", ""),
            now
        ))
        
        self.knowledge_db.conn.commit()

    def _update_archive_in_db(self, file_path: Path, metadata: Dict[str, Any]):
        content = file_path.read_text(encoding="utf-8")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        loop_num = metadata.get("loopNum", 0)
        
        self.knowledge_db.conn.execute("""
            INSERT OR REPLACE INTO archives 
            (id, loop_num, path, summary, lessons_learned, tasks_completed,
             infrastructure_created, content_full, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get("id", file_path.stem),
            loop_num,
            str(file_path),
            metadata.get("summary", ""),
            metadata.get("lessons_learned", ""),
            json.dumps(metadata.get("tasks_completed", [])),
            json.dumps(metadata.get("infrastructure_created", [])),
            content,
            now
        ))
        
        self._extract_lessons_from_content(content, "archive", metadata.get("id"), loop_num)
        self.knowledge_db.conn.commit()

    def _update_doc_in_db(self, file_path: Path, metadata: Dict[str, Any]):
        content = file_path.read_text(encoding="utf-8")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        self.knowledge_db.conn.execute("""
            INSERT OR REPLACE INTO docs 
            (id, path, title, category, tags, refs, content_full, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get("id", file_path.stem),
            str(file_path),
            metadata.get("title", file_path.stem),
            metadata.get("category", ""),
            json.dumps(metadata.get("tags", [])),
            json.dumps(metadata.get("references", [])),
            content,
            now
        ))
        
        self.knowledge_db.conn.commit()

    def _update_generic_in_db(self, file_path: Path, metadata: Dict[str, Any]):
        print(f"Processed generic file: {file_path}")

    def _extract_lessons_from_content(self, content: str, source_type: str, source_id: str, loop_num: int) -> int:
        lessons_extracted = 0
        lines = content.split("\n")
        
        for i, line in enumerate(lines):
            if line.strip().startswith("- ") or line.strip().startswith("* "):
                lesson_text = line.strip()[2:].strip()
                if any(keyword in lesson_text.lower() for keyword in
                       ["lesson", "learned", "success", "failure", "issue", "problem", "solution"]):
                    try:
                        self.knowledge_db.conn.execute("""
                            INSERT INTO lessons 
                            (source_type, source_id, loop_num, lesson_text, category,
                             confidence_score, context_section, indexed_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            source_type,
                            source_id,
                            loop_num,
                            lesson_text,
                            self._categorize_lesson(lesson_text),
                            0.7,
                            f"Line {i+1}",
                            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                        ))
                        lessons_extracted += 1
                    except Exception as e:
                        print(f"Error extracting lesson: {e}")
                        
        return lessons_extracted

    def _categorize_lesson(self, lesson_text: str) -> str:
        text_lower = lesson_text.lower()
        if "success" in text_lower or "worked" in text_lower:
            return "success"
        elif "failure" in text_lower or "failed" in text_lower or "issue" in text_lower:
            return "failure"
        elif "warning" in text_lower or "caution" in text_lower:
            return "warning"
        else:
            return "observation"

    def run_etl_pipeline(self) -> ETLResult:
        start_time = time.time()
        files_processed = 0
        metadata_extracted = 0
        database_updates = 0
        errors = []
        
        try:
            files_to_process = self._get_files_to_process()
            
            for file_path in files_to_process:
                try:
                    if self.process_file_incremental(file_path):
                        files_processed += 1
                        metadata_extracted += 1
                        database_updates += 1
                    else:
                        errors.append(f"Failed to process {file_path}")
                except Exception as e:
                    errors.append(f"Error processing {file_path}: {e}")
                    
            self._save_checksum_cache()
            
        except Exception as e:
            errors.append(f"ETL pipeline error: {e}")
            
        finally:
            self.knowledge_db.close()
            
        duration = time.time() - start_time
        
        return ETLResult(
            files_processed=files_processed,
            metadata_extracted=metadata_extracted,
            database_updates=database_updates,
            errors=errors,
            duration_seconds=duration
        )

    def unified_search(self, query: str, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """Use the KnowledgeDB's built-in search functionality."""
        results = {
            "reports": [],
            "tasks": [],
            "archives": [],
            "docs": [],
            "lessons": []
        }
        
        try:
            # Use KnowledgeDB's search method
            search_results = self.knowledge_db.search(query, limit=limit)
            
            # Organize results by type
            for result in search_results:
                result_dict = {
                    "id": result.id,
                    "title": result.context.get('title', result.context.get('id', result.id)),
                    "content": result.snippet,
                    "type": result.type,
                    "score": result.relevance,
                    "metadata": result.context
                }
                
                if result.type == "report":
                    results["reports"].append(result_dict)
                elif result.type == "task":
                    results["tasks"].append(result_dict)
                elif result.type == "archive":
                    results["archives"].append(result_dict)
                elif result.type == "doc":
                    results["docs"].append(result_dict)
                elif result.type == "lesson":
                    results["lessons"].append(result_dict)
                    
        except Exception as e:
            print(f"Search error: {e}")
            
        return results

    def get_cross_system_analytics(self) -> Dict[str, Any]:
        analytics = {}
        
        try:
            # Quality distribution
            cursor = self.knowledge_db.conn.execute("""
                SELECT
                    AVG(enhanced_quality_score) as avg_quality,
                    AVG(enhanced_connectivity_score) as avg_connectivity,
                    COUNT(*) as total_reports
                FROM reports
            """)
            
            row = cursor.fetchone()
            if row:
                analytics["quality_metrics"] = dict(row)
                
            # Lesson categories distribution
            cursor = self.knowledge_db.conn.execute("""
                SELECT category, COUNT(*) as count
                FROM lessons
                GROUP BY category
                ORDER BY count DESC
            """)
            
            analytics["lesson_categories"] = [dict(row) for row in cursor]
            
            # File type distribution
            cursor = self.knowledge_db.conn.execute("""
                SELECT "reports" as type, COUNT(*) as count FROM reports
                UNION ALL
                SELECT "tasks" as type, COUNT(*) as count FROM tasks
                UNION ALL
                SELECT "archives" as type, COUNT(*) as count FROM archives
                UNION ALL
                SELECT "docs" as type, COUNT(*) as count FROM docs
            """)
            
            analytics["content_distribution"] = [dict(row) for row in cursor]
            
        except Exception as e:
            print(f"Analytics error: {e}")
            analytics["error"] = str(e)
            
        return analytics

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Database-Metadata Connection Pipeline")
    parser.add_argument("--run-etl", action="store_true", help="Run ETL pipeline")
    parser.add_argument("--search", help="Perform unified search")
    parser.add_argument("--analytics", action="store_true", help="Generate cross-system analytics")
    parser.add_argument("--rebuild", action="store_true", help="Full database rebuild")
    
    args = parser.parse_args()
    
    workspace_root = Path(".")
    pipeline = MetadataDatabasePipeline(workspace_root)
    
    if args.run_etl:
        print("Running ETL pipeline...")
        result = pipeline.run_etl_pipeline()
        print(f"Processed {result.files_processed} files in {result.duration_seconds:.2f}s")
        print(f"Metadata extracted: {result.metadata_extracted}")
        print(f"Database updates: {result.database_updates}")
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")
                
    elif args.search:
        print(f"Searching for: {args.search}")
        results = pipeline.unified_search(args.search)
        for table, items in results.items():
            if items:
                print(f"\n{table.upper()}:")
                for item in items[:5]:
                    print(f"  - {item}")
                    
    elif args.analytics:
        print("Generating cross-system analytics...")
        analytics = pipeline.get_cross_system_analytics()
        print(json.dumps(analytics, indent=2))
        
    elif args.rebuild:
        print("Performing full database rebuild...")
        stats = pipeline.knowledge_db.rebuild()
        print(f"Rebuild complete: {stats}")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

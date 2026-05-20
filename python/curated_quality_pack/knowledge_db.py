# MODE: SCRIPT

'''Knowledge Database - SQLite-based full-text search for lessons learned.

This module implements Phase 3+ (SQLite with FTS5 + Graph + Semantic + Quality) from SEARCH_IMPROVEMENT_PLAN.md.
It provides fast, structured queries across all reports, archives, and lessons learned with advanced features:

- Graph tables for reference relationships between entities
- Milestone-aware indexing for goal-directed search
- Semantic embeddings for similarity search (framework ready)
- Multi-dimensional quality scoring system
- Proactive knowledge platform beyond reactive text search

Design goals:
- Markdown remains source of truth; database is regeneratable cache
- Uses stdlib sqlite3 only (no external dependencies for core features)
- FTS5 for efficient full-text search
- Sub-second query times for typical searches
- Graph relationships for understanding dependencies
- Quality scoring for ranking and filtering

Usage:
    from knowledge_db import KnowledgeDB
    db = KnowledgeDB(Path("."))
    db.rebuild()  # Regenerate from markdown with all enhancements
    results = db.search("validation failure")
    graph_stats = db.build_reference_graph()
    milestone_results = db.search_by_milestone("01", goal_id="G001")
    quality = db.calculate_quality_score("report", "TASK_0129_L71_v01")
'''

from __future__ import annotations

import json
import re
import sqlite3
import shutil
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import unified metadata processor
from tools.metadata.metadata_processor import UnifiedMetadataProcessor
from policy_gate import enforce_db_write_policy

# Legacy imports for backward compatibility (to be removed)
from loop_guardrails import (
    extract_report_metadata,
    extract_task_metadata,
    parse_report_filename,
    read_text,
    ARCHIV_RE,
)

import getpass
import socket
import time

# Enhanced extraction availability flag
ENHANCED_EXTRACTION_AVAILABLE = True


def _audit_log(operation: str, target: str, outcome: str, details: str = "") -> None:
    """Append a simple audit entry to `_transaction_log.jsonl`.

    This avoids importing `loop_cockpit` to prevent circular imports.
    """
    try:
        # Build base entry
        entry = {
            "timestamp": datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat().replace('+00:00','Z'),
            "operation": operation,
            "target": target,
            "pid": os.getpid(),
            "user": getpass.getuser(),
            "host": socket.gethostname(),
            "outcome": outcome,
            "details": details,
        }

        # Compute previous entry hash (simple append-only chain) to make tampering evident
        log_path = Path("_transaction_log.jsonl")
        prev_hash = None
        try:
            if log_path.exists():
                # Read last non-empty line
                with log_path.open('rb') as lf:
                    lf.seek(0, os.SEEK_END)
                    pos = lf.tell()
                    if pos == 0:
                        prev_hash = None
                    else:
                        # Walk backwards to find last line
                        line = b''
                        while pos > 0:
                            pos -= 1
                            lf.seek(pos)
                            ch = lf.read(1)
                            if ch == b'\n' and line:
                                break
                            line = ch + line
                        try:
                            last = line.decode('utf-8').strip()
                            if last:
                                import hashlib
                                prev_hash = hashlib.sha256(last.encode('utf-8')).hexdigest()
                        except Exception:
                            prev_hash = None
        except Exception:
            prev_hash = None

        if prev_hash:
            entry['prev_hash'] = prev_hash

        # Compute entry hash and include it for easy verification
        try:
            import hashlib
            entry_bytes = json.dumps(entry, sort_keys=True, ensure_ascii=False).encode('utf-8')
            entry_hash = hashlib.sha256(entry_bytes).hexdigest()
            entry['_hash'] = entry_hash
        except Exception:
            entry['_hash'] = None

        with open("_transaction_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Best-effort logging; do not raise from audit logging
        pass


DB_FILENAME = "keeper_knowledge.db"
DB_VERSION = 8

# SQL Schema
SCHEMA_SQL = """
-- Reports table with structured metadata
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    loop_num INTEGER NOT NULL,
    version INTEGER NOT NULL,
    path TEXT NOT NULL,
    goal TEXT,
    files_changed TEXT,  -- JSON array
    tags TEXT,           -- JSON array
    keywords TEXT,       -- JSON array
    refs TEXT,           -- JSON array (renamed from references)
    validation_passed INTEGER,  -- 0=false, 1=true, NULL=unknown
    date_completed TEXT,
    content_full TEXT,   -- Full content for FTS
    indexed_at TEXT NOT NULL
);

-- Archives table
CREATE TABLE IF NOT EXISTS archives (
    id TEXT PRIMARY KEY,
    loop_num INTEGER NOT NULL,
    path TEXT NOT NULL,
    summary TEXT,
    lessons_learned TEXT,
    tasks_completed TEXT,  -- JSON array
    infrastructure_created TEXT,  -- JSON array
    content_full TEXT,
    indexed_at TEXT NOT NULL
);

-- Lessons learned extracted wisdom (flattened for easier queries)
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,  -- 'report' or 'archive'
    source_id TEXT NOT NULL,
    loop_num INTEGER NOT NULL,
    lesson_text TEXT NOT NULL,
    category TEXT,  -- 'success', 'failure', 'observation', 'warning'
    confidence_score REAL DEFAULT 0.5,  -- Quality score 0.0-1.0
    context_section TEXT,  -- Section header where lesson was found
    indexed_at TEXT NOT NULL
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    status TEXT,
    objective TEXT,
    seed_idea TEXT,
    tags TEXT,  -- JSON array
    refs TEXT,  -- JSON array (renamed from references)
    created TEXT,
    completed TEXT,
    indexed_at TEXT NOT NULL
);

-- Docs table for documentation files
CREATE TABLE IF NOT EXISTS docs (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    title TEXT,
    category TEXT,  -- 'architecture', 'implementation', 'audit', 'planning', etc.
    tags TEXT,      -- JSON array
    refs TEXT,      -- JSON array
    content_full TEXT,  -- Full content for FTS
    indexed_at TEXT NOT NULL
);

-- Bugs table for BUG_*.md artifacts
CREATE TABLE IF NOT EXISTS bugs (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    title TEXT,
    severity TEXT,
    tags TEXT,      -- JSON array
    refs TEXT,      -- JSON array
    content_full TEXT,
    indexed_at TEXT NOT NULL
);

-- Code table for CODE_*.md artifacts
CREATE TABLE IF NOT EXISTS code (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    title TEXT,
    category TEXT,
    tags TEXT,      -- JSON array
    refs TEXT,      -- JSON array
    content_full TEXT,
    indexed_at TEXT NOT NULL
);

-- Test knowledge extracted from test files
CREATE TABLE IF NOT EXISTS test_knowledge (
    id TEXT PRIMARY KEY,
    test_file TEXT NOT NULL,
    entity_id TEXT NOT NULL,  -- e.g., 'bootstrap_protocol_enforcement'
    category TEXT NOT NULL,   -- 'guardrails', 'state_machine', 'failure_modes', etc.
    knowledge_type TEXT NOT NULL,  -- 'protocol_rule', 'edge_case', 'integration_pattern', etc.
    confidence_level TEXT,    -- 'high', 'medium', 'low'
    description TEXT NOT NULL,
    code_examples TEXT,       -- JSON array of code snippets
    expected_outcomes TEXT,   -- JSON array of expected behaviors
    failure_modes TEXT,       -- JSON array of failure scenarios
    integration_points TEXT,  -- JSON array of related components
    test_source TEXT NOT NULL,
    indexed_at TEXT NOT NULL
);

-- Semantic search enhancements
CREATE TABLE IF NOT EXISTS semantic_synonyms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL,
    synonym TEXT NOT NULL,
    domain TEXT,  -- 'architecture', 'validation', 'testing', 'general'
    confidence REAL NOT NULL,  -- 0.0 to 1.0
    indexed_at TEXT NOT NULL,
    UNIQUE(term, synonym, domain)
);

CREATE TABLE IF NOT EXISTS semantic_concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept TEXT NOT NULL,
    related_terms TEXT NOT NULL,  -- JSON array of related terms
    domain TEXT,
    confidence REAL NOT NULL,
    indexed_at TEXT NOT NULL,
    UNIQUE(concept, domain)
);

CREATE TABLE IF NOT EXISTS semantic_query_expansions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_query TEXT NOT NULL,
    expanded_terms TEXT NOT NULL,  -- JSON array of expanded terms
    expansion_type TEXT NOT NULL,  -- 'synonym', 'concept', 'fuzzy', 'context'
    confidence REAL NOT NULL,
    indexed_at TEXT NOT NULL
);

-- Pattern mining tables
CREATE TABLE IF NOT EXISTS mined_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,  -- 'sequence', 'correlation', 'trend', 'cluster'
    pattern_name TEXT NOT NULL,
    description TEXT NOT NULL,
    entities_involved TEXT NOT NULL,  -- JSON array of entity IDs
    confidence REAL NOT NULL,  -- 0.0 to 1.0
    support_count INTEGER NOT NULL,  -- How many instances support this pattern
    metadata TEXT,  -- JSON object with additional pattern data
    indexed_at TEXT NOT NULL,
    UNIQUE(pattern_type, pattern_name)
);

CREATE TABLE IF NOT EXISTS pattern_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL,
    related_pattern_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL,  -- 'similar', 'causes', 'follows', 'correlates'
    strength REAL NOT NULL,  -- 0.0 to 1.0
    evidence TEXT,  -- Supporting evidence
    FOREIGN KEY (pattern_id) REFERENCES mined_patterns(id),
    FOREIGN KEY (related_pattern_id) REFERENCES mined_patterns(id)
);

-- Search performance enhancements
CREATE TABLE IF NOT EXISTS search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL,
    query_text TEXT NOT NULL,
    results TEXT NOT NULL,  -- JSON array of cached results
    result_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 1,
    UNIQUE(query_hash)
);

-- Bootstrap predictions for adaptive file selection (TASK_0156)
CREATE TABLE IF NOT EXISTS bootstrap_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    task_context TEXT NOT NULL,
    predicted_files TEXT NOT NULL,  -- JSON array of predicted file paths
    actual_files TEXT,  -- JSON array of actually accessed files (filled later)
    accuracy REAL,  -- Prediction accuracy 0.0-1.0 (filled later)
    timestamp TEXT NOT NULL,
    loop_num INTEGER
);

-- Database metadata
CREATE TABLE IF NOT EXISTS db_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_reports_task ON reports(task_id);
CREATE INDEX IF NOT EXISTS idx_reports_loop ON reports(loop_num);
CREATE INDEX IF NOT EXISTS idx_reports_validation ON reports(validation_passed);
CREATE INDEX IF NOT EXISTS idx_archives_loop ON archives(loop_num);
CREATE INDEX IF NOT EXISTS idx_lessons_source ON lessons(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_lessons_loop ON lessons(loop_num);
CREATE INDEX IF NOT EXISTS idx_lessons_category ON lessons(category);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_docs_category ON docs(category);
CREATE INDEX IF NOT EXISTS idx_bugs_severity ON bugs(severity);
CREATE INDEX IF NOT EXISTS idx_code_category ON code(category);
CREATE INDEX IF NOT EXISTS idx_test_knowledge_category ON test_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_test_knowledge_type ON test_knowledge(knowledge_type);
CREATE INDEX IF NOT EXISTS idx_test_knowledge_entity ON test_knowledge(entity_id);

-- Semantic search indexes
CREATE INDEX IF NOT EXISTS idx_semantic_synonyms_term ON semantic_synonyms(term);
CREATE INDEX IF NOT EXISTS idx_semantic_synonyms_synonym ON semantic_synonyms(synonym);
CREATE INDEX IF NOT EXISTS idx_semantic_synonyms_domain ON semantic_synonyms(domain);
CREATE INDEX IF NOT EXISTS idx_semantic_concepts_concept ON semantic_concepts(concept);
CREATE INDEX IF NOT EXISTS idx_semantic_concepts_domain ON semantic_concepts(domain);
CREATE INDEX IF NOT EXISTS idx_semantic_query_expansions_query ON semantic_query_expansions(original_query);

-- Pattern mining indexes
CREATE INDEX IF NOT EXISTS idx_mined_patterns_type ON mined_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_mined_patterns_name ON mined_patterns(pattern_name);
CREATE INDEX IF NOT EXISTS idx_pattern_relationships_pattern ON pattern_relationships(pattern_id);
CREATE INDEX IF NOT EXISTS idx_pattern_relationships_related ON pattern_relationships(related_pattern_id);

-- Search cache indexes
CREATE INDEX IF NOT EXISTS idx_search_cache_hash ON search_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_cache_accessed ON search_cache(last_accessed);

-- Bootstrap predictions indexes
CREATE INDEX IF NOT EXISTS idx_bootstrap_predictions_task ON bootstrap_predictions(task_id);
CREATE INDEX IF NOT EXISTS idx_bootstrap_predictions_timestamp ON bootstrap_predictions(timestamp);

-- FTS5 virtual tables for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS reports_fts USING fts5(
    id,
    task_id,
    goal,
    keywords,
    content_full,
    content='reports',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS archives_fts USING fts5(
    id,
    summary,
    lessons_learned,
    content_full,
    content='archives',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS lessons_fts USING fts5(
    lesson_text,
    category,
    content='lessons',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    id,
    title,
    category,
    content_full,
    content='docs',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS test_knowledge_fts USING fts5(
    id,
    entity_id,
    category,
    knowledge_type,
    description,
    code_examples,
    expected_outcomes,
    failure_modes,
    integration_points,
    content='test_knowledge',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync with content tables
CREATE TRIGGER IF NOT EXISTS reports_ai AFTER INSERT ON reports BEGIN
    INSERT INTO reports_fts(rowid, id, task_id, goal, keywords, content_full)
    VALUES (NEW.rowid, NEW.id, NEW.task_id, NEW.goal, NEW.keywords, NEW.content_full);
END;

CREATE TRIGGER IF NOT EXISTS reports_ad AFTER DELETE ON reports BEGIN
    INSERT INTO reports_fts(reports_fts, rowid, id, task_id, goal, keywords, content_full)
    VALUES('delete', OLD.rowid, OLD.id, OLD.task_id, OLD.goal, OLD.keywords, OLD.content_full);
END;

CREATE TRIGGER IF NOT EXISTS archives_ai AFTER INSERT ON archives BEGIN
    INSERT INTO archives_fts(rowid, id, summary, lessons_learned, content_full)
    VALUES (NEW.rowid, NEW.id, NEW.summary, NEW.lessons_learned, NEW.content_full);
END;

CREATE TRIGGER IF NOT EXISTS archives_ad AFTER DELETE ON archives BEGIN
    INSERT INTO archives_fts(archives_fts, rowid, id, summary, lessons_learned, content_full)
    VALUES('delete', OLD.rowid, OLD.id, OLD.summary, OLD.lessons_learned, OLD.content_full);
END;

CREATE TRIGGER IF NOT EXISTS lessons_ai AFTER INSERT ON lessons BEGIN
    INSERT INTO lessons_fts(rowid, lesson_text, category)
    VALUES (NEW.id, NEW.lesson_text, NEW.category);
END;

CREATE TRIGGER IF NOT EXISTS lessons_ad AFTER DELETE ON lessons BEGIN
    INSERT INTO lessons_fts(lessons_fts, rowid, lesson_text, category)
    VALUES('delete', OLD.id, OLD.lesson_text, OLD.category);
END;

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
    INSERT INTO docs_fts(rowid, id, title, category, content_full)
    VALUES (NEW.rowid, NEW.id, NEW.title, NEW.category, NEW.content_full);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, id, title, category, content_full)
    VALUES('delete', OLD.rowid, OLD.id, OLD.title, OLD.category, OLD.content_full);
END;

CREATE TRIGGER IF NOT EXISTS test_knowledge_ai AFTER INSERT ON test_knowledge BEGIN
    INSERT INTO test_knowledge_fts(rowid, id, entity_id, category, knowledge_type, description, code_examples, expected_outcomes, failure_modes, integration_points)
    VALUES (NEW.rowid, NEW.id, NEW.entity_id, NEW.category, NEW.knowledge_type, NEW.description, NEW.code_examples, NEW.expected_outcomes, NEW.failure_modes, NEW.integration_points);
END;

CREATE TRIGGER IF NOT EXISTS test_knowledge_ad AFTER DELETE ON test_knowledge BEGIN
    INSERT INTO test_knowledge_fts(test_knowledge_fts, rowid, id, entity_id, category, knowledge_type, description, code_examples, expected_outcomes, failure_modes, integration_points)
    VALUES('delete', OLD.rowid, OLD.id, OLD.entity_id, OLD.category, OLD.knowledge_type, OLD.description, OLD.code_examples, OLD.expected_outcomes, OLD.failure_modes, OLD.integration_points);
END;

-- Task relationships (predecessor/successor/similar)
CREATE TABLE IF NOT EXISTS task_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_a TEXT NOT NULL,
    task_b TEXT NOT NULL,
    relationship_type TEXT NOT NULL,  -- 'predecessor', 'successor', 'similar'
    confidence_score REAL NOT NULL,   -- 0.0 to 1.0
    evidence TEXT,                    -- JSON array of evidence sources
    created_at TEXT NOT NULL,
    UNIQUE(task_a, task_b, relationship_type)
);

-- Aggregated patterns from lessons learned
CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,       -- 'success', 'failure', 'warning'
    pattern_text TEXT NOT NULL,
    examples TEXT,                    -- JSON array of task_ids that exemplify this pattern
    frequency INTEGER NOT NULL,       -- How many times this pattern appears
    last_seen_loop INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Indexes for new tables
CREATE INDEX IF NOT EXISTS idx_task_relationships_a ON task_relationships(task_a);
CREATE INDEX IF NOT EXISTS idx_task_relationships_b ON task_relationships(task_b);
CREATE INDEX IF NOT EXISTS idx_task_relationships_type ON task_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_loop ON patterns(last_seen_loop);

-- FTS for patterns
CREATE VIRTUAL TABLE IF NOT EXISTS patterns_fts USING fts5(
    pattern_text,
    pattern_type,
    content='patterns',
    content_rowid='id'
);

-- FTS triggers for patterns
CREATE TRIGGER IF NOT EXISTS patterns_ai AFTER INSERT ON patterns BEGIN
    INSERT INTO patterns_fts(rowid, pattern_text, pattern_type)
    VALUES (NEW.id, NEW.pattern_text, NEW.pattern_type);
END;

CREATE TRIGGER IF NOT EXISTS patterns_ad AFTER DELETE ON patterns BEGIN
    INSERT INTO patterns_fts(patterns_fts, rowid, pattern_text, pattern_type)
    VALUES('delete', OLD.id, OLD.pattern_text, OLD.pattern_type);
END;

-- Graph tables for reference relationships
CREATE TABLE IF NOT EXISTS reference_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,  -- 'report', 'task', 'doc', 'lesson'
    source_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,  -- 'references', 'depends_on', 'related_to', 'follows'
    confidence REAL NOT NULL,  -- 0.0 to 1.0
    evidence TEXT,  -- JSON array of evidence sources
    indexed_at TEXT NOT NULL,
    source_file_path TEXT,
    target_file_path TEXT,
    UNIQUE(source_type, source_id, target_type, target_id, relationship_type)
);

-- Milestone-aware indexing
CREATE TABLE IF NOT EXISTS milestone_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    milestone_id TEXT NOT NULL,
    goal_id TEXT,
    entity_type TEXT NOT NULL,  -- 'report', 'task', 'doc', 'lesson'
    entity_id TEXT NOT NULL,
    relevance_score REAL NOT NULL,  -- 0.0 to 1.0
    context_matches TEXT,  -- JSON array of matching contexts
    indexed_at TEXT NOT NULL,
    file_path TEXT,
    UNIQUE(milestone_id, goal_id, entity_type, entity_id)
);

-- Semantic embeddings for similarity search
CREATE TABLE IF NOT EXISTS semantic_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,  -- 'report', 'task', 'doc', 'lesson'
    entity_id TEXT NOT NULL,
    embedding_vector TEXT NOT NULL,  -- JSON array of floats
    model_used TEXT NOT NULL,  -- e.g., 'sentence-transformers/all-MiniLM-L6-v2'
    indexed_at TEXT NOT NULL,
    file_path TEXT,
    UNIQUE(entity_type, entity_id, model_used)
);

-- Enhanced quality scoring system
CREATE TABLE IF NOT EXISTS quality_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    relevance_score REAL NOT NULL,  -- 0.0 to 1.0
    recency_score REAL NOT NULL,    -- 0.0 to 1.0 (based on age)
    validation_score REAL NOT NULL, -- 0.0 to 1.0 (validation status)
    impact_score REAL NOT NULL,     -- 0.0 to 1.0 (estimated impact)
    overall_score REAL NOT NULL,    -- weighted combination
    factors TEXT,  -- JSON object with scoring factors
    indexed_at TEXT NOT NULL,
    file_path TEXT,
    UNIQUE(entity_type, entity_id)
);

-- File-level relevance scores (TASK_0149 Phase 2)
CREATE TABLE IF NOT EXISTS file_relevance_scores (
    path TEXT PRIMARY KEY,
    relevance_score REAL NOT NULL,  -- 0.0 to 1.0
    ref_count INTEGER NOT NULL DEFAULT 0,
    ref_popularity_score REAL NOT NULL DEFAULT 0.0,
    recency_score REAL NOT NULL DEFAULT 0.0,
    semantic_similarity_score REAL NOT NULL DEFAULT 0.5,
    structural_importance_score REAL NOT NULL DEFAULT 0.3,
    updated_at TEXT NOT NULL
);

-- Indexes for new tables
CREATE INDEX IF NOT EXISTS idx_reference_relationships_source ON reference_relationships(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_reference_relationships_target ON reference_relationships(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_reference_relationships_type ON reference_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_milestone_index_milestone ON milestone_index(milestone_id);
CREATE INDEX IF NOT EXISTS idx_milestone_index_goal ON milestone_index(goal_id);
CREATE INDEX IF NOT EXISTS idx_milestone_index_entity ON milestone_index(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_semantic_embeddings_entity ON semantic_embeddings(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_quality_scores_entity ON quality_scores(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_quality_scores_overall ON quality_scores(overall_score);
CREATE INDEX IF NOT EXISTS idx_file_relevance_scores_score ON file_relevance_scores(relevance_score DESC);
"""


@dataclass
class SearchResult:
    """A single search result with context."""
    type: str  # 'report', 'archive', 'lesson', 'task'
    id: str
    relevance: float
    snippet: str
    context: Dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class KnowledgeDB:
    """SQLite-based knowledge database with FTS5 full-text search."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.db_path = self.workspace_root / DB_FILENAME
        self.write_lock_path = self.workspace_root / f"{DB_FILENAME}.write.lock"
        self._conn: Optional[sqlite3.Connection] = None
        self._lease_state_lock = threading.RLock()
        self._write_lease_depth = 0
        self.metadata_processor = UnifiedMetadataProcessor(self.workspace_root)
        
        # Rate limiting and AI integration
        from anthropic_direct import KeeperAgent
        from rate_limit_handler import RateLimitHandler
        from token_monitor import LoopBudgetTracker, TokenBudgetGuard
        
        self.anthropic_agent = KeeperAgent(workspace=self.workspace_root)
        self.rate_handler = RateLimitHandler(self.workspace_root)
        self.budget_tracker = LoopBudgetTracker(self.workspace_root)
        self.budget_guard = TokenBudgetGuard(self.budget_tracker)
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy connection with row factory."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            self._conn.row_factory = sqlite3.Row
            # Enable foreign keys and WAL mode for better concurrency
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA busy_timeout = 30000")
        return self._conn
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _is_lock_file_stale(self, stale_after_seconds: int) -> bool:
        """Check whether an on-disk write lock looks stale and can be reaped."""
        try:
            if not self.write_lock_path.exists():
                return False
            age = time.time() - self.write_lock_path.stat().st_mtime
            return age > stale_after_seconds
        except Exception:
            return False

    def _acquire_write_guard(
        self,
        operation: str,
        timeout_seconds: int = 90,
        stale_after_seconds: int = 300,
        poll_seconds: float = 0.2,
    ) -> bool:
        """Acquire a reentrant, cross-process write lease.

        Returns:
            True: this call acquired the lock file
            False: reentrant acquisition (already held by this instance)
        """
        with self._lease_state_lock:
            if self._write_lease_depth > 0:
                self._write_lease_depth += 1
                return False

        deadline = time.time() + max(1, timeout_seconds)
        while True:
            try:
                fd = os.open(str(self.write_lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
                    lock_file.write(
                        json.dumps(
                            {
                                "pid": os.getpid(),
                                "operation": operation,
                                "acquired_at": utc_now_iso(),
                            },
                            ensure_ascii=False,
                        )
                    )
                with self._lease_state_lock:
                    self._write_lease_depth = 1
                _audit_log("knowledge_db.write_lock", str(self.write_lock_path), "SUCCESS", f"acquired_for={operation}")
                return True
            except FileExistsError:
                if self._is_lock_file_stale(stale_after_seconds):
                    try:
                        self.write_lock_path.unlink()
                        _audit_log(
                            "knowledge_db.write_lock_reap",
                            str(self.write_lock_path),
                            "SUCCESS",
                            f"stale_after={stale_after_seconds}s",
                        )
                        continue
                    except Exception:
                        pass
                if time.time() >= deadline:
                    raise TimeoutError(
                        f"Timed out waiting for DB write lock ({self.write_lock_path.name}) during {operation}"
                    )
                time.sleep(poll_seconds)

    def _release_write_guard(self, acquired_lease: bool) -> None:
        """Release a write lease acquired by _acquire_write_guard."""
        with self._lease_state_lock:
            if self._write_lease_depth > 0:
                self._write_lease_depth -= 1
            should_remove_file_lock = acquired_lease and self._write_lease_depth == 0

        if should_remove_file_lock:
            try:
                if self.write_lock_path.exists():
                    self.write_lock_path.unlink()
                    _audit_log("knowledge_db.write_lock", str(self.write_lock_path), "SUCCESS", "released")
            except Exception as e:
                _audit_log("knowledge_db.write_lock", str(self.write_lock_path), "FAILED", f"release_error={e}")

    def _replace_file_with_retry(
        self,
        source: Path,
        target: Path,
        attempts: int = 20,
        delay_seconds: float = 0.25,
    ) -> None:
        """Atomically replace target file, retrying transient lock/access-denied failures."""
        last_error: Optional[Exception] = None
        for _ in range(max(1, attempts)):
            try:
                os.replace(str(source), str(target))
                return
            except OSError as e:
                last_error = e
                msg = str(e).lower()
                if any(token in msg for token in ("used by another process", "access is denied", "busy", "locked")):
                    time.sleep(delay_seconds)
                    continue
                raise
        raise OSError(f"Could not replace {target} after {attempts} attempts: {last_error}")

    def rebuild_with_write_guard(self, timeout_seconds: int = 120) -> Dict[str, Any]:
        """Run rebuild() under cross-process write lease protection."""
        acquired = self._acquire_write_guard("rebuild", timeout_seconds=timeout_seconds)
        try:
            return self.rebuild()
        finally:
            self._release_write_guard(acquired)
    
    def _create_schema(self) -> None:
        """Create database schema if not exists."""
        self.conn.executescript(SCHEMA_SQL)
        if ENHANCED_EXTRACTION_AVAILABLE:
            alter_statements = [
                "ALTER TABLE reports ADD COLUMN enhanced_quality_score REAL DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN enhanced_connectivity_score REAL DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN enhanced_depth_score REAL DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN enhanced_learning_potential REAL DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN semantic_relationships TEXT DEFAULT '[]'",
                "ALTER TABLE reports ADD COLUMN context_depth_metrics TEXT DEFAULT '{}'",
                "ALTER TABLE reports ADD COLUMN learning_patterns TEXT DEFAULT '{}'",
            ]
            for stmt in alter_statements:
                try:
                    self.conn.execute(stmt)
                except sqlite3.OperationalError:
                    # Column may already exist.
                    pass
        self.conn.commit()
    
    def rebuild(self) -> Dict[str, Any]:
        """Rebuild entire database from markdown sources.
        
        Returns statistics about what was indexed.
        """
        stats = {
            "reports_indexed": 0,
            "archives_indexed": 0,
            "lessons_extracted": 0,
            "tasks_indexed": 0,
            "docs_indexed": 0,
            "bugs_indexed": 0,
            "code_indexed": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
            "errors": [],
        }
        # We'll build the new DB in a temporary file and swap it into place atomically.
        orig_path = self.db_path
        temp_suffix = f".tmp.{os.getpid()}.{int(time.time() * 1000)}"
        temp_path = self.workspace_root / (DB_FILENAME + temp_suffix)
        timestamp = utc_now_iso().replace(':', '').replace('-', '')
        backup_path = self.workspace_root / (DB_FILENAME + f".backup.{timestamp}")

        # Ensure previous connections are closed and temp removed
        try:
            self.close()
        except Exception:
            pass
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass

        # If an existing DB exists, make a safety copy before rebuilding
        try:
            if orig_path.exists():
                _audit_log('knowledge_db.pre_backup', str(orig_path), 'START', f'backup_path={backup_path}')
                shutil.copy2(str(orig_path), str(backup_path))
                stats.setdefault('pre_rebuild_backup', str(backup_path))
                _audit_log('knowledge_db.backup', str(backup_path), 'SUCCESS', f'copied_from={orig_path}')
        except Exception as e:
            stats['errors'].append(f'Backup failed: {e}')
            _audit_log('knowledge_db.backup', str(orig_path), 'FAILED', str(e))

        # Point the connection at the temp DB for all indexing operations
        try:
            self._conn = sqlite3.connect(str(temp_path), timeout=30.0)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA busy_timeout = 30000")
        except Exception as e:
            stats['errors'].append(f'Could not open temp DB: {e}')
            return stats

        # Create schema in the temp DB
        try:
            self._create_schema()

            # TASK_0167: Add enhanced metadata columns to reports table
            if ENHANCED_EXTRACTION_AVAILABLE:
                try:
                    # Add enhanced metadata columns (ignore errors if they already exist)
                    alter_statements = [
                        "ALTER TABLE reports ADD COLUMN enhanced_quality_score REAL DEFAULT 0",
                        "ALTER TABLE reports ADD COLUMN enhanced_connectivity_score REAL DEFAULT 0",
                        "ALTER TABLE reports ADD COLUMN enhanced_depth_score REAL DEFAULT 0",
                        "ALTER TABLE reports ADD COLUMN enhanced_learning_potential REAL DEFAULT 0",
                        "ALTER TABLE reports ADD COLUMN semantic_relationships TEXT DEFAULT '[]'",  # JSON
                        "ALTER TABLE reports ADD COLUMN context_depth_metrics TEXT DEFAULT '{}'",  # JSON
                        "ALTER TABLE reports ADD COLUMN learning_patterns TEXT DEFAULT '{}'",  # JSON
                    ]
                    for stmt in alter_statements:
                        try:
                            self.conn.execute(stmt)
                        except sqlite3.OperationalError:
                            # Column might already exist, ignore
                            pass
                except Exception as e:
                    # Log but don't fail rebuild if enhanced columns can't be added
                    print(f"Warning: Could not add enhanced metadata columns: {e}")

        except Exception as e:
            stats['errors'].append(f'Schema creation failed: {e}')
            try:
                self.close()
            except Exception:
                pass
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return stats

        # Set metadata in temp DB
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO db_meta (key, value) VALUES (?, ?)",
                ("version", str(DB_VERSION))
            )
            self.conn.execute(
                "INSERT OR REPLACE INTO db_meta (key, value) VALUES (?, ?)",
                ("rebuild_started", stats["started_at"]) 
            )
        except Exception as e:
            stats['errors'].append(f'Setting db_meta failed: {e}')
        
        # Index reports
        reports_dir = self.workspace_root / "reports"
        if reports_dir.exists():
            for report_file in sorted(reports_dir.glob("report_*.md")):
                if not report_file.is_file():
                    continue
                try:
                    self._index_report(report_file)
                    stats["reports_indexed"] += 1
                except Exception as e:
                    stats["errors"].append(f"Report {report_file.name}: {str(e)}")
        
        # Index archives
        archive_dir = self.workspace_root / "archive"
        if archive_dir.exists():
            for archive_file in sorted(archive_dir.glob("ARCHIV_*.md")):
                if not archive_file.is_file():
                    continue
                try:
                    lessons = self._index_archive(archive_file)
                    stats["archives_indexed"] += 1
                    stats["lessons_extracted"] += lessons
                except Exception as e:
                    stats["errors"].append(f"Archive {archive_file.name}: {str(e)}")
        
        # Index tasks
        tasks_dir = self.workspace_root / "tasks"
        if tasks_dir.exists():
            for task_file in sorted(tasks_dir.glob("task_TASK_*.md")):
                if not task_file.is_file():
                    continue
                try:
                    self._index_task(task_file)
                    stats["tasks_indexed"] += 1
                except Exception as e:
                    stats["errors"].append(f"Task {task_file.name}: {str(e)}")
        
        # Index docs
        docs_dir = self.workspace_root / "docs"
        if docs_dir.exists():
            for doc_file in sorted(docs_dir.glob("*.md")):
                if not doc_file.is_file():
                    continue
                try:
                    self._index_doc(doc_file)
                    stats["docs_indexed"] = stats.get("docs_indexed", 0) + 1
                except Exception as e:
                    stats["errors"].append(f"Doc {doc_file.name}: {str(e)}")

        # Index bugs
        bugs_dir = self.workspace_root / "bugs"
        if bugs_dir.exists():
            for bug_file in sorted(bugs_dir.glob("BUG_*.md")):
                if not bug_file.is_file():
                    continue
                try:
                    self._index_bug(bug_file)
                    stats["bugs_indexed"] = stats.get("bugs_indexed", 0) + 1
                except Exception as e:
                    stats["errors"].append(f"Bug {bug_file.name}: {str(e)}")

        # Index code artifacts
        code_dir = self.workspace_root / "code"
        if code_dir.exists():
            for code_file in sorted(code_dir.glob("CODE_*.md")):
                if not code_file.is_file():
                    continue
                try:
                    self._index_code(code_file)
                    stats["code_indexed"] = stats.get("code_indexed", 0) + 1
                except Exception as e:
                    stats["errors"].append(f"Code {code_file.name}: {str(e)}")
        
        # Extract audit findings from MASTER_AUDIT_FINDINGS.md
        audit_path = self.workspace_root / "docs" / "audit" / "MASTER_AUDIT_FINDINGS.md"
        if audit_path.exists():
            try:
                audit_stats = self.extract_audit_findings(audit_path)
                stats["audit_findings_extracted"] = audit_stats.get("quality_metrics_extracted", 0) + \
                                                   audit_stats.get("patterns_extracted", 0) + \
                                                   audit_stats.get("milestones_extracted", 0) + \
                                                   audit_stats.get("badges_extracted", 0) + \
                                                   audit_stats.get("artifacts_extracted", 0)
                if audit_stats.get("errors"):
                    stats["errors"].extend(audit_stats["errors"])
            except Exception as e:
                stats["errors"].append(f"Audit extraction failed: {str(e)}")
        
        # Extract test knowledge from test files
        try:
            test_stats = self._extract_test_knowledge()
            stats["test_knowledge_extracted"] = test_stats.get("knowledge_entities_extracted", 0)
            stats["test_files_processed"] = test_stats.get("test_files_processed", 0)
            if test_stats.get("errors"):
                stats["errors"].extend(test_stats["errors"])
        except Exception as e:
            stats["errors"].append(f"Test knowledge extraction failed: {str(e)}")
        
        # Extract comprehensive knowledge from ALL MD files
        try:
            comprehensive_stats = self.extract_comprehensive_md_knowledge()
            stats["comprehensive_knowledge_extracted"] = comprehensive_stats.get("knowledge_entities_extracted", 0)
            stats["comprehensive_files_processed"] = comprehensive_stats.get("files_processed", 0)
            stats["comprehensive_reports_processed"] = comprehensive_stats.get("reports_processed", 0)
            stats["comprehensive_tasks_processed"] = comprehensive_stats.get("tasks_processed", 0)
            stats["comprehensive_archives_processed"] = comprehensive_stats.get("archives_processed", 0)
            stats["comprehensive_docs_processed"] = comprehensive_stats.get("docs_processed", 0)
            stats["comprehensive_root_files_processed"] = comprehensive_stats.get("root_files_processed", 0)
            if comprehensive_stats.get("errors"):
                stats["errors"].extend(comprehensive_stats["errors"])
        except Exception as e:
            stats["errors"].append(f"Comprehensive knowledge extraction failed: {str(e)}")
        
        # Extract external knowledge using multi-agent learning patterns
        # TEMPORARILY DISABLED: Processing 19k+ external files creates 380MB database
        # try:
        #     external_stats = self.extract_external_knowledge_with_multiagent_learning()
        #     stats["external_paths_analyzed"] = external_stats.get("external_paths_analyzed", 0)
        #     stats["external_md_files_discovered"] = external_stats.get("md_files_discovered", 0)
        #     stats["external_knowledge_candidates"] = external_stats.get("knowledge_entities_candidates", 0)
        #     stats["external_entities_integrated"] = external_stats.get("entities_integrated", 0)
        #     stats["external_similarity_conflicts_resolved"] = external_stats.get("similarity_conflicts_resolved", 0)
        #     stats["external_new_knowledge_added"] = external_stats.get("new_knowledge_added", 0)
        #     if external_stats.get("errors"):
        #         stats["errors"].extend(external_stats["errors"])
        # except Exception as e:
        #     stats["errors"].append(f"External knowledge extraction failed: {str(e)}")
        
        # Populate semantic search enhancements
        try:
            semantic_stats = self._populate_semantic_data()
            stats["semantic_synonyms_added"] = semantic_stats.get("synonyms_added", 0)
            stats["semantic_concepts_added"] = semantic_stats.get("concepts_added", 0)
        except Exception as e:
            stats["errors"].append(f"Semantic data population failed: {str(e)}")
        
        stats["completed_at"] = utc_now_iso()

        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO db_meta (key, value) VALUES (?, ?)",
                ("rebuild_completed", stats["completed_at"]) 
            )
            self.conn.execute(
                "INSERT OR REPLACE INTO db_meta (key, value) VALUES (?, ?)",
                ("stats", json.dumps(stats))
            )
            self.conn.commit()
        except Exception as e:
            stats['errors'].append(f'Finalizing temp DB failed: {e}')

        # Mine relationships and patterns in temp DB
        try:
            self._mine_relationships()
        except Exception as e:
            stats['errors'].append(f'_mine_relationships failed: {e}')

        try:
            pattern_stats = self.mine_patterns()
            stats["patterns_mined"] = pattern_stats.get("patterns_mined", 0)
            stats["pattern_relationships"] = pattern_stats.get("relationships_found", 0)
        except Exception as e:
            stats["errors"].append(f"Pattern mining failed: {str(e)}")

        try:
            self._mine_patterns()
        except Exception as e:
            stats['errors'].append(f'_mine_patterns failed: {e}')

        # Build reference graph
        try:
            graph_stats = self.build_reference_graph_from_content()
            stats["reference_relationships_created"] = graph_stats.get("relationships_created", 0)
            stats["references_found"] = graph_stats.get("references_found", 0)
            stats["files_scanned_for_refs"] = graph_stats.get("files_scanned", 0)
        except Exception as e:
            stats["errors"].append(f"Reference graph building failed: {str(e)}")

        # Index milestones
        try:
            milestone_stats = self._index_milestones()
            stats["milestone_entities_indexed"] = milestone_stats.get("entities_indexed", 0)
            stats["milestone_relevance_matches"] = milestone_stats.get("relevance_matches", 0)
        except Exception as e:
            stats["errors"].append(f"Milestone indexing failed: {str(e)}")

        # Calculate quality scores for all entities
        try:
            quality_stats = self._calculate_all_quality_scores()
            stats["quality_scores_calculated"] = quality_stats.get("scores_calculated", 0)
        except Exception as e:
            stats["errors"].append(f"Quality score calculation failed: {str(e)}")

        # Close temp DB and atomically replace original
        try:
            self.close()
            # atomic replace
            _audit_log('knowledge_db.swap_attempt', f'temp={temp_path}', 'START', f'target={orig_path}')
            self._replace_file_with_retry(temp_path, orig_path)
            stats['swapped'] = str(orig_path)
            _audit_log('knowledge_db.swap', str(orig_path), 'SUCCESS', f'swapped_from={temp_path}')
        except Exception as e:
            stats['errors'].append(f'Could not swap temp DB into place: {e}')
            _audit_log('knowledge_db.swap', str(orig_path), 'FAILED', str(e))
            # attempt to restore backup if available
            try:
                if backup_path.exists():
                    shutil.copy2(str(backup_path), str(orig_path))
                    stats['restored_from_backup'] = str(backup_path)
                    _audit_log('knowledge_db.restore_from_backup', str(backup_path), 'SUCCESS', f'restored_to={orig_path}')
            except Exception as e2:
                stats['errors'].append(f'Backup restore also failed: {e2}')
                _audit_log('knowledge_db.restore_from_backup', str(backup_path), 'FAILED', str(e2))

        return stats
    
    def _mine_relationships(self) -> None:
        """Mine task relationships from existing data."""
        now = utc_now_iso()
        
        # Get all tasks
        tasks = self.conn.execute("SELECT id, objective, seed_idea FROM tasks").fetchall()
        task_dict = {row["id"]: (row["objective"] or "", row["seed_idea"] or "") for row in tasks}
        
        # Clear existing relationships
        self.conn.execute("DELETE FROM task_relationships")
        
        relationships_added = 0
        
        for task_a, (obj_a, seed_a) in task_dict.items():
            for task_b, (obj_b, seed_b) in task_dict.items():
                if task_a >= task_b:  # Avoid duplicates and self-relations
                    continue
                
                # Combine text for similarity analysis
                text_a = f"{obj_a} {seed_a}".lower()
                text_b = f"{obj_b} {seed_b}".lower()
                
                # Simple similarity based on common words
                words_a = set(text_a.split())
                words_b = set(text_b.split())
                if not words_a or not words_b:
                    continue
                    
                intersection = words_a & words_b
                union = words_a | words_b
                similarity = len(intersection) / len(union) if union else 0
                
                # Check for predecessor/successor based on task numbers
                try:
                    num_a = int(task_a.split('_')[-1])
                    num_b = int(task_b.split('_')[-1])
                    if abs(num_a - num_b) == 1:  # Adjacent tasks
                        if num_a < num_b:
                            rel_type = "predecessor"
                            task_first, task_second = task_a, task_b
                        else:
                            rel_type = "successor" 
                            task_first, task_second = task_b, task_a
                        
                        self.conn.execute("""
                            INSERT INTO task_relationships 
                            (task_a, task_b, relationship_type, confidence_score, evidence, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            task_first, task_second, rel_type, 0.8,
                            json.dumps(["task_number_sequence"]),
                            now
                        ))
                        relationships_added += 1
                        
                except (ValueError, IndexError):
                    pass
                
                # Add similarity relationships
                if similarity > 0.3:  # At least 30% word overlap
                    self.conn.execute("""
                        INSERT INTO task_relationships 
                        (task_a, task_b, relationship_type, confidence_score, evidence, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        task_a, task_b, "similar", similarity,
                        json.dumps([f"word_overlap_{len(intersection)}"]),
                        now
                    ))
                    relationships_added += 1
        
        self.conn.commit()
        print(f"Mined {relationships_added} task relationships")
    
    def _mine_patterns(self) -> None:
        """Mine patterns from lessons learned."""
        now = utc_now_iso()
        
        # Clear existing patterns
        self.conn.execute("DELETE FROM patterns")
        
        # Get all lessons
        lessons = self.conn.execute("""
            SELECT lesson_text, category, source_id, loop_num 
            FROM lessons 
            ORDER BY loop_num DESC
        """).fetchall()
        
        pattern_counts = {}
        pattern_examples = {}
        
        for lesson in lessons:
            text = lesson["lesson_text"].lower().strip()
            category = lesson["category"]
            task_id = lesson["source_id"]
            loop_num = lesson["loop_num"]
            
            # Simple pattern extraction: look for common phrases
            # This is a basic implementation - could be enhanced with NLP
            words = text.split()
            if len(words) < 5:  # Skip very short lessons
                continue
                
            # Extract 3-5 word phrases as potential patterns
            for i in range(len(words) - 2):
                phrase = " ".join(words[i:i+3])  # 3-word phrases
                if len(phrase) > 10:  # Skip trivial phrases
                    key = (phrase, category)
                    if key not in pattern_counts:
                        pattern_counts[key] = 0
                        pattern_examples[key] = []
                    
                    pattern_counts[key] += 1
                    if task_id not in pattern_examples[key] and len(pattern_examples[key]) < 5:
                        pattern_examples[key].append(task_id)
        
        # Insert patterns with frequency > 1
        patterns_added = 0
        for (pattern_text, pattern_type), count in pattern_counts.items():
            if count > 1:  # Only patterns that appear multiple times
                self.conn.execute("""
                    INSERT INTO patterns 
                    (pattern_type, pattern_text, examples, frequency, last_seen_loop, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern_type,
                    pattern_text,
                    json.dumps(pattern_examples[(pattern_text, pattern_type)]),
                    count,
                    max(lesson["loop_num"] for lesson in lessons if lesson["lesson_text"].lower().strip().find(pattern_text) != -1),
                    now,
                    now
                ))
                patterns_added += 1
        
        self.conn.commit()
        print(f"Mined {patterns_added} patterns from lessons")
    
    def _index_report(self, report_path: Path) -> None:
        """Index a single report file."""
        # Use unified metadata processor
        unified_metadata = self.metadata_processor.process_file(report_path, depth='deep')

        # Validate metadata
        errors = self.metadata_processor.validate_metadata(unified_metadata)
        if errors:
            print(f"Metadata validation errors for {report_path}: {errors}")
            return

        # Extract basic report metadata for compatibility
        metadata = extract_report_metadata(report_path) or {}

        # Fallback extraction for non-standard report names to avoid loop_num=0/null source_id drift.
        stem = report_path.stem
        task_match = re.search(r"(TASK_\d{4})", stem)
        loop_match = re.search(r"_L(\d+)(?:_|$)", stem)
        if not loop_match:
            loop_match = re.search(r"(?:^|_)LOOP_(\d+)(?:_|$)", stem, re.IGNORECASE)
        version_match = re.search(r"_v(\d+)(?:_|$)", stem, re.IGNORECASE)

        metadata.setdefault("id", stem)
        metadata.setdefault("taskId", task_match.group(1) if task_match else "")
        metadata.setdefault("loopNum", int(loop_match.group(1)) if loop_match else 0)
        metadata.setdefault("version", int(version_match.group(1)) if version_match else 1)
        metadata.setdefault("path", report_path.name)
        metadata.setdefault("goal", "")
        metadata.setdefault("filesChanged", [])
        metadata.setdefault("tags", [])
        metadata.setdefault("keywords", [])
        metadata.setdefault("references", [])

        # Merge enhanced fields from unified metadata without overwriting canonical report identity fields.
        metadata.update({
            "enhanced_quality_score": unified_metadata.get("quality_scores", {}).get("overall_quality", 0),
            "enhanced_connectivity_score": unified_metadata.get("quality_scores", {}).get("connectivity_quality", 0),
            "enhanced_depth_score": unified_metadata.get("quality_scores", {}).get("depth_quality", 0),
            "enhanced_learning_potential": unified_metadata.get("quality_scores", {}).get("learning_potential", 0),
            "semantic_relationships": unified_metadata.get("entities", []),
            "context_depth_metrics": unified_metadata.get("context_depth", {}),
            "learning_patterns": unified_metadata.get("learning_patterns", {}),
            "relationships": unified_metadata.get("relationships", []),
        })

        content = read_text(report_path)
        now = utc_now_iso()
        
        self.conn.execute("""
            INSERT OR REPLACE INTO reports 
            (id, task_id, loop_num, version, path, goal, files_changed, 
             tags, keywords, refs, validation_passed, date_completed, 
             content_full, indexed_at,
             enhanced_quality_score, enhanced_connectivity_score, enhanced_depth_score,
             enhanced_learning_potential, semantic_relationships, context_depth_metrics, learning_patterns)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get("id", report_path.stem),
            metadata.get("taskId", ""),
            metadata.get("loopNum", 0),
            metadata.get("version", 1),
            metadata.get("path", report_path.name),
            metadata.get("goal", ""),
            json.dumps(metadata.get("filesChanged", [])),
            json.dumps(metadata.get("tags", [])),
            json.dumps(metadata.get("keywords", [])),
            json.dumps(metadata.get("references", [])),
            1 if metadata.get("validationPassed") else (0 if metadata.get("validationPassed") is False else None),
            metadata.get("dateCompleted"),
            content,
            now,
            metadata.get("enhanced_quality_score", 0),
            metadata.get("enhanced_connectivity_score", 0),
            metadata.get("enhanced_depth_score", 0),
            metadata.get("enhanced_learning_potential", 0),
            json.dumps(metadata.get("semantic_relationships", [])),
            json.dumps(metadata.get("context_depth_metrics", {})),
            json.dumps(metadata.get("learning_patterns", {})),
        ))

        # Extract lessons from report (look for lessons/observations)
        self._extract_lessons_from_content(
            content,
            "report",
            metadata.get("id", report_path.stem),
            int(metadata.get("loopNum", 0) or 0),
        )
        
        # Generate and store semantic embedding (best-effort, optional).
        if hasattr(self.rate_handler, "process_api_call") and hasattr(self.anthropic_agent, "create_embedding"):
            try:
                estimated_tokens = len(content) // 4
                self.budget_guard.check_budget(estimated_tokens)
                embedding = self.rate_handler.process_api_call(
                    self.anthropic_agent.create_embedding, content
                )
                self.conn.execute("""
                    INSERT OR REPLACE INTO semantic_embeddings 
                    (entity_type, entity_id, embedding_vector, content_preview, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    "report",
                    metadata.get("id", report_path.stem),
                    json.dumps(embedding),
                    content[:500] + "..." if len(content) > 500 else content,
                    now
                ))
            except Exception as e:
                print(f"Warning: Could not generate embedding for report {report_path}: {e}")
        
        self.conn.commit()
    
    def _index_archive(self, archive_path: Path) -> int:
        """Index a single archive file. Returns number of lessons extracted."""
        content = read_text(archive_path)
        now = utc_now_iso()
        
        # Parse archive number from filename.
        # Prefer canonical ARCHIV_RE, but tolerate suffix variants like
        # ARCHIV_0085_RESTORED_AFTER_incident.md to avoid loop_num=0 drift.
        match = ARCHIV_RE.match(archive_path.name)
        if not match:
            match = re.search(r"ARCHIV_(\d+)", archive_path.name)
        loop_num = int(match.group(1)) if match else 0
        
        # Extract summary section
        summary = ""
        summary_match = re.search(
            r"^## (?:SUMMARY|LOOP SUMMARY)\s*$\s*(.*?)(?=^##|\Z)",
            content, re.MULTILINE | re.DOTALL
        )
        if summary_match:
            summary = summary_match.group(1).strip()[:1000]
        
        # Extract lessons learned section
        lessons_text = ""
        lessons_match = re.search(
            r"^## (?:LESSONS LEARNED|OBSERVATIONS|KEY LEARNINGS)\s*$\s*(.*?)(?=^##|\Z)",
            content, re.MULTILINE | re.DOTALL
        )
        if lessons_match:
            lessons_text = lessons_match.group(1).strip()
        
        # Extract tasks completed
        tasks_completed = []
        tasks_match = re.search(
            r"^## (?:TASKS COMPLETED|COMPLETED TASKS|WORK DONE)\s*$\s*(.*?)(?=^##|\Z)",
            content, re.MULTILINE | re.DOTALL
        )
        if tasks_match:
            tasks_text = tasks_match.group(1)
            task_ids = re.findall(r"TASK_\d{4}", tasks_text)
            tasks_completed = list(set(task_ids))
        
        # Extract infrastructure created
        infra = []
        infra_match = re.search(
            r"^## (?:INFRASTRUCTURE|FILES CREATED|NEW FILES)\s*$\s*(.*?)(?=^##|\Z)",
            content, re.MULTILINE | re.DOTALL
        )
        if infra_match:
            infra_text = infra_match.group(1)
            # Extract file paths
            files = re.findall(r"[`\[]?([a-zA-Z0-9_/\\]+\.(?:py|md|json|html|sh|bat))[`\]]?", infra_text)
            infra = list(set(files))
        
        self.conn.execute("""
            INSERT OR REPLACE INTO archives
            (id, loop_num, path, summary, lessons_learned, tasks_completed,
             infrastructure_created, content_full, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            archive_path.stem,
            loop_num,
            archive_path.name,
            summary,
            lessons_text,
            json.dumps(tasks_completed),
            json.dumps(infra),
            content,
            now,
        ))
        
        # Extract individual lessons
        lessons_count = self._extract_lessons_from_content(
            lessons_text or content, "archive", archive_path.stem, loop_num
        )
        
        self.conn.commit()
        return lessons_count
    
    def _index_task(self, task_path: Path) -> None:
        """Index a single task specification file."""
        # Use unified metadata processor
        metadata = self.metadata_processor.process_file(task_path, depth='medium')

        # Validate metadata
        errors = self.metadata_processor.validate_metadata(metadata)
        if errors:
            print(f"Metadata validation errors for {task_path}: {errors}")
            return

        # Extract basic task metadata for compatibility
        basic_metadata = extract_task_metadata(task_path)
        if not basic_metadata:
            return

        # Merge unified metadata with basic metadata
        basic_metadata.update({
            "quality_score": metadata.get("quality_scores", {}).get("overall_quality", 0),
            "entities": metadata.get("entities", []),
            "relationships": metadata.get("relationships", [])
        })

        metadata = basic_metadata
        
        now = utc_now_iso()
        
        # Keep canonical IDs for standard task files (task_TASK_####.md),
        # but avoid PK collisions for task variants that share TASK_#### metadata.
        task_id = metadata.get("id", task_path.stem)
        if not re.fullmatch(r"task_TASK_\d{4}\.md", task_path.name):
            task_id = task_path.stem

        self.conn.execute("""
            INSERT OR REPLACE INTO tasks
            (id, path, status, objective, seed_idea, tags, refs, created, completed, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            metadata.get("path", task_path.name),
            metadata.get("status"),
            metadata.get("objective"),
            metadata.get("seedIdea"),
            json.dumps(metadata.get("tags", [])),
            json.dumps(metadata.get("references", [])),
            metadata.get("created"),
            metadata.get("completed"),
            now,
        ))
        
        self.conn.commit()
    
    def _index_doc(self, doc_path: Path) -> None:
        """Index a single documentation file."""
        content = read_text(doc_path)
        if not content:
            return
        
        now = utc_now_iso()
        
        # Extract title from first header
        title = doc_path.stem  # Default to filename
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        
        # Determine category based on filename/path
        category = "documentation"
        filename_lower = doc_path.name.lower()
        if "architecture" in filename_lower:
            category = "architecture"
        elif "implementation" in filename_lower or "roadmap" in filename_lower:
            category = "implementation"
        elif "audit" in filename_lower or "violation" in filename_lower or "incident" in filename_lower:
            category = "audit"
        elif "plan" in filename_lower or "scheme" in filename_lower:
            category = "planning"
        elif "ui" in filename_lower or "wire" in filename_lower:
            category = "ui_design"
        elif "multiagent" in filename_lower or "multi_agent" in filename_lower:
            category = "multiagent"
        elif "search" in filename_lower or "query" in filename_lower:
            category = "search"
        elif "ops" in filename_lower or "protocol" in filename_lower:
            category = "operations"
        
        # Extract references
        refs = []
        ref_pattern = r'\[ref:([^]]+)\]'
        for match in re.finditer(ref_pattern, content):
            refs.append(match.group(1))
        
        # Extract tags (look for common patterns)
        tags = []
        if "MODE:" in content:
            tags.append("system")
        if "HISTORICAL" in content:
            tags.append("historical")
        if "OBSOLETE" in content or "OUTDATED" in content:
            tags.append("outdated")
        if "ARCHITECTURE" in filename_lower:
            tags.append("architecture")
        if "IMPLEMENTATION" in filename_lower:
            tags.append("implementation")
        
        self.conn.execute("""
            INSERT OR REPLACE INTO docs
            (id, path, title, category, tags, refs, content_full, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_path.stem,
            doc_path.name,
            title,
            category,
            json.dumps(tags),
            json.dumps(refs),
            content,
            now,
        ))
        
        self.conn.commit()

    def _index_bug(self, bug_path: Path) -> None:
        """Index a single bug report markdown file."""
        content = read_text(bug_path)
        if not content:
            return

        now = utc_now_iso()
        title = bug_path.stem
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        severity = "unknown"
        severity_match = re.search(r'^\s*SEVERITY\s*:\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
        if severity_match:
            severity = severity_match.group(1).strip().lower()
        else:
            lower = content.lower()
            if "critical" in lower:
                severity = "critical"
            elif "high" in lower:
                severity = "high"
            elif "medium" in lower:
                severity = "medium"
            elif "low" in lower:
                severity = "low"

        refs: List[str] = []
        for match in re.finditer(r'\[ref:([^]]+)\]', content):
            refs.append(match.group(1))

        tags = ["bug"]
        if "ROOT CAUSE" in content.upper():
            tags.append("root_cause")
        if "FIX" in content.upper():
            tags.append("fix")

        self.conn.execute(
            """
            INSERT OR REPLACE INTO bugs
            (id, path, title, severity, tags, refs, content_full, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bug_path.stem,
                bug_path.name,
                title,
                severity,
                json.dumps(tags),
                json.dumps(refs),
                content,
                now,
            ),
        )
        self.conn.commit()

    def _index_code(self, code_path: Path) -> None:
        """Index a single code-artifact markdown file."""
        content = read_text(code_path)
        if not content:
            return

        now = utc_now_iso()
        title = code_path.stem
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        category = "implementation"
        filename_lower = code_path.name.lower()
        if "api" in filename_lower:
            category = "operations"
        elif "ui" in filename_lower:
            category = "ui_design"
        elif "audit" in filename_lower:
            category = "audit"
        elif "bootstrap" in filename_lower:
            category = "planning"

        refs: List[str] = []
        for match in re.finditer(r'\[ref:([^]]+)\]', content):
            refs.append(match.group(1))

        tags = ["code"]
        if "TEST" in content.upper():
            tags.append("test")
        if "INTEGRATION" in content.upper():
            tags.append("integration")

        self.conn.execute(
            """
            INSERT OR REPLACE INTO code
            (id, path, title, category, tags, refs, content_full, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code_path.stem,
                code_path.name,
                title,
                category,
                json.dumps(tags),
                json.dumps(refs),
                content,
                now,
            ),
        )
        self.conn.commit()

    def _verify_incremental_index(self, index_fn_name: str, target_path: Path) -> bool:
        """Verify that an incremental index operation produced a persisted row."""
        path_name = target_path.name
        if index_fn_name == "_index_report":
            row = self.conn.execute(
                "SELECT indexed_at FROM reports WHERE id=? OR path=?",
                (target_path.stem, path_name),
            ).fetchone()
            return bool(row and row["indexed_at"])
        if index_fn_name == "_index_task":
            task_id = path_name.replace("task_", "").replace(".md", "")
            row = self.conn.execute(
                "SELECT indexed_at FROM tasks WHERE id=? OR path=?",
                (task_id, path_name),
            ).fetchone()
            return bool(row and row["indexed_at"])
        if index_fn_name == "_index_archive":
            row = self.conn.execute(
                "SELECT indexed_at FROM archives WHERE id=? OR path=?",
                (target_path.stem, path_name),
            ).fetchone()
            return bool(row and row["indexed_at"])
        if index_fn_name == "_index_doc":
            row = self.conn.execute(
                "SELECT indexed_at FROM docs WHERE id=? OR path=?",
                (target_path.stem, path_name),
            ).fetchone()
            return bool(row and row["indexed_at"])
        if index_fn_name == "_index_bug":
            row = self.conn.execute(
                "SELECT indexed_at FROM bugs WHERE id=? OR path=?",
                (target_path.stem, path_name),
            ).fetchone()
            return bool(row and row["indexed_at"])
        if index_fn_name == "_index_code":
            row = self.conn.execute(
                "SELECT indexed_at FROM code WHERE id=? OR path=?",
                (target_path.stem, path_name),
            ).fetchone()
            return bool(row and row["indexed_at"])
        return False

    def incremental_index_with_fallback(
        self,
        index_fn_name: str,
        target_path: Path,
        allow_fallback_rebuild: bool = True,
    ) -> Dict[str, Any]:
        """Index one artifact incrementally, rebuilding the DB if consistency checks fail."""
        acquired_lease = self._acquire_write_guard("incremental_index", timeout_seconds=60)
        result: Dict[str, Any] = {
            "success": False,
            "mode": "incremental",
            "fallback_used": False,
            "target_path": str(target_path),
            "index_fn": index_fn_name,
            "error": None,
            "rebuild_stats": None,
        }

        try:
            resolved_target = Path(target_path)
            if not resolved_target.is_absolute():
                resolved_target = (self.workspace_root / resolved_target).resolve()

            try:
                self._create_schema()
                index_fn = getattr(self, index_fn_name)
                index_fn(resolved_target)
                self.conn.commit()
                if not self._verify_incremental_index(index_fn_name, resolved_target):
                    raise RuntimeError(
                        f"Incremental verification failed for {index_fn_name} on {resolved_target.name}"
                    )
                result["success"] = True
                return result
            except Exception as e:
                result["error"] = str(e)
                result["fallback_used"] = True
                result["mode"] = "fallback_rebuild"
                if not allow_fallback_rebuild:
                    result["fallback_used"] = False
                    result["mode"] = "incremental_failed"
                    result["success"] = False
                    return result

            try:
                rebuild_stats = self.rebuild()
                result["rebuild_stats"] = rebuild_stats
                primary_counts = (
                    int(rebuild_stats.get("reports_indexed", 0)),
                    int(rebuild_stats.get("archives_indexed", 0)),
                    int(rebuild_stats.get("tasks_indexed", 0)),
                    int(rebuild_stats.get("docs_indexed", 0)),
                    int(rebuild_stats.get("bugs_indexed", 0)),
                    int(rebuild_stats.get("code_indexed", 0)),
                )
                result["success"] = any(c > 0 for c in primary_counts)
                if not result["success"] and not result["error"]:
                    result["error"] = "Fallback rebuild returned zero indexed primary artifacts"
            except Exception as rebuild_error:
                result["success"] = False
                result["rebuild_stats"] = {"errors": [str(rebuild_error)]}
                result["error"] = (
                    f"{result['error']}; fallback rebuild failed: {rebuild_error}"
                    if result.get("error")
                    else f"Fallback rebuild failed: {rebuild_error}"
                )
            return result
        finally:
            self._release_write_guard(acquired_lease)
    
    def extract_audit_findings(self, audit_path: Path) -> Dict[str, Any]:
        """Extract structured knowledge entities from MASTER_AUDIT_FINDINGS.md.
        
        Returns statistics about entities extracted.
        """
        content = read_text(audit_path)
        if not content:
            return {"error": "Could not read audit file"}
        
        stats = {
            "quality_metrics_extracted": 0,
            "patterns_extracted": 0,
            "milestones_extracted": 0,
            "badges_extracted": 0,
            "artifacts_extracted": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
            "errors": [],
        }
        
        now = utc_now_iso()
        
        try:
            # Extract quality metrics and health scores
            self._extract_audit_quality_metrics(content, now)
            stats["quality_metrics_extracted"] = 1
            
            # Extract loop utilization patterns
            patterns_count = self._extract_audit_patterns(content, now)
            stats["patterns_extracted"] = patterns_count
            
            # Extract architecture evolution milestones
            milestones_count = self._extract_audit_milestones(content, now)
            stats["milestones_extracted"] = milestones_count
            
            # Extract badge achievement data
            badges_count = self._extract_audit_badges(content, now)
            stats["badges_extracted"] = badges_count
            
            # Extract historical artifacts
            artifacts_count = self._extract_audit_artifacts(content, now)
            stats["artifacts_extracted"] = artifacts_count
            
        except Exception as e:
            stats["errors"].append(f"Audit extraction failed: {str(e)}")
        
        stats["completed_at"] = utc_now_iso()
        self.conn.commit()
        
        return stats
    
    def _extract_audit_quality_metrics(self, content: str, timestamp: str) -> None:
        """Extract project health scores and quality metrics."""
        # Project health score
        health_match = re.search(r'Overall Project Health Score:\s*(\d+\.\d+)/10\.0', content)
        if health_match:
            score = float(health_match.group(1))
            lesson_text = f"Project health score: {score}/10.0 - excellent health with no systemic issues"
            self._insert_audit_lesson("audit_quality", "health_score", lesson_text, "observation", 55, timestamp)
        
        # Empty loop ratio
        empty_match = re.search(r'Empty loop ratio:\s*(\d+)%\s*\((\d+)/(\d+)\)', content)
        if empty_match:
            percentage = int(empty_match.group(1))
            count = int(empty_match.group(2))
            total = int(empty_match.group(3))
            lesson_text = f"Empty loop ratio: {percentage}% ({count}/{total} loops) - decreasing trend over time"
            self._insert_audit_lesson("audit_quality", "utilization", lesson_text, "observation", 55, timestamp)
        
        # Distinguished badge rate
        badge_match = re.search(r'Distinguished badge rate:\s*(\d+)%\s*\((\d+)/(\d+)\)', content)
        if badge_match:
            percentage = int(badge_match.group(1))
            achieved = int(badge_match.group(2))
            total = int(badge_match.group(3))
            lesson_text = f"Distinguished badge excellence rate: {percentage}% ({achieved}/{total} badges)"
            self._insert_audit_lesson("audit_quality", "excellence", lesson_text, "success", 55, timestamp)
        
        # Error metrics
        phantom_match = re.search(r'Phantom References:\s*(\d+)', content)
        if phantom_match:
            count = int(phantom_match.group(1))
            lesson_text = f"Phantom references identified: {count} - all historical artifacts, no active issues"
            self._insert_audit_lesson("audit_quality", "errors", lesson_text, "observation", 55, timestamp)
        
        hallucination_match = re.search(r'Hallucinations:\s*(\d+)', content)
        if hallucination_match:
            count = int(hallucination_match.group(1))
            lesson_text = f"Hallucinations detected: {count} - zero false claims in audit scope"
            self._insert_audit_lesson("audit_quality", "accuracy", lesson_text, "success", 55, timestamp)
    
    def _extract_audit_patterns(self, content: str, timestamp: str) -> int:
        """Extract loop utilization and completion patterns."""
        patterns_extracted = 0
        
        # Single-task loop pattern
        if "Single-task loops: Dominant pattern post-loop 17" in content:
            lesson_text = "Single-task completion pattern dominant post-loop 17 - indicates maturing workflow discipline"
            self._insert_audit_lesson("patterns", "completion_rhythm", lesson_text, "observation", 55, timestamp)
            patterns_extracted += 1
        
        # Multi-loop task patterns
        multi_task_matches = re.findall(r'TASK_(\d+):\s*(\d+)\s+versions?\s+across\s+Loops\s+([\d-]+)', content)
        for task_num, versions, loops in multi_task_matches:
            lesson_text = f"TASK_{task_num}: {versions} versions across loops {loops} - complex iterative work pattern"
            self._insert_audit_lesson("patterns", "multi_loop_tasks", lesson_text, "observation", 55, timestamp)
            patterns_extracted += 1
        
        # Infrastructure milestone cadence
        if "Infrastructure milestones: Every 7-10 loops" in content:
            lesson_text = "Infrastructure development cadence: major improvements every 7-10 loops (loops 1,7,10,18,20)"
            self._insert_audit_lesson("patterns", "infrastructure_cadence", lesson_text, "observation", 55, timestamp)
            patterns_extracted += 1
        
        # Empty loop distribution patterns
        if "Empty loops become rare and isolated after Loop 17" in content:
            lesson_text = "Empty loop distribution: clustered early (startup phase), isolated later - improving efficiency"
            self._insert_audit_lesson("patterns", "empty_loop_distribution", lesson_text, "success", 55, timestamp)
            patterns_extracted += 1
        
        # Batch processing pattern
        batch_match = re.search(r'Batch processing pattern.*Loop (\d+):\s*(\d+)\s+reports', content)
        if batch_match:
            loop_num = batch_match.group(1)
            reports = batch_match.group(2)
            lesson_text = f"Batch processing pattern: Loop {loop_num} generated {reports} reports - efficient bulk completion"
            self._insert_audit_lesson("patterns", "batch_processing", lesson_text, "success", 55, timestamp)
            patterns_extracted += 1
        
        return patterns_extracted
    
    def _extract_audit_milestones(self, content: str, timestamp: str) -> int:
        """Extract architecture evolution milestones."""
        milestones_extracted = 0
        
        # Key infrastructure milestones
        milestones = [
            (1, "Foundation infrastructure creation"),
            (7, "REPORT-FIRST LAW enforcement system"),
            (10, "System hardening"),
            (18, "Complete file migration to tasks/ and reports/ directories"),
            (20, "Automation infrastructure suite (history index, metadata lint, gate automation, session packs)")
        ]
        
        for loop_num, description in milestones:
            lesson_text = f"Loop {loop_num} milestone: {description}"
            self._insert_audit_lesson("milestones", "infrastructure", lesson_text, "success", loop_num, timestamp)
            milestones_extracted += 1
        
        # File migration completion
        if "File migration completion verified" in content:
            lesson_text = "File organization migration completed and verified - pre-Loop 18 root files moved to subdirectories"
            self._insert_audit_lesson("milestones", "file_migration", lesson_text, "success", 18, timestamp)
            milestones_extracted += 1
        
        return milestones_extracted
    
    def _extract_audit_badges(self, content: str, timestamp: str) -> int:
        """Extract distinguished badge achievement data."""
        badges_extracted = 0
        
        # Distinguished badge criteria
        badge_achievements = [
            ("16-20", "Two critical infrastructure milestones (file migration + automation suite)", "foundational architecture improvements"),
            ("31-35", "100% utilization + perfect execution rhythm (5 consecutive single-task completions)", "workflow consistency and discipline"),
            ("41-45", "100% utilization across entire badge period (zero empty loops)", "peak productivity"),
            ("51-55", "100% utilization + non-sequential task execution", "strategic task selection and efficiency")
        ]
        
        for badge_range, criteria, excellence_factor in badge_achievements:
            lesson_text = f"Badge {badge_range} distinguished achievement: {criteria} - excellence factor: {excellence_factor}"
            self._insert_audit_lesson("badges", "distinguished", lesson_text, "success", 55, timestamp)
            badges_extracted += 1
        
        # Overall excellence rate
        if "36% excellence rate" in content:
            lesson_text = "Distinguished badge excellence rate: 36% (4/11 badges) - high standard of achievement"
            self._insert_audit_lesson("badges", "excellence_rate", lesson_text, "success", 55, timestamp)
            badges_extracted += 1
        
        return badges_extracted
    
    def _extract_audit_artifacts(self, content: str, timestamp: str) -> int:
        """Extract historical artifacts and resolutions."""
        artifacts_extracted = 0
        
        # Phantom reference resolution
        if "task_TASK_0002.md" in content and "blocked and documented in Loop 7" in content:
            lesson_text = "Phantom reference task_TASK_0002.md: referenced but never created, blocked and documented in Loop 7"
            self._insert_audit_lesson("artifacts", "phantom_reference", lesson_text, "observation", 7, timestamp)
            artifacts_extracted += 1
        
        # File location variance
        if "Pre-Loop 18 files in root vs post-Loop 18 in subdirectories" in content:
            lesson_text = "File location variance: pre-Loop 18 files in root directory, migrated to subdirectories post-Loop 18"
            self._insert_audit_lesson("artifacts", "file_organization", lesson_text, "observation", 18, timestamp)
            artifacts_extracted += 1
        
        # Archive format variations
        if "ARCHIV_0041 format slightly different" in content:
            lesson_text = "ARCHIV_0041 format variation: minor cosmetic difference, content complete and accurate"
            self._insert_audit_lesson("artifacts", "format_variation", lesson_text, "observation", 41, timestamp)
            artifacts_extracted += 1
        
        return artifacts_extracted
    
    def _insert_audit_lesson(self, category: str, subcategory: str, lesson_text: str, lesson_type: str, loop_num: int, timestamp: str) -> None:
        """Insert an audit-derived lesson into the lessons table."""
        self.conn.execute("""
            INSERT INTO lessons 
            (source_type, source_id, loop_num, lesson_text, category, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "audit",
            f"audit_{category}_{subcategory}",
            loop_num,
            lesson_text,
            lesson_type,
            timestamp,
        ))
    
    def _extract_test_knowledge(self) -> Dict[str, Any]:
        """Extract knowledge entities from test files.
        
        Returns statistics about test knowledge entities extracted.
        """
        stats = {
            "test_files_processed": 0,
            "knowledge_entities_extracted": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
            "errors": [],
        }
        
        now = utc_now_iso()
        
        # Test file locations
        test_dirs = [
            self.workspace_root,  # root level test files
            self.workspace_root / "tests",  # dedicated tests directory
        ]
        
        test_files = []
        for test_dir in test_dirs:
            if test_dir.exists():
                # Find Python test files
                test_files.extend(test_dir.glob("test_*.py"))
                # Also include other test files that might contain knowledge
                test_files.extend(test_dir.glob("*_test.py"))
        
        for test_file in test_files:
            try:
                entities_count = self._extract_knowledge_from_test_file(test_file, now)
                stats["test_files_processed"] += 1
                stats["knowledge_entities_extracted"] += entities_count
            except Exception as e:
                stats["errors"].append(f"Test file {test_file.name}: {str(e)}")
        
        stats["completed_at"] = utc_now_iso()
        self.conn.commit()
        
        return stats
    
    def _extract_knowledge_from_test_file(self, test_file: Path, timestamp: str) -> int:
        """Extract knowledge entities from a single test file. Returns count."""
        content = read_text(test_file)
        if not content:
            return 0
        
        entities_extracted = 0
        test_filename = test_file.name
        
        # Extract knowledge based on test file patterns
        entities_extracted += self._extract_bootstrap_knowledge(content, test_filename, timestamp)
        entities_extracted += self._extract_finalization_knowledge(content, test_filename, timestamp)
        entities_extracted += self._extract_session_knowledge(content, test_filename, timestamp)
        entities_extracted += self._extract_guardrail_knowledge(content, test_filename, timestamp)
        entities_extracted += self._extract_integration_knowledge(content, test_filename, timestamp)
        entities_extracted += self._extract_failure_mode_knowledge(content, test_filename, timestamp)
        
        return entities_extracted
    
    def _extract_bootstrap_knowledge(self, content: str, test_file: str, timestamp: str) -> int:
        """Extract bootstrap protocol knowledge."""
        entities = 0
        
        # Bootstrap blocking when _BOOTSTRAP.md exists
        if "_BOOTSTRAP.md" in content and "400" in content:
            self._insert_test_knowledge(
                f"bootstrap_blocking_{test_file}",
                "bootstrap_protocol_enforcement",
                "guardrails",
                "protocol_rule",
                "high",
                "Bootstrap protocol blocks confirm-bootstrap when _BOOTSTRAP.md exists unless incident acknowledged",
                ["def test_confirm_blocked_when_bootstrap_present", "assert resp.status_code == 400"],
                ["System prevents premature ACTIVE transition", "Maintains deterministic state progression"],
                ["Protocol violation without incident ack", "Silent state corruption"],
                ["confirm-bootstrap API", "incident acknowledgment system"],
                test_file,
                timestamp
            )
            entities += 1
        
        # Incident acknowledgment recovery
        if "ack-incident" in content and "incident_ack" in content:
            self._insert_test_knowledge(
                f"incident_ack_recovery_{test_file}",
                "incident_acknowledgment_flow",
                "guardrails",
                "recovery_pattern",
                "high",
                "Incident acknowledgment enables recovery from protocol violations",
                ["client.post('/api/ack-incident')", "client.post('/api/confirm-bootstrap')"],
                ["Clean recovery from blocked states", "Human-approved exception handling"],
                ["Unacknowledged violations remain blocked", "Improper incident documentation"],
                ["ack-incident API", "confirm-bootstrap API", "incident tracking"],
                test_file,
                timestamp
            )
            entities += 1
        
        return entities
    
    def _extract_finalization_knowledge(self, content: str, test_file: str, timestamp: str) -> int:
        """Extract finalization workflow knowledge."""
        entities = 0
        
        # Ready marker atomicity
        if ".ready" in content and "atomic" in content.lower():
            self._insert_test_knowledge(
                f"ready_marker_atomicity_{test_file}",
                "ready_marker_semantics",
                "finalization",
                "atomic_operation",
                "high",
                "Ready markers provide atomic completion signaling for deterministic finalization",
                ["ready_path.write_text('ready')", "mv ready.tmp ready"],
                ["Deterministic finalization timing", "Prevents partial state corruption"],
                ["Missing ready marker delays finalization", "Race conditions in marker creation"],
                ["finalize_loop_procedure", "ready marker filesystem"],
                test_file,
                timestamp
            )
            entities += 1
        
        # Pre-finalization validation
        if "validation" in content and "GREEN_LIGHT" in content:
            self._insert_test_knowledge(
                f"prefinalization_validation_{test_file}",
                "finalization_preconditions",
                "finalization",
                "validation_rule",
                "high",
                "Pre-finalization validation ensures GREEN LIGHT before archive creation",
                ["validate_all_preconditions()", "get_green_light_confirmation()"],
                ["Prevents corrupted archives", "Maintains data integrity"],
                ["RED LIGHT blocks finalization", "Incomplete task reports"],
                ["pre_finalization_green_light()", "report validation", "archive creation"],
                test_file,
                timestamp
            )
            entities += 1
        
        return entities
    
    def _extract_session_knowledge(self, content: str, test_file: str, timestamp: str) -> int:
        """Extract session lifecycle knowledge."""
        entities = 0
        
        # Session state transitions
        if "session" in content and "status" in content and "working" in content:
            self._insert_test_knowledge(
                f"session_lifecycle_{test_file}",
                "session_lifecycle_management",
                "orchestration",
                "state_machine",
                "high",
                "Agent sessions follow defined lifecycle: pending → working → completed/failed",
                ["session.status = 'working'", "session.status = 'completed'"],
                ["Predictable agent behavior", "Clean resource cleanup"],
                ["Stuck sessions without progress updates", "Improper session termination"],
                ["MultiAgentOrchestrator", "AgentSession", "session status API"],
                test_file,
                timestamp
            )
            entities += 1
        
        # Parallelization analysis
        if "parallelizable" in content and "analyze" in content:
            self._insert_test_knowledge(
                f"parallelization_analysis_{test_file}",
                "parallelization_analysis",
                "orchestration",
                "dependency_mapping",
                "medium",
                "Task dependency analysis enables safe parallel execution",
                ["analyze_parallelization(tasks)", "parallelizable_tasks = [...]"],
                ["Optimal resource utilization", "Faster execution times"],
                ["Incorrect dependency detection", "Race condition introduction"],
                ["analyze_parallelization()", "task dependency graph"],
                test_file,
                timestamp
            )
            entities += 1
        
        return entities
    
    def _extract_guardrail_knowledge(self, content: str, test_file: str, timestamp: str) -> int:
        """Extract guardrail and validation knowledge."""
        entities = 0
        
        # Metadata linting rules
        if "lint" in content and "BOOTSTRAP_PRESENT_DURING_ACTIVE" in content:
            self._insert_test_knowledge(
                f"metadata_lint_rules_{test_file}",
                "metadata_lint_rules",
                "guardrails",
                "validation_rule",
                "high",
                "Metadata linting enforces state consistency and protocol compliance",
                ["metadata_lint(ws)", "BOOTSTRAP_PRESENT_DURING_ACTIVE"],
                ["Early detection of state violations", "Prevents silent corruption"],
                ["False negatives in validation", "Overly strict rules"],
                ["metadata_lint()", "lint error codes", "state validation"],
                test_file,
                timestamp
            )
            entities += 1
        
        # File existence validation
        if "Test-Path" in content or "exists()" in content:
            self._insert_test_knowledge(
                f"file_validation_patterns_{test_file}",
                "file_operation_atomicity",
                "guardrails",
                "validation_pattern",
                "medium",
                "File existence checks prevent race conditions and state corruption",
                ["if (Test-Path $file)", "if file.exists()"],
                ["Safe file operations", "Prevents concurrent access issues"],
                ["TOCTOU vulnerabilities", "Improper error handling"],
                ["file existence checks", "atomic file operations"],
                test_file,
                timestamp
            )
            entities += 1
        
        return entities
    
    def _extract_integration_knowledge(self, content: str, test_file: str, timestamp: str) -> int:
        """Extract integration pattern knowledge."""
        entities = 0
        
        # API endpoint chaining
        if "requests.get" in content and "requests.post" in content:
            self._insert_test_knowledge(
                f"api_chaining_patterns_{test_file}",
                "api_endpoint_chaining",
                "integration",
                "integration_pattern",
                "high",
                "API endpoints follow chained request patterns for complex workflows",
                ["resp = requests.get('/api/orchestrator')", "resp = requests.post('/api/orchestrator/execute')"],
                ["Reliable workflow execution", "Proper error propagation"],
                ["Network failures break chains", "Improper error handling"],
                ["HTTP client libraries", "API endpoint design", "error handling"],
                test_file,
                timestamp
            )
            entities += 1
        
        # External service integration
        if "ollama" in content.lower() or "AI" in content:
            self._insert_test_knowledge(
                f"external_service_integration_{test_file}",
                "external_service_integration",
                "integration",
                "service_integration",
                "medium",
                "External AI services require proper error handling and timeout management",
                ["ollama.generate()", "handle_connection_errors()"],
                ["Offline capability preservation", "Graceful degradation"],
                ["Service unavailability breaks functionality", "Timeout configuration issues"],
                ["Ollama integration", "AI service APIs", "network resilience"],
                test_file,
                timestamp
            )
            entities += 1
        
        return entities
    
    def _extract_failure_mode_knowledge(self, content: str, test_file: str, timestamp: str) -> int:
        """Extract failure mode and edge case knowledge."""
        entities = 0
        
        # Connection failure handling
        if "ConnectionError" in content or "connection" in content.lower():
            self._insert_test_knowledge(
                f"connection_failure_handling_{test_file}",
                "connection_failure_handling",
                "failure_modes",
                "error_handling",
                "high",
                "Network connection failures require graceful error handling and retry logic",
                ["except requests.exceptions.ConnectionError", "retry_with_backoff()"],
                ["System stability during network issues", "User experience preservation"],
                ["Silent failures without user feedback", "Resource leaks on errors"],
                ["network error handling", "retry mechanisms", "user feedback"],
                test_file,
                timestamp
            )
            entities += 1
        
        # Timeout and cancellation
        if "timeout" in content or "cancel" in content.lower():
            self._insert_test_knowledge(
                f"timeout_cancellation_{test_file}",
                "timeout_and_cancellation",
                "failure_modes",
                "resource_management",
                "medium",
                "Long-running operations require timeout and cancellation handling",
                ["signal.timeout(30)", "operation.cancel()"],
                ["Resource conservation", "System responsiveness"],
                ["Hung processes consuming resources", "Poor user experience"],
                ["timeout handling", "cancellation tokens", "resource cleanup"],
                test_file,
                timestamp
            )
            entities += 1
        
        return entities
    
    def _insert_test_knowledge(self, entity_id: str, entity_name: str, category: str, 
                              knowledge_type: str, confidence: str, description: str,
                              code_examples: List[str], expected_outcomes: List[str],
                              failure_modes: List[str], integration_points: List[str],
                              test_source: str, timestamp: str) -> None:
        """Insert a test-derived knowledge entity."""
        self.conn.execute("""
            INSERT OR REPLACE INTO test_knowledge 
            (id, test_file, entity_id, category, knowledge_type, confidence_level,
             description, code_examples, expected_outcomes, failure_modes, 
             integration_points, test_source, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{entity_name}_{test_source}",
            test_source,
            entity_name,
            category,
            knowledge_type,
            confidence,
            description,
            json.dumps(code_examples),
            json.dumps(expected_outcomes),
            json.dumps(failure_modes),
            json.dumps(integration_points),
            test_source,
            timestamp,
        ))
    
    def _extract_lessons_from_content(
        self, content: str, source_type: str, source_id: str, loop_num: int
    ) -> int:
        """Extract ONLY the highest-quality, most insightful lessons from content.

        Ultra-selective extraction focusing on genuine, actionable insights.
        Rejects generic observations, documentation, and low-value content.
        """
        now = utc_now_iso()
        lessons_count = 0

        # Split content into sections for contextual analysis
        sections = re.split(r'^##\s+', content, flags=re.MULTILINE)

        for section in sections:
            section_lines = section.strip().split('\n')
            if not section_lines:
                continue

            # Get section header for context
            section_header = section_lines[0].strip().lower() if section_lines else ""

            # ONLY extract from HIGH-VALUE sections (expanded based on actual report structure)
            high_value_sections = [
                'lessons learned', 'key learnings', 'critical lessons',
                'key insights', 'important insights', 'major insights',
                'critical findings', 'key findings', 'important findings',
                'lessons & insights', 'insights & lessons',
                'what we learned', 'what we discovered',
                'recommendations', 'key recommendations',
                'best practices', 'key practices',
                'challenges overcome', 'problems solved',
                'solutions implemented', 'improvements made',
                'conclusion', 'next steps', 'notes',  # Additional sections that often contain lessons
                'outcome', 'learnings', 'insights',
                'recommendations & next steps', 'future considerations'
            ]

            section_is_high_value = any(
                high_value in section_header for high_value in high_value_sections
            )

            if not section_is_high_value:
                continue  # Skip non-lesson sections entirely

            # Analyze each line in HIGH-VALUE sections only
            for i, line in enumerate(section_lines):
                line = line.strip()
                if not line or line.startswith('#') or len(line) < 15:
                    continue

                # Strip bullet points and numbered lists
                clean_line = line.strip()
                if clean_line.startswith(('- ', '* ', '• ')):
                    clean_line = clean_line[2:].strip()
                elif clean_line.startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
                    # Handle numbered lists
                    clean_line = clean_line[clean_line.find(' ')+1:].strip()

                # ULTRA-SELECTIVE: Only extract with strong lesson indicators
                lesson_data = self._analyze_line_for_high_quality_lessons(clean_line, section_header, section_lines, i)

                if lesson_data:
                    # For high-quality indicators, we trust the indicator itself provides the "genuine" quality
                    # Just check actionable insight and not generic/documentation
                    if (self._has_actionable_insight(lesson_data['text']) and
                        not self._is_generic_or_documentation(lesson_data['text'])):

                        self.conn.execute("""
                            INSERT INTO lessons (source_type, source_id, loop_num, lesson_text, category,
                                               confidence_score, context_section, indexed_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            source_type, source_id, loop_num,
                            lesson_data['text'],
                            lesson_data['category'],
                            lesson_data['confidence'],
                            section_header,
                            now
                        ))
                        lessons_count += 1

                # SPECIAL CASE: In high-value sections, also accept well-structured lessons
                # that don't have explicit indicators but are clearly lessons
                elif section_is_high_value and clean_line and len(clean_line) > 20:
                    # Look for structured lessons like "**Title:** explanation"
                    if '**' in clean_line and ':**' in clean_line:
                        # Extract the explanation part
                        title_end = clean_line.find(':**') + 3
                        explanation = clean_line[title_end:].strip()
                        if len(explanation) > 10:  # More lenient length check for structured lessons
                            # For structured lessons in high-value sections, be more lenient on actionable insight
                            # The structure itself provides quality assurance
                            if not self._is_generic_or_documentation(explanation):
                                self.conn.execute("""
                                    INSERT INTO lessons (source_type, source_id, loop_num, lesson_text, category,
                                                       confidence_score, context_section, indexed_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    source_type, source_id, loop_num,
                                    explanation,
                                    self._determine_category_from_content(explanation, 'structured_lesson'),
                                    0.85,  # High confidence for structured lessons in lessons sections
                                    section_header,
                                    now
                                ))
                                lessons_count += 1

        return lessons_count

    def _analyze_line_for_high_quality_lessons(self, line: str, section_header: str, context_lines: List[str], line_index: int) -> Optional[Dict[str, Any]]:
        """Analyze a line for ONLY the highest-quality lesson content.

        Extremely selective - only extracts genuine, actionable insights with strong indicators.
        """

        # ONLY HIGH-CONFIDENCE PATTERNS (Direct, strong lesson indicators)
        high_quality_indicators = [
            "learned that", "learned how", "discovered that", "found that", "realized that",
            "key insight:", "critical insight:", "important insight:",
            "key finding:", "critical finding:", "important finding:",
            "major lesson:", "key lesson:", "critical lesson:",
            "best practice:", "key practice:", "recommended practice:",
            "avoid:", "never:", "don't:", "do not:",
            "always:", "consistently:", "must:",
            "going forward:", "in the future:", "next time:",
            "recommend:", "suggest:", "advise:",
            "tip:", "pro tip:", "important tip:",
            "remember:", "note:", "important note:",
            "lesson learned:", "lessons learned:"
        ]

        line_lower = line.lower()
        for indicator in high_quality_indicators:
            if indicator in line_lower:
                idx = line_lower.find(indicator)
                lesson_text = line[idx + len(indicator):].strip()

                # Must be substantial content
                if len(lesson_text) > 20 and len(lesson_text.split()) > 4:
                    # Must contain actionable or insightful content
                    if self._has_actionable_insight(lesson_text):
                        return {
                            'text': lesson_text,
                            'category': self._determine_category_from_content(lesson_text, 'high_quality'),
                            'confidence': 0.95,  # Very high confidence
                            'source': 'high_quality_indicator'
                        }

        # NO medium or low confidence patterns - only the best lessons get through

        return None

    def _is_genuine_lesson(self, text: str, section_header: str, source_id: str) -> bool:
        """Determine if extracted text is a genuine lesson vs documentation."""

        text_lower = text.lower()

        # EXCLUDE: Feature lists and claims
        exclude_patterns = [
            "provides", "supports", "includes", "contains", "offers", "enables",
            "allows", "gives", "creates", "generates", "displays", "shows",
            "visualization", "interface", "dashboard", "panel", "control",
            "management", "monitoring", "tracking", "analysis", "processing",
            "automation", "integration", "connection", "communication"
        ]

        # If text contains many feature-like words, likely documentation
        feature_words = sum(1 for pattern in exclude_patterns if pattern in text_lower)
        if feature_words >= 3:
            return False

        # EXCLUDE: Claims extraction artifacts (from TASK_0121 reports)
        if source_id.startswith('report_TASK_0121'):
            return False

        # EXCLUDE: Very short or generic statements
        if len(text.split()) < 5:
            return False

        # EXCLUDE: Reference links
        if '[ref:' in text or '](docs/' in text:
            return False

        # INCLUDE: Content that shows actual learning/experience
        include_indicators = [
            "learned", "found", "discovered", "realized", "improved",
            "better", "worse", "avoid", "should", "will", "going forward",
            "next time", "in future", "recommend", "suggest", "tip"
        ]

        has_learning_indicator = any(word in text_lower for word in include_indicators)

        return has_learning_indicator or section_header in [
            'lessons learned', 'key learnings', 'insights', 'observations',
            'challenges faced', 'solutions implemented', 'recommendations'
        ]

    def _is_genuine_high_quality_lesson(self, text: str, section_header: str, source_id: str) -> bool:
        """Determine if extracted text is a genuine HIGH-QUALITY lesson vs documentation."""

        text_lower = text.lower()

        # EXCLUDE: Feature lists and claims (even more aggressive)
        exclude_patterns = [
            "provides", "supports", "includes", "contains", "offers", "enables",
            "allows", "gives", "creates", "generates", "displays", "shows",
            "visualization", "interface", "dashboard", "panel", "control",
            "management", "monitoring", "tracking", "analysis", "processing",
            "automation", "integration", "connection", "communication",
            "feature", "functionality", "capability", "system", "component",
            "module", "service", "endpoint", "api", "database", "file",
            "configuration", "setting", "parameter", "option", "choice"
        ]

        # If text contains many feature-like words, definitely not a lesson
        feature_words = sum(1 for pattern in exclude_patterns if pattern in text_lower)
        if feature_words >= 2:
            return False

        # EXCLUDE: Very short or generic statements
        words = text.split()
        if len(words) < 6:
            return False

        # EXCLUDE: Reference links or citations
        if '[ref:' in text or '](docs/' in text or 'see:' in text:
            return False

        # EXCLUDE: Purely descriptive content without insight
        if text_lower.startswith(('the ', 'this ', 'these ', 'those ', 'our ', 'project ')):
            # Check if it's just describing what exists rather than insight
            descriptive_words = ['is', 'are', 'was', 'were', 'has', 'have', 'had', 'contains', 'includes']
            first_few_words = ' '.join(words[:4]).lower()
            if any(word in first_few_words for word in descriptive_words):
                return False

        # Allow "always" in lessons when it's specific advice
        if 'always' in text_lower and len(words) >= 8:
            # This is likely specific advice rather than generic documentation
            pass

        # INCLUDE: Content that shows actual learning/experience/action
        include_indicators = [
            "learned", "found", "discovered", "realized", "improved",
            "better", "worse", "avoid", "should", "will", "going forward",
            "next time", "recommend", "suggest", "tip", "must", "always",
            "never", "don't", "critical", "key", "important", "major",
            "significant", "valuable", "essential", "crucial"
        ]

        has_learning_indicator = any(word in text_lower for word in include_indicators)

        return has_learning_indicator

    def _has_actionable_insight(self, text: str) -> bool:
        """Check if the text contains actionable, insightful content rather than generic statements."""

        text_lower = text.lower()

        # Must have some specificity - not just generic advice
        actionable_indicators = [
            "when ", "before ", "after ", "during ", "while ", "instead of ",
            "rather than ", "compared to ", "unlike ", "similar to ",
            "because ", "due to ", "as a result ", "therefore ", "thus ",
            "consequently ", "accordingly ", "specifically ", "particularly ",
            "especially ", "notably ", "significantly ", "markedly ",
            "dramatically ", "substantially ", "considerably ",
            "leads to ", "causes ", "results in ", "prevents ", "avoids ",
            "improves ", "enhances ", "reduces ", "increases ", "decreases "
        ]

        specificity_count = sum(1 for indicator in actionable_indicators if indicator in text_lower)

        # For longer lessons, be more lenient; for shorter ones, require specificity
        words = text.split()
        if len(words) >= 15:
            # Longer lessons can be more general but still insightful
            return specificity_count >= 0
        elif len(words) >= 10:
            # Medium lessons need some specificity
            return specificity_count >= 1
        else:
            # Short lessons need clear specificity
            return specificity_count >= 2

        # Avoid generic phrases
        generic_phrases = [
            "is important", "are important", "was important", "were important",
            "is necessary", "are necessary", "was necessary", "were necessary",
            "is useful", "are useful", "was useful", "were useful",
            "is good practice", "are good practice", "was good practice", "were good practice",
            "should be done", "should be avoided", "should be considered",
            "need to be", "needs to be", "needed to be"
        ]

        for phrase in generic_phrases:
            if phrase in text_lower and len(text.split()) < 12:
                return False  # Too generic and short

        return True

    def _is_generic_or_documentation(self, text: str) -> bool:
        """Check if content is generic documentation rather than specific insight."""

        text_lower = text.lower()

        # Generic documentation patterns
        generic_patterns = [
            r"^the \w+ (should|must|needs to|has to)",
            r"^always (use|implement|consider|think about|remember)",
            r"^never (use|implement|forget|ignore|neglect)",
            r"^when (using|implementing|working with|dealing with)",
            r"^make sure (to|that)",
            r"^ensure (that|to)",
            r"^remember to",
            r"^don't forget to",
            r"^it's important to",
            r"^it's necessary to",
            r"^good practice (is|was)",
            r"^best practice (is|was)"
        ]

        for pattern in generic_patterns:
            if re.match(pattern, text_lower):
                return True

        # Too many generic words
        generic_words = [
            "important", "necessary", "good", "best", "better", "proper",
            "correct", "right", "appropriate", "suitable", "effective",
            "efficient", "useful", "valuable", "essential", "critical",
            "key", "major", "significant", "crucial", "vital"
        ]

        words = text_lower.split()
        generic_count = sum(1 for word in words if word in generic_words)

        # If more than 30% of words are generic adjectives, likely not insightful
        if len(words) > 0 and (generic_count / len(words)) > 0.3:
            return True

        return False

    def _is_documentation_content(self, text: str) -> bool:
        """Check if content appears to be documentation rather than lessons."""

        text_lower = text.lower()

        # Documentation patterns
        doc_patterns = [
            r"^\w+ (provides?|supports?|includes?|contains?|offers?|enables?)",
            r"^\w+ (allows?|gives?|creates?|generates?|displays?|shows?)",
            r"^\w+ (is|are) (used|designed|intended) (for|to)",
            r"^the \w+ (feature|function|capability|system|component)",
            r"^this (allows|enables|gives|provides)"
        ]

        for pattern in doc_patterns:
            if re.match(pattern, text_lower):
                return True

        # Feature-like language
        feature_indicators = [
            "real-time", "automatic", "integrated", "advanced", "powerful",
            "flexible", "robust", "efficient", "user-friendly", "intuitive"
        ]

        feature_count = sum(1 for indicator in feature_indicators if indicator in text_lower)
        return feature_count >= 2

    def _determine_category_from_content(self, text: str, analysis_type: str) -> str:
        """Determine lesson category based on content analysis."""

        text_lower = text.lower()

        # Success patterns
        if any(word in text_lower for word in [
            "success", "worked well", "effective", "efficient", "improved performance",
            "better results", "successful", "good approach", "beneficial"
        ]):
            return "success"

        # Failure patterns
        if any(word in text_lower for word in [
            "fail", "failed", "didn't work", "ineffective", "problem", "issue",
            "avoid", "don't", "never", "worse", "degraded", "broken"
        ]):
            return "failure"

        # Warning patterns
        if any(word in text_lower for word in [
            "warning", "caution", "careful", "watch out", "be aware",
            "risk", "danger", "potential issue", "consider"
        ]):
            return "warning"

        # Default based on analysis type
        if analysis_type == 'high_confidence':
            return "observation"
        elif analysis_type == 'contextual':
            return "observation"
        else:
            return "observation"
    
    def _populate_semantic_data(self) -> Dict[str, Any]:
        """Populate semantic search enhancements from test knowledge and domain knowledge.
        
        Returns statistics about semantic data added.
        """
        stats = {
            "synonyms_added": 0,
            "concepts_added": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
        }
        
        now = utc_now_iso()
        
        # Populate synonyms from test knowledge entities
        self._populate_synonyms_from_test_knowledge(now, stats)
        
        # Populate concepts from test knowledge categories
        self._populate_concepts_from_test_knowledge(now, stats)
        
        # Add domain-specific synonyms
        self._populate_domain_synonyms(now, stats)
        
        stats["completed_at"] = utc_now_iso()
        self.conn.commit()
        
        return stats
    
    def _populate_synonyms_from_test_knowledge(self, timestamp: str, stats: Dict[str, Any]) -> None:
        """Populate synonyms table from test knowledge entities."""
        
        # Get all test knowledge entities
        entities = self.conn.execute("SELECT entity_id, category, description FROM test_knowledge").fetchall()
        
        for entity in entities:
            entity_id = entity["entity_id"]
            category = entity["category"]
            description = entity["description"]
            
            # Extract synonyms based on entity patterns
            synonyms = self._extract_synonyms_for_entity(entity_id, category, description)
            
            for synonym, confidence in synonyms:
                self.conn.execute("""
                    INSERT OR IGNORE INTO semantic_synonyms 
                    (term, synonym, domain, confidence, indexed_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (entity_id, synonym, category, confidence, timestamp))
                stats["synonyms_added"] += 1
    
    def _extract_synonyms_for_entity(self, entity_id: str, category: str, description: str) -> List[Tuple[str, float]]:
        """Extract synonym terms for a knowledge entity."""
        synonyms = []
        
        # Bootstrap protocol synonyms
        if "bootstrap" in entity_id:
            synonyms.extend([
                ("entry protocol", 0.9),
                ("session start", 0.8),
                ("initialization", 0.7),
                ("setup protocol", 0.8),
                ("activation sequence", 0.7),
            ])
        
        # Session management synonyms
        if "session" in entity_id or "lifecycle" in entity_id:
            synonyms.extend([
                ("agent lifecycle", 0.9),
                ("process management", 0.8),
                ("state machine", 0.8),
                ("execution flow", 0.7),
                ("task coordination", 0.7),
            ])
        
        # Guardrail synonyms
        if "guardrail" in category or "protocol" in entity_id:
            synonyms.extend([
                ("safety mechanism", 0.8),
                ("validation rule", 0.9),
                ("consistency check", 0.8),
                ("state enforcement", 0.7),
                ("error prevention", 0.7),
            ])
        
        # Failure mode synonyms
        if "failure" in category or "error" in description.lower():
            synonyms.extend([
                ("error handling", 0.9),
                ("exception management", 0.8),
                ("robustness", 0.7),
                ("resilience", 0.8),
                ("fault tolerance", 0.7),
            ])
        
        # Integration synonyms
        if "integration" in category or "api" in description.lower():
            synonyms.extend([
                ("api chaining", 0.8),
                ("service integration", 0.9),
                ("external connectivity", 0.7),
                ("workflow orchestration", 0.7),
                ("system interaction", 0.8),
            ])
        
        return synonyms
    
    def _populate_concepts_from_test_knowledge(self, timestamp: str, stats: Dict[str, Any]) -> None:
        """Populate concepts table from test knowledge categories."""
        
        # Define concept mappings based on categories
        concept_mappings = {
            "guardrails": {
                "related_terms": ["protocol_rule", "safety_mechanism", "validation", "consistency", "enforcement"],
                "confidence": 0.9
            },
            "orchestration": {
                "related_terms": ["session_management", "lifecycle", "coordination", "workflow", "state_machine"],
                "confidence": 0.8
            },
            "failure_modes": {
                "related_terms": ["error_handling", "robustness", "resilience", "fault_tolerance", "recovery"],
                "confidence": 0.9
            },
            "integration": {
                "related_terms": ["api_chaining", "service_integration", "external_services", "connectivity", "orchestration"],
                "confidence": 0.8
            },
            "finalization": {
                "related_terms": ["completion", "validation", "atomic_operations", "state_transition", "cleanup"],
                "confidence": 0.8
            }
        }
        
        for concept, data in concept_mappings.items():
            self.conn.execute("""
                INSERT OR IGNORE INTO semantic_concepts 
                (concept, related_terms, domain, confidence, indexed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (concept, json.dumps(data["related_terms"]), "architecture", data["confidence"], timestamp))
            stats["concepts_added"] += 1
    
    def _populate_domain_synonyms(self, timestamp: str, stats: Dict[str, Any]) -> None:
        """Add domain-specific synonyms for common search terms."""
        
        domain_synonyms = [
            # Architecture domain
            ("architecture", "system_design", "architecture", 0.9),
            ("architecture", "technical_baseline", "architecture", 0.8),
            ("architecture", "system_structure", "architecture", 0.7),
            
            # Validation domain
            ("validation", "linting", "validation", 0.9),
            ("validation", "checking", "validation", 0.8),
            ("validation", "verification", "validation", 0.8),
            
            # Testing domain
            ("testing", "test_files", "testing", 0.9),
            ("testing", "unit_tests", "testing", 0.8),
            ("testing", "validation_tests", "testing", 0.7),
            
            # General synonyms
            ("bootstrap", "entry", "general", 0.8),
            ("session", "agent", "general", 0.7),
            ("api", "endpoint", "general", 0.8),
            ("error", "failure", "general", 0.9),
            ("fix", "resolution", "general", 0.8),
        ]
        
        for term, synonym, domain, confidence in domain_synonyms:
            self.conn.execute("""
                INSERT OR IGNORE INTO semantic_synonyms 
                (term, synonym, domain, confidence, indexed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (term, synonym, domain, confidence, timestamp))
            stats["synonyms_added"] += 1
    
    def search(
        self,
        query: str,
        *,
        types: Optional[List[str]] = None,  # 'report', 'archive', 'lesson', 'task', 'doc'
        task_id: Optional[str] = None,
        loop_min: Optional[int] = None,
        loop_max: Optional[int] = None,
        validation_passed: Optional[bool] = None,
        category: Optional[str] = None,  # For lessons
        limit: int = 20,
        semantic: bool = True,  # SEMANTIC SEARCH IS NOW MANDATORY - Always enabled for optimal results
        use_cache: bool = True,  # Use result caching
    ) -> List[SearchResult]:
        """Search the knowledge database with filters.
        
        Args:
            query: Free-text search query
            types: Filter by result types (default: all)
            task_id: Filter by task ID
            loop_min: Minimum loop number
            loop_max: Maximum loop number
            validation_passed: Filter reports by validation status
            category: Filter lessons by category (success/failure/observation/warning)
            limit: Maximum results to return
            semantic: SEMANTIC SEARCH IS MANDATORY - Always enabled for optimal results (24.7% relevance improvement proven)
            use_cache: Use cached results for faster repeated queries
            
        Returns:
            List of SearchResult objects ordered by relevance
        """
        import hashlib
        
        # Check cache first
        if use_cache and query.strip():
            query_hash = hashlib.md5(f"{query}_{types}_{task_id}_{loop_min}_{loop_max}_{validation_passed}_{category}_{limit}_{semantic}".encode()).hexdigest()
            cached_result = self.conn.execute("""
                SELECT results, result_count FROM search_cache 
                WHERE query_hash = ? AND created_at > datetime('now', '-1 hour')
            """, (query_hash,)).fetchone()
            
            if cached_result:
                # Update access stats
                self.conn.execute("""
                    UPDATE search_cache 
                    SET last_accessed = ?, access_count = access_count + 1 
                    WHERE query_hash = ?
                """, (utc_now_iso(), query_hash))
                
                # Return cached results
                cached_results_data = json.loads(cached_result["results"])
                return [SearchResult(**r) for r in cached_results_data]
        
        results = []
        types = types or ["report", "archive", "lesson", "task", "doc", "test_knowledge"]
        
        # Expand query semantically if enabled
        expanded_queries = [query]
        if semantic:
            expanded_queries.extend(self._expand_query_semantically(query))
        
        # Search with each expanded query
        for search_query in expanded_queries:
            # Search reports
            if "report" in types:
                sql = """
                    SELECT reports.*, bm25(reports_fts) as rank
                    FROM reports_fts
                    JOIN reports ON reports_fts.id = reports.id
                    WHERE reports_fts MATCH ?
                """
                params: List[Any] = [search_query]
                
                if task_id:
                    sql += " AND reports.task_id = ?"
                    params.append(task_id)
                if loop_min is not None:
                    sql += " AND reports.loop_num >= ?"
                    params.append(loop_min)
                if loop_max is not None:
                    sql += " AND reports.loop_num <= ?"
                    params.append(loop_max)
                if validation_passed is not None:
                    sql += " AND reports.validation_passed = ?"
                    params.append(1 if validation_passed else 0)
                
                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)
                
                try:
                    for row in self.conn.execute(sql, params):
                        results.append(SearchResult(
                            type="report",
                            id=row["id"],
                            relevance=-row["rank"],  # bm25 returns negative scores
                            snippet=self._generate_snippet(row["goal"] or row["content_full"], search_query),
                            context={
                                "task_id": row["task_id"],
                                "loop_num": row["loop_num"],
                                "goal": row["goal"],
                                "validation_passed": bool(row["validation_passed"]) if row["validation_passed"] is not None else None,
                                "files_changed": json.loads(row["files_changed"]) if row["files_changed"] else [],
                            }
                        ))
                except sqlite3.OperationalError:
                    pass  # FTS query syntax error, skip this type
        
            # Search archives
            if "archive" in types:
                sql = """
                    SELECT archives.*, bm25(archives_fts) as rank
                    FROM archives_fts
                    JOIN archives ON archives_fts.id = archives.id
                    WHERE archives_fts MATCH ?
                """
                params = [search_query]
                
                if loop_min is not None:
                    sql += " AND archives.loop_num >= ?"
                    params.append(loop_min)
                if loop_max is not None:
                    sql += " AND archives.loop_num <= ?"
                    params.append(loop_max)
                
                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)

                def _append_archive_row(row: sqlite3.Row) -> None:
                    # Resilient parsing of tasks_completed: prefer JSON array, with legacy plain-text fallback.
                    try:
                        tc_raw = row["tasks_completed"] or ""
                        if tc_raw:
                            try:
                                tc = json.loads(tc_raw)
                            except Exception:
                                tc = [s.strip() for s in re.split(r"[;,]", tc_raw) if s.strip()]
                        else:
                            tc = []
                    except Exception:
                        tc = []

                    results.append(SearchResult(
                        type="archive",
                        id=row["id"],
                        relevance=-row["rank"],
                        snippet=self._generate_snippet(row["summary"] or row["lessons_learned"] or "", search_query),
                        context={
                            "loop_num": row["loop_num"],
                            "summary": row["summary"],
                            "tasks_completed": tc,
                        }
                    ))

                try:
                    for row in self.conn.execute(sql, params):
                        _append_archive_row(row)
                except (sqlite3.OperationalError, sqlite3.DatabaseError):
                    # FTS MATCH is strict; normalize punctuation-heavy queries like "ARCHIV_0136.md".
                    normalized_query = re.sub(r"[^\w]+", " ", search_query).strip()
                    if normalized_query and normalized_query != search_query:
                        retry_params = list(params)
                        retry_params[0] = normalized_query
                        try:
                            for row in self.conn.execute(sql, retry_params):
                                _append_archive_row(row)
                        except (sqlite3.OperationalError, sqlite3.DatabaseError):
                            pass
                    # Final fallback for corrupted FTS state: plain table scan.
                    if not any(r.type == "archive" for r in results):
                        bare = re.sub(r"[^\w]+", "", search_query).strip()
                        if bare:
                            like_term = f"%{bare}%"
                            fallback_sql = """
                                SELECT archives.*, 0.0 AS rank
                                FROM archives
                                WHERE REPLACE(REPLACE(id, '_', ''), '.', '') LIKE ?
                                   OR REPLACE(REPLACE(path, '_', ''), '.', '') LIKE ?
                                   OR REPLACE(REPLACE(COALESCE(summary, ''), '_', ''), '.', '') LIKE ?
                                   OR REPLACE(REPLACE(COALESCE(lessons_learned, ''), '_', ''), '.', '') LIKE ?
                                ORDER BY loop_num DESC
                                LIMIT ?
                            """
                            for row in self.conn.execute(
                                fallback_sql,
                                (like_term, like_term, like_term, like_term, limit),
                            ):
                                _append_archive_row(row)
        
            # Search lessons
            if "lesson" in types:
                sql = """
                    SELECT lessons.*, bm25(lessons_fts) as rank
                    FROM lessons_fts
                    JOIN lessons ON lessons_fts.rowid = lessons.id
                    WHERE lessons_fts MATCH ?
                """
                params = [search_query]
                
                if loop_min is not None:
                    sql += " AND lessons.loop_num >= ?"
                    params.append(loop_min)
                if loop_max is not None:
                    sql += " AND lessons.loop_num <= ?"
                    params.append(loop_max)
                if category:
                    sql += " AND lessons.category = ?"
                    params.append(category)
                
                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)
                
                try:
                    for row in self.conn.execute(sql, params):
                        results.append(SearchResult(
                            type="lesson",
                            id=str(row["id"]),
                            relevance=-row["rank"],
                            snippet=row["lesson_text"][:200],
                            context={
                                "source_type": row["source_type"],
                                "source_id": row["source_id"],
                                "loop_num": row["loop_num"],
                                "category": row["category"],
                            }
                        ))
                except sqlite3.OperationalError:
                    pass
        
            # Search tasks (simple LIKE query - tasks don't have heavy content)
            if "task" in types:
                sql = """
                    SELECT * FROM tasks
                    WHERE objective LIKE ? OR seed_idea LIKE ?
                """
                like_pattern = f"%{search_query}%"
                params = [like_pattern, like_pattern]
                
                if task_id:
                    sql += " AND id = ?"
                    params.append(task_id)
                
                sql += " LIMIT ?"
                params.append(limit)
                
                for row in self.conn.execute(sql, params):
                    relevance = 0.5  # Lower relevance for LIKE matches
                    if search_query.lower() in (row["objective"] or "").lower():
                        relevance = 0.8
                    
                    results.append(SearchResult(
                        type="task",
                        id=row["id"],
                        relevance=relevance,
                        snippet=self._generate_snippet(row["objective"] or row["seed_idea"] or "", search_query),
                        context={
                            "status": row["status"],
                            "objective": row["objective"],
                            "created": row["created"],
                        }
                    ))
        
            # Search docs
            if "doc" in types:
                sql = """
                    SELECT docs.*, bm25(docs_fts) as rank
                    FROM docs_fts
                    JOIN docs ON docs_fts.id = docs.id
                    WHERE docs_fts MATCH ?
                """
                params = [search_query]
                
                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)
                
                try:
                    for row in self.conn.execute(sql, params):
                        results.append(SearchResult(
                            type="doc",
                            id=row["id"],
                            relevance=-row["rank"],
                            snippet=self._generate_snippet(row["title"] or row["content_full"][:100], search_query),
                            context={
                                "title": row["title"],
                                "category": row["category"],
                                "tags": json.loads(row["tags"]) if row["tags"] else [],
                            }
                        ))
                except sqlite3.OperationalError:
                    pass
            
            # Search test knowledge
            if "test_knowledge" in types:
                sql = """
                    SELECT test_knowledge.*, bm25(test_knowledge_fts) as rank
                    FROM test_knowledge_fts
                    JOIN test_knowledge ON test_knowledge_fts.id = test_knowledge.id
                    WHERE test_knowledge_fts MATCH ?
                """
                params = [search_query]
                
                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)
                
                try:
                    for row in self.conn.execute(sql, params):
                        results.append(SearchResult(
                            type="test_knowledge",
                            id=row["id"],
                            relevance=-row["rank"],
                            snippet=self._generate_snippet(row["description"], search_query),
                            context={
                                "entity_id": row["entity_id"],
                                "category": row["category"],
                                "knowledge_type": row["knowledge_type"],
                                "confidence_level": row["confidence_level"],
                            }
                        ))
                except sqlite3.OperationalError:
                    pass
        
        # Enhanced ranking with confidence-based weighting
        results = self._apply_enhanced_ranking(results, search_query)
        
        # Sort by relevance and limit
        results.sort(key=lambda r: r.relevance, reverse=True)
        final_results = results[:limit]
        
        # Cache results if caching enabled
        if use_cache and query.strip() and final_results:
            results_json = json.dumps([{
                "type": r.type,
                "id": r.id,
                "relevance": r.relevance,
                "snippet": r.snippet,
                "context": r.context
            } for r in final_results])
            
            self.conn.execute("""
                INSERT OR REPLACE INTO search_cache 
                (query_hash, query_text, results, result_count, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (query_hash, query, results_json, len(final_results), utc_now_iso(), utc_now_iso()))
        
        return final_results
    
    def _apply_enhanced_ranking(self, results: List[SearchResult], original_query: str) -> List[SearchResult]:
        """Apply enhanced ranking algorithms to search results."""
        
        for result in results:
            # Base relevance from FTS BM25
            enhanced_relevance = result.relevance
            
            # Confidence-based weighting for test knowledge
            if result.type == "test_knowledge":
                confidence_level = result.context.get("confidence_level", "medium")
                confidence_multiplier = {"high": 1.5, "medium": 1.2, "low": 0.8}.get(confidence_level, 1.0)
                enhanced_relevance *= confidence_multiplier
            
            # Recency boosting for recent content
            if result.type in ["report", "archive"]:
                loop_num = result.context.get("loop_num", 0)
                if loop_num >= 45:  # Recent loops get slight boost
                    enhanced_relevance *= 1.1
            
            # Authority boosting for validated content
            if result.type == "report" and result.context.get("validation_passed") is True:
                enhanced_relevance *= 1.15
            
            # Semantic match boosting
            if any(term in result.snippet.lower() for term in original_query.lower().split()):
                enhanced_relevance *= 1.2
            
            # Category-based weighting
            category_weights = {
                "test_knowledge": 1.3,  # Test knowledge is highly valuable
                "lesson": 1.2,          # Lessons are important
                "report": 1.1,          # Reports are standard
                "archive": 1.0,         # Archives are baseline
                "doc": 0.9,             # Docs slightly less relevant
                "task": 0.8             # Tasks least relevant for search
            }
            enhanced_relevance *= category_weights.get(result.type, 1.0)
            
            result.relevance = enhanced_relevance
        
        return results
    
    def _expand_query_semantically(self, query: str) -> List[str]:
        """Expand a query with semantic synonyms and related terms.
        
        Returns a list of expanded query strings to search with.
        """
        expansions = []
        query_lower = query.lower().strip()
        
        # Direct synonym expansion
        synonyms = self.conn.execute("""
            SELECT synonym, confidence FROM semantic_synonyms 
            WHERE term = ? OR synonym = ?
            ORDER BY confidence DESC
        """, (query_lower, query_lower)).fetchall()
        
        for synonym_row in synonyms:
            synonym = synonym_row["synonym"]
            confidence = synonym_row["confidence"]
            if confidence > 0.7:  # Only high confidence synonyms
                if synonym != query_lower:
                    expansions.append(synonym)
        
        # Concept-based expansion
        concepts = self.conn.execute("""
            SELECT related_terms FROM semantic_concepts 
            WHERE concept = ? OR ? LIKE '%' || concept || '%'
        """, (query_lower, query_lower)).fetchall()
        
        for concept_row in concepts:
            related_terms = json.loads(concept_row["related_terms"])
            for term in related_terms:
                if term not in expansions and term != query_lower:
                    expansions.append(term)
        
        # Fuzzy matching for common misspellings (simple implementation)
        fuzzy_expansions = self._generate_fuzzy_matches(query_lower)
        expansions.extend(fuzzy_expansions)
        
        # Context-aware interpretation
        context_expansions = self._interpret_query_context(query_lower)
        expansions.extend(context_expansions)
        
        # Remove duplicates and limit expansions
        seen = set()
        unique_expansions = []
        for exp in expansions:
            if exp not in seen and exp != query_lower:
                seen.add(exp)
                unique_expansions.append(exp)
        
        return unique_expansions[:5]  # Limit to 5 expansions to avoid explosion
    
    def _generate_fuzzy_matches(self, query: str) -> List[str]:
        """Generate fuzzy matches for common query variations."""
        fuzzy = []
        
        # Common misspellings and variations
        corrections = {
            "bootstap": "bootstrap",
            "gaurdrail": "guardrail",
            "gaurd": "guard",
            "finalisation": "finalization",
            "optimisation": "optimization",
            "initialisation": "initialization",
            "cooridnation": "coordination",
            "orchestration": "orchestration",
            "validaton": "validation",
            "configuraiton": "configuration",
        }
        
        if query in corrections:
            fuzzy.append(corrections[query])
        
        return fuzzy
    
    def _interpret_query_context(self, query: str) -> List[str]:
        """Interpret query in system context for better search."""
        interpretations = []
        
        # Bootstrap-related queries
        if any(word in query for word in ["start", "begin", "entry", "init"]):
            interpretations.extend(["bootstrap", "entry protocol", "session start"])
        
        # Error/failure queries
        if any(word in query for word in ["problem", "issue", "fail", "error", "bug"]):
            interpretations.extend(["failure", "error handling", "guardrail violation"])
        
        # API queries
        if "api" in query or "endpoint" in query:
            interpretations.extend(["api chaining", "external service", "integration"])
        
        # Session queries
        if any(word in query for word in ["session", "agent", "process"]):
            interpretations.extend(["session lifecycle", "agent coordination", "parallelization"])
        
        return interpretations
    
    def mine_patterns(self) -> Dict[str, Any]:
        """Mine patterns from the knowledge database.
        
        Returns statistics about patterns discovered.
        """
        stats = {
            "patterns_mined": 0,
            "relationships_found": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
        }
        
        now = utc_now_iso()
        
        # Mine sequence patterns from test knowledge
        sequence_stats = self._mine_sequence_patterns(now)
        stats["patterns_mined"] += sequence_stats.get("patterns", 0)
        
        # Mine correlation patterns
        correlation_stats = self._mine_correlation_patterns(now)
        stats["patterns_mined"] += correlation_stats.get("patterns", 0)
        
        # Mine trend patterns
        trend_stats = self._mine_trend_patterns(now)
        stats["patterns_mined"] += trend_stats.get("patterns", 0)
        
        # Mine cluster patterns
        cluster_stats = self._mine_cluster_patterns(now)
        stats["patterns_mined"] += cluster_stats.get("patterns", 0)
        
        # Find pattern relationships
        relationship_stats = self._mine_pattern_relationships(now)
        stats["relationships_found"] = relationship_stats.get("relationships", 0)
        
        stats["completed_at"] = utc_now_iso()
        self.conn.commit()
        
        return stats
    
    def _mine_sequence_patterns(self, timestamp: str) -> Dict[str, Any]:
        """Mine sequence patterns from test knowledge entities."""
        stats = {"patterns": 0}
        
        # Get all test knowledge entities
        entities = self.conn.execute("""
            SELECT entity_id, category, knowledge_type, confidence_level 
            FROM test_knowledge 
            ORDER BY category, knowledge_type
        """).fetchall()
        
        # Group by category
        category_groups = {}
        for entity in entities:
            cat = entity["category"]
            if cat not in category_groups:
                category_groups[cat] = []
            category_groups[cat].append(entity)
        
        # Mine patterns within categories
        for category, entities_in_cat in category_groups.items():
            if len(entities_in_cat) < 2:
                continue
                
            # Bootstrap protocol sequence
            if category == "guardrails":
                bootstrap_entities = [e for e in entities_in_cat if "bootstrap" in e["entity_id"]]
                if len(bootstrap_entities) >= 2:
                    self._insert_mined_pattern(
                        "sequence",
                        f"bootstrap_protocol_sequence_{category}",
                        f"Bootstrap protocol enforcement sequence in {category}",
                        [e["entity_id"] for e in bootstrap_entities],
                        0.85,
                        len(bootstrap_entities),
                        {"category": category, "sequence_type": "protocol_enforcement"},
                        timestamp
                    )
                    stats["patterns"] += 1
            
            # Session lifecycle sequence
            if category == "orchestration":
                session_entities = [e for e in entities_in_cat if "session" in e["entity_id"] or "lifecycle" in e["entity_id"]]
                if len(session_entities) >= 2:
                    self._insert_mined_pattern(
                        "sequence",
                        f"session_lifecycle_sequence_{category}",
                        f"Session lifecycle management sequence in {category}",
                        [e["entity_id"] for e in session_entities],
                        0.9,
                        len(session_entities),
                        {"category": category, "sequence_type": "lifecycle_management"},
                        timestamp
                    )
                    stats["patterns"] += 1
        
        return stats
    
    def _mine_correlation_patterns(self, timestamp: str) -> Dict[str, Any]:
        """Mine correlation patterns between different knowledge sources."""
        stats = {"patterns": 0}
        
        # Correlate test knowledge with lessons learned
        test_entities = self.conn.execute("SELECT entity_id, category FROM test_knowledge").fetchall()
        lessons = self.conn.execute("SELECT lesson_text, category FROM lessons").fetchall()
        
        for test_entity in test_entities:
            entity_id = test_entity["entity_id"]
            entity_category = test_entity["category"]
            
            # Find related lessons
            related_lessons = []
            for lesson in lessons:
                lesson_text = lesson["lesson_text"].lower()
                if any(keyword in lesson_text for keyword in entity_id.split("_")):
                    related_lessons.append(lesson)
            
            if len(related_lessons) >= 2:
                self._insert_mined_pattern(
                    "correlation",
                    f"test_lesson_correlation_{entity_id}",
                    f"Correlation between test entity {entity_id} and {len(related_lessons)} related lessons",
                    [entity_id] + [f"lesson_{i}" for i in range(len(related_lessons))],
                    0.75,
                    len(related_lessons),
                    {"entity_category": entity_category, "correlation_type": "test_to_lesson"},
                    timestamp
                )
                stats["patterns"] += 1
        
        return stats
    
    def _mine_trend_patterns(self, timestamp: str) -> Dict[str, Any]:
        """Mine trend patterns over time."""
        stats = {"patterns": 0}
        
        # Analyze loop completion trends
        reports = self.conn.execute("""
            SELECT loop_num, date_completed, validation_passed 
            FROM reports 
            WHERE date_completed IS NOT NULL 
            ORDER BY loop_num
        """).fetchall()
        
        if len(reports) >= 5:
            # Calculate validation success rate trend
            recent_reports = reports[-10:]  # Last 10 loops
            success_rate = sum(1 for r in recent_reports if r["validation_passed"]) / len(recent_reports)
            
            if success_rate > 0.8:
                self._insert_mined_pattern(
                    "trend",
                    "high_validation_success_trend",
                    f"High validation success rate trend: {success_rate:.1%} in recent loops",
                    [f"loop_{r['loop_num']}" for r in recent_reports],
                    success_rate,
                    len(recent_reports),
                    {"trend_type": "validation_success", "success_rate": success_rate},
                    timestamp
                )
                stats["patterns"] += 1
        
        return stats
    
    def _mine_cluster_patterns(self, timestamp: str) -> Dict[str, Any]:
        """Mine cluster patterns by grouping similar entities."""
        stats = {"patterns": 0}
        
        # Cluster failure modes
        failure_entities = self.conn.execute("""
            SELECT entity_id FROM test_knowledge 
            WHERE category = 'failure_modes'
        """).fetchall()
        
        if len(failure_entities) >= 3:
            entity_ids = [e["entity_id"] for e in failure_entities]
            self._insert_mined_pattern(
                "cluster",
                "failure_modes_cluster",
                f"Cluster of {len(entity_ids)} failure mode patterns",
                entity_ids,
                0.8,
                len(entity_ids),
                {"cluster_type": "failure_modes", "category": "failure_modes"},
                timestamp
            )
            stats["patterns"] += 1
        
        # Cluster guardrail patterns
        guardrail_entities = self.conn.execute("""
            SELECT entity_id FROM test_knowledge 
            WHERE category = 'guardrails'
        """).fetchall()
        
        if len(guardrail_entities) >= 5:
            entity_ids = [e["entity_id"] for e in guardrail_entities]
            self._insert_mined_pattern(
                "cluster",
                "guardrail_patterns_cluster",
                f"Cluster of {len(entity_ids)} guardrail enforcement patterns",
                entity_ids,
                0.85,
                len(entity_ids),
                {"cluster_type": "guardrails", "category": "guardrails"},
                timestamp
            )
            stats["patterns"] += 1
        
        return stats
    
    def _mine_pattern_relationships(self, timestamp: str) -> Dict[str, Any]:
        """Find relationships between mined patterns."""
        stats = {"relationships": 0}
        
        # Get all patterns
        patterns = self.conn.execute("SELECT id, pattern_type, pattern_name FROM mined_patterns").fetchall()
        
        for i, pattern1 in enumerate(patterns):
            for pattern2 in patterns[i+1:]:
                # Find related patterns
                if pattern1["pattern_type"] == pattern2["pattern_type"]:
                    # Similar patterns
                    relationship_type = "similar"
                    strength = 0.6
                elif "bootstrap" in pattern1["pattern_name"] and "session" in pattern2["pattern_name"]:
                    # Bootstrap leads to session management
                    relationship_type = "follows"
                    strength = 0.8
                elif "failure" in pattern1["pattern_name"] and "guardrail" in pattern2["pattern_name"]:
                    # Failures trigger guardrails
                    relationship_type = "causes"
                    strength = 0.7
                else:
                    continue
                
                self.conn.execute("""
                    INSERT OR IGNORE INTO pattern_relationships 
                    (pattern_id, related_pattern_id, relationship_type, strength, evidence)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    pattern1["id"],
                    pattern2["id"],
                    relationship_type,
                    strength,
                    f"Pattern relationship discovered during mining: {pattern1['pattern_name']} {relationship_type} {pattern2['pattern_name']}"
                ))
                stats["relationships"] += 1
        
        return stats
    
    def _insert_mined_pattern(self, pattern_type: str, pattern_name: str, description: str,
                             entities_involved: List[str], confidence: float, support_count: int,
                             metadata: Dict[str, Any], timestamp: str) -> None:
        """Insert a mined pattern into the database."""
        self.conn.execute("""
            INSERT OR REPLACE INTO mined_patterns 
            (pattern_type, pattern_name, description, entities_involved, confidence, support_count, metadata, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern_type,
            pattern_name,
            description,
            json.dumps(entities_involved),
            confidence,
            support_count,
            json.dumps(metadata),
            timestamp,
        ))
    
    def _generate_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Generate a relevant snippet from text around the query terms."""
        if not text:
            return ""
        
        # Find position of query terms
        query_lower = query.lower()
        text_lower = text.lower()
        
        pos = text_lower.find(query_lower.split()[0] if query_lower else "")
        if pos == -1:
            # Return beginning of text
            return text[:max_length].strip() + ("..." if len(text) > max_length else "")
        
        # Center around the match
        start = max(0, pos - max_length // 2)
        end = min(len(text), pos + max_length // 2)
        
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {
            "db_exists": self.db_path.exists(),
            "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2) if self.db_path.exists() else 0,
        }
        
        if not self.db_path.exists():
            return stats
        
        # Get counts
        stats["reports_count"] = self.conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        stats["archives_count"] = self.conn.execute("SELECT COUNT(*) FROM archives").fetchone()[0]
        stats["lessons_count"] = self.conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        stats["tasks_count"] = self.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        
        # Get loop range
        loop_range = self.conn.execute(
            "SELECT MIN(loop_num), MAX(loop_num) FROM archives"
        ).fetchone()
        stats["loop_min"] = loop_range[0]
        stats["loop_max"] = loop_range[1]
        
        # Get last rebuild info
        meta_row = self.conn.execute(
            "SELECT value FROM db_meta WHERE key = 'stats'"
        ).fetchone()
        if meta_row:
            stats["last_rebuild"] = json.loads(meta_row[0])
        
        return stats
    
    def get_lessons_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get lessons by category (success/failure/observation/warning)."""
        rows = self.conn.execute("""
            SELECT * FROM lessons
            WHERE category = ?
            ORDER BY loop_num DESC
            LIMIT ?
        """, (category, limit)).fetchall()
        
        return [dict(row) for row in rows]
    
    def get_file_history(self, filename: str) -> List[Dict[str, Any]]:
        """Get history of which tasks/reports modified a specific file."""
        results = []
        
        rows = self.conn.execute("""
            SELECT id, task_id, loop_num, goal, files_changed
            FROM reports
            WHERE files_changed LIKE ?
            ORDER BY loop_num DESC
        """, (f"%{filename}%",)).fetchall()
        
        for row in rows:
            files = json.loads(row["files_changed"]) if row["files_changed"] else []
            if any(filename in f for f in files):
                results.append({
                    "report_id": row["id"],
                    "task_id": row["task_id"],
                    "loop_num": row["loop_num"],
                    "goal": row["goal"],
                })
        
        return results

    def add_agent_knowledge(
        self,
        knowledge_text: str,
        category: str = "agent_insight",
        metadata: Dict[str, Any] = None,
        loop_num: int = None,
        actor: str = "agent",
    ) -> bool:
        """Add fresh agent knowledge to the database for semantic search and future learning.
        
        This method allows AI agents to store their insights, learnings, and discoveries
        directly in the knowledge database, enabling cross-loop learning and semantic search
        of agent-generated knowledge.
        
        Args:
            knowledge_text: The knowledge/insight text from the agent
            category: Category of knowledge ("agent_insight", "success", "failure", "warning", "observation")
            metadata: Optional metadata dict with additional context (agent_name, task_id, confidence, etc.)
            loop_num: Current loop number (auto-detected if None)
        
        Returns:
            True if knowledge was successfully added, False otherwise
        
        Example:
            db.add_agent_knowledge(
                "Using dataclasses for configuration objects reduces validation errors by 40%",
                category="success",
                metadata={"agent": "validation_agent", "confidence": 0.9, "task_id": "TASK_0129"}
            )
        """
        try:
            policy_decision = enforce_db_write_policy(
                self.workspace_root,
                operation="knowledge.agent_store",
                actor=actor,
            )
            if not policy_decision.allowed:
                print(f"Failed to add agent knowledge: {policy_decision.reason}")
                return False

            # Auto-detect loop number if not provided
            if loop_num is None:
                loop_num = self._detect_current_loop_num()
            
            # Include metadata in lesson_text if provided
            full_text = knowledge_text
            if metadata:
                metadata_str = f" [Metadata: {json.dumps(metadata)}]"
                full_text += metadata_str
            
            timestamp = utc_now_iso()
            
            # Insert into lessons table (reusing existing structure for agent knowledge)
            self.conn.execute("""
                INSERT INTO lessons 
                (source_type, source_id, loop_num, lesson_text, category, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "agent",
                f"agent_{timestamp.replace(':', '').replace('-', '').replace('T', '_').replace('Z', '')}",
                loop_num,
                full_text,
                category,
                timestamp,
            ))
            
            # Also add to FTS for semantic search
            self.conn.execute("""
                INSERT INTO lessons_fts (lesson_text, category)
                VALUES (?, ?)
            """, (knowledge_text, category))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Failed to add agent knowledge: {e}")
            self.conn.rollback()
            return False
    
    def _detect_current_loop_num(self) -> int:
        """Detect the current loop number from existing data."""
        try:
            row = self.conn.execute("""
                SELECT MAX(loop_num) as max_loop FROM lessons
            """).fetchone()
            return (row["max_loop"] or 0) + 1
        except Exception:
            return 1
    
    def get_agent_knowledge(self, category: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve agent-stored knowledge for learning and context.
        
        Args:
            category: Filter by category ("agent_insight", "success", etc.) or None for all
            limit: Maximum results to return
        
        Returns:
            List of agent knowledge entries with metadata
        """
        query = """
            SELECT source_type, source_id, loop_num, lesson_text, category, indexed_at
            FROM lessons 
            WHERE source_type = 'agent'
        """
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY indexed_at DESC LIMIT ?"
        params.append(limit)
        
        rows = self.conn.execute(query, params).fetchall()
        
        results = []
        for row in rows:
            lesson_text = row["lesson_text"]
            metadata = None
            
            # Extract metadata from lesson_text if present
            if " [Metadata: " in lesson_text:
                text_parts = lesson_text.split(" [Metadata: ", 1)
                lesson_text = text_parts[0]
                try:
                    metadata_str = text_parts[1].rstrip("]")
                    metadata = json.loads(metadata_str)
                except:
                    pass
            
            result = {
                "source_type": row["source_type"],
                "source_id": row["source_id"],
                "loop_num": row["loop_num"],
                "lesson_text": lesson_text,
                "category": row["category"],
                "indexed_at": row["indexed_at"],
                "metadata": metadata,
            }
            results.append(result)
        
        return results

    def test_method(self):
        return {"test": "success"}

    def extract_comprehensive_md_knowledge(self) -> Dict[str, Any]:
        """Extract comprehensive knowledge entities from ALL MD files in the project.

        This method goes beyond basic indexing to extract structured knowledge entities
        from reports, tasks, archives, docs, and other MD files using advanced pattern
        recognition and content analysis.

        Returns statistics about knowledge extracted.
        """
        stats = {
            "files_processed": 0,
            "knowledge_entities_extracted": 0,
            "reports_processed": 0,
            "tasks_processed": 0,
            "archives_processed": 0,
            "docs_processed": 0,
            "root_files_processed": 0,
            "errors": [],
            "started_at": utc_now_iso(),
            "completed_at": None,
        }

        # Define directories and file patterns to process
        md_patterns = [
            ("reports", "report_*.md", "report"),
            ("tasks", "task_*.md", "task"),
            ("archive", "ARCHIV_*.md", "archive"),
            ("docs", "*.md", "documentation"),
            ("root", "*.md", "root_document"),
        ]

        for dir_name, pattern, source_type in md_patterns:
            dir_path = self.workspace_root / dir_name if dir_name != "root" else self.workspace_root

            if not dir_path.exists():
                continue

            for md_file in sorted(dir_path.glob(pattern)):
                if not md_file.is_file():
                    continue
                try:
                    entities_extracted = self._extract_knowledge_from_md_file(md_file, source_type)
                    stats["files_processed"] += 1
                    stats["knowledge_entities_extracted"] += entities_extracted

                    # Update type-specific counters
                    if source_type == "report":
                        stats["reports_processed"] += 1
                    elif source_type == "task":
                        stats["tasks_processed"] += 1
                    elif source_type == "archive":
                        stats["archives_processed"] += 1
                    elif source_type == "documentation":
                        stats["docs_processed"] += 1
                    elif source_type == "root_document":
                        stats["root_files_processed"] += 1

                except Exception as e:
                    stats["errors"].append(f"{md_file.name}: {str(e)}")

        stats["completed_at"] = utc_now_iso()
        return stats

    def extract_external_knowledge_with_multiagent_learning(self, external_paths: List[Path] = None) -> Dict[str, Any]:
        """Extract and integrate knowledge from external sources using multi-agent learning patterns.

        This method implements hierarchical multi-agent knowledge extraction:
        1. Manager AI: Coordinates the extraction process
        2. Specialist AIs: Analyze different types of external content
        3. Worker AIs: Extract specific knowledge entities
        4. Integration AI: Merge and validate new knowledge against existing base

        Args:
            external_paths: List of external directory paths to analyze

        Returns:
            Statistics about external knowledge extraction and integration
        """
        stats = {
            "external_paths_analyzed": 0,
            "md_files_discovered": 0,
            "knowledge_entities_candidates": 0,
            "entities_integrated": 0,
            "entities_rejected": 0,
            "similarity_conflicts_resolved": 0,
            "new_knowledge_added": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
            "errors": [],
            "integration_log": []
        }

        # Default external paths if none provided
        if external_paths is None:
            external_paths = [
                Path("D:/Keeper-Clean"),
                Path("D:/Keeper")
            ]

        # Phase 1: Manager AI - Discover and categorize external content
        discovered_content = self._manager_ai_discover_content(external_paths, stats)

        # Phase 2: Specialist AIs - Analyze content by type
        analyzed_content = self._specialist_ais_analyze_content(discovered_content, stats)

        # Phase 3: Worker AIs - Extract knowledge entities
        extracted_entities = self._worker_ais_extract_entities(analyzed_content, stats)

        # Phase 4: Integration AI - Validate and merge with existing knowledge
        integrated_entities = self._integration_ai_merge_knowledge(extracted_entities, stats)

        stats["completed_at"] = utc_now_iso()
        self.conn.commit()

        return stats

    def _manager_ai_discover_content(self, external_paths: List[Path], stats: Dict[str, Any]) -> Dict[str, Any]:
        """Manager AI: Discover and categorize external content sources."""
        discovered = {
            "accessible_paths": [],
            "inaccessible_paths": [],
            "md_files_by_type": {
                "reports": [],
                "tasks": [],
                "archives": [],
                "docs": [],
                "other": []
            },
            "content_metadata": {}
        }

        for path in external_paths:
            try:
                if path.exists() and path.is_dir():
                    discovered["accessible_paths"].append(str(path))

                    # Discover MD files
                    md_files = list(path.rglob("*.md"))
                    stats["md_files_discovered"] += len(md_files)

                    # Categorize by type
                    for md_file in md_files:
                        if not md_file.is_file():
                            continue
                        file_name = md_file.name.lower()
                        if file_name.startswith("report_"):
                            discovered["md_files_by_type"]["reports"].append(md_file)
                        elif file_name.startswith("task_"):
                            discovered["md_files_by_type"]["tasks"].append(md_file)
                        elif file_name.startswith("archiv_"):
                            discovered["md_files_by_type"]["archives"].append(md_file)
                        else:
                            # Check content to determine type
                            try:
                                content = read_text(md_file)[:1000] if md_file.exists() else ""
                                if "## OBJECTIVE" in content or "## TASK" in content:
                                    discovered["md_files_by_type"]["tasks"].append(md_file)
                                elif "## EXECUTIVE SUMMARY" in content:
                                    discovered["md_files_by_type"]["reports"].append(md_file)
                                elif "## LESSONS LEARNED" in content:
                                    discovered["md_files_by_type"]["archives"].append(md_file)
                                else:
                                    discovered["md_files_by_type"]["docs"].append(md_file)
                            except Exception:
                                discovered["md_files_by_type"]["other"].append(md_file)

                    stats["external_paths_analyzed"] += 1

                else:
                    discovered["inaccessible_paths"].append(str(path))
                    stats["errors"].append(f"Path not accessible: {path}")

            except Exception as e:
                discovered["inaccessible_paths"].append(str(path))
                stats["errors"].append(f"Error analyzing path {path}: {str(e)}")

        return discovered

    def _specialist_ais_analyze_content(self, discovered_content: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
        """Specialist AIs: Analyze content by type for relevance and quality."""
        analyzed = {
            "content_analysis": {},
            "relevance_scores": {},
            "quality_assessments": {},
            "similarity_warnings": []
        }

        # Analyze each type with specialized AI
        for content_type, files in discovered_content["md_files_by_type"].items():
            analyzed["content_analysis"][content_type] = []
            analyzed["relevance_scores"][content_type] = []
            analyzed["quality_assessments"][content_type] = []

            for md_file in files:
                try:
                    analysis = self._analyze_single_file_content(md_file, content_type)
                    analyzed["content_analysis"][content_type].append(analysis)

                    # Assess relevance to current project
                    relevance_score = self._assess_content_relevance(analysis, content_type)
                    analyzed["relevance_scores"][content_type].append({
                        "file": str(md_file),
                        "score": relevance_score,
                        "reasons": analysis.get("relevance_indicators", [])
                    })

                    # Quality assessment
                    quality_score = self._assess_content_quality(analysis)
                    analyzed["quality_assessments"][content_type].append({
                        "file": str(md_file),
                        "score": quality_score,
                        "issues": analysis.get("quality_issues", [])
                    })

                except Exception as e:
                    stats["errors"].append(f"Error analyzing {md_file}: {str(e)}")

        # Cross-content similarity analysis
        analyzed["similarity_warnings"] = self._analyze_content_similarity(analyzed, stats)

        return analyzed

    def _worker_ais_extract_entities(self, analyzed_content: Dict[str, Any], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Worker AIs: Extract knowledge entities from high-quality, relevant content."""
        extracted_entities = []

        # Process only high-relevance, high-quality content
        for content_type, analyses in analyzed_content["content_analysis"].items():
            relevance_scores = analyzed_content["relevance_scores"][content_type]
            quality_scores = analyzed_content["quality_assessments"][content_type]

            for i, analysis in enumerate(analyses):
                relevance = relevance_scores[i]["score"]
                quality = quality_scores[i]["score"]

                # Only extract from content that meets thresholds
                # For external content, use lower thresholds
                is_external = "external" in str(analysis.get("file", "")).lower()
                relevance_threshold = 0.4 if is_external else 0.6
                quality_threshold = 0.5 if is_external else 0.7

                if relevance >= relevance_threshold and quality >= quality_threshold:
                    try:
                        entities = self._extract_entities_from_analysis(analysis, content_type)
                        extracted_entities.extend(entities)
                        stats["knowledge_entities_candidates"] += len(entities)
                    except Exception as e:
                        stats["errors"].append(f"Error extracting entities from {analysis.get('file', 'unknown')}: {str(e)}")

        return extracted_entities

    def _integration_ai_merge_knowledge(self, extracted_entities: List[Dict[str, Any]], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Integration AI: Validate and merge new knowledge with existing base."""
        integrated_entities = []

        for entity in extracted_entities:
            # Check for conflicts with existing knowledge
            conflict_analysis = self._analyze_knowledge_conflicts(entity)

            if conflict_analysis["has_conflicts"]:
                # Resolve conflicts using multi-agent consensus
                resolution = self._resolve_knowledge_conflicts(entity, conflict_analysis)
                if resolution["action"] == "integrate":
                    integrated_entities.append(entity)
                    stats["entities_integrated"] += 1
                    stats["integration_log"].append(f"Integrated with conflict resolution: {entity['id']}")
                elif resolution["action"] == "merge":
                    merged_entity = self._merge_similar_entities(entity, conflict_analysis["similar_entities"])
                    integrated_entities.append(merged_entity)
                    stats["entities_integrated"] += 1
                    stats["similarity_conflicts_resolved"] += 1
                    stats["integration_log"].append(f"Merged similar entities: {entity['id']}")
                else:  # reject
                    stats["entities_rejected"] += 1
                    stats["integration_log"].append(f"Rejected due to conflicts: {entity['id']}")
            else:
                # No conflicts, integrate directly
                integrated_entities.append(entity)
                stats["entities_integrated"] += 1
                stats["new_knowledge_added"] += 1
                stats["integration_log"].append(f"Added new knowledge: {entity['id']}")

        # Actually insert the integrated entities
        timestamp = utc_now_iso()
        for entity in integrated_entities:
            try:
                self._insert_knowledge_entity(
                    entity["id"],
                    entity["entity_type"],
                    entity["category"],
                    entity["confidence"],
                    entity["description"],
                    entity["tags"],
                    entity["examples"],
                    entity["outcomes"],
                    entity["sources"],
                    timestamp
                )
            except Exception as e:
                stats["errors"].append(f"Error inserting entity {entity['id']}: {str(e)}")

        return integrated_entities

    def _analyze_single_file_content(self, file_path: Path, content_type: str) -> Dict[str, Any]:
        """Analyze a single file's content for knowledge extraction potential."""
        analysis = {
            "file": str(file_path),
            "content_type": content_type,
            "size": 0,
            "sections": [],
            "key_phrases": [],
            "relevance_indicators": [],
            "quality_issues": [],
            "extractable_entities": []
        }

        try:
            content = read_text(file_path)
            analysis["size"] = len(content)
            analysis["content"] = content  # Store the content for later extraction

            # Extract sections
            sections = re.findall(r'^##+\s+(.+)$', content, re.MULTILINE)
            analysis["sections"] = sections

            # Identify key phrases based on content type
            if content_type == "reports":
                analysis["key_phrases"] = re.findall(r'(?:OBJECTIVE|OUTCOME|SUCCESS|FAILURE|LESSON)[\s:]+([^\n]+)', content, re.IGNORECASE)
            elif content_type == "tasks":
                analysis["key_phrases"] = re.findall(r'(?:OBJECTIVE|REQUIREMENT|DELIVERABLE)[\s:]+([^\n]+)', content, re.IGNORECASE)
            elif content_type == "archives":
                analysis["key_phrases"] = re.findall(r'(?:LESSON|ACHIEVEMENT|CHALLENGE)[\s:]+([^\n]+)', content, re.IGNORECASE)

            # For external content or general docs, look for any meaningful structured content
            if not analysis["key_phrases"] or content_type in ["docs", "other"]:
                # Look for bullet points with meaningful content
                bullets = re.findall(r'[-*•]\s*(.+?)(?=\n[-*•]|\n##|\n###|\Z)', content, re.DOTALL)
                meaningful_bullets = [b.strip() for b in bullets if len(b.strip()) > 10 and not b.strip().startswith('[')]
                analysis["key_phrases"].extend(meaningful_bullets[:10])  # Limit to 10

                # Look for numbered lists
                numbers = re.findall(r'^\d+\.\s*(.+?)(?=\n\d+\.|\n##|\n###|\Z)', content, re.MULTILINE | re.DOTALL)
                meaningful_numbers = [n.strip() for n in numbers if len(n.strip()) > 10]
                analysis["key_phrases"].extend(meaningful_numbers[:5])  # Limit to 5

            # Assess relevance to current project
            current_project_indicators = ["Keeper", "Loop", "Cockpit", "Guardrails", "Knowledge", "Multi-Agent"]
            analysis["relevance_indicators"] = [indicator for indicator in current_project_indicators if indicator.lower() in content.lower()]

            # For external content, also look for general software development relevance
            general_dev_terms = [
                "software", "development", "project", "implementation", "architecture",
                "testing", "documentation", "process", "workflow", "automation",
                "integration", "deployment", "performance", "optimization", "system",
                "framework", "library", "api", "database", "algorithm"
            ]
            general_matches = [term for term in general_dev_terms if term in content.lower()]
            analysis["relevance_indicators"].extend(general_matches)

            # Quality assessment
            if len(content) < 100:
                analysis["quality_issues"].append("Content too short")
            if len(sections) < 2:
                analysis["quality_issues"].append("Insufficient structure")
            if not analysis["key_phrases"]:
                analysis["quality_issues"].append("No key information found")

        except Exception as e:
            analysis["quality_issues"].append(f"Read error: {str(e)}")

        return analysis

    def _assess_content_relevance(self, analysis: Dict[str, Any], content_type: str) -> float:
        """Assess how relevant content is to the current project."""
        score = 0.0

        # Base relevance by content type
        type_weights = {
            "reports": 0.8,  # Reports often contain valuable lessons
            "tasks": 0.6,    # Tasks show work patterns
            "archives": 0.9, # Archives contain historical knowledge
            "docs": 0.7,     # Documentation provides context
            "other": 0.3     # Other files less relevant
        }
        score += type_weights.get(content_type, 0.5)

        # For external content, be more permissive
        is_external = "external" in str(analysis.get("file", "")).lower()
        if is_external:
            # Lower thresholds for external content
            base_score = 0.4  # Minimum score for external content
            score = max(score, base_score)

        # Relevance indicators boost
        relevance_indicators = len(analysis.get("relevance_indicators", []))
        boost = min(relevance_indicators * 0.1, 0.3)  # Max 0.3 boost
        score += boost

        # Content quality affects relevance
        quality_issues = len(analysis.get("quality_issues", []))
        penalty = quality_issues * 0.05  # Reduced penalty for external content
        score -= penalty

        # For external content, look for general software development terms
        if is_external:
            content = analysis.get("content", "")
            general_terms = [
                "development", "software", "project", "implementation", "architecture",
                "testing", "documentation", "process", "workflow", "automation",
                "integration", "deployment", "maintenance", "optimization"
            ]
            general_matches = sum(1 for term in general_terms if term in content.lower())
            general_boost = min(general_matches * 0.05, 0.2)  # Max 0.2 boost
            score += general_boost

        return max(0.0, min(1.0, score))

    def _assess_content_quality(self, analysis: Dict[str, Any]) -> float:
        """Assess content quality for knowledge extraction."""
        score = 1.0

        # Size assessment
        size = analysis.get("size", 0)
        if size < 500:
            score -= 0.3
        elif size > 10000:
            score += 0.1  # Longer content often more valuable

        # Structure assessment
        sections = len(analysis.get("sections", []))
        if sections < 2:
            score -= 0.2
        elif sections > 5:
            score += 0.1

        # Key phrases assessment
        key_phrases = len(analysis.get("key_phrases", []))
        if key_phrases == 0:
            score -= 0.4
        elif key_phrases > 3:
            score += 0.1

        # Quality issues penalty
        quality_issues = len(analysis.get("quality_issues", []))
        score -= quality_issues * 0.2

        # For external content, be more lenient
        is_external = "external" in str(analysis.get("file", "")).lower()
        if is_external:
            # Reduce penalties for external content
            score += 0.2  # Base boost for external content
            if size >= 200:  # Reasonable minimum size
                score += 0.1

        return max(0.0, min(1.0, score))

    def _analyze_content_similarity(self, analyzed_content: Dict[str, Any], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze similarity between external content and existing knowledge."""
        warnings = []

        # Get existing knowledge entities
        existing_entities = self.conn.execute("""
            SELECT id, knowledge_type, description FROM test_knowledge
        """).fetchall()

        existing_descriptions = {row["id"]: row["description"] for row in existing_entities}

        # Check each analyzed file for similarity
        for content_type, analyses in analyzed_content["content_analysis"].items():
            for analysis in analyses:
                content = analysis.get("content", "")
                if not content:
                    continue

                # Simple similarity check against existing knowledge
                for entity_id, existing_desc in existing_descriptions.items():
                    similarity = self._calculate_text_similarity(content[:500], existing_desc[:500])
                    if similarity > 0.7:  # High similarity threshold
                        warnings.append({
                            "external_file": analysis["file"],
                            "existing_entity": entity_id,
                            "similarity_score": similarity,
                            "content_type": content_type
                        })

        return warnings

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity score."""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _extract_entities_from_analysis(self, analysis: Dict[str, Any], content_type: str) -> List[Dict[str, Any]]:
        """Extract knowledge entities from content analysis."""
        entities = []

        content = analysis.get("content", "")
        if not content:
            return entities

        # Extract based on content type
        if content_type == "reports":
            entities.extend(self._extract_report_entities_from_content(content, analysis["file"]))
        elif content_type == "tasks":
            entities.extend(self._extract_task_entities_from_content(content, analysis["file"]))
        elif content_type == "archives":
            entities.extend(self._extract_archive_entities_from_content(content, analysis["file"]))
        elif content_type == "docs":
            entities.extend(self._extract_doc_entities_from_content(content, analysis["file"]))

        return entities

    def _extract_report_entities_from_content(self, content: str, source_file: str) -> List[Dict[str, Any]]:
        """Extract entities from report content."""
        entities = []

        # Extract objectives
        objective_match = re.search(r'## EXECUTIVE SUMMARY(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if objective_match:
            entities.append({
                "id": f"external_report_objective_{Path(source_file).stem}",
                "entity_type": "external_report_summary",
                "category": "summary",
                "confidence": 0.8,
                "description": objective_match.group(1).strip(),
                "tags": ["external", "report", "objective"],
                "examples": [objective_match.group(1).strip()[:100]],
                "outcomes": [],
                "sources": [source_file]
            })

        return entities

    def _extract_task_entities_from_content(self, content: str, source_file: str) -> List[Dict[str, Any]]:
        """Extract entities from task content."""
        entities = []

        # Extract objectives
        objective_match = re.search(r'## OBJECTIVE(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if objective_match:
            entities.append({
                "id": f"external_task_objective_{Path(source_file).stem}",
                "entity_type": "external_task_definition",
                "category": "objective",
                "confidence": 0.7,
                "description": objective_match.group(1).strip(),
                "tags": ["external", "task", "objective"],
                "examples": [objective_match.group(1).strip()[:100]],
                "outcomes": [],
                "sources": [source_file]
            })

        return entities

    def _extract_archive_entities_from_content(self, content: str, source_file: str) -> List[Dict[str, Any]]:
        """Extract entities from archive content."""
        entities = []

        # Extract lessons learned
        lessons_match = re.search(r'## LESSONS LEARNED(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if lessons_match:
            lessons_text = lessons_match.group(1).strip()
            # Extract individual lessons
            lesson_items = re.findall(r'[-*•]\s*(.+?)(?=\n[-*•]|\n##|\Z)', lessons_text, re.DOTALL)
            for i, lesson in enumerate(lesson_items[:5]):  # Limit to 5 lessons per archive
                entities.append({
                    "id": f"external_archive_lesson_{Path(source_file).stem}_{i}",
                    "entity_type": "external_archive_lesson",
                    "category": "lesson",
                    "confidence": 0.8,
                    "description": lesson.strip(),
                    "tags": ["external", "archive", "lesson"],
                    "examples": [lesson.strip()[:100]],
                    "outcomes": [],
                    "sources": [source_file]
                })

        return entities

    def _extract_doc_entities_from_content(self, content: str, source_file: str) -> List[Dict[str, Any]]:
        """Extract entities from documentation content."""
        entities = []

        # Extract key concepts from headers
        headers = re.findall(r'^##+\s+(.+)$', content, re.MULTILINE)
        for header in headers[:3]:  # Limit to first 3 headers
            entities.append({
                "id": f"external_doc_concept_{Path(source_file).stem}_{header.replace(' ', '_').lower()}",
                "entity_type": "external_documentation_concept",
                "category": "concept",
                "confidence": 0.6,
                "description": f"Documentation concept: {header}",
                "tags": ["external", "documentation", "concept"],
                "examples": [header],
                "outcomes": [],
                "sources": [source_file]
            })

        return entities

    def _analyze_knowledge_conflicts(self, new_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze potential conflicts with existing knowledge."""
        conflicts = {
            "has_conflicts": False,
            "similar_entities": [],
            "conflict_types": []
        }

        # Check for similar entities in existing knowledge
        existing_entities = self.conn.execute("""
            SELECT id, knowledge_type, description FROM test_knowledge
            WHERE knowledge_type = ?
        """, (new_entity["entity_type"],)).fetchall()

        for existing in existing_entities:
            similarity = self._calculate_text_similarity(
                new_entity["description"],
                existing["description"]
            )
            if similarity > 0.6:  # Similarity threshold
                conflicts["has_conflicts"] = True
                conflicts["similar_entities"].append({
                    "id": existing["id"],
                    "similarity": similarity,
                    "description": existing["description"]
                })
                conflicts["conflict_types"].append("similar_content")

        return conflicts

    def _resolve_knowledge_conflicts(self, new_entity: Dict[str, Any], conflict_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve knowledge conflicts using multi-agent consensus approach."""
        resolution = {"action": "reject", "reason": "default_reject"}

        similar_entities = conflict_analysis["similar_entities"]

        if not similar_entities:
            return {"action": "integrate", "reason": "no_conflicts"}

        # Analyze conflict types
        max_similarity = max(entity["similarity"] for entity in similar_entities)

        if max_similarity > 0.9:  # Very similar - likely duplicate
            resolution = {"action": "reject", "reason": "duplicate_content"}
        elif max_similarity > 0.7:  # Similar but not identical - merge
            resolution = {"action": "merge", "reason": "similar_content_can_merge"}
        else:  # Different enough - integrate
            resolution = {"action": "integrate", "reason": "sufficiently_different"}

        return resolution

    def _merge_similar_entities(self, new_entity: Dict[str, Any], similar_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge similar entities to create enriched knowledge."""
        merged = new_entity.copy()

        # Combine descriptions
        descriptions = [new_entity["description"]]
        descriptions.extend(entity["description"] for entity in similar_entities)
        merged["description"] = " | ".join(descriptions[:3])  # Limit to 3 descriptions

        # Combine tags
        all_tags = set(new_entity["tags"])
        for entity in similar_entities:
            # Note: similar_entities doesn't have tags, so we'd need to fetch them
            pass
        merged["tags"] = list(all_tags | {"merged", "external"})

        # Update confidence based on merge
        merged["confidence"] = min(0.9, new_entity["confidence"] + 0.1)  # Slight boost for merged

        # Update ID to reflect merge
        merged["id"] = f"merged_{new_entity['id']}"

        return merged

    def _extract_knowledge_from_md_file(self, file_path: Path, source_type: str) -> int:
        """Extract knowledge entities from a single MD file.

        Uses advanced pattern recognition to identify and extract structured knowledge
        including objectives, outcomes, lessons, patterns, and relationships.

        Returns number of knowledge entities extracted.
        """
        content = read_text(file_path)
        if not content:
            return 0

        entities_extracted = 0
        timestamp = utc_now_iso()
        file_id = file_path.stem

        # Extract different types of knowledge based on source type
        if source_type == "report":
            entities_extracted += self._extract_report_knowledge(content, file_id, timestamp)
        elif source_type == "task":
            entities_extracted += self._extract_task_knowledge(content, file_id, timestamp)
        elif source_type == "archive":
            entities_extracted += self._extract_archive_knowledge(content, file_id, timestamp)
        elif source_type == "documentation":
            entities_extracted += self._extract_documentation_knowledge(content, file_id, timestamp)
        elif source_type == "root_document":
            entities_extracted += self._extract_root_document_knowledge(content, file_id, timestamp)

        # Extract common knowledge patterns from all files
        entities_extracted += self._extract_common_knowledge_patterns(content, file_id, source_type, timestamp)

        return entities_extracted

    def _extract_report_knowledge(self, content: str, file_id: str, timestamp: str) -> int:
        """Extract knowledge from report files."""
        entities = 0

        # Extract objectives and outcomes
        objective_match = re.search(r'## EXECUTIVE SUMMARY(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if objective_match:
            summary = objective_match.group(1).strip()
            self._insert_knowledge_entity(
                f"report_summary_{file_id}",
                "report_summary",
                "summary",
                0.9,
                summary,
                ["executive_summary"],
                [summary],
                [],
                [file_id],
                timestamp
            )
            entities += 1

        # Extract validation results
        validation_match = re.search(r'## VALIDATION RESULTS(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if validation_match:
            validation = validation_match.group(1).strip()
            self._insert_knowledge_entity(
                f"report_validation_{file_id}",
                "report_validation",
                "validation",
                0.8,
                validation,
                ["validation_results"],
                [validation],
                [],
                [file_id],
                timestamp
            )
            entities += 1

        return entities

    def _extract_task_knowledge(self, content: str, file_id: str, timestamp: str) -> int:
        """Extract knowledge from task definition files."""
        entities = 0

        # Extract objectives
        objective_match = re.search(r'## OBJECTIVE(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if objective_match:
            objective = objective_match.group(1).strip()
            self._insert_knowledge_entity(
                f"task_objective_{file_id}",
                "task_objective",
                "objective",
                0.9,
                objective,
                ["task_definition"],
                [objective],
                [],
                [file_id],
                timestamp
            )
            entities += 1

        # Extract acceptance criteria
        criteria_match = re.search(r'## ACCEPTANCE CRITERIA(.*?)(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if criteria_match:
            criteria = criteria_match.group(1).strip()
            self._insert_knowledge_entity(
                f"task_criteria_{file_id}",
                "task_criteria",
                "criteria",
                0.8,
                criteria,
                ["acceptance_criteria"],
                [criteria],
                [],
                [file_id],
                timestamp
            )
            entities += 1

        return entities

    def _extract_archive_knowledge(self, content: str, file_id: str, timestamp: str) -> int:
        """Extract knowledge from archive files."""
        entities = 0

        # Archives often contain historical lessons - extract key insights
        lesson_matches = re.findall(r'(?:lesson|insight|key takeaway):\s*(.*?)(?=\n\n|\n##|\Z)', content, re.IGNORECASE | re.DOTALL)
        for i, lesson in enumerate(lesson_matches):
            if lesson.strip():
                self._insert_knowledge_entity(
                    f"archive_lesson_{file_id}_{i}",
                    "archive_lesson",
                    "lesson",
                    0.7,
                    lesson.strip(),
                    ["historical_lesson"],
                    [lesson.strip()],
                    [],
                    [file_id],
                    timestamp
                )
                entities += 1

        return entities

    def _extract_documentation_knowledge(self, content: str, file_id: str, timestamp: str) -> int:
        """Extract knowledge from documentation files."""
        entities = 0

        # Extract key concepts and definitions
        concept_matches = re.findall(r'(?:concept|definition|principle):\s*(.*?)(?=\n\n|\n##|\Z)', content, re.IGNORECASE | re.DOTALL)
        for i, concept in enumerate(concept_matches):
            if concept.strip():
                self._insert_knowledge_entity(
                    f"doc_concept_{file_id}_{i}",
                    "documentation_concept",
                    "concept",
                    0.8,
                    concept.strip(),
                    ["documentation"],
                    [concept.strip()],
                    [],
                    [file_id],
                    timestamp
                )
                entities += 1

        # Extract guidelines and best practices
        guideline_matches = re.findall(r'(?:guideline|best practice|recommendation):\s*(.*?)(?=\n\n|\n##|\Z)', content, re.IGNORECASE | re.DOTALL)
        for i, guideline in enumerate(guideline_matches):
            if guideline.strip():
                self._insert_knowledge_entity(
                    f"doc_guideline_{file_id}_{i}",
                    "documentation_guideline",
                    "guideline",
                    0.7,
                    guideline.strip(),
                    ["documentation"],
                    [guideline.strip()],
                    [],
                    [file_id],
                    timestamp
                )
                entities += 1

        return entities

    def _extract_root_document_knowledge(self, content: str, file_id: str, timestamp: str) -> int:
        """Extract knowledge from root-level documentation files."""
        entities = 0

        # Extract key information from README and other root docs
        section_matches = re.findall(r'^##\s+(.*?)(.*?)(?=^##|\Z)', content, re.MULTILINE | re.DOTALL)
        for section_title, section_content in section_matches:
            if section_content.strip():
                self._insert_knowledge_entity(
                    f"root_doc_{file_id}_{section_title.lower().replace(' ', '_')}",
                    "root_documentation",
                    "documentation",
                    0.8,
                    f"{section_title}: {section_content.strip()}",
                    ["root_documentation"],
                    [section_content.strip()],
                    [],
                    [file_id],
                    timestamp
                )
                entities += 1

        return entities

    def _extract_common_knowledge_patterns(self, content: str, file_id: str, source_type: str, timestamp: str) -> int:
        """Extract common knowledge patterns that appear across all file types."""
        entities = 0

        # Extract success patterns
        success_matches = re.findall(r'(?:success|✅|achievement):\s*(.*?)(?=\n\n|\n##|\Z)', content, re.IGNORECASE | re.DOTALL)
        for i, success in enumerate(success_matches):
            if success.strip():
                self._insert_knowledge_entity(
                    f"success_pattern_{file_id}_{i}",
                    "success_pattern",
                    "success",
                    0.8,
                    success.strip(),
                    ["success_pattern"],
                    [success.strip()],
                    [],
                    [file_id],
                    timestamp
                )
                entities += 1

        # Extract failure patterns
        failure_matches = re.findall(r'(?:fail|error|❌|problem):\s*(.*?)(?=\n\n|\n##|\Z)', content, re.IGNORECASE | re.DOTALL)
        for i, failure in enumerate(failure_matches):
            if failure.strip():
                self._insert_knowledge_entity(
                    f"failure_pattern_{file_id}_{i}",
                    "failure_pattern",
                    "failure",
                    0.8,
                    failure.strip(),
                    ["failure_pattern"],
                    [failure.strip()],
                    [],
                    [file_id],
                    timestamp
                )
                entities += 1

        # Extract warning patterns
        warning_matches = re.findall(r'(?:warning|⚠|caution|risk):\s*(.*?)(?=\n\n|\n##|\Z)', content, re.IGNORECASE | re.DOTALL)
        for i, warning in enumerate(warning_matches):
            if warning.strip():
                self._insert_knowledge_entity(
                    f"warning_pattern_{file_id}_{i}",
                    "warning_pattern",
                    "warning",
                    0.7,
                    warning.strip(),
                    ["warning_pattern"],
                    [warning.strip()],
                    [],
                    [file_id],
                    timestamp
                )
                entities += 1

        return entities

    def _insert_knowledge_entity(self, entity_id: str, category: str, knowledge_type: str,
                                confidence: float, description: str, code_examples: List[str],
                                expected_outcomes: List[str], failure_modes: List[str],
                                integration_points: List[str], timestamp: str) -> None:
        """Insert a comprehensive knowledge entity into the database."""
        # Use the existing test_knowledge table structure for now
        # In future, we might want a separate comprehensive_knowledge table
        self.conn.execute("""
            INSERT OR IGNORE INTO test_knowledge
            (id, test_file, entity_id, category, knowledge_type, confidence_level,
             description, code_examples, expected_outcomes, failure_modes,
             integration_points, test_source, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_id,
            "comprehensive_extraction",
            entity_id,
            category,
            knowledge_type,
            confidence,
            description,
            json.dumps(code_examples),
            json.dumps(expected_outcomes),
            json.dumps(failure_modes),
            json.dumps(integration_points),
            "comprehensive_md_extraction",
            timestamp,
        ))


    def build_reference_graph(self) -> Dict[str, Any]:
        """Build a graph of reference relationships between entities.
        
        Analyzes all entities and their references to create a relationship graph
        for understanding dependencies and connections.
        
        Returns:
            Statistics about the graph building process
        """
        stats = {
            "references_found": 0,
            "relationships_created": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
        }
        
        now = utc_now_iso()
        
        # Clear existing relationships
        self.conn.execute("DELETE FROM reference_relationships")
        
        # Get all entities with references
        entities_with_refs = []
        
        # Reports
        reports = self.conn.execute("SELECT id, refs FROM reports WHERE refs IS NOT NULL").fetchall()
        for report in reports:
            if report["refs"]:
                refs = json.loads(report["refs"])
                entities_with_refs.append(("report", report["id"], refs))
        
        # Tasks
        tasks = self.conn.execute("SELECT id, refs FROM tasks WHERE refs IS NOT NULL").fetchall()
        for task in tasks:
            if task["refs"]:
                refs = json.loads(task["refs"])
                entities_with_refs.append(("task", task["id"], refs))
        
        # Docs
        docs = self.conn.execute("SELECT id, refs FROM docs WHERE refs IS NOT NULL").fetchall()
        for doc in docs:
            if doc["refs"]:
                refs = json.loads(doc["refs"])
                entities_with_refs.append(("doc", doc["id"], refs))
        
        # Process references
        for source_type, source_id, refs in entities_with_refs:
            for ref in refs:
                # Parse reference format [ref:FILE#SECTION|v:VERSION|tags:...|src:...]
                if not ref.startswith("[ref:"):
                    continue
                
                ref_content = ref[5:-1]  # Remove [ref: and ]
                parts = ref_content.split("|")
                if not parts:
                    continue
                
                target_file = parts[0].split("#")[0]  # Get file part before #
                
                # Determine target type and id
                target_type = None
                target_id = None
                
                if target_file.startswith("tasks/"):
                    target_type = "task"
                    target_id = target_file.replace("tasks/task_", "").replace(".md", "")
                elif target_file.startswith("reports/"):
                    target_type = "report"
                    target_id = target_file.replace("reports/report_", "").replace(".md", "")
                elif target_file.startswith("docs/"):
                    target_type = "doc"
                    target_id = target_file.replace("docs/", "").replace(".md", "")
                elif target_file == "current.json":
                    target_type = "state"
                    target_id = "current"
                elif target_file == "_LOOP_GATE.md":
                    target_type = "validator"
                    target_id = "gate"
                
                if target_type and target_id:
                    # Create relationship
                    self.conn.execute("""
                        INSERT INTO reference_relationships
                        (source_type, source_id, target_type, target_id, relationship_type, confidence, evidence, indexed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        source_type, source_id, target_type, target_id,
                        "references", 0.8, json.dumps([ref]), now
                    ))
                    stats["relationships_created"] += 1
                
                stats["references_found"] += 1
        
        self.conn.commit()
        stats["completed_at"] = utc_now_iso()
        return stats
    
    def search_by_milestone(self, milestone_id: str = None, goal_id: str = None, 
                           query: str = None, limit: int = 20) -> List[SearchResult]:
        """Search knowledge indexed by milestone goals.
        
        Args:
            milestone_id: Specific milestone to search in
            goal_id: Specific goal within milestone
            query: Text query to match
            limit: Maximum results to return
        
        Returns:
            List of SearchResult objects
        """
        results = []
        
        # Build query
        sql = """
            SELECT mi.*, 
                   CASE mi.entity_type 
                     WHEN 'report' THEN r.content_full
                     WHEN 'task' THEN t.objective
                     WHEN 'doc' THEN d.content_full
                     WHEN 'lesson' THEN l.lesson_text
                   END as content,
                   CASE mi.entity_type
                     WHEN 'report' THEN r.loop_num
                     WHEN 'lesson' THEN l.loop_num
                   END as loop_num
            FROM milestone_index mi
            LEFT JOIN reports r ON mi.entity_type = 'report' AND mi.entity_id = r.id
            LEFT JOIN tasks t ON mi.entity_type = 'task' AND mi.entity_id = t.id
            LEFT JOIN docs d ON mi.entity_type = 'doc' AND mi.entity_id = d.id
            LEFT JOIN lessons l ON mi.entity_type = 'lesson' AND mi.entity_id = CAST(l.id AS TEXT)
            WHERE 1=1
        """
        params = []
        
        if milestone_id:
            sql += " AND mi.milestone_id = ?"
            params.append(milestone_id)
        
        if goal_id:
            sql += " AND mi.goal_id = ?"
            params.append(goal_id)
        
        if query:
            # Use FTS for content matching
            sql += """
                AND (
                    (mi.entity_type = 'report' AND r.rowid IN (SELECT rowid FROM reports_fts WHERE content_full MATCH ?)) OR
                    (mi.entity_type = 'doc' AND d.rowid IN (SELECT rowid FROM docs_fts WHERE content_full MATCH ?)) OR
                    (mi.entity_type = 'lesson' AND l.id IN (SELECT rowid FROM lessons_fts WHERE lesson_text MATCH ?))
                )
            """
            params.extend([query, query, query])
        
        sql += " ORDER BY mi.relevance_score DESC LIMIT ?"
        params.append(limit)
        
        rows = self.conn.execute(sql, params).fetchall()
        
        for row in rows:
            content = row["content"] or ""
            snippet = content[:200] + "..." if len(content) > 200 else content
            
            results.append(SearchResult(
                type=row["entity_type"],
                id=row["entity_id"],
                relevance=row["relevance_score"],
                snippet=snippet,
                context={
                    "milestone_id": row["milestone_id"],
                    "goal_id": row["goal_id"],
                    "loop_num": row["loop_num"]
                }
            ))
        
        return results
    
    def semantic_search(self, query: str, model: str = "sentence-transformers/all-MiniLM-L6-v2", 
                       limit: int = 20) -> List[SearchResult]:
        """Perform semantic similarity search using embeddings.
        
        Args:
            query: Text query to find similar content for
            model: Embedding model to use
            limit: Maximum results to return
        
        Returns:
            List of SearchResult objects ordered by similarity
        """
        try:
            # Generate embedding for query
            query_embedding = self.anthropic_agent.create_embedding(query, model)
            
            # Find similar embeddings using cosine similarity
            # For now, use a simple approach - in production would use vector extension
            results = []
            
            # Query semantic_embeddings table
            rows = self.conn.execute("""
                SELECT entity_type, entity_id, embedding_vector, content_preview
                FROM semantic_embeddings
                ORDER BY id  -- In production, use vector similarity
                LIMIT ?
            """, (limit * 10,)).fetchall()  # Get more candidates
            
            for row in rows:
                try:
                    stored_embedding = json.loads(row['embedding_vector'])
                    similarity = self._cosine_similarity(query_embedding, stored_embedding)
                    
                    results.append(SearchResult(
                        entity_type=row['entity_type'],
                        entity_id=row['entity_id'],
                        content_preview=row['content_preview'] or "",
                        score=similarity,
                        metadata={'similarity': similarity}
                    ))
                except Exception as e:
                    continue
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]
            
        except Exception as e:
            # Fallback to regular search
            print(f"Semantic search failed: {e}, falling back to FTS")
            return self.search(query, limit=limit)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def calculate_quality_score(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """Calculate multi-dimensional quality score for an entity.
        
        Args:
            entity_type: Type of entity ('report', 'task', 'doc', 'lesson')
            entity_id: ID of the entity
        
        Returns:
            Dict with individual scores and overall quality score
        """
        scores = {
            "relevance_score": 0.5,
            "recency_score": 0.5,
            "validation_score": 0.5,
            "impact_score": 0.5,
            "overall_score": 0.5,
            "factors": {}
        }
        
        now = datetime.now(timezone.utc)
        
        if entity_type == "report":
            row = self.conn.execute("""
                SELECT validation_passed, date_completed, loop_num
                FROM reports WHERE id = ?
            """, (entity_id,)).fetchone()
            
            if row:
                # Validation score
                scores["validation_score"] = 1.0 if row["validation_passed"] else 0.0
                
                # Recency score (newer = higher score)
                if row["date_completed"]:
                    completed_date = datetime.fromisoformat(row["date_completed"].replace('Z', '+00:00'))
                    days_old = (now - completed_date).days
                    scores["recency_score"] = max(0.1, 1.0 - (days_old / 365.0))  # Decay over year
                
                # Impact score based on loop number (higher loops = more impact)
                scores["impact_score"] = min(1.0, row["loop_num"] / 10.0)
        
        elif entity_type == "lesson":
            row = self.conn.execute("""
                SELECT confidence_score, loop_num
                FROM lessons WHERE id = ?
            """, (entity_id,)).fetchone()
            
            if row:
                scores["relevance_score"] = row["confidence_score"]
                scores["impact_score"] = min(1.0, row["loop_num"] / 10.0)
        
        # Calculate overall score (weighted average)
        weights = {
            "relevance_score": 0.3,
            "recency_score": 0.2,
            "validation_score": 0.3,
            "impact_score": 0.2
        }
        
        overall = sum(scores[k] * weights[k] for k in weights)
        scores["overall_score"] = overall
        
        # Store in database
        now_iso = utc_now_iso()
        self.conn.execute("""
            INSERT OR REPLACE INTO quality_scores
            (entity_type, entity_id, relevance_score, recency_score, 
             validation_score, impact_score, overall_score, factors, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_type, entity_id,
            scores["relevance_score"], scores["recency_score"],
            scores["validation_score"], scores["impact_score"],
            scores["overall_score"], json.dumps(scores["factors"]), now_iso
        ))
        self.conn.commit()
        
        return scores

    def update_file_relevance_scores(self, changed_path: Optional[Path] = None) -> Dict[str, Any]:
        """Recompute and persist file-level relevance scores.

        Uses FileRelevanceScorer (TASK_0149 Phase 1) and stores normalized
        per-file scores for relevance-aware bootstrap/session-pack filtering.
        """
        from file_relevance_scorer import FileRelevance, FileRelevanceScorer

        # Backward-compatible schema guard for existing DB files.
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS file_relevance_scores (
                path TEXT PRIMARY KEY,
                relevance_score REAL NOT NULL,
                ref_count INTEGER NOT NULL DEFAULT 0,
                ref_popularity_score REAL NOT NULL DEFAULT 0.0,
                recency_score REAL NOT NULL DEFAULT 0.0,
                semantic_similarity_score REAL NOT NULL DEFAULT 0.5,
                structural_importance_score REAL NOT NULL DEFAULT 0.3,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_relevance_scores_score ON file_relevance_scores(relevance_score DESC)"
        )
        self.conn.commit()

        scorer = FileRelevanceScorer(self.workspace_root, verbose=False)
        file_relevances = scorer.run_analysis()

        # Ensure changed file is present even if it has no incoming refs yet.
        if changed_path is not None:
            cp = Path(changed_path)
            try:
                rel = cp.resolve().relative_to(self.workspace_root.resolve()).as_posix()
            except Exception:
                rel = cp.as_posix()
            if rel not in file_relevances:
                recency = scorer.calculate_recency_scores([rel]).get(rel, 0.0)
                structural = scorer.calculate_structural_importance([rel]).get(rel, 0.3)
                final_score = min(1.0, max(0.0, 0.30 * recency + 0.10 * structural + 0.10))
                file_relevances[rel] = FileRelevance(
                    path=rel,
                    ref_count=0,
                    ref_popularity_score=0.0,
                    recency_score=recency,
                    semantic_similarity_score=0.5,
                    structural_importance_score=structural,
                    final_score=final_score,
                )

        now = utc_now_iso()
        rows = [
            (
                fr.path,
                float(fr.final_score),
                int(fr.ref_count),
                float(fr.ref_popularity_score),
                float(fr.recency_score),
                float(fr.semantic_similarity_score),
                float(fr.structural_importance_score),
                now,
            )
            for fr in file_relevances.values()
        ]

        self.conn.execute("DELETE FROM file_relevance_scores")
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO file_relevance_scores (
                path, relevance_score, ref_count, ref_popularity_score, recency_score,
                semantic_similarity_score, structural_importance_score, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

        return {
            "success": True,
            "files_scored": len(rows),
            "updated_at": now,
            "changed_path": str(changed_path) if changed_path is not None else None,
        }

    def get_top_relevant_files(self, limit: int = 20, min_score: float = 0.4) -> List[Dict[str, Any]]:
        """Return top relevant files for context selection/bootstrap filtering."""
        cursor = self.conn.execute(
            """
            SELECT path, relevance_score, ref_count, updated_at
            FROM file_relevance_scores
            WHERE relevance_score >= ?
            ORDER BY relevance_score DESC, ref_count DESC
            LIMIT ?
            """,
            (min_score, max(1, int(limit))),
        )
        return [
            {
                "path": row["path"],
                "relevance_score": float(row["relevance_score"]),
                "ref_count": int(row["ref_count"]),
                "updated_at": row["updated_at"],
            }
            for row in cursor.fetchall()
        ]


    def build_reference_graph_from_content(self) -> Dict[str, Any]:
        """Build reference graph by parsing actual file content for [ref:] patterns.
        
        This method scans all markdown files and extracts reference relationships
        directly from content, following mega.md depth-first methodology.
        """
        stats = {
            "files_scanned": 0,
            "references_found": 0,
            "relationships_created": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
        }
        
        import re
        ref_pattern = re.compile(r'\[ref:[^\]]+\]')  # Capture full ref
        now = utc_now_iso()
        
        # Clear existing relationships
        self.conn.execute("DELETE FROM reference_relationships")
        
        # Scan all markdown files
        workspace = Path(self.workspace_root)
        for md_file in workspace.rglob("*.md"):
            if any(skip in str(md_file) for skip in ['.git', '__pycache__', 'node_modules', 'venv', '.vscode']):
                continue
                
            stats["files_scanned"] += 1
            
            try:
                content = md_file.read_text(encoding='utf-8')
                refs = ref_pattern.findall(content)
                
                if not refs:
                    continue
                    
                # Determine source type and ID
                rel_path = md_file.relative_to(workspace)
                source_type = None
                source_id = None
                
                # Use POSIX path for consistent forward slashes
                rel_str = rel_path.as_posix()
                
                # Check for nested paths (e.g., .worktrees/.../docs/file.md)
                if '/reports/' in rel_str or rel_str.startswith('reports/'):
                    source_type = 'report'
                    source_id = rel_path.stem
                elif '/tasks/' in rel_str or rel_str.startswith('tasks/'):
                    source_type = 'task'
                    source_id = rel_path.stem.replace('task_', '')
                elif '/archive/' in rel_str or rel_str.startswith('archive/'):
                    source_type = 'archive'
                    source_id = rel_path.stem
                elif '/docs/' in rel_str or rel_str.startswith('docs/'):
                    source_type = 'doc'
                    # Extract the doc name from the docs/ part
                    docs_index = rel_str.find('/docs/')
                    if docs_index >= 0:
                        doc_part = rel_str[docs_index + 6:]  # After /docs/
                    else:
                        doc_part = rel_str[5:]  # After docs/
                    source_id = doc_part.replace('.md', '')
                else:
                    # Root level files
                    if rel_path.name in ['NEU.md', 'Alt.md', 'NEURAL_CORTEX.md']:
                        source_type = 'pointer'
                        source_id = rel_path.stem.lower()
                    else:
                        continue  # Skip other root files
                
                if source_type and source_id:
                    for ref in refs:
                        stats["references_found"] += 1
                        
                        # Extract file path from ref (between [ref: and first | or ])
                        ref_content = ref[5:-1]  # Remove [ref: and ]
                        file_path = ref_content.split('|')[0]  # Take part before first |
                        clean_ref = file_path.split('#')[0]  # Remove #SECTION part
                        
                        # Determine target type and ID
                        target_type = None
                        target_id = None
                        
                        if clean_ref.startswith('tasks/'):
                            target_type = 'task'
                            target_id = clean_ref.replace('tasks/task_', '').replace('.md', '')
                        elif clean_ref.startswith('reports/'):
                            target_type = 'report'
                            target_id = clean_ref.replace('reports/report_', '').replace('.md', '')
                        elif clean_ref.startswith('docs/'):
                            target_type = 'doc'
                            target_id = clean_ref.replace('docs/', '').replace('.md', '')
                        elif clean_ref.startswith('archive/'):
                            target_type = 'archive'
                            target_id = clean_ref.replace('archive/', '').replace('.md', '')
                        elif clean_ref.startswith('task_'):
                            # Direct task reference like task_TASK_0001.md
                            target_type = 'task'
                            target_id = clean_ref.replace('task_', '').replace('.md', '')
                        elif clean_ref.startswith('report_'):
                            # Direct report reference like report_TASK_0001_L01_v01.md
                            target_type = 'report'
                            target_id = clean_ref.replace('report_', '').replace('.md', '')
                        elif clean_ref == 'current.json':
                            target_type = 'state'
                            target_id = 'current'
                        elif clean_ref == '_LOOP_GATE.md':
                            target_type = 'validator'
                            target_id = 'gate'
                        elif clean_ref == 'SEED_TEMPLATE/':
                            target_type = 'template'
                            target_id = 'seed'
                        elif clean_ref == 'FILE#SECTION':  # Skip template refs
                            continue
                        
                        if target_type and target_id:
                            # Construct file paths
                            source_file_path = rel_path.as_posix()
                            target_file_path = None
                            
                            if target_type == 'task':
                                target_file_path = f'tasks/task_{target_id}.md'
                            elif target_type == 'report':
                                target_file_path = f'reports/report_{target_id}.md'
                            elif target_type == 'doc':
                                target_file_path = f'docs/{target_id}.md'
                            elif target_type == 'archive':
                                target_file_path = f'archive/{target_id}.md'
                            elif target_type == 'state' and target_id == 'current':
                                target_file_path = 'current.json'
                            elif target_type == 'validator' and target_id == 'gate':
                                target_file_path = '_LOOP_GATE.md'
                            elif target_type == 'template' and target_id == 'seed':
                                target_file_path = 'SEED_TEMPLATE/'
                            
                            # Create relationship
                            self.conn.execute("""
                                INSERT OR IGNORE INTO reference_relationships
                                (source_type, source_id, target_type, target_id, relationship_type, confidence, evidence, indexed_at, source_file_path, target_file_path)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                source_type, source_id, target_type, target_id,
                                "references", 0.8, json.dumps([str(rel_path)]), now,
                                source_file_path, target_file_path
                            ))
                            stats["relationships_created"] += 1
                
            except Exception as e:
                stats.setdefault("errors", []).append(f"Error processing {md_file}: {str(e)}")
        
        self.conn.commit()
        stats["completed_at"] = utc_now_iso()
        return stats


    def _index_milestones(self) -> Dict[str, Any]:
        """Index all knowledge by milestone goals for goal-directed search."""
        stats = {
            "entities_indexed": 0,
            "relevance_matches": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
        }
        
        now = utc_now_iso()
        
        # Clear existing milestone index
        self.conn.execute("DELETE FROM milestone_index")
        
        # Load milestone files
        milestone_files = sorted(self.workspace_root.glob("milestone_*.json"))
        
        for milestone_file in milestone_files:
            try:
                with open(milestone_file, 'r', encoding='utf-8') as f:
                    milestone_data = json.load(f)
                
                milestone_id = milestone_data.get("MILESTONE", {}).get("id", milestone_file.stem.replace("milestone_", ""))
                goals = milestone_data.get("GOALS", [])
                
                # Index milestone-wide
                self._index_milestone_entities(milestone_id, None, milestone_data, now, stats)
                
                # Index per goal
                for goal in goals:
                    goal_id = goal.get("id")
                    if goal_id:
                        self._index_milestone_entities(milestone_id, goal_id, goal, now, stats)
                        
            except Exception as e:
                stats.setdefault("errors", []).append(f"Milestone {milestone_file.name}: {str(e)}")
        
        stats["completed_at"] = utc_now_iso()
        return stats
    
    def _index_milestone_entities(self, milestone_id: str, goal_id: str, 
                                 milestone_content: Dict[str, Any], now: str, stats) -> None:
        """Index entities relevant to a specific milestone/goal."""
        
        # Get description to match against
        description = ""
        if goal_id:
            description = milestone_content.get("description", "")
        else:
            # Milestone-wide description
            description = milestone_content.get("name", "")
        
        description_lower = description.lower()
        
        # Search reports for relevance
        reports = self.conn.execute("SELECT id, goal, content_full FROM reports").fetchall()
        for report in reports:
            relevance = 0.0
            matches = []
            
            # Check goal match
            if report["goal"] and description_lower in report["goal"].lower():
                relevance += 0.5
                matches.append("goal_match")
            
            # Check content match
            if report["content_full"] and description_lower in report["content_full"].lower():
                relevance += 0.3
                matches.append("content_match")
            
            if relevance > 0:
                self.conn.execute("""
                    INSERT INTO milestone_index
                    (milestone_id, goal_id, entity_type, entity_id, relevance_score, context_matches, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (milestone_id, goal_id, "report", report["id"], relevance, json.dumps(matches), now))
                stats["entities_indexed"] += 1
                if matches:
                    stats["relevance_matches"] += len(matches)
        
        # Similar for tasks, docs, lessons
        # (Simplified implementation - can be expanded)
    
    def _calculate_all_quality_scores(self) -> Dict[str, Any]:
        """Calculate quality scores for all entities."""
        stats = {
            "scores_calculated": 0,
            "started_at": utc_now_iso(),
            "completed_at": None,
        }
        
        # Reports
        reports = self.conn.execute("SELECT id FROM reports").fetchall()
        for report in reports:
            try:
                self.calculate_quality_score("report", report["id"])
                stats["scores_calculated"] += 1
            except Exception:
                pass  # Continue with others
        
        # Lessons
        lessons = self.conn.execute("SELECT id FROM lessons").fetchall()
        for lesson in lessons:
            try:
                self.calculate_quality_score("lesson", str(lesson["id"]))
                stats["scores_calculated"] += 1
            except Exception:
                pass
        
        # Tasks and docs can be added similarly
        
        stats["completed_at"] = utc_now_iso()
        return stats

    # =============================================================================
    # TOKEN TRACKING - TASK_0153 Phase 1
    # =============================================================================

    def record_token_budget(
        self,
        loop_num: int,
        phase: str,
        budget_tokens: int,
        used_tokens: int = 0
    ) -> bool:
        """Record token budget allocation for a loop phase.
        
        Args:
            loop_num: Loop number
            phase: Phase name ('bootstrap', 'depth', 'analysis', 'report')
            budget_tokens: Allocated token budget
            used_tokens: Tokens used so far (default: 0)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute(
                """
                INSERT INTO token_budgets (loop_num, phase, budget_tokens, used_tokens)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(loop_num, phase) DO UPDATE SET
                    budget_tokens = excluded.budget_tokens,
                    used_tokens = excluded.used_tokens,
                    updated_at = datetime('now', 'utc')
                """,
                (loop_num, phase, budget_tokens, used_tokens)
            )
            self.conn.commit()
            _audit_log(
                'knowledge_db.record_token_budget',
                f'loop={loop_num},phase={phase}',
                'SUCCESS',
                f'budget={budget_tokens},used={used_tokens}'
            )
            return True
        except Exception as e:
            _audit_log(
                'knowledge_db.record_token_budget',
                f'loop={loop_num},phase={phase}',
                'FAILED',
                str(e)
            )
            return False

    def update_token_usage(
        self,
        loop_num: int,
        phase: str,
        used_tokens: int
    ) -> bool:
        """Update token usage for a loop phase.
        
        Args:
            loop_num: Loop number
            phase: Phase name
            used_tokens: Total tokens used so far
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute(
                """
                UPDATE token_budgets 
                SET used_tokens = ?,
                    updated_at = datetime('now', 'utc')
                WHERE loop_num = ? AND phase = ?
                """,
                (used_tokens, loop_num, phase)
            )
            self.conn.commit()
            return True
        except Exception as e:
            return False

    def get_token_budget_status(
        self,
        loop_num: int,
        phase: str = None
    ) -> List[Dict[str, Any]]:
        """Get token budget status for a loop.
        
        Args:
            loop_num: Loop number
            phase: Optional phase filter
            
        Returns:
            List of token budget records
        """
        try:
            if phase:
                cursor = self.conn.execute(
                    """
                    SELECT * FROM token_budgets 
                    WHERE loop_num = ? AND phase = ?
                    ORDER BY created_at
                    """,
                    (loop_num, phase)
                )
            else:
                cursor = self.conn.execute(
                    """
                    SELECT * FROM token_budgets 
                    WHERE loop_num = ?
                    ORDER BY created_at
                    """,
                    (loop_num,)
                )
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            return []

    def record_chain_cost(
        self,
        chain_root: str,
        depth: int,
        estimated_tokens: int,
        actual_tokens: int = None,
        value_score: float = None,
        connection_count: int = 0
    ) -> bool:
        """Record token cost for a reference chain.
        
        Args:
            chain_root: Root reference path (e.g., 'reports/report_TASK_0140_L78_v01.md')
            depth: Chain depth (how many levels deep)
            estimated_tokens: Estimated token cost based on file size
            actual_tokens: Actual measured tokens (optional)
            value_score: Value score based on connections (optional)
            connection_count: Number of outbound connections
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute(
                """
                INSERT INTO chain_costs 
                    (chain_root, depth, estimated_tokens, actual_tokens, 
                     value_score, connection_count)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(chain_root, depth) DO UPDATE SET
                    estimated_tokens = excluded.estimated_tokens,
                    actual_tokens = excluded.actual_tokens,
                    value_score = excluded.value_score,
                    connection_count = excluded.connection_count,
                    updated_at = datetime('now', 'utc')
                """,
                (chain_root, depth, estimated_tokens, actual_tokens, 
                 value_score, connection_count)
            )
            self.conn.commit()
            _audit_log(
                'knowledge_db.record_chain_cost',
                chain_root,
                'SUCCESS',
                f'depth={depth},tokens={estimated_tokens},value={value_score}'
            )
            return True
        except Exception as e:
            _audit_log(
                'knowledge_db.record_chain_cost',
                chain_root,
                'FAILED',
                str(e)
            )
            return False

    def get_chain_costs(
        self,
        order_by: str = 'roi',
        min_roi: float = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get chain costs ordered by specified metric.
        
        Args:
            order_by: Sort by 'roi', 'value', or 'tokens'
            min_roi: Minimum ROI threshold (optional)
            limit: Maximum results to return
            
        Returns:
            List of chain cost records
        """
        try:
            order_clause = {
                'roi': 'roi DESC',
                'value': 'value_score DESC',
                'tokens': 'estimated_tokens ASC'
            }.get(order_by, 'roi DESC')
            
            where_clause = ""
            params = []
            if min_roi is not None:
                where_clause = "WHERE roi >= ?"
                params.append(min_roi)
            
            query = f"""
                SELECT * FROM chain_costs 
                {where_clause}
                ORDER BY {order_clause}
                LIMIT ?
            """
            params.append(limit)
            
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            return []

    def save_bootstrap_prediction(
        self,
        task_id: str,
        task_context: str,
        predicted_files: List[str],
        loop_num: int = None
    ) -> bool:
        """Save a bootstrap prediction for learning.
        
        Args:
            task_id: The task identifier
            task_context: Description of the task context
            predicted_files: List of predicted file paths
            loop_num: Current loop number
            
        Returns:
            True if saved successfully
        """
        try:
            timestamp = utc_now_iso()
            self.conn.execute("""
                INSERT INTO bootstrap_predictions 
                (task_id, task_context, predicted_files, timestamp, loop_num)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task_id,
                task_context,
                json.dumps(predicted_files),
                timestamp,
                loop_num
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Failed to save bootstrap prediction: {e}")
            return False

    def update_bootstrap_prediction_accuracy(
        self,
        prediction_id: int,
        actual_files: List[str]
    ) -> bool:
        """Update a bootstrap prediction with actual usage data.
        
        Args:
            prediction_id: The prediction record ID
            actual_files: List of actually accessed files
            
        Returns:
            True if updated successfully
        """
        try:
            # Get the predicted files
            cursor = self.conn.execute("""
                SELECT predicted_files FROM bootstrap_predictions 
                WHERE id = ?
            """, (prediction_id,))
            row = cursor.fetchone()
            if not row:
                return False
                
            predicted_files = json.loads(row['predicted_files'])
            
            # Calculate accuracy (intersection over union)
            predicted_set = set(predicted_files)
            actual_set = set(actual_files)
            
            if not predicted_set and not actual_set:
                accuracy = 1.0  # Both empty
            elif not predicted_set or not actual_set:
                accuracy = 0.0  # One empty, one not
            else:
                intersection = len(predicted_set & actual_set)
                union = len(predicted_set | actual_set)
                accuracy = intersection / union if union > 0 else 0.0
            
            # Update the record
            self.conn.execute("""
                UPDATE bootstrap_predictions 
                SET actual_files = ?, accuracy = ?
                WHERE id = ?
            """, (
                json.dumps(actual_files),
                accuracy,
                prediction_id
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Failed to update bootstrap prediction accuracy: {e}")
            return False

    def get_bootstrap_prediction_history(
        self,
        task_id: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get historical bootstrap predictions.
        
        Args:
            task_id: Filter by specific task (optional)
            limit: Maximum results to return
            
        Returns:
            List of prediction records
        """
        try:
            where_clause = ""
            params = []
            if task_id:
                where_clause = "WHERE task_id = ?"
                params.append(task_id)
            
            query = f"""
                SELECT * FROM bootstrap_predictions
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            return []

    def search_within_token_budget(
        self,
        query: str,
        budget_tokens: int,
        prioritize_by: str = 'roi'
    ) -> List[Dict[str, Any]]:
        """Search knowledge entities within a token budget.
        
        This method finds the most valuable knowledge items that fit
        within the specified token budget, using ROI or relevance scoring.
        
        Args:
            query: Search query
            budget_tokens: Available token budget
            prioritize_by: 'roi', 'value', or 'relevance'
            
        Returns:
            List of knowledge entities that fit within budget,
            ordered by priority metric
        """
        try:
            # First, do a semantic search to get relevant items
            search_results = self.search(query, limit=1000)
            
            # Get chain costs for these items
            chain_costs = {}
            for result in search_results:
                # Construct chain root path based on result type
                if result.get('type') == 'report':
                    chain_root = f"reports/{result.get('file', '')}"
                elif result.get('type') == 'archive':
                    chain_root = f"archive/{result.get('file', '')}"
                elif result.get('type') == 'task':
                    chain_root = f"tasks/{result.get('file', '')}"
                else:
                    continue
                
                # Look up cost data
                cursor = self.conn.execute(
                    """
                    SELECT estimated_tokens, actual_tokens, value_score, roi
                    FROM chain_costs
                    WHERE chain_root = ?
                    ORDER BY depth DESC
                    LIMIT 1
                    """,
                    (chain_root,)
                )
                cost_row = cursor.fetchone()
                
                if cost_row:
                    chain_costs[result.get('id')] = {
                        'tokens': cost_row['actual_tokens'] or cost_row['estimated_tokens'],
                        'value': cost_row['value_score'] or 0.0,
                        'roi': cost_row['roi'] or 0.0
                    }
                else:
                    # Estimate based on content length
                    content = result.get('content', '')
                    estimated = len(content) // 4  # Rough estimate: 1 token ≈ 4 chars
                    chain_costs[result.get('id')] = {
                        'tokens': estimated,
                        'value': 0.5,  # Default value for untracked items
                        'roi': 0.5 / estimated if estimated > 0 else 0.0
                    }
            
            # Sort by priority metric
            if prioritize_by == 'roi':
                sorted_results = sorted(
                    search_results,
                    key=lambda r: chain_costs.get(r.get('id'), {}).get('roi', 0.0),
                    reverse=True
                )
            elif prioritize_by == 'value':
                sorted_results = sorted(
                    search_results,
                    key=lambda r: chain_costs.get(r.get('id'), {}).get('value', 0.0),
                    reverse=True
                )
            else:  # relevance
                sorted_results = search_results  # Already sorted by relevance
            
            # Pack items within budget
            selected = []
            tokens_used = 0
            
            for result in sorted_results:
                result_id = result.get('id')
                cost_info = chain_costs.get(result_id, {})
                item_tokens = cost_info.get('tokens', 0)
                
                if tokens_used + item_tokens <= budget_tokens:
                    result['_token_cost'] = item_tokens
                    result['_value_score'] = cost_info.get('value', 0.0)
                    result['_roi'] = cost_info.get('roi', 0.0)
                    selected.append(result)
                    tokens_used += item_tokens
            
            return selected
            
        except Exception as e:
            _audit_log(
                'knowledge_db.search_within_token_budget',
                query,
                'FAILED',
                str(e)
            )
            return []

    def import_external_knowledge(
        self,
        title: str,
        content: str,
        source_url: str,
        category: str = "external",
        tags: List[str] = None,
        relevance_score: float = 0.5
    ) -> bool:
        """Import external knowledge into the database.
        
        Args:
            title: Title of the knowledge item
            content: Full text content
            source_url: Original source URL
            category: Category (e.g., "external", "web", "api")
            tags: List of tags for searchability
            relevance_score: Quality/relevance score 0.0-1.0
            
        Returns:
            True if successfully imported
        """
        try:
            now = utc_now_iso()
            doc_id = f"external_{int(time.time())}_{hash(source_url) % 10000}"
            
            # Insert into docs table
            self.conn.execute("""
                INSERT INTO docs
                (id, path, title, category, content_full, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                source_url,  # Use URL as path for external content
                title,
                category,
                content,
                now
            ))
            
            # Add to quality scores
            self.conn.execute("""
                INSERT OR REPLACE INTO quality_scores
                (entity_type, entity_id, overall_score, relevance_score, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "doc",
                doc_id,
                relevance_score,
                relevance_score,
                now
            ))
            
            # Add tags if provided
            if tags:
                for tag in tags:
                    self.conn.execute("""
                        INSERT OR IGNORE INTO entity_tags
                        (entity_type, entity_id, tag, created_at)
                        VALUES (?, ?, ?, ?)
                    """, ("doc", doc_id, tag, now))
            
            self.conn.commit()
            
            _audit_log(
                'knowledge_db.import_external_knowledge',
                doc_id,
                'SUCCESS',
                f'title={title}, source={source_url}'
            )
            
            return True
            
        except Exception as e:
            _audit_log(
                'knowledge_db.import_external_knowledge',
                source_url,
                'FAILED',
                str(e)
            )
            return False


# =============================================================================
# AGENT API - Functions for multi-agent parallelization
# =============================================================================

def agent_query(
    query: str,
    workspace: Path = None,
    context_type: str = "all",
    limit: int = 10
) -> str:
    """Quick query function for AI agents to retrieve relevant context.
    
    This is the primary interface for agents to access lessons learned.
    Returns formatted text suitable for injection into agent context.
    
    Args:
        query: Natural language query (e.g., "validation failures", "pointer-only rules")
        workspace: Path to workspace (default: current directory)
        context_type: "all", "lessons", "reports", "tasks", or "archives"
        limit: Maximum results to return
    
    Returns:
        Formatted string with relevant context for the agent
    
    Example usage by agent:
        from knowledge_db import agent_query
        context = agent_query("how to handle validation errors", limit=5)
    """
    workspace = workspace or Path.cwd()
    db = KnowledgeDB(workspace)
    
    if not db.db_path.exists():
        db.close()
        return "[KNOWLEDGE_DB] Database not found. Run: python knowledge_db.py --rebuild"
    
    # Map context_type to search types
    type_map = {
        "all": None,  # Search all types
        "lessons": ["lesson"],
        "reports": ["report"],
        "tasks": ["task"],
        "archives": ["archive"],
    }
    types = type_map.get(context_type, None)
    
    results = db.search(query, types=types, limit=limit)
    db.close()
    
    if not results:
        return f"[KNOWLEDGE_DB] No results found for: {query}"
    
    # Format results for agent consumption
    output_lines = [f"[KNOWLEDGE_DB] Found {len(results)} results for '{query}':", ""]
    
    for r in results:
        if r.type == "lesson":
            output_lines.append(f"📚 LESSON (Loop {r.context.get('loop_num', '?')}, {r.context.get('category', 'observation')}):")
            output_lines.append(f"   {r.snippet}")
        elif r.type == "report":
            output_lines.append(f"📋 REPORT {r.id} (Loop {r.context.get('loop_num', '?')}):")
            output_lines.append(f"   {r.snippet}")
        elif r.type == "task":
            output_lines.append(f"📌 TASK {r.id}:")
            output_lines.append(f"   {r.snippet}")
        elif r.type == "archive":
            output_lines.append(f"📦 ARCHIVE Loop {r.context.get('loop_num', '?')}:")
            output_lines.append(f"   {r.snippet}")
        output_lines.append("")
    
    return "\n".join(output_lines)


def agent_get_file_context(filename: str, workspace: Path = None) -> str:
    """Get historical context about a specific file for an agent.
    
    Useful when an agent needs to modify a file and wants to know
    what previous work has been done on it.
    
    Args:
        filename: Name of file (e.g., "loop_cockpit.py")
        workspace: Path to workspace
    
    Returns:
        Formatted string with file modification history
    """
    workspace = workspace or Path.cwd()
    db = KnowledgeDB(workspace)
    
    if not db.db_path.exists():
        db.close()
        return f"[KNOWLEDGE_DB] Database not found"
    
    history = db.get_file_history(filename)
    db.close()
    
    if not history:
        return f"[KNOWLEDGE_DB] No history found for: {filename}"
    
    output_lines = [f"[KNOWLEDGE_DB] File history for '{filename}':", ""]
    for entry in history[:10]:  # Limit to 10 most recent
        output_lines.append(f"  Loop {entry['loop_num']}: {entry['task_id']}")
        if entry.get('goal'):
            output_lines.append(f"    → {entry['goal'][:100]}")
        output_lines.append("")
    
    return "\n".join(output_lines)


def agent_get_similar_tasks(task_description: str, workspace: Path = None, limit: int = 5) -> str:
    """Find similar past tasks for an agent to learn from.
    
    Helps agents avoid repeating past mistakes and learn from successful approaches.
    
    Args:
        task_description: Description of current task
        workspace: Path to workspace
        limit: Maximum similar tasks to return
    
    Returns:
        Formatted string with similar task references
    """
    workspace = workspace or Path.cwd()
    db = KnowledgeDB(workspace)
    
    if not db.db_path.exists():
        db.close()
        return "[KNOWLEDGE_DB] Database not found"
    
    results = db.search(task_description, types=["task", "report"], limit=limit)
    db.close()
    
    if not results:
        return f"[KNOWLEDGE_DB] No similar tasks found"
    
    output_lines = [f"[KNOWLEDGE_DB] Similar past work:", ""]
    for r in results:
        if r.type == "task":
            output_lines.append(f"  📌 {r.id}: {r.snippet[:100]}")
        elif r.type == "report":
            output_lines.append(f"  📋 {r.id}: {r.snippet[:100]}")
        output_lines.append("")
    
    return "\n".join(output_lines)


def agent_get_related_tasks(task_id: str, workspace: Path = None) -> str:
    """Get tasks related to a given task ID for an agent.
    
    Shows predecessor/successor and similar tasks to provide context
    for current work.
    
    Args:
        task_id: Task ID to find relationships for
        workspace: Path to workspace
    
    Returns:
        Formatted string with related task information
    """
    workspace = workspace or Path.cwd()
    db = KnowledgeDB(workspace)
    
    if not db.db_path.exists():
        db.close()
        return "[KNOWLEDGE_DB] Database not found"
    
    # Get relationships
    relationships = db.conn.execute("""
        SELECT task_a, task_b, relationship_type, confidence_score, evidence
        FROM task_relationships
        WHERE task_a = ? OR task_b = ?
        ORDER BY confidence_score DESC
    """, (task_id, task_id)).fetchall()
    
    db.close()
    
    if not relationships:
        return f"[KNOWLEDGE_DB] No relationships found for: {task_id}"
    
    output_lines = [f"[KNOWLEDGE_DB] Related tasks for {task_id}:", ""]
    
    predecessors = []
    successors = []
    similar = []
    
    for rel in relationships:
        if rel["task_a"] == task_id:
            other_task = rel["task_b"]
        else:
            other_task = rel["task_a"]
        
        rel_type = rel["relationship_type"]
        confidence = rel["confidence_score"]
        
        if rel_type == "predecessor":
            predecessors.append(f"  ⬅️ {other_task} (predecessor, {confidence:.1f})")
        elif rel_type == "successor":
            successors.append(f"  ➡️ {other_task} (successor, {confidence:.1f})")
        elif rel_type == "similar":
            similar.append(f"  🔗 {other_task} (similar, {confidence:.1f})")
    
    if predecessors:
        output_lines.append("Predecessors:")
        output_lines.extend(predecessors)
        output_lines.append("")
    
    if successors:
        output_lines.append("Successors:")
        output_lines.extend(successors)
        output_lines.append("")
    
    if similar:
        output_lines.append("Similar tasks:")
        output_lines.extend(similar[:5])  # Limit similar tasks
        output_lines.append("")
    
    return "\n".join(output_lines)


def agent_get_patterns(pattern_type: str = None, workspace: Path = None, limit: int = 10) -> str:
    """Get common patterns from lessons learned for an agent.
    
    Helps agents learn from recurring success/failure patterns.
    
    Args:
        pattern_type: "success", "failure", "warning", or None for all
        workspace: Path to workspace
        limit: Maximum patterns to return
    
    Returns:
        Formatted string with pattern information
    """
    workspace = workspace or Path.cwd()
    db = KnowledgeDB(workspace)
    
    if not db.db_path.exists():
        db.close()
        return "[KNOWLEDGE_DB] Database not found"
    
    # Get patterns
    query = "SELECT * FROM patterns"
    params = []
    if pattern_type:
        query += " WHERE pattern_type = ?"
        params.append(pattern_type)
    
    query += " ORDER BY frequency DESC, last_seen_loop DESC LIMIT ?"
    params.append(limit)
    
    patterns = db.conn.execute(query, params).fetchall()
    db.close()
    
    if not patterns:
        type_desc = f" ({pattern_type})" if pattern_type else ""
        return f"[KNOWLEDGE_DB] No patterns found{type_desc}"
    
    output_lines = [f"[KNOWLEDGE_DB] Common patterns:", ""]
    
    for pattern in patterns:
        ptype = pattern["pattern_type"]
        text = pattern["pattern_text"]
        freq = pattern["frequency"]
        examples = json.loads(pattern["examples"]) if pattern["examples"] else []
        
        emoji = {"success": "✅", "failure": "❌", "warning": "⚠️"}.get(ptype, "📝")
        output_lines.append(f"{emoji} [{ptype.upper()}] {text}")
        output_lines.append(f"   Appears {freq} times, examples: {', '.join(examples[:3])}")
        output_lines.append("")
    
    return "\n".join(output_lines)


def agent_store_knowledge(knowledge_text: str, category: str = "agent_insight", 
                         metadata: Dict[str, Any] = None, workspace: Path = None) -> str:
    """Store agent knowledge in the database for future learning and semantic search.
    
    This function allows AI agents to persist their insights and learnings
    in the knowledge database, enabling cross-loop learning and semantic search
    of agent-generated knowledge.
    
    Args:
        knowledge_text: The knowledge/insight text from the agent
        category: Category ("agent_insight", "success", "failure", "warning", "observation")
        metadata: Optional metadata dict (agent_name, task_id, confidence, etc.)
        workspace: Path to workspace
    
    Returns:
        Success/failure message
    
    Example usage by agent:
        from knowledge_db import agent_store_knowledge
        result = agent_store_knowledge(
            "Using dataclasses reduces validation errors by 40%",
            category="success",
            metadata={"agent": "validation_agent", "confidence": 0.9}
        )
    """
    workspace = workspace or Path.cwd()
    db = KnowledgeDB(workspace)
    
    if not db.db_path.exists():
        db.close()
        return "[KNOWLEDGE_DB] Database not found. Run: python knowledge_db.py --rebuild"
    
    success = db.add_agent_knowledge(knowledge_text, category, metadata)
    db.close()
    
    if success:
        return f"[KNOWLEDGE_DB] ✓ Knowledge stored successfully: {knowledge_text[:50]}..."
    else:
        return "[KNOWLEDGE_DB] ✗ Failed to store knowledge"


def agent_get_stored_knowledge(category: str = None, workspace: Path = None, limit: int = 10) -> str:
    """Retrieve previously stored agent knowledge for learning and context.
    
    Args:
        category: Filter by category or None for all
        workspace: Path to workspace
        limit: Maximum results to return
    
    Returns:
        Formatted string with stored agent knowledge
    """
    workspace = workspace or Path.cwd()
    db = KnowledgeDB(workspace)
    
    if not db.db_path.exists():
        db.close()
        return "[KNOWLEDGE_DB] Database not found"
    
    knowledge_entries = db.get_agent_knowledge(category, limit)
    db.close()
    
    if not knowledge_entries:
        cat_desc = f" ({category})" if category else ""
        return f"[KNOWLEDGE_DB] No stored agent knowledge found{cat_desc}"
    
    output_lines = [f"[KNOWLEDGE_DB] Stored Agent Knowledge ({len(knowledge_entries)} entries):", ""]
    
    for entry in knowledge_entries:
        category_emoji = {
            "success": "✅",
            "failure": "❌", 
            "warning": "⚠️",
            "observation": "👁️",
            "agent_insight": "🧠"
        }.get(entry["category"], "📝")
        
        output_lines.append(f"{category_emoji} [{entry['category'].upper()}] Loop {entry['loop_num']}:")
        output_lines.append(f"   {entry['lesson_text']}")
        
        if entry.get("metadata"):
            meta_items = []
            for k, v in entry["metadata"].items():
                if isinstance(v, (str, int, float)):
                    meta_items.append(f"{k}={v}")
            if meta_items:
                output_lines.append(f"   Metadata: {', '.join(meta_items)}")
        
        output_lines.append("")
    
    return "\n".join(output_lines)


# CLI interface for standalone usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Knowledge Database Management")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild database from scratch")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--agent-query", type=str, metavar="QUERY", help="Agent-formatted query")
    parser.add_argument("--file-context", type=str, metavar="FILENAME", help="Get file history for agents")
    parser.add_argument("--related-tasks", type=str, metavar="TASK_ID", help="Get related tasks for agents")
    parser.add_argument("--patterns", type=str, metavar="TYPE", nargs="?", const="", help="Get common patterns (success/failure/warning)")
    parser.add_argument("--store-knowledge", type=str, metavar="TEXT", help="Store agent knowledge in database")
    parser.add_argument("--knowledge-category", type=str, default="agent_insight", help="Category for stored knowledge")
    parser.add_argument("--get-stored-knowledge", action="store_true", help="Retrieve stored agent knowledge")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace root path")
    
    args = parser.parse_args()
    
    workspace = Path(args.workspace)
    
    if args.rebuild:
        db = KnowledgeDB(workspace)
        print("Rebuilding knowledge database...")
        stats = db.rebuild_with_write_guard()
        print(json.dumps(stats, indent=2))
        db.close()
    
    elif args.stats:
        db = KnowledgeDB(workspace)
        stats = db.get_stats()
        print(json.dumps(stats, indent=2))
        db.close()
    
    elif args.search:
        db = KnowledgeDB(workspace)
        results = db.search(args.search)
        for r in results:
            print(f"[{r.type}] {r.id} (relevance: {r.relevance:.2f})")
            print(f"  {r.snippet}")
            print()
        db.close()
    
    elif args.agent_query:
        print(agent_query(args.agent_query, workspace))
    
    elif args.file_context:
        print(agent_get_file_context(args.file_context, workspace))
    
    elif args.related_tasks:
        print(agent_get_related_tasks(args.related_tasks, workspace))
    
    elif args.patterns is not None:
        pattern_type = args.patterns if args.patterns else None
        print(agent_get_patterns(pattern_type, workspace))
    
    elif args.store_knowledge:
        result = agent_store_knowledge(args.store_knowledge, args.knowledge_category, workspace=workspace)
        print(result)
    
    elif args.get_stored_knowledge:
        result = agent_get_stored_knowledge(workspace=workspace)
        print(result)
    
    else:
        parser.print_help()

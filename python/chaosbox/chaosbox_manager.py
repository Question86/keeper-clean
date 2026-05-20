#!/usr/bin/env python3
"""
Chaosbox Manager - Quality Control Pipeline for Seed Ideas

Manages the intake, validation, transformation, and queuing of seed ideas
before they become formal tasks. Provides quality control and structured
processing to ensure only well-formed, valuable ideas enter the development pipeline.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import time

class IdeaStatus(Enum):
    """Status of an idea in the chaosbox pipeline."""
    RECEIVED = "received"
    VALIDATING = "validating"
    TRANSFORMING = "transforming"
    QUEUED = "queued"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"

class RejectionReason(Enum):
    """Reasons why an idea might be rejected."""
    DUPLICATE = "duplicate"
    INFEASIBLE = "infeasible"
    OUT_OF_SCOPE = "out_of_scope"
    LOW_PRIORITY = "low_priority"
    MALFORMED = "malformed"
    INSUFFICIENT_DETAIL = "insufficient_detail"

@dataclass
class SeedIdea:
    """Represents a raw seed idea submission."""
    idea_id: str
    title: str
    description: str
    submitted_by: str
    submitted_at: str
    tags: List[str]
    metadata: Dict[str, Any]
    status: IdeaStatus
    quality_score: Optional[float] = None
    rejection_reason: Optional[RejectionReason] = None
    transformed_task: Optional[Dict[str, Any]] = None
    processing_history: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.processing_history is None:
            self.processing_history = []

class ChaosboxManager:
    """Main orchestrator for the seed idea quality control pipeline."""

    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.chaosbox_dir = self.workspace / "chaosbox"
        self.chaosbox_dir.mkdir(exist_ok=True)

        self.ideas_dir = self.chaosbox_dir / "ideas"
        self.ideas_dir.mkdir(exist_ok=True)

        self.queue_dir = self.chaosbox_dir / "queue"
        self.queue_dir.mkdir(exist_ok=True)
        self.quality_threshold = float(os.getenv("CHAOSBOX_MIN_QUALITY", "0.5"))

        # Processing queue for asynchronous operations
        self.processing_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False

        # Import components (lazy loading to avoid circular imports)
        self._validation_engine = None
        self._transformation_pipeline = None
        self._quality_scorer = None

    @property
    def validation_engine(self):
        if self._validation_engine is None:
            from chaosbox.validation_engine import ValidationEngine
            self._validation_engine = ValidationEngine()
        return self._validation_engine

    @property
    def transformation_pipeline(self):
        if self._transformation_pipeline is None:
            from chaosbox.transformation_pipeline import TransformationPipeline
            self._transformation_pipeline = TransformationPipeline(workspace_root=str(self.workspace))
        return self._transformation_pipeline

    @property
    def quality_scorer(self):
        if self._quality_scorer is None:
            from chaosbox.quality_scorer import QualityScorer
            self._quality_scorer = QualityScorer()
        return self._quality_scorer

    def start_processing(self):
        """Start the asynchronous processing worker."""
        if self.is_running:
            return

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._processing_worker, daemon=True)
        self.worker_thread.start()

    def stop_processing(self):
        """Stop the asynchronous processing worker."""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

    def submit_idea(self, title: str, description: str, submitted_by: str = "user",
                   tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """
        Submit a new seed idea to the chaosbox for processing.

        Args:
            title: Brief title of the idea
            description: Detailed description
            submitted_by: Who submitted the idea
            tags: Optional tags for categorization
            metadata: Additional metadata

        Returns:
            Unique idea ID
        """
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}

        idea_id = f"idea_{int(datetime.now(timezone.utc).timestamp())}_{hash(title) % 10000:04d}"

        idea = SeedIdea(
            idea_id=idea_id,
            title=title,
            description=description,
            submitted_by=submitted_by,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            tags=tags,
            metadata=metadata,
            status=IdeaStatus.RECEIVED
        )

        # Save idea to disk
        self._save_idea(idea)

        # Add to processing queue
        self.processing_queue.put(idea_id)

        # Start processing if not already running
        self.start_processing()

        return idea_id

    def get_idea_status(self, idea_id: str) -> Optional[SeedIdea]:
        """Get the current status of an idea."""
        return self._load_idea(idea_id)

    def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the chaosbox queue."""
        ideas = self._load_all_ideas()

        status_counts = {}
        for status in IdeaStatus:
            status_counts[status.value] = 0

        for idea in ideas:
            status_counts[idea.status.value] += 1

        # Get queue size
        queue_size = self.processing_queue.qsize()

        return {
            "total_ideas": len(ideas),
            "status_counts": status_counts,
            "queue_size": queue_size,
            "is_processing": self.is_running,
            "recent_ideas": [
                {
                    "id": idea.idea_id,
                    "title": idea.title,
                    "status": idea.status.value,
                    "submitted_at": idea.submitted_at,
                    "quality_score": idea.quality_score
                }
                for idea in sorted(ideas, key=lambda x: x.submitted_at, reverse=True)[:10]
            ]
        }

    def _processing_worker(self):
        """Background worker for processing ideas through the pipeline."""
        while self.is_running:
            try:
                # Get next idea to process (with timeout)
                idea_id = self.processing_queue.get(timeout=1)

                # Process the idea
                self._process_idea(idea_id)

                self.processing_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing idea: {e}")
                # Continue processing other ideas

    def _process_idea(self, idea_id: str):
        """Process a single idea through the quality control pipeline."""
        idea = self._load_idea(idea_id)
        if not idea:
            return

        try:
            # Step 1: Validation
            idea.status = IdeaStatus.VALIDATING
            self._save_idea(idea)

            validation_result = self.validation_engine.validate_idea(idea)
            idea.processing_history.append({
                "stage": "validation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": validation_result
            })

            if not validation_result["passed"]:
                idea.status = IdeaStatus.REJECTED
                idea.rejection_reason = RejectionReason(validation_result["reason"])
                self._save_idea(idea)
                return

            # Step 2: Quality Scoring
            quality_result = self.quality_scorer.score_idea(idea)
            idea.quality_score = quality_result["composite_score"]
            idea.processing_history.append({
                "stage": "quality_scoring",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": quality_result
            })

            # Check quality threshold
            if quality_result["composite_score"] < self.quality_threshold:
                idea.status = IdeaStatus.REJECTED
                idea.rejection_reason = RejectionReason.LOW_PRIORITY
                self._save_idea(idea)
                return

            # Step 3: Transformation
            idea.status = IdeaStatus.TRANSFORMING
            self._save_idea(idea)

            transformation_result = self.transformation_pipeline.transform_idea(idea)
            idea.transformed_task = transformation_result["task_spec"]
            idea.processing_history.append({
                "stage": "transformation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": transformation_result
            })

            # Step 4: Queue for integration
            idea.status = IdeaStatus.QUEUED
            self._save_idea(idea)

            # Create task from transformed spec
            task_spec = idea.transformed_task
            task_id = task_spec["task_id"]

            # Create task file
            tasks_dir = Path(self.workspace) / "tasks"
            tasks_dir.mkdir(exist_ok=True)
            task_file = tasks_dir / f"task_{task_id}.md"

            task_content = f"""# {task_id}

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

---

## SEED IDEA

{idea.description}

---

## OBJECTIVE

{task_spec.get('objective', '')}

---

## TASK_TYPE

{task_spec.get('task_type', '')}

---

## ACCEPTANCE CRITERIA

{task_spec.get('acceptance_criteria', '')}

---

## NOTES

Created via Chaosbox quality control pipeline.
Idea ID: {idea.idea_id}
Quality Score: {idea.quality_score}

---

END OF DOCUMENT
"""

            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(task_content)

            # Add to NEU.md
            neu_md = Path(self.workspace) / "NEU.md"
            if neu_md.exists():
                neu_content = neu_md.read_text(encoding='utf-8')
            else:
                neu_content = "# NEU\n\n## TASK QUEUE\n\n(Empty - all tasks completed)\n"
            neu_lines = neu_content.split('\n')

            task_ref_path = f"tasks/task_{task_id}.md"
            task_ref = f"[ref:{task_ref_path}|v:1|tags:new,chaosbox|src:user] - {idea.title[:80]}{'...' if len(idea.title) > 80 else ''}"

            # Insert under TASK QUEUE header
            insert_idx = None
            for i, line in enumerate(neu_lines):
                if line.strip().startswith('## TASK QUEUE'):
                    insert_idx = i + 2
                    break

            if insert_idx is not None:
                # Replace empty marker if present
                for j in range(insert_idx, min(insert_idx + 5, len(neu_lines))):
                    if '(Empty - all tasks completed)' in neu_lines[j] or 'No active tasks' in neu_lines[j]:
                        neu_lines[j] = task_ref
                        neu_lines.insert(j + 1, '')
                        break
                else:
                    neu_lines.insert(insert_idx, task_ref)
                    neu_lines.insert(insert_idx + 1, '')
            else:
                # Fallback: append
                neu_lines.append('')
                neu_lines.append(task_ref)

            neu_md.write_text('\n'.join(neu_lines), encoding='utf-8')

            # Mark idea as accepted
            idea.status = IdeaStatus.ACCEPTED
            self._save_idea(idea)

        except Exception as e:
            idea.status = IdeaStatus.ERROR
            idea.processing_history.append({
                "stage": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            })
            self._save_idea(idea)

    def _save_idea(self, idea: SeedIdea):
        """Save idea to disk."""
        idea_file = self.ideas_dir / f"{idea.idea_id}.json"
        with open(idea_file, 'w', encoding='utf-8') as f:
            # Convert enums to strings for JSON serialization
            data = asdict(idea)
            data["status"] = idea.status.value
            if idea.rejection_reason:
                data["rejection_reason"] = idea.rejection_reason.value
            
            # Convert any enums in processing_history
            for history_item in data.get("processing_history", []):
                if "result" in history_item and isinstance(history_item["result"], dict):
                    result = history_item["result"]
                    if "reason" in result and hasattr(result["reason"], "value"):
                        result["reason"] = result["reason"].value
            
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_idea(self, idea_id: str) -> Optional[SeedIdea]:
        """Load idea from disk."""
        idea_file = self.ideas_dir / f"{idea_id}.json"
        if not idea_file.exists():
            return None

        with open(idea_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert strings back to enums with backward-compatible fallbacks.
        raw_status = data.get("status")
        try:
            data["status"] = IdeaStatus(raw_status)
        except Exception:
            # Some legacy records stored rejection reasons in status.
            try:
                rr = RejectionReason(raw_status)
                data["status"] = IdeaStatus.REJECTED
                data["rejection_reason"] = rr
            except Exception:
                data["status"] = IdeaStatus.ERROR

        if data.get("rejection_reason"):
            try:
                data["rejection_reason"] = RejectionReason(data["rejection_reason"])
            except Exception:
                data["rejection_reason"] = None

        return SeedIdea(**data)

    def _load_all_ideas(self) -> List[SeedIdea]:
        """Load all ideas from disk."""
        ideas = []
        for idea_file in self.ideas_dir.glob("*.json"):
            idea = self._load_idea(idea_file.stem)
            if idea:
                ideas.append(idea)
        return ideas

# Global instance for API access
_chaosbox_manager = None

def get_chaosbox_manager() -> ChaosboxManager:
    """Get the global chaosbox manager instance."""
    global _chaosbox_manager
    if _chaosbox_manager is None:
        _chaosbox_manager = ChaosboxManager()
    return _chaosbox_manager

# API Functions for loop_cockpit.py integration
def submit_seed_idea(title: str, description: str, submitted_by: str = "user",
                    tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
    """API function to submit a seed idea."""
    manager = get_chaosbox_manager()
    return manager.submit_idea(title, description, submitted_by, tags, metadata)

def get_chaosbox_status() -> Dict[str, Any]:
    """API function to get chaosbox status."""
    manager = get_chaosbox_manager()
    return manager.get_queue_status()

def get_idea_details(idea_id: str) -> Optional[Dict[str, Any]]:
    """API function to get idea details."""
    manager = get_chaosbox_manager()
    idea = manager.get_idea_status(idea_id)
    if idea:
        data = asdict(idea)
        data["status"] = idea.status.value
        if idea.rejection_reason:
            data["rejection_reason"] = idea.rejection_reason.value
        return data

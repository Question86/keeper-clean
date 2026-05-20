#!/usr/bin/env python3
"""
Git Checkpoint Manager

TASK_0157: Automatic work-in-progress commits during loop execution
Implements strategic git checkpoints to prevent data loss and enable rollback.

Features:
- Time-based auto-commits (every 60 minutes)
- Phase-based manual commits (after major milestones)
- Standardized WIP commit format
- Integration with loop cockpit for automatic triggering
"""

import os
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages automatic git checkpoints during loop execution."""

    def __init__(self, workspace_root: Path, loop_num: int):
        self.workspace_root = workspace_root
        self.loop_num = loop_num
        self.checkpoint_count = 0
        self.last_commit_time = time.time()
        self.phase_checkpoints = {}
        self._ensure_git_repo()

    def _ensure_git_repo(self) -> bool:
        """Ensure we're in a git repository."""
        try:
            # Check if we're in a git repo
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Git not available or not in a git repository")
            return False

    def should_checkpoint(self, elapsed_minutes: int = 60) -> bool:
        """Determine if a checkpoint should be created based on time elapsed."""
        elapsed = time.time() - self.last_commit_time
        return elapsed >= (elapsed_minutes * 60)

    def create_checkpoint(self, summary: str, phase: Optional[str] = None,
                         force: bool = False) -> bool:
        """
        Create a WIP commit checkpoint.

        Args:
            summary: Brief description of work completed
            phase: Current phase (e.g., "Phase 1", "Phase 2")
            force: Force commit even if no changes

        Returns:
            True if checkpoint was created, False otherwise
        """
        if not self._ensure_git_repo():
            logger.warning("Cannot create checkpoint: not in a git repository")
            return False

        try:
            # Check for changes to commit
            if not force:
                result = subprocess.run(
                    ['git', 'status', '--porcelain'],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if not result.stdout.strip():
                    logger.info("No changes to commit for checkpoint")
                    return False

            # Stage all changes
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=self.workspace_root,
                capture_output=True,
                timeout=60
            )

            # Create commit
            commit_message = self._format_commit_message(summary, phase)
            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.checkpoint_count += 1
                self.last_commit_time = time.time()
                if phase:
                    self.phase_checkpoints[phase] = self.checkpoint_count

                logger.info(f"Created checkpoint {self.checkpoint_count}: {commit_message[:50]}...")
                self._log_checkpoint(summary, phase)
                return True
            else:
                logger.warning(f"Failed to create checkpoint: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Checkpoint creation timed out")
            return False
        except Exception as e:
            logger.error(f"Error creating checkpoint: {e}")
            return False

    def _format_commit_message(self, summary: str, phase: Optional[str]) -> str:
        """Format a standardized WIP commit message."""
        phase_str = f" - {phase}" if phase else ""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")

        return f"""WIP: Loop {self.loop_num}{phase_str} (checkpoint {self.checkpoint_count + 1})

{summary}

Status: In progress ({timestamp})
Next: {phase or 'Continuing work'}
"""

    def _log_checkpoint(self, summary: str, phase: Optional[str]) -> None:
        """Log checkpoint creation for audit trail."""
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "loop_num": self.loop_num,
                "checkpoint_num": self.checkpoint_count,
                "phase": phase,
                "summary": summary,
                "type": "automatic" if not phase else "phase_milestone"
            }

            log_path = self.workspace_root / "checkpoint_log.jsonl"
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry}\n")

        except Exception as e:
            logger.warning(f"Failed to log checkpoint: {e}")

    def get_checkpoint_stats(self) -> Dict[str, Any]:
        """Get statistics about checkpoints created."""
        return {
            "total_checkpoints": self.checkpoint_count,
            "last_commit_time": self.last_commit_time,
            "phase_checkpoints": self.phase_checkpoints,
            "time_since_last": time.time() - self.last_commit_time
        }

    def force_checkpoint(self, reason: str) -> bool:
        """Force create a checkpoint for critical moments."""
        return self.create_checkpoint(
            f"Emergency checkpoint: {reason}",
            force=True
        )


# Global checkpoint manager instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager(loop_num: Optional[int] = None) -> CheckpointManager:
    """Get or create the global checkpoint manager."""
    global _checkpoint_manager

    if _checkpoint_manager is None and loop_num is not None:
        workspace_root = Path.cwd()
        _checkpoint_manager = CheckpointManager(workspace_root, loop_num)

    return _checkpoint_manager


def initialize_checkpoints(loop_num: int) -> None:
    """Initialize checkpointing for a new loop."""
    global _checkpoint_manager
    workspace_root = Path.cwd()
    _checkpoint_manager = CheckpointManager(workspace_root, loop_num)
    logger.info(f"Initialized checkpointing for Loop {loop_num}")


def create_phase_checkpoint(phase: str, summary: str) -> bool:
    """Create a checkpoint at phase completion."""
    manager = get_checkpoint_manager()
    if manager:
        return manager.create_checkpoint(summary, phase)
    return False


def check_and_create_checkpoint() -> bool:
    """Check if checkpoint is needed and create if so."""
    manager = get_checkpoint_manager()
    if manager and manager.should_checkpoint():
        return manager.create_checkpoint("Automatic time-based checkpoint")
    return False
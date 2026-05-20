#!/usr/bin/env python3
"""
AI Breadcrumb Tracking System

Implements TASK_0174: AI Decision Path Tracking
Creates unique breadcrumb trails for AI logical navigation through the codebase.

This system passively tracks the AI's decision-making path by embedding unique
hash-based references in files that indicate the source context that led to
each file access or creation. These breadcrumbs can be extracted later to
map the AI's logical flow over time.

Architecture:
- Unique hash-based breadcrumbs tied to source context
- Automatic injection on file access/creation
- Extractable by scripts for path analysis
- Integrated with existing hash validation system
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone


@dataclass
class Breadcrumb:
    """Represents a single breadcrumb in the AI's decision path."""
    target_file: str
    source_context: str
    timestamp: str
    breadcrumb_hash: str
    operation: str  # 'access', 'create', 'modify'
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'target_file': self.target_file,
            'source_context': self.source_context,
            'timestamp': self.timestamp,
            'breadcrumb_hash': self.breadcrumb_hash,
            'operation': self.operation,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Breadcrumb':
        # Handle both snake_case and camelCase formats for backward compatibility
        return cls(
            target_file=data.get('target_file') or data.get('targetFile'),
            source_context=data.get('source_context') or data.get('sourceContext'),
            timestamp=data['timestamp'],
            breadcrumb_hash=data.get('breadcrumb_hash') or data.get('breadcrumbHash'),
            operation=data['operation'],
            metadata=data.get('metadata', {})
        )


class AIBreadcrumbTracker:
    """Tracks AI decision paths through unique breadcrumb references."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.breadcrumb_log = workspace_root / "breadcrumb_trail.jsonl"
        self.current_context: Optional[str] = None

    def _generate_breadcrumb_hash(self, target_file: str, source_context: str, timestamp: str) -> str:
        """Generate a unique hash for this breadcrumb using SHA256."""
        content = f"{target_file}|{source_context}|{timestamp}|{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]  # Short hash for readability

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def set_current_context(self, context: str) -> None:
        """Set the current source context for future breadcrumbs."""
        self.current_context = context

    def create_breadcrumb(self, target_file: str, operation: str, metadata: Dict[str, Any] = None) -> Breadcrumb:
        """Create a new breadcrumb for a file operation."""
        if not self.current_context:
            # Default context if none set
            self.current_context = "unknown_context"

        timestamp = self._get_timestamp()
        breadcrumb_hash = self._generate_breadcrumb_hash(target_file, self.current_context, timestamp)

        breadcrumb = Breadcrumb(
            target_file=target_file,
            source_context=self.current_context,
            timestamp=timestamp,
            breadcrumb_hash=breadcrumb_hash,
            operation=operation,
            metadata=metadata or {}
        )

        # Log the breadcrumb
        self._log_breadcrumb(breadcrumb)

        return breadcrumb

    def _log_breadcrumb(self, breadcrumb: Breadcrumb) -> None:
        """Log breadcrumb to the trail file."""
        try:
            with open(self.breadcrumb_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(breadcrumb.to_dict()) + '\n')
        except Exception:
            # Don't fail if logging fails
            pass

    def inject_breadcrumb_into_file(self, file_path: Path, breadcrumb: Breadcrumb) -> bool:
        """Inject breadcrumb reference into a file as a comment."""
        try:
            content = file_path.read_text(encoding='utf-8')

            # Create breadcrumb comment
            breadcrumb_comment = f"<!-- AI_BREADCRUMB: {breadcrumb.breadcrumb_hash} | SRC: {breadcrumb.source_context} | OP: {breadcrumb.operation} | TS: {breadcrumb.timestamp} -->\n"

            # For Python files
            if file_path.suffix == '.py':
                if not content.startswith('"""') and not content.startswith("'''"):
                    # Add at the top
                    new_content = f'"""\nAI Breadcrumb: {breadcrumb.breadcrumb_hash}\nSource: {breadcrumb.source_context}\nOperation: {breadcrumb.operation}\nTimestamp: {breadcrumb.timestamp}\n"""\n\n{content}'
                else:
                    # Insert after existing docstring
                    lines = content.split('\n')
                    docstring_end = -1
                    in_docstring = False
                    quote_type = None

                    for i, line in enumerate(lines):
                        if line.strip().startswith('"""') or line.strip().startswith("'''"):
                            if not in_docstring:
                                in_docstring = True
                                quote_type = '"""' if '"""' in line else "'''"
                            elif quote_type in line:
                                docstring_end = i
                                break

                    if docstring_end >= 0:
                        lines.insert(docstring_end + 1, f'# AI_BREADCRUMB: {breadcrumb.breadcrumb_hash} | SRC: {breadcrumb.source_context}')
                        new_content = '\n'.join(lines)
                    else:
                        new_content = content

            # For Markdown files
            elif file_path.suffix == '.md':
                if not content.startswith('<!--'):
                    new_content = breadcrumb_comment + content
                else:
                    # Insert after existing comments
                    lines = content.split('\n')
                    comment_end = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('<!--') and '-->' in line:
                            comment_end = i + 1
                        elif not line.strip().startswith('<!--'):
                            break
                    lines.insert(comment_end, breadcrumb_comment.strip())
                    new_content = '\n'.join(lines)

            # For JSON files
            elif file_path.suffix == '.json':
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and '_ai_breadcrumbs' not in data:
                        data['_ai_breadcrumbs'] = []
                    if isinstance(data, dict):
                        data['_ai_breadcrumbs'].append({
                            'hash': breadcrumb.breadcrumb_hash,
                            'source': breadcrumb.source_context,
                            'operation': breadcrumb.operation,
                            'timestamp': breadcrumb.timestamp
                        })
                        new_content = json.dumps(data, indent=2, ensure_ascii=False)
                    else:
                        new_content = content
                except json.JSONDecodeError:
                    new_content = content

            else:
                # For other files, add as comment if possible
                new_content = content

            # Write back only if content changed
            if new_content != content:
                file_path.write_text(new_content, encoding='utf-8')

            return True

        except Exception:
            return False

    def extract_breadcrumbs_from_file(self, file_path: Path) -> List[Breadcrumb]:
        """Extract all breadcrumbs from a file."""
        breadcrumbs = []

        try:
            content = file_path.read_text(encoding='utf-8')

            # Extract from comments
            import re
            breadcrumb_pattern = r'AI_BREADCRUMB:\s*([a-f0-9]+)\s*\|\s*SRC:\s*([^|]+)\s*\|\s*OP:\s*(\w+)\s*\|\s*TS:\s*([^-\n]+)'
            matches = re.findall(breadcrumb_pattern, content)

            for match in matches:
                hash_val, source, op, ts = match
                breadcrumbs.append(Breadcrumb(
                    target_file=str(file_path.relative_to(self.workspace_root)),
                    source_context=source.strip(),
                    timestamp=ts.strip(),
                    breadcrumb_hash=hash_val,
                    operation=op.strip()
                ))

            # Extract from JSON
            if file_path.suffix == '.json':
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and '_ai_breadcrumbs' in data:
                        for bc_data in data['_ai_breadcrumbs']:
                            breadcrumbs.append(Breadcrumb(
                                target_file=str(file_path.relative_to(self.workspace_root)),
                                source_context=bc_data.get('source', 'unknown'),
                                timestamp=bc_data.get('timestamp', ''),
                                breadcrumb_hash=bc_data.get('hash', ''),
                                operation=bc_data.get('operation', 'unknown')
                            ))
                except json.JSONDecodeError:
                    pass

        except Exception:
            pass

        return breadcrumbs

    def get_breadcrumb_trail(self, target_file: str = None, limit: int = 100) -> List[Breadcrumb]:
        """Get breadcrumb trail, optionally filtered by target file."""
        breadcrumbs = []

        try:
            if self.breadcrumb_log.exists():
                with open(self.breadcrumb_log, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line)
                                bc = Breadcrumb.from_dict(data)
                                if target_file is None or bc.target_file == target_file:
                                    breadcrumbs.append(bc)
                            except json.JSONDecodeError:
                                continue

            # Sort by timestamp, most recent first
            breadcrumbs.sort(key=lambda x: x.timestamp, reverse=True)

        except Exception:
            pass

        return breadcrumbs[:limit]

    def analyze_decision_paths(self) -> Dict[str, Any]:
        """Analyze breadcrumb trails to understand AI decision patterns."""
        all_breadcrumbs = self.get_breadcrumb_trail(limit=1000)

        analysis = {
            'total_breadcrumbs': len(all_breadcrumbs),
            'unique_files': len(set(bc.target_file for bc in all_breadcrumbs)),
            'operation_counts': {},
            'source_contexts': {},
            'temporal_patterns': []
        }

        # Count operations
        for bc in all_breadcrumbs:
            analysis['operation_counts'][bc.operation] = analysis['operation_counts'].get(bc.operation, 0) + 1
            analysis['source_contexts'][bc.source_context] = analysis['source_contexts'].get(bc.source_context, 0) + 1

        return analysis


# Global tracker instance
_breadcrumb_tracker: Optional[AIBreadcrumbTracker] = None


def get_breadcrumb_tracker(workspace_root: Path = None) -> AIBreadcrumbTracker:
    """Get or create the global breadcrumb tracker."""
    global _breadcrumb_tracker

    if workspace_root is None:
        workspace_root = Path.cwd()

    if _breadcrumb_tracker is None or _breadcrumb_tracker.workspace_root != workspace_root:
        _breadcrumb_tracker = AIBreadcrumbTracker(workspace_root)

    return _breadcrumb_tracker


def track_file_access(file_path: str, source_context: str = None) -> None:
    """Track access to a file with breadcrumb."""
    tracker = get_breadcrumb_tracker()

    if source_context:
        tracker.set_current_context(source_context)

    breadcrumb = tracker.create_breadcrumb(file_path, 'access')
    file_obj = Path(file_path)
    if file_obj.exists():
        tracker.inject_breadcrumb_into_file(file_obj, breadcrumb)


def track_file_creation(file_path: str, source_context: str = None) -> None:
    """Track creation of a file with breadcrumb."""
    tracker = get_breadcrumb_tracker()

    if source_context:
        tracker.set_current_context(source_context)

    breadcrumb = tracker.create_breadcrumb(file_path, 'create')
    file_obj = Path(file_path)
    tracker.inject_breadcrumb_into_file(file_obj, breadcrumb)


def track_file_modification(file_path: str, source_context: str = None) -> None:
    """Track modification of a file with breadcrumb."""
    tracker = get_breadcrumb_tracker()

    if source_context:
        tracker.set_current_context(source_context)

    breadcrumb = tracker.create_breadcrumb(file_path, 'modify')
    file_obj = Path(file_path)
    tracker.inject_breadcrumb_into_file(file_obj, breadcrumb)


# Bootstrap integration: Auto-inject breadcrumb tracking into key functions
def bootstrap_breadcrumb_tracking():
    """Bootstrap function to inject breadcrumb tracking into the system."""

    # This would be called during system initialization
    tracker = get_breadcrumb_tracker()

    # Set initial context
    tracker.set_current_context("bootstrap_initialization")

    print("🗺️  AI Breadcrumb Tracking System initialized")
    print("   Breadcrumb trail will be logged to: breadcrumb_trail.jsonl")
    print("   Use get_breadcrumb_tracker() to access tracking functions")


if __name__ == "__main__":
    # Demo the breadcrumb system
    bootstrap_breadcrumb_tracking()
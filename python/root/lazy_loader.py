#!/usr/bin/env python3
"""
Lazy Loader - On-demand loading of excluded files with caching and usage tracking.

TASK_0154: Implement lazy-loading infrastructure for huge files (>100k tokens)
to enable on-demand loading only when actually referenced.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import OrderedDict
import json


class LazyLoader:
    """Lazy loading system for excluded files with LRU caching and usage tracking."""

    def __init__(self, workspace_root: Path, cache_size: int = 10, max_cache_mb: int = 50):
        self.workspace_root = workspace_root
        self.cache_size = cache_size  # Max number of files
        self.max_cache_mb = max_cache_mb  # Max memory in MB

        # LRU cache: OrderedDict for O(1) access and LRU eviction
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.cache_memory_usage = 0  # In bytes

        # Usage tracking
        self.usage_stats = {
            'total_accesses': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'files_loaded': 0,
            'memory_evictions': 0,
            'file_access_times': {},  # file -> list of access timestamps
            'excluded_files_accessed': set(),  # Set of excluded files that were loaded
        }

        # Exclusion list (to be loaded from bootstrap optimizer)
        self.excluded_files: set = set()

    def load_exclusion_list(self, exclusion_data: Optional[Dict] = None) -> None:
        """Load the list of excluded files from bootstrap optimizer data."""
        if exclusion_data and 'exclusion_candidates' in exclusion_data:
            self.excluded_files = {
                candidate['path'] for candidate in exclusion_data['exclusion_candidates']
            }
        else:
            # Try to load from default location
            exclusion_file = self.workspace_root / 'bootstrap_exclusion_cache.json'
            if exclusion_file.exists():
                try:
                    with open(exclusion_file, 'r') as f:
                        data = json.load(f)
                    self.excluded_files = set(data.get('excluded_files', []))
                except Exception as e:
                    print(f"Warning: Could not load exclusion list: {e}")

    def is_excluded(self, file_path: str) -> bool:
        """Check if a file is in the exclusion list."""
        return file_path in self.excluded_files

    def _estimate_memory_usage(self, content: str) -> int:
        """Estimate memory usage of content in bytes."""
        return len(content.encode('utf-8'))

    def _evict_lru(self) -> None:
        """Evict least recently used items to free memory."""
        while (len(self.cache) > self.cache_size or
               self.cache_memory_usage > self.max_cache_mb * 1024 * 1024) and self.cache:
            # Remove oldest (LRU) item
            file_path, data = self.cache.popitem(last=False)
            self.cache_memory_usage -= data['memory_usage']
            self.usage_stats['memory_evictions'] += 1

    def load_file(self, file_path: str) -> Optional[str]:
        """Load a file with lazy loading and caching."""
        abs_path = self.workspace_root / file_path

        # Check if file exists
        if not abs_path.exists():
            return None

        # Track access
        self.usage_stats['total_accesses'] += 1
        current_time = time.time()

        if file_path in self.cache:
            # Cache hit
            self.usage_stats['cache_hits'] += 1
            data = self.cache[file_path]
            data['last_access'] = current_time
            data['access_count'] += 1
            # Move to end (most recently used)
            self.cache.move_to_end(file_path)
            return data['content']
        else:
            # Cache miss - load from disk
            self.usage_stats['cache_misses'] += 1

            try:
                with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error loading file {file_path}: {e}")
                return None

            # Track if this was an excluded file
            if self.is_excluded(file_path):
                self.usage_stats['excluded_files_accessed'].add(file_path)
                self.usage_stats['files_loaded'] += 1

            # Estimate memory usage
            memory_usage = self._estimate_memory_usage(content)

            # Evict if necessary
            self._evict_lru()

            # Add to cache
            self.cache[file_path] = {
                'content': content,
                'memory_usage': memory_usage,
                'load_time': current_time,
                'last_access': current_time,
                'access_count': 1
            }
            self.cache_memory_usage += memory_usage

            # Track access time
            if file_path not in self.usage_stats['file_access_times']:
                self.usage_stats['file_access_times'][file_path] = []
            self.usage_stats['file_access_times'][file_path].append(current_time)

            return content

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get file content with automatic lazy loading for excluded files."""
        return self.load_file(file_path)

    def preload_excluded_file(self, file_path: str) -> bool:
        """Preload an excluded file into cache (useful for anticipated access)."""
        if self.is_excluded(file_path):
            return self.load_file(file_path) is not None
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics."""
        cache_hit_rate = (
            self.usage_stats['cache_hits'] / self.usage_stats['total_accesses']
            if self.usage_stats['total_accesses'] > 0 else 0
        )

        return {
            'cache_stats': {
                'current_size': len(self.cache),
                'max_size': self.cache_size,
                'memory_usage_mb': self.cache_memory_usage / (1024 * 1024),
                'max_memory_mb': self.max_cache_mb,
                'hit_rate': cache_hit_rate,
                'total_accesses': self.usage_stats['total_accesses'],
                'cache_hits': self.usage_stats['cache_hits'],
                'cache_misses': self.usage_stats['cache_misses'],
            },
            'lazy_loading_stats': {
                'excluded_files_count': len(self.excluded_files),
                'excluded_files_accessed': len(self.usage_stats['excluded_files_accessed']),
                'files_loaded': self.usage_stats['files_loaded'],
                'memory_evictions': self.usage_stats['memory_evictions'],
            },
            'file_access_patterns': {
                'most_accessed_files': sorted(
                    [(k, len(v)) for k, v in self.usage_stats['file_access_times'].items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:10],  # Top 10
                'excluded_files_accessed': list(self.usage_stats['excluded_files_accessed']),
            },
            'cache_contents': [
                {
                    'file': k,
                    'memory_mb': v['memory_usage'] / (1024 * 1024),
                    'access_count': v['access_count'],
                    'last_access': v['last_access']
                }
                for k, v in self.cache.items()
            ]
        }

    def clear_cache(self) -> None:
        """Clear the entire cache."""
        self.cache.clear()
        self.cache_memory_usage = 0

    def remove_from_cache(self, file_path: str) -> bool:
        """Remove a specific file from cache."""
        if file_path in self.cache:
            data = self.cache[file_path]
            self.cache_memory_usage -= data['memory_usage']
            del self.cache[file_path]
            return True
        return False


# Integration with knowledge_db.py
def integrate_lazy_loader_with_knowledge_db(knowledge_db_instance, lazy_loader: LazyLoader):
    """Integrate LazyLoader with KnowledgeDB for automatic lazy loading."""
    # Monkey patch the file reading method
    original_read_file = knowledge_db_instance._read_file_content

    def lazy_read_file(file_path):
        # Check if file is excluded and load via lazy loader
        if lazy_loader.is_excluded(file_path):
            content = lazy_loader.get_file_content(file_path)
            if content is not None:
                return content
        # Fall back to original method
        return original_read_file(file_path)

    knowledge_db_instance._read_file_content = lazy_read_file
    return knowledge_db_instance


# CLI interface for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python lazy_loader.py <workspace_root> [file_to_load]")
        sys.exit(1)

    workspace = Path(sys.argv[1])
    loader = LazyLoader(workspace)

    # Load exclusion list
    loader.load_exclusion_list()

    if len(sys.argv) > 2:
        file_path = sys.argv[2]
        content = loader.get_file_content(file_path)
        if content:
            print(f"Loaded {file_path} ({len(content)} chars)")
        else:
            print(f"Failed to load {file_path}")

    # Print stats
    stats = loader.get_stats()
    print(f"Cache hit rate: {stats['cache_stats']['hit_rate']:.2%}")
    print(f"Excluded files accessed: {stats['lazy_loading_stats']['excluded_files_accessed']}")
    print(f"Files in cache: {stats['cache_stats']['current_size']}")

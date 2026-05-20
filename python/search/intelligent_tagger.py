# MODE: LIBRARY

"""
Intelligent Tagger - Dynamic Tag Generation and Management

AI-powered tagging system that generates relevant tags from:
- Database content analysis
- Breadcrumb trail patterns
- File metadata extraction
- Cross-reference analysis
- Usage pattern recognition

Integrates with breadcrumb_trail.jsonl and knowledge_db.py for intelligent tag suggestions.
"""

from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

# Download required NLTK data if not present
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
    NLTK_AVAILABLE = True
except ImportError:
    nltk = None
    NLTK_AVAILABLE = False
    # Fallback implementations
    class WordNetLemmatizer:
        def lemmatize(self, word): return word

    def word_tokenize(text): return text.split()

    class stopwords:
        @staticmethod
        def words(lang): return []


@dataclass
class TagMetadata:
    """Metadata for a generated tag."""
    tag: str
    confidence: float
    source: str  # 'content', 'breadcrumb', 'metadata', 'reference'
    frequency: int
    last_used: datetime
    related_tags: List[str]


@dataclass
class FileTags:
    """Tags associated with a specific file."""
    file_path: str
    tags: List[TagMetadata]
    generated_at: datetime
    context_hash: str


class IntelligentTagger:
    """
    Intelligent tagging system for dynamic tag generation.

    Analyzes content, usage patterns, and relationships to generate
    relevant tags for files and search optimization.
    """

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(['a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                              'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                              'to', 'was', 'will', 'with'])  # Basic stop words

        if NLTK_AVAILABLE:
            try:
                self.stop_words.update(stopwords.words('english'))
            except:
                pass  # Use basic stop words if NLTK data not available

        # Additional domain-specific stop words
        self.stop_words.update({
            'file', 'code', 'function', 'class', 'method', 'variable',
            'import', 'from', 'def', 'return', 'if', 'for', 'while',
            'task', 'report', 'analysis', 'implementation', 'test'
        })

        # Tag patterns and weights
        self.tag_patterns = {
            'language': {
                'patterns': [r'\.py$', r'\.js$', r'\.md$', r'\.json$', r'\.txt$'],
                'weight': 1.0
            },
            'framework': {
                'keywords': ['flask', 'django', 'react', 'vue', 'angular', 'fastapi'],
                'weight': 0.9
            },
            'purpose': {
                'keywords': ['test', 'analysis', 'report', 'config', 'script', 'utility'],
                'weight': 0.8
            },
            'domain': {
                'keywords': ['ai', 'ml', 'api', 'database', 'search', 'ui', 'network'],
                'weight': 0.7
            }
        }

        # Cache for generated tags
        self.tag_cache: Dict[str, FileTags] = {}
        self.global_tag_stats: Dict[str, TagMetadata] = {}

        # Load existing tag knowledge
        self._load_existing_tags()

    def _load_existing_tags(self) -> None:
        """Load existing tag knowledge from workspace."""
        # Load from breadcrumb patterns
        self._analyze_breadcrumb_patterns()

        # Load from file content analysis
        self._analyze_workspace_content()

    def _analyze_breadcrumb_patterns(self) -> None:
        """Analyze breadcrumb trail for usage-based tagging."""
        breadcrumb_file = self.workspace / "breadcrumb_trail.jsonl"

        if not breadcrumb_file.exists():
            return

        context_patterns = defaultdict(list)
        file_operations = defaultdict(list)

        try:
            with open(breadcrumb_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    entry = json.loads(line)
                    file_path = entry.get('target_file', '')
                    context = entry.get('source_context', '')
                    operation = entry.get('operation', '')
                    timestamp = entry.get('timestamp', '')

                    if context:
                        context_patterns[context].append(file_path)
                    if operation:
                        file_operations[file_path].append(operation)

        except (json.JSONDecodeError, FileNotFoundError):
            pass

        # Generate context-based tags
        for context, files in context_patterns.items():
            if len(files) > 2:  # Only for contexts with multiple files
                context_tag = f"context:{context}"
                self.global_tag_stats[context_tag] = TagMetadata(
                    tag=context_tag,
                    confidence=min(1.0, len(files) / 10),
                    source='breadcrumb',
                    frequency=len(files),
                    last_used=datetime.now(timezone.utc),
                    related_tags=[]
                )

    def _analyze_workspace_content(self) -> None:
        """Analyze workspace content for keyword-based tagging."""
        # Scan key files for common patterns
        key_files = [
            'README.md',
            'requirements.txt',
            'config.json',
            'mega.md'
        ]

        for filename in key_files:
            file_path = self.workspace / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()

                    # Extract technology keywords
                    for category, config in self.tag_patterns.items():
                        if 'keywords' in config:
                            for keyword in config['keywords']:
                                if keyword in content:
                                    tag = f"{category}:{keyword}"
                                    if tag not in self.global_tag_stats:
                                        self.global_tag_stats[tag] = TagMetadata(
                                            tag=tag,
                                            confidence=0.6,
                                            source='content',
                                            frequency=1,
                                            last_used=datetime.now(timezone.utc),
                                            related_tags=[]
                                        )

                except (IOError, UnicodeDecodeError):
                    pass

    def generate_tags_for_file(self, file_path: str, content: Optional[str] = None) -> FileTags:
        """
        Generate intelligent tags for a specific file.

        Args:
            file_path: Path to the file
            content: Optional file content (will read if not provided)

        Returns:
            FileTags object with generated tags
        """
        # Check cache first
        content_hash = self._get_content_hash(file_path, content)
        cache_key = f"{file_path}:{content_hash}"

        if cache_key in self.tag_cache:
            return self.tag_cache[cache_key]

        # Read content if not provided
        if content is None:
            try:
                with open(self.workspace / file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError):
                content = ""

        # Generate tags from different sources
        tags = []

        # File extension tags
        tags.extend(self._generate_extension_tags(file_path))

        # Content analysis tags
        tags.extend(self._generate_content_tags(content))

        # Metadata tags
        tags.extend(self._generate_metadata_tags(file_path))

        # Breadcrumb tags
        tags.extend(self._generate_breadcrumb_tags(file_path))

        # Reference tags
        tags.extend(self._generate_reference_tags(file_path, content))

        # Create FileTags object
        file_tags = FileTags(
            file_path=file_path,
            tags=tags,
            generated_at=datetime.now(timezone.utc),
            context_hash=content_hash
        )

        # Cache the result
        self.tag_cache[cache_key] = file_tags

        return file_tags

    def _get_content_hash(self, file_path: str, content: Optional[str] = None) -> str:
        """Generate content hash for caching."""
        if content is not None:
            return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]

        try:
            with open(self.workspace / file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:8]
        except (IOError, OSError):
            return "unknown"

    def _generate_extension_tags(self, file_path: str) -> List[TagMetadata]:
        """Generate tags based on file extension."""
        tags = []

        if file_path.endswith('.py'):
            tags.append(TagMetadata(
                tag='language:python',
                confidence=1.0,
                source='metadata',
                frequency=1,
                last_used=datetime.now(timezone.utc),
                related_tags=['framework:flask', 'framework:fastapi']
            ))
        elif file_path.endswith('.js'):
            tags.append(TagMetadata(
                tag='language:javascript',
                confidence=1.0,
                source='metadata',
                frequency=1,
                last_used=datetime.now(timezone.utc),
                related_tags=['framework:react', 'framework:vue']
            ))
        elif file_path.endswith('.md'):
            tags.append(TagMetadata(
                tag='format:markdown',
                confidence=1.0,
                source='metadata',
                frequency=1,
                last_used=datetime.now(timezone.utc),
                related_tags=['purpose:documentation']
            ))

        return tags

    def _generate_content_tags(self, content: str) -> List[TagMetadata]:
        """Generate tags based on content analysis."""
        tags = []

        if not content:
            return tags

        content_lower = content.lower()

        # Technology detection
        tech_indicators = {
            'flask': 'framework:flask',
            'django': 'framework:django',
            'fastapi': 'framework:fastapi',
            'react': 'framework:react',
            'vue': 'framework:vue',
            'tensorflow': 'framework:tensorflow',
            'pytorch': 'framework:pytorch',
            'sqlite': 'database:sqlite',
            'mongodb': 'database:mongodb',
            'api': 'purpose:api',
            'test': 'purpose:test',
            'analysis': 'purpose:analysis'
        }

        for indicator, tag in tech_indicators.items():
            if indicator in content_lower:
                confidence = 0.8 if len(content) > 100 else 0.6
                tags.append(TagMetadata(
                    tag=tag,
                    confidence=confidence,
                    source='content',
                    frequency=content_lower.count(indicator),
                    last_used=datetime.now(timezone.utc),
                    related_tags=[]
                ))

        # Keyword extraction for domain tags
        domain_keywords = self._extract_keywords(content)
        for keyword in domain_keywords[:5]:  # Top 5 keywords
            if len(keyword) > 3:  # Skip very short words
                tag = f"domain:{keyword}"
                tags.append(TagMetadata(
                    tag=tag,
                    confidence=0.5,
                    source='content',
                    frequency=domain_keywords.count(keyword),
                    last_used=datetime.now(timezone.utc),
                    related_tags=[]
                ))

        return tags

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract important keywords from content."""
        # Tokenize and clean
        if NLTK_AVAILABLE:
            try:
                tokens = word_tokenize(content.lower())
            except:
                tokens = content.lower().split()
        else:
            tokens = content.lower().split()

        # Remove stop words and non-alphabetic tokens
        keywords = [
            self.lemmatizer.lemmatize(token)
            for token in tokens
            if token.isalpha() and token not in self.stop_words and len(token) > 2
        ]

        # Get most common keywords
        keyword_counts = Counter(keywords)
        return [word for word, count in keyword_counts.most_common(10)]

    def _generate_metadata_tags(self, file_path: str) -> List[TagMetadata]:
        """Generate tags based on file metadata."""
        tags = []

        # Check if file is in reports directory
        if 'report' in file_path:
            tags.append(TagMetadata(
                tag='type:report',
                confidence=0.9,
                source='metadata',
                frequency=1,
                last_used=datetime.now(timezone.utc),
                related_tags=['purpose:analysis', 'purpose:documentation']
            ))

        # Check if file is a task
        if 'task' in file_path:
            tags.append(TagMetadata(
                tag='type:task',
                confidence=0.9,
                source='metadata',
                frequency=1,
                last_used=datetime.now(timezone.utc),
                related_tags=['purpose:implementation']
            ))

        return tags

    def _generate_breadcrumb_tags(self, file_path: str) -> List[TagMetadata]:
        """Generate tags based on breadcrumb usage patterns."""
        tags = []

        # Use global tag stats for breadcrumb-based tags
        for tag_name, metadata in self.global_tag_stats.items():
            if metadata.source == 'breadcrumb' and metadata.confidence > 0.5:
                tags.append(metadata)

        return tags

    def _generate_reference_tags(self, file_path: str, content: str) -> List[TagMetadata]:
        """Generate tags based on reference analysis (mega.md style)."""
        tags = []

        if not content:
            return tags

        # Look for reference patterns
        reference_patterns = [
            r'references?:\s*\[([^\]]+)\]',
            r'see also:\s*([^\n]+)',
            r'related:\s*([^\n]+)',
            r'References?\s*:\s*([^\n]+)'
        ]

        for pattern in reference_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                tags.append(TagMetadata(
                    tag='has_references',
                    confidence=0.7,
                    source='reference',
                    frequency=len(matches),
                    last_used=datetime.now(timezone.utc),
                    related_tags=['methodology:mega']
                ))
                break

        return tags

    def get_related_tags(self, tag: str, limit: int = 10) -> List[TagMetadata]:
        """Get tags related to a given tag."""
        if tag not in self.global_tag_stats:
            return []

        related = []
        base_metadata = self.global_tag_stats[tag]

        # Find tags with similar sources or related keywords
        for other_tag, metadata in self.global_tag_stats.items():
            if other_tag == tag:
                continue

            # Same source type
            if metadata.source == base_metadata.source:
                related.append(metadata)
                continue

            # Related by keyword
            tag_parts = tag.split(':')
            other_parts = other_tag.split(':')

            if len(tag_parts) > 1 and len(other_parts) > 1:
                if tag_parts[0] == other_parts[0]:  # Same category
                    related.append(metadata)

        return related[:limit]

    def update_tag_usage(self, tag: str) -> None:
        """Update usage statistics for a tag."""
        if tag in self.global_tag_stats:
            metadata = self.global_tag_stats[tag]
            metadata.frequency += 1
            metadata.last_used = datetime.now(timezone.utc)

    def get_popular_tags(self, limit: int = 20) -> List[TagMetadata]:
        """Get most popular tags by usage frequency."""
        sorted_tags = sorted(
            self.global_tag_stats.values(),
            key=lambda x: x.frequency,
            reverse=True
        )
        return sorted_tags[:limit]

    def search_by_tags(self, tags: List[str], operator: str = 'AND') -> List[str]:
        """
        Search for files that match given tags.

        Args:
            tags: List of tags to search for
            operator: 'AND' or 'OR' logic

        Returns:
            List of file paths that match the tag criteria
        """
        matching_files = set()

        for cache_key, file_tags in self.tag_cache.items():
            file_path = file_tags.file_path
            file_tag_names = {tag.tag for tag in file_tags.tags}

            if operator == 'AND':
                if all(tag in file_tag_names for tag in tags):
                    matching_files.add(file_path)
            elif operator == 'OR':
                if any(tag in file_tag_names for tag in tags):
                    matching_files.add(file_path)

        return list(matching_files)
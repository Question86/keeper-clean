#!/usr/bin/env python3
"""
Multi-Agent Code Snippet Extraction System

This system browses all files in the Keeper-Clean-Loop1 workspace and extracts
code snippets with their explanatory headers/comments. Each snippet is saved
as a separate text file in the all_snippets_collected directory for database indexing.

Features:
- Supports multiple programming languages (Python, JavaScript, HTML, CSS, etc.)
- Extracts comment blocks with associated code
- Preserves original file structure and content
- Creates searchable text files for database indexing
- Handles various comment styles (//, /* */, #, <!-- -->)
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
import hashlib

class CodeSnippetExtractor:
    """Multi-language code snippet extractor with comment analysis."""

    def __init__(self, workspace_root: Path, output_dir: Path):
        self.workspace_root = workspace_root
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

        # Language-specific comment patterns
        self.comment_patterns = {
            'python': [
                (r'# (.+?)\n((?:(?!# ).*\n)*)', 'single_line'),  # # comment followed by code
                (r'""".*?\n(.+?)\n.*?"""', 'docstring'),  # Docstrings
            ],
            'javascript': [
                (r'// (.+?)\n((?:(?!// ).*\n)*)', 'single_line'),  # // comment followed by code
                (r'/\*\s*(.+?)\s*\*/\s*\n((?:.*?\n)*?)', 'block'),  # /* */ block comments
            ],
            'typescript': [
                (r'// (.+?)\n((?:(?!// ).*\n)*)', 'single_line'),
                (r'/\*\s*(.+?)\s*\*/\s*\n((?:.*?\n)*?)', 'block'),
            ],
            'html': [
                (r'<!-- (.+?) -->\s*\n((?:.*?\n)*?)', 'html_comment'),  # HTML comments
            ],
            'css': [
                (r'/\*\s*(.+?)\s*\*/\s*\n((?:.*?\n)*?)', 'block'),
            ],
            'cpp': [
                (r'// (.+?)\n((?:(?!// ).*\n)*)', 'single_line'),
                (r'/\*\s*(.+?)\s*\*/\s*\n((?:.*?\n)*?)', 'block'),
            ],
            'c': [
                (r'// (.+?)\n((?:(?!// ).*\n)*)', 'single_line'),
                (r'/\*\s*(.+?)\s*\*/\s*\n((?:.*?\n)*?)', 'block'),
            ],
            'java': [
                (r'// (.+?)\n((?:(?!// ).*\n)*)', 'single_line'),
                (r'/\*\s*(.+?)\s*\*/\s*\n((?:.*?\n)*?)', 'block'),
            ],
            'shell': [
                (r'# (.+?)\n((?:(?!# ).*\n)*)', 'single_line'),
            ],
            'yaml': [
                (r'# (.+?)\n((?:(?!# ).*\n)*)', 'single_line'),
            ],
            'json': [
                # JSON doesn't have comments, but we can extract structure
            ],
            'markdown': [
                # Markdown headers and code blocks
                (r'^#+\s*(.+?)\n((?:.*?\n)*?)(?=^#|\Z)', 'header_section'),
                (r'```.*?\n(.+?)\n```', 'code_block'),
            ],
        }

        # File extensions to language mapping
        self.file_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.java': 'java',
            '.sh': 'shell',
            '.bash': 'shell',
            '.zsh': 'shell',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.md': 'markdown',
            '.txt': 'markdown',  # Treat as markdown-like
        }

        # Files and directories to skip
        self.skip_patterns = [
            '__pycache__',
            '.git',
            '.vscode',
            'node_modules',
            'venv',
            'env',
            '.pytest_cache',
            'build',
            'dist',
            '*.pyc',
            '*.pyo',
            '*.log',
            '*.tmp',
            '*.bak',
            '*.swp',
            '*.swo',
            '.DS_Store',
            'Thumbs.db',
        ]

    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        # Skip by name
        if any(pattern in str(file_path) for pattern in self.skip_patterns):
            return True

        # Skip by extension
        if file_path.suffix.lower() in ['.pyc', '.pyo', '.log', '.tmp', '.bak', '.swp', '.swo']:
            return True

        # Skip very small files
        try:
            if file_path.stat().st_size < 10:  # Less than 10 bytes
                return True
        except:
            return True

        return False

    def detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        return self.file_extensions.get(file_path.suffix.lower())

    def extract_snippets_from_file(self, file_path: Path) -> List[Dict]:
        """Extract code snippets with comments from a single file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

        language = self.detect_language(file_path)
        if not language or language not in self.comment_patterns:
            # Try to extract some basic structure even for unknown languages
            return self.extract_generic_snippets(content, file_path)

        snippets = []
        patterns = self.comment_patterns[language]

        for pattern, comment_type in patterns:
            try:
                matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
                for match in matches:
                    if isinstance(match, tuple):
                        comment, code = match
                    else:
                        comment, code = match, ""

                    # Clean up the comment and code
                    comment = comment.strip()
                    code = code.strip()

                    # Skip if comment is too short or generic
                    if len(comment) < 5 or comment.lower() in ['todo', 'fixme', 'note', 'hack']:
                        continue

                    # Skip if code is empty or too short
                    if len(code.strip()) < 5:
                        continue

                    snippet = {
                        'file_path': str(file_path.relative_to(self.workspace_root)),
                        'language': language,
                        'comment_type': comment_type,
                        'comment': comment,
                        'code': code,
                        'line_number': self.find_line_number(content, comment),
                        'file_hash': self.get_file_hash(file_path),
                    }
                    snippets.append(snippet)

            except Exception as e:
                print(f"Error processing {file_path} with pattern {pattern}: {e}")
                continue

        return snippets

    def extract_generic_snippets(self, content: str, file_path: Path) -> List[Dict]:
        """Extract snippets from files without specific language support."""
        snippets = []

        # Try to find any comment-like patterns
        lines = content.split('\n')
        current_comment = None
        current_code = []

        for i, line in enumerate(lines):
            line = line.strip()

            # Look for comment starts
            if line.startswith('//') or line.startswith('#') or line.startswith('/*') or '/*' in line:
                if current_comment and current_code:
                    # Save previous snippet
                    snippets.append({
                        'file_path': str(file_path.relative_to(self.workspace_root)),
                        'language': 'generic',
                        'comment_type': 'generic',
                        'comment': current_comment,
                        'code': '\n'.join(current_code),
                        'line_number': i - len(current_code),
                        'file_hash': self.get_file_hash(file_path),
                    })

                # Start new comment
                if line.startswith('//'):
                    current_comment = line[2:].strip()
                elif line.startswith('#'):
                    current_comment = line[1:].strip()
                elif line.startswith('/*'):
                    current_comment = line[2:].strip()
                elif '/*' in line:
                    current_comment = line.split('/*')[1].strip()
                else:
                    current_comment = line

                current_code = []

            elif current_comment and line and not line.startswith('//') and not line.startswith('#'):
                # Add code line if we have a current comment
                current_code.append(line)

        # Save final snippet
        if current_comment and current_code:
            snippets.append({
                'file_path': str(file_path.relative_to(self.workspace_root)),
                'language': 'generic',
                'comment_type': 'generic',
                'comment': current_comment,
                'code': '\n'.join(current_code),
                'line_number': len(lines) - len(current_code),
                'file_hash': self.get_file_hash(file_path),
            })

        return snippets

    def find_line_number(self, content: str, search_text: str) -> int:
        """Find the line number of a piece of text in content."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if search_text in line:
                return i + 1
        return 0

    def get_file_hash(self, file_path: Path) -> str:
        """Get a hash of the file for change detection."""
        try:
            content = file_path.read_bytes()
            return hashlib.md5(content).hexdigest()[:8]
        except:
            return "unknown"

    def save_snippet_to_file(self, snippet: Dict, index: int):
        """Save a single snippet to a text file."""
        # Create a clean filename from the comment
        comment_slug = re.sub(r'[^\w\s-]', '', snippet['comment']).strip()
        comment_slug = re.sub(r'\s+', '_', comment_slug)[:50]  # Limit length

        if not comment_slug:
            comment_slug = f"snippet_{index}"

        filename = f"{comment_slug}_{snippet['file_hash']}.txt"
        filepath = self.output_dir / filename

        # Create the content
        content = f"""CODE SNIPPET EXTRACTION
=====================

File: {snippet['file_path']}
Language: {snippet['language']}
Comment Type: {snippet['comment_type']}
Line Number: {snippet['line_number']}
File Hash: {snippet['file_hash']}
Extracted At: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

COMMENT:
{snippet['comment']}

CODE:
{snippet['code']}

=====================
END OF SNIPPET
"""

        try:
            filepath.write_text(content, encoding='utf-8')
            return str(filepath)
        except Exception as e:
            print(f"Error saving snippet to {filepath}: {e}")
            return None

    def process_workspace(self) -> Dict[str, any]:
        """Process the entire workspace and extract all code snippets."""
        print("Starting comprehensive code snippet extraction...")
        print(f"Workspace: {self.workspace_root}")
        print(f"Output directory: {self.output_dir}")
        print("=" * 60)

        stats = {
            'files_processed': 0,
            'snippets_extracted': 0,
            'files_skipped': 0,
            'errors': 0,
            'languages_found': set(),
            'start_time': datetime.now(timezone.utc).isoformat(),
        }

        # Walk through all files in the workspace
        for root, dirs, files in os.walk(self.workspace_root):
            # Skip directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self.skip_patterns)]

            for file in files:
                file_path = Path(root) / file

                # Skip files we don't want to process
                if self.should_skip_file(file_path):
                    stats['files_skipped'] += 1
                    continue

                try:
                    snippets = self.extract_snippets_from_file(file_path)
                    stats['files_processed'] += 1

                    if snippets:
                        language = self.detect_language(file_path) or 'generic'
                        stats['languages_found'].add(language)

                        for i, snippet in enumerate(snippets):
                            saved_path = self.save_snippet_to_file(snippet, stats['snippets_extracted'] + i)
                            if saved_path:
                                print(f"✓ Extracted snippet: {snippet['comment'][:50]}... -> {Path(saved_path).name}")

                        stats['snippets_extracted'] += len(snippets)

                    # Progress indicator
                    if stats['files_processed'] % 100 == 0:
                        print(f"Processed {stats['files_processed']} files, extracted {stats['snippets_extracted']} snippets...")

                except Exception as e:
                    print(f"✗ Error processing {file_path}: {e}")
                    stats['errors'] += 1

        stats['end_time'] = datetime.now(timezone.utc).isoformat()
        stats['languages_found'] = list(stats['languages_found'])

        print("=" * 60)
        print("EXTRACTION COMPLETE")
        print(f"Files processed: {stats['files_processed']}")
        print(f"Files skipped: {stats['files_skipped']}")
        print(f"Snippets extracted: {stats['snippets_extracted']}")
        print(f"Errors: {stats['errors']}")
        print(f"Languages found: {', '.join(stats['languages_found'])}")
        print(f"Output directory: {self.output_dir}")

        # Save stats
        stats_file = self.output_dir / "extraction_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)

        return stats

def main():
    workspace_root = Path("D:/Keeper-Clean-Loop1")
    output_dir = workspace_root / "all_snippets_collected"

    extractor = CodeSnippetExtractor(workspace_root, output_dir)
    stats = extractor.process_workspace()

    print(f"\nNext steps:")
    print("1. Review the extracted snippets in: all_snippets_collected/")
    print("2. Add these text files to the knowledge database for searchable code")
    print("3. Use query_db.py to search for specific code implementations")

if __name__ == "__main__":
    main()
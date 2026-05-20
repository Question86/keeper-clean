#!/usr/bin/env python3
"""
Improved Multi-Agent Code Snippet Extraction System

This system browses all files in the Keeper-Clean-Loop1 workspace and extracts
code snippets with their explanatory headers/comments. Each meaningful section
is saved as a separate text file for database indexing.

Key improvements:
- Extracts each major section separately (marked by section headers)
- Better binary file detection and skipping
- More sophisticated comment pattern recognition
- Handles various section header formats
- Creates comprehensive text files for all code sections
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
import hashlib
import mimetypes

class ImprovedCodeSnippetExtractor:
    """Enhanced code snippet extractor with section-based extraction."""

    def __init__(self, workspace_root: Path, output_dir: Path):
        self.workspace_root = workspace_root
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

        # Section header patterns (these indicate major code sections)
        self.section_patterns = [
            r'# -+\s*([A-Z][A-Z\s]+[A-Z])\s*-+',  # # ---------- SECTION NAME ----------
            r'# =+\s*([A-Z][A-Z\s]+[A-Z])\s*=+',  # # ========== SECTION NAME ==========
            r'/\*\s*-+\s*([A-Z][A-Z\s]+[A-Z])\s*-+\s*\*/',  # /* ---------- SECTION NAME ---------- */
            r'// -+\s*([A-Z][A-Z\s]+[A-Z])\s*-+',  # // ---------- SECTION NAME ----------
            r'#\s*([A-Z][A-Z\s]+[A-Z])\s*$',  # # SECTION NAME (simple headers)
        ]

        # Comment patterns for code extraction
        self.comment_patterns = {
            'python': [
                (r'# (.+?)\n((?:(?!# ).*\n)*)', 'single_line'),
                (r'""".*?\n(.+?)\n.*?"""', 'docstring'),
            ],
            'javascript': [
                (r'// (.+?)\n((?:(?!// ).*\n)*)', 'single_line'),
                (r'/\*\s*(.+?)\s*\*/\s*\n((?:.*?\n)*?)', 'block'),
            ],
            'typescript': [
                (r'// (.+?)\n((?:(?!// ).*\n)*)', 'single_line'),
                (r'/\*\s*(.+?)\s*\*/\s*\n((?:.*?\n)*?)', 'block'),
            ],
            'html': [
                (r'<!-- (.+?) -->\s*\n((?:.*?\n)*?)', 'html_comment'),
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
            '.txt': 'markdown',
        }

        # Binary file extensions to skip
        self.binary_extensions = {
            '.pyc', '.pyo', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv',
            '.mp3', '.wav', '.flac', '.aac', '.ogg',
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.exe', '.dll', '.so', '.dylib',
            '.npz', '.npy', '.pkl', '.pickle', '.h5', '.hdf5',
            '.db', '.sqlite', '.sqlite3',
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
            'all_snippets_collected',  # Don't process our own output
        ]

    def is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary by extension or content."""
        # Check extension
        if file_path.suffix.lower() in self.binary_extensions:
            return True

        # Check mime type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and not mime_type.startswith('text/'):
            return True

        # Check file size (very large files are likely binary)
        try:
            if file_path.stat().st_size > 50 * 1024 * 1024:  # 50MB
                return True
        except:
            return True

        # Try to read as text
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                # Check for null bytes (common in binary files)
                if b'\x00' in chunk:
                    return True
                # Try to decode as UTF-8
                chunk.decode('utf-8', errors='strict')
                return False
        except (UnicodeDecodeError, OSError):
            return True

        return False

    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        # Skip by name
        if any(pattern in str(file_path) for pattern in self.skip_patterns):
            return True

        # Skip binary files
        if self.is_binary_file(file_path):
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

    def extract_sections_from_file(self, file_path: Path) -> List[Dict]:
        """Extract major sections from a file based on section headers."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

        sections = []
        lines = content.split('\n')
        current_section = None
        current_content = []
        current_start_line = 0

        for i, line in enumerate(lines):
            # Check if this line is a section header
            section_match = None
            for pattern in self.section_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    section_match = match.group(1).strip()
                    break

            if section_match:
                # Save previous section if it exists
                if current_section and current_content:
                    sections.append({
                        'file_path': str(file_path.relative_to(self.workspace_root)),
                        'language': self.detect_language(file_path) or 'generic',
                        'section_type': 'section_header',
                        'section_name': current_section,
                        'content': '\n'.join(current_content),
                        'start_line': current_start_line,
                        'end_line': i - 1,
                        'file_hash': self.get_file_hash(file_path),
                    })

                # Start new section
                current_section = section_match
                current_content = []
                current_start_line = i + 1

            elif current_section:
                # Add line to current section
                current_content.append(line)

        # Save final section
        if current_section and current_content:
            sections.append({
                'file_path': str(file_path.relative_to(self.workspace_root)),
                'language': self.detect_language(file_path) or 'generic',
                'section_type': 'section_header',
                'section_name': current_section,
                'content': '\n'.join(current_content),
                'start_line': current_start_line,
                'end_line': len(lines) - 1,
                'file_hash': self.get_file_hash(file_path),
            })

        return sections

    def extract_commented_code_from_file(self, file_path: Path) -> List[Dict]:
        """Extract code snippets with comments (fallback method)."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

        language = self.detect_language(file_path)
        if not language or language not in self.comment_patterns:
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
                        'section_type': 'commented_code',
                        'section_name': comment[:50],  # Use comment as section name
                        'content': code,
                        'start_line': self.find_line_number(content, comment),
                        'end_line': self.find_line_number(content, code.split('\n')[-1]) if code else 0,
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
                        'section_type': 'generic_comment',
                        'section_name': current_comment,
                        'content': '\n'.join(current_code),
                        'start_line': i - len(current_code),
                        'end_line': i - 1,
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
                'section_type': 'generic_comment',
                'section_name': current_comment,
                'content': '\n'.join(current_code),
                'start_line': len(lines) - len(current_code),
                'end_line': len(lines) - 1,
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

    def save_section_to_file(self, section: Dict, index: int):
        """Save a section to a text file."""
        # Create a clean filename from the section name
        section_slug = re.sub(r'[^\w\s-]', '', section['section_name']).strip()
        section_slug = re.sub(r'\s+', '_', section_slug)[:40]  # Limit length

        if not section_slug:
            section_slug = f"section_{index}"

        filename = f"{section_slug}_{section['file_hash']}.txt"
        filepath = self.output_dir / filename

        # Create the content
        content = f"""CODE SECTION EXTRACTION
========================

File: {section['file_path']}
Language: {section['language']}
Section Type: {section['section_type']}
Section Name: {section['section_name']}
Lines: {section['start_line']}-{section['end_line']}
File Hash: {section['file_hash']}
Extracted At: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

CONTENT:
{section['content']}

========================
END OF SECTION
"""

        try:
            filepath.write_text(content, encoding='utf-8')
            return str(filepath)
        except Exception as e:
            print(f"Error saving section to {filepath}: {e}")
            return None

    def process_workspace(self) -> Dict[str, any]:
        """Process the entire workspace and extract all code sections."""
        print("Starting improved code section extraction...")
        print(f"Workspace: {self.workspace_root}")
        print(f"Output directory: {self.output_dir}")
        print("=" * 60)

        stats = {
            'files_processed': 0,
            'sections_extracted': 0,
            'files_skipped': 0,
            'binary_files_skipped': 0,
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
                    if self.is_binary_file(file_path):
                        stats['binary_files_skipped'] += 1
                    else:
                        stats['files_skipped'] += 1
                    continue

                try:
                    # First try section-based extraction
                    sections = self.extract_sections_from_file(file_path)

                    # If no sections found, try comment-based extraction
                    if not sections:
                        sections = self.extract_commented_code_from_file(file_path)

                    stats['files_processed'] += 1

                    if sections:
                        language = self.detect_language(file_path) or 'generic'
                        stats['languages_found'].add(language)

                        for i, section in enumerate(sections):
                            saved_path = self.save_section_to_file(section, stats['sections_extracted'] + i)
                            if saved_path:
                                print(f"✓ Extracted section: {section['section_name'][:50]}... -> {Path(saved_path).name}")

                        stats['sections_extracted'] += len(sections)

                    # Progress indicator
                    if stats['files_processed'] % 50 == 0:
                        print(f"Processed {stats['files_processed']} files, extracted {stats['sections_extracted']} sections...")

                except Exception as e:
                    print(f"✗ Error processing {file_path}: {e}")
                    stats['errors'] += 1

        stats['end_time'] = datetime.now(timezone.utc).isoformat()
        stats['languages_found'] = list(stats['languages_found'])

        print("=" * 60)
        print("EXTRACTION COMPLETE")
        print(f"Files processed: {stats['files_processed']}")
        print(f"Files skipped: {stats['files_skipped']}")
        print(f"Binary files skipped: {stats['binary_files_skipped']}")
        print(f"Sections extracted: {stats['sections_extracted']}")
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

    extractor = ImprovedCodeSnippetExtractor(workspace_root, output_dir)
    stats = extractor.process_workspace()

    print(f"\nNext steps:")
    print("1. Review the extracted sections in: all_snippets_collected/")
    print("2. Add these text files to the knowledge database for searchable code")
    print("3. Use query_db.py to search for specific code implementations")

if __name__ == "__main__":
    main()
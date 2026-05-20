#!/usr/bin/env python3
"""
Context Dreaming Engine via Mega.md Framework

Uses the depth-first metadata network to explore new contexts,
generate novel insights, and "dream up" connections between knowledge nodes.

Based on mega.md mathematical framework for knowledge connectivity.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
import random
from collections import defaultdict
import math

class ContextDreamer:
    """
    Context dreaming engine using depth-first metadata network.

    Enhanced with document-level context parameters (A, B, C):
    - A: Stickiness - how static/true/flexible the context behaves
    - B: Significance - impact on project (measured by connections)
    - C: Complexity - token complexity for AI comprehension

    QKV-Inspired Relevance Dimensions (U, S, H):
    - U: Urgency - temporal criticality and immediacy
    - S: Strategic Fit - alignment with project goals and superior references
    - H: Historical Reliability - proven effectiveness and track record

    Mathematical Foundation (from mega.md):
    - Branching Factor: b ≥ 5
    - Depth-First Coverage: ρ_df = (b^d - 1)/(b - 1)
    - Token Efficiency: η = connections/token
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.network_graph = self._build_network_graph()

        # Mathematical targets from depth_vs_breathe.md
        self.branching_factor = 3  # From mathematical proof (b=3)
        self.max_depth = 5  # Token-safe optimal depth (d=5)
        self.superior_depth = 7  # Superior performance depth (d=7, 52× advantage)
        self.token_budget = 200000  # Copilot token limit
        self.token_base = 1000  # Base token cost
        self.token_metadata = 500  # Per-node metadata cost

        # Context dreaming parameters
        self.context_profiles = self._load_context_profiles()
        self.random_sample_size = 4  # 2-4 files per loop for comprehensive analysis
        self.iteration_memory = []  # Store analysis history

    def calculate_optimal_depth(self, token_budget: int = None) -> int:
        """
        Calculate optimal depth based on depth_vs_breathe.md mathematical constraints.

        For b=3, T_metadata=500, T_base=1000:
        b^d ≤ (T_budget - T_base) / T_metadata
        d ≤ log_b((T_budget - T_base)/T_metadata + b) - 1

        Returns token-safe optimal depth (d=5) or superior depth (d=7) if budget allows.
        """
        if token_budget is None:
            token_budget = self.token_budget

        b = self.branching_factor
        T_base = self.token_base
        T_meta = self.token_metadata

        # Maximum depth allowed by token budget
        if b > 1:
            max_depth_budget = math.log(
                ((token_budget - T_base) * (b - 1) / T_meta) + b,
                b
            ) - 1
        else:
            max_depth_budget = (token_budget - T_base) / T_meta

        # Return optimal depth (5) if budget allows, otherwise maximum possible
        optimal_depth = min(int(max_depth_budget), self.superior_depth)
        return max(1, optimal_depth)  # Minimum depth of 1

    def calculate_connectivity_advantage(self, depth: int) -> Dict:
        """
        Calculate connectivity advantage at given depth using depth_vs_breathe.md formulas.

        Returns comparison between depth-first and breadth-first approaches.
        """
        b = self.branching_factor

        # Depth-first connectivity: ρ_df = (b^(d+1) - b) / (b - 1)
        if b > 1:
            df_connectivity = (b ** (depth + 1) - b) / (b - 1)
        else:
            df_connectivity = depth

        # Breadth-first connectivity: ρ_bf = b * depth
        bf_connectivity = b * depth

        # Token costs (simplified)
        df_tokens = self.token_base + depth * self.token_metadata * (b ** depth)
        bf_tokens = self.token_base + depth * self.token_metadata * b

        # Normalized efficiency (connections per token)
        df_efficiency = df_connectivity / df_tokens if df_tokens > 0 else 0
        bf_efficiency = bf_connectivity / bf_tokens if bf_tokens > 0 else 0

        return {
            'depth': depth,
            'branching_factor': b,
            'depth_first': {
                'connectivity': df_connectivity,
                'tokens': df_tokens,
                'efficiency': df_efficiency,
                'inference_hops': depth  # k-hop transitive inference
            },
            'breadth_first': {
                'connectivity': bf_connectivity,
                'tokens': bf_tokens,
                'efficiency': bf_efficiency,
                'inference_hops': 1  # Only direct inference
            },
            'advantage_ratio': df_connectivity / bf_connectivity if bf_connectivity > 0 else float('inf'),
            'efficiency_ratio': df_efficiency / bf_efficiency if bf_efficiency > 0 else float('inf')
        }

    def vectorize_dreaming_strategy(self, target_depth: int = None) -> Dict:
        """
        Vectorize dreaming strategy based on depth_vs_breathe.md mathematical targets.

        Returns optimal parameters for context dreaming vectorization.
        """
        if target_depth is None:
            target_depth = self.calculate_optimal_depth()

        # Ensure we don't exceed superior depth
        target_depth = min(target_depth, self.superior_depth)

        advantage_analysis = self.calculate_connectivity_advantage(target_depth)

        # Vectorization parameters based on mathematical optimization
        vectorization = {
            'optimal_depth': target_depth,
            'branching_factor': self.branching_factor,
            'sample_size_per_iteration': self.random_sample_size,
            'token_budget_utilization': min(0.8, advantage_analysis['depth_first']['tokens'] / self.token_budget),
            'expected_connectivity_gain': advantage_analysis['advantage_ratio'],
            'inference_capability_hops': advantage_analysis['depth_first']['inference_hops'],
            'mathematical_targets': {
                'superior_depth_7_advantage': self.calculate_connectivity_advantage(7)['advantage_ratio'],
                'optimal_depth_5_safety': self.calculate_connectivity_advantage(5)['advantage_ratio'],
                'token_safe_depth': self.calculate_optimal_depth(),
                'branching_factor_3_verified': self.branching_factor == 3
            },
            'vectorization_guidelines': {
                'iterations_needed': max(1, int(1000 / advantage_analysis['depth_first']['connectivity'])),
                'confidence_threshold': 0.7,  # Based on 7-hop capability
                'significance_boost_rate': 0.1,  # Gradual parameter updates
                'cycle_detection_enabled': True,
                'metadata_caching': True
            }
        }

        return vectorization

        # Context dreaming parameters
        self.context_profiles = self._load_context_profiles()
        self.random_sample_size = 3  # 2-4 files for precision
        self.iteration_memory = []  # Store analysis history

    def _load_context_profiles(self) -> Dict[str, Dict]:
        """Load existing context profiles for documents."""
        profiles_file = self.workspace / "context_profiles.json"
        if profiles_file.exists():
            try:
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Warning: Could not load context profiles: {e}")
        return {}

    def _save_context_profiles(self):
        """Save updated context profiles."""
        profiles_file = self.workspace / "context_profiles.json"
        with open(profiles_file, 'w', encoding='utf-8') as f:
            json.dump(self.context_profiles, f, indent=2, ensure_ascii=False)
        print(f"💾 Context profiles updated: {profiles_file}")

    def _initialize_context_profile(self, file_id: str) -> Dict:
        """Initialize context parameters for a new document."""
        if file_id not in self.network_graph:
            return None

        node_data = self.network_graph[file_id]
        content = node_data['content_preview']

        # Estimate initial parameters
        profile = {
            'file_id': file_id,
            'parameters': {
                'A_stickiness': self._estimate_stickiness(content),
                'B_significance': 0.5,  # Will be updated through connections
                'C_complexity': self._estimate_complexity(content)
            },
            'connection_history': [],
            'last_analyzed': datetime.now().isoformat(),
            'analysis_count': 0
        }

        return profile

    def _estimate_stickiness(self, content: str) -> float:
        """Estimate how static/true/flexible the context behaves (0.0-1.0)."""
        content_lower = content.lower()

        # Static indicators (increase stickiness)
        static_keywords = ['must', 'always', 'never', 'required', 'fixed', 'constant', 'immutable']
        static_score = sum(1 for word in static_keywords if word in content_lower)

        # Flexible indicators (decrease stickiness)
        flexible_keywords = ['may', 'optional', 'configurable', 'variable', 'dynamic', 'adaptive']
        flexible_score = sum(1 for word in flexible_keywords if word in content_lower)

        # Code-like content tends to be more static
        code_indicators = ['```', 'function', 'class', 'import', 'def ', 'const ']
        code_score = sum(1 for indicator in code_indicators if indicator in content)

        # Normalize and combine
        total_indicators = len(static_keywords) + len(flexible_keywords) + len(code_indicators)
        raw_score = (static_score + code_score - flexible_score) / max(total_indicators, 1)

        # Sigmoid normalization to 0-1 range
        return 1 / (1 + math.exp(-raw_score))

    def _estimate_complexity(self, content: str) -> float:
        """Estimate token complexity for AI comprehension (0.0-1.0)."""
        # Rough token estimation (words + punctuation)
        word_count = len(content.split())
        char_count = len(content)

        # Complexity factors
        technical_terms = ['algorithm', 'optimization', 'complexity', 'asymptotic', 'theorem', 'proof']
        technical_score = sum(1 for term in technical_terms if term.lower() in content.lower())

        # Mathematical content
        math_indicators = ['=', '+', '-', '*', '/', '∑', '∫', '∂', '∞', 'θ', 'λ', 'μ']
        math_score = sum(1 for indicator in math_indicators if indicator in content)

        # Code blocks
        code_blocks = content.count('```')
        code_lines = sum(1 for line in content.split('\n') if line.strip().startswith(('def ', 'class ', 'function ', 'const ')))

        # Normalize to 0-1 scale
        complexity_score = min(1.0, (
            (word_count / 1000) +          # Length factor
            (technical_score / 5) +        # Technical depth
            (math_score / 10) +            # Mathematical complexity
            (code_blocks / 3) +            # Code content
            (code_lines / 20)              # Code density
        ) / 5)

        return complexity_score

    def _build_network_graph(self) -> Dict[str, Dict]:
        """
        Build comprehensive network graph from ALL files in workspace.

        Scans recursively through all directories and processes files by type:
        - Markdown: Extract references, metadata, content analysis
        - Python: Extract imports, functions, classes, docstrings
        - JSON: Extract structure, keys, values
        - Other: Extract content patterns and metadata
        """
        graph = {}

        # Define file patterns to include (comprehensive coverage)
        file_patterns = [
            "**/*.md",      # Documentation and reports
            "**/*.py",      # Python code
            "**/*.js",      # JavaScript code
            "**/*.ts",      # TypeScript code
            "**/*.json",    # Data files
            "**/*.txt",     # Text files
            "**/*.yml",     # YAML files
            "**/*.yaml",    # YAML files
            "**/*.log",     # Log files
        ]

        print(f"🔍 Scanning workspace for connectivity analysis...")

        for pattern in file_patterns:
            try:
                files = list(self.workspace.glob(pattern))
                print(f"  Found {len(files)} files matching {pattern}")

                for file_path in files:
                    try:
                        # Skip certain directories that are not relevant for context analysis
                        if any(skip in str(file_path) for skip in [
                            '__pycache__', 'node_modules', '.pytest_cache', 
                            'venv', 'venv310', 'venv311', 'venv312',
                            'vscode-extension', '.vscode', '.svcode', '.worktrees',
                            'seed_template', '.github', 'tmp', 'backups', '_pytest_cache'
                        ]):
                            continue

                        node_id = str(file_path.relative_to(self.workspace))
                        content = self._read_file_content(file_path)

                        if content:  # Only process files with readable content
                            graph[node_id] = self._analyze_file_comprehensive(file_path, content)

                    except Exception as e:
                        print(f"⚠️  Error processing {file_path}: {e}")
                        continue

            except Exception as e:
                print(f"⚠️  Error scanning pattern {pattern}: {e}")
                continue

        print(f"✅ Built network graph with {len(graph)} nodes")
        return graph

    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read file content with appropriate encoding handling."""
        try:
            # Try UTF-8 first
            return file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # Try with errors='replace' for problematic characters
                return file_path.read_text(encoding='utf-8', errors='replace')
            except Exception:
                return None
        except Exception:
            return None

    def _analyze_file_comprehensive(self, file_path: Path, content: str) -> Dict:
        """Analyze file comprehensively based on its type."""
        file_type = self._classify_file_type(file_path)

        analysis = {
            'file': str(file_path),
            'file_type': file_type,
            'size': len(content),
            'lines': len(content.split('\n')),
            'content_preview': content[:1000] + "..." if len(content) > 1000 else content,
        }

        # Type-specific analysis
        if file_type == 'markdown':
            analysis.update(self._analyze_markdown_file(content))
        elif file_type == 'python':
            analysis.update(self._analyze_python_file(content))
        elif file_type == 'json':
            analysis.update(self._analyze_json_file(content))
        elif file_type == 'javascript':
            analysis.update(self._analyze_javascript_file(content))
        else:
            analysis.update(self._analyze_generic_file(content))

        # Extract metadata for abstract linking
        analysis['metadata'] = self._extract_file_metadata(file_path, content, file_type)

        return analysis

    def _classify_file_type(self, file_path: Path) -> str:
        """Classify file type based on extension and content."""
        suffix = file_path.suffix.lower()

        type_map = {
            '.md': 'markdown',
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.json': 'json',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.txt': 'text',
            '.log': 'log',
        }

        return type_map.get(suffix, 'unknown')

    def _analyze_markdown_file(self, content: str) -> Dict:
        """Analyze markdown file for comprehensive connectivity."""
        analysis = {}

        # Extract references (existing functionality)
        analysis['references'] = self._extract_references(content)

        # Extract headers and structure
        analysis['headers'] = self._extract_markdown_headers(content)

        # Extract code blocks
        analysis['code_blocks'] = self._extract_code_blocks(content)

        # Extract links and mentions
        analysis['links'] = self._extract_markdown_links(content)
        analysis['mentions'] = self._extract_mentions(content)

        # Extract metadata from frontmatter or headers
        analysis['frontmatter'] = self._extract_frontmatter(content)

        return analysis

    def _analyze_python_file(self, content: str) -> Dict:
        """Analyze Python file for imports, functions, classes, etc."""
        analysis = {}

        # Extract imports
        analysis['imports'] = self._extract_python_imports(content)

        # Extract functions and classes
        analysis['functions'] = self._extract_python_functions(content)
        analysis['classes'] = self._extract_python_classes(content)

        # Extract docstrings
        analysis['docstrings'] = self._extract_python_docstrings(content)

        # Extract comments and TODOs
        analysis['comments'] = self._extract_python_comments(content)
        analysis['todos'] = self._extract_todos(content)

        # Extract string literals (potential configuration or data)
        analysis['string_literals'] = self._extract_python_strings(content)

        return analysis

    def _analyze_json_file(self, content: str) -> Dict:
        """Analyze JSON file for structure and keys."""
        analysis = {}

        try:
            data = json.loads(content)
            analysis['json_structure'] = self._analyze_json_structure(data)
            analysis['json_keys'] = self._extract_json_keys(data)
            analysis['json_values'] = self._extract_json_values(data)
        except json.JSONDecodeError:
            analysis['json_error'] = "Invalid JSON"
            analysis['json_keys'] = []
            analysis['json_values'] = []

        return analysis

    def _analyze_javascript_file(self, content: str) -> Dict:
        """Analyze JavaScript/TypeScript file."""
        analysis = {}

        # Similar to Python but for JS patterns
        analysis['imports'] = self._extract_js_imports(content)
        analysis['functions'] = self._extract_js_functions(content)
        analysis['classes'] = self._extract_js_classes(content)
        analysis['comments'] = self._extract_js_comments(content)

        return analysis

    def _analyze_generic_file(self, content: str) -> Dict:
        """Analyze generic text file."""
        analysis = {}

        # Basic text analysis
        analysis['word_count'] = len(content.split())
        analysis['line_count'] = len(content.split('\n'))
        analysis['contains_code'] = self._detect_code_patterns(content)
        analysis['contains_urls'] = self._detect_urls(content)

        return analysis

    # ===== EXTRACTION METHODS FOR COMPREHENSIVE ANALYSIS =====

    def _extract_markdown_headers(self, content: str) -> List[Dict]:
        """Extract all headers from markdown content."""
        headers = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                headers.append({
                    'level': level,
                    'title': title,
                    'line': i + 1
                })

        return headers

    def _extract_code_blocks(self, content: str) -> List[Dict]:
        """Extract code blocks from markdown."""
        code_blocks = []
        lines = content.split('\n')
        in_code_block = False
        code_start = 0
        language = ""

        for i, line in enumerate(lines):
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Start of code block
                    in_code_block = True
                    code_start = i + 1
                    language = line.strip()[3:].strip()
                else:
                    # End of code block
                    code_content = '\n'.join(lines[code_start:i])
                    code_blocks.append({
                        'language': language,
                        'content': code_content,
                        'start_line': code_start,
                        'end_line': i + 1
                    })
                    in_code_block = False
                    language = ""

        return code_blocks

    def _extract_markdown_links(self, content: str) -> List[Dict]:
        """Extract all links from markdown."""
        links = []
        import re

        # Markdown link pattern: [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(link_pattern, content)

        for text, url in matches:
            links.append({
                'text': text,
                'url': url,
                'is_external': url.startswith(('http://', 'https://')),
                'is_local': not url.startswith(('http://', 'https://')) and '/' in url
            })

        return links

    def _extract_mentions(self, content: str) -> List[str]:
        """Extract mentions of tasks, reports, etc."""
        mentions = []
        import re

        # Patterns for different types of mentions
        patterns = [
            r'\btask_[^\s]+',      # task_TASK_0123
            r'\breport_[^\s]+',    # report_TASK_0123
            r'\bTASK_[^\s]+',      # TASK_0123
            r'\bLOOP_[^\s]+',      # LOOP_83
            r'\b[^\s]+\.md\b',     # Any .md file reference
            r'\b[^\s]+\.py\b',     # Any .py file reference
            r'\b[^\s]+\.json\b',   # Any .json file reference
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            mentions.extend(matches)

        return list(set(mentions))  # Remove duplicates

    def _extract_frontmatter(self, content: str) -> Dict:
        """Extract YAML frontmatter from markdown."""
        frontmatter = {}

        if content.startswith('---'):
            lines = content.split('\n')
            if len(lines) > 1:
                end_idx = -1
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == '---':
                        end_idx = i
                        break

                if end_idx > 0:
                    frontmatter_text = '\n'.join(lines[1:end_idx])
                    # Simple YAML parsing (could be enhanced)
                    for line in frontmatter_text.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            frontmatter[key.strip()] = value.strip()

        return frontmatter

    def _extract_references(self, content: str) -> List[str]:
        """Extract reference links from markdown content."""
        references = []
        lines = content.split('\n')

        # Look for explicit reference sections
        in_references_section = False
        for line in lines:
            line = line.strip().lower()
            if line.startswith('## references') or line.startswith('### references'):
                in_references_section = True
                continue
            elif line.startswith('## ') and in_references_section:
                in_references_section = False
                continue

            if in_references_section or '**references:**' in line.lower():
                # Extract references from reference sections
                if '[' in line and '](' in line:
                    # Markdown link format
                    start = line.find('](') + 2
                    end = line.find(')', start)
                    if end > start:
                        ref = line[start:end]
                        if ref.endswith('.md'):
                            ref = ref[:-3]  # Remove .md extension
                        references.append(ref)
                elif 'report_' in line or 'task_' in line:
                    # Plain text references
                    words = line.split()
                    for word in words:
                        word = word.strip('.,()[]')
                        if word.startswith(('report_', 'task_')):
                            references.append(word)

        # Also scan entire content for embedded references
        import re
        # Find all report_ and task_ mentions
        report_matches = re.findall(r'\b(report_[^\s]+)\b', content)
        task_matches = re.findall(r'\b(task_[^\s]+)\b', content)

        # Also find general .md file references
        md_matches = re.findall(r'\b([^\s]+\.md)\b', content)

        all_matches = report_matches + task_matches + md_matches
        for match in all_matches:
            match = match.strip('.,()[]')
            if match not in references:
                references.append(match)

        return list(set(references))  # Remove duplicates

    # ===== PYTHON FILE ANALYSIS METHODS =====

    def _extract_python_imports(self, content: str) -> List[Dict]:
        """Extract all import statements from Python code."""
        imports = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append({
                    'statement': line,
                    'line': i + 1,
                    'type': 'import' if line.startswith('import ') else 'from_import'
                })

        return imports

    def _extract_python_functions(self, content: str) -> List[Dict]:
        """Extract function definitions from Python code."""
        functions = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('def '):
                # Extract function name
                func_name = line.split('(')[0].replace('def ', '').strip()
                functions.append({
                    'name': func_name,
                    'signature': line,
                    'line': i + 1
                })

        return functions

    def _extract_python_classes(self, content: str) -> List[Dict]:
        """Extract class definitions from Python code."""
        classes = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('class '):
                # Extract class name
                class_name = line.split('(')[0].split(':')[0].replace('class ', '').strip()
                classes.append({
                    'name': class_name,
                    'definition': line,
                    'line': i + 1
                })

        return classes

    def _extract_python_docstrings(self, content: str) -> List[Dict]:
        """Extract docstrings from Python code."""
        docstrings = []
        lines = content.split('\n')
        in_docstring = False
        docstring_start = 0
        quote_type = ""

        for i, line in enumerate(lines):
            stripped = line.strip()

            if not in_docstring:
                # Look for docstring start
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_docstring = True
                    docstring_start = i
                    quote_type = '"""' if stripped.startswith('"""') else "'''"
                    if stripped.count(quote_type) == 2:
                        # Single line docstring
                        docstrings.append({
                            'content': stripped.strip(quote_type),
                            'start_line': i + 1,
                            'end_line': i + 1
                        })
                        in_docstring = False
            else:
                # Look for docstring end
                if quote_type in stripped:
                    docstring_content = '\n'.join(lines[docstring_start:i+1])
                    # Clean up the quotes
                    docstring_content = docstring_content.strip(quote_type).strip()
                    docstrings.append({
                        'content': docstring_content,
                        'start_line': docstring_start + 1,
                        'end_line': i + 1
                    })
                    in_docstring = False

        return docstrings

    def _extract_python_comments(self, content: str) -> List[Dict]:
        """Extract comments from Python code."""
        comments = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#'):
                comments.append({
                    'content': stripped[1:].strip(),
                    'line': i + 1,
                    'inline': False
                })
            elif '#' in line and not line.strip().startswith('#'):
                # Inline comment
                comment_part = line.split('#', 1)[1].strip()
                if comment_part:
                    comments.append({
                        'content': comment_part,
                        'line': i + 1,
                        'inline': True
                    })

        return comments

    def _extract_todos(self, content: str) -> List[Dict]:
        """Extract TODO items from comments and docstrings."""
        todos = []
        import re

        # Find TODO, FIXME, XXX in comments and docstrings
        todo_pattern = r'(?i)(todo|fixme|xxx|hack|note|warning):\s*(.+?)(?=\n|$)'
        matches = re.findall(todo_pattern, content)

        for match in matches:
            todos.append({
                'type': match[0].upper(),
                'content': match[1].strip()
            })

        return todos

    def _extract_python_strings(self, content: str) -> List[str]:
        """Extract string literals from Python code."""
        strings = []
        import re

        # Simple string extraction (could be more sophisticated)
        string_patterns = [
            r"'([^']*)'",     # Single quotes
            r'"([^"]*)"',     # Double quotes
            r"'''([^']*)'''", # Triple single quotes
            r'"""([^"]*)"""', # Triple double quotes
        ]

        for pattern in string_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            strings.extend(matches)

        return strings

    # ===== JSON ANALYSIS METHODS =====

    def _analyze_json_structure(self, data) -> Dict:
        """Analyze JSON structure recursively."""
        if isinstance(data, dict):
            return {
                'type': 'object',
                'keys': len(data),
                'nested_objects': sum(1 for v in data.values() if isinstance(v, dict)),
                'arrays': sum(1 for v in data.values() if isinstance(v, list)),
                'primitives': sum(1 for v in data.values() if not isinstance(v, (dict, list)))
            }
        elif isinstance(data, list):
            return {
                'type': 'array',
                'length': len(data),
                'contains_objects': any(isinstance(item, dict) for item in data),
                'contains_arrays': any(isinstance(item, list) for item in data)
            }
        else:
            return {'type': 'primitive', 'value_type': type(data).__name__}

    def _extract_json_keys(self, data, prefix="") -> List[str]:
        """Extract all keys from nested JSON structure."""
        keys = []
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                keys.append(full_key)
                keys.extend(self._extract_json_keys(value, full_key))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                full_key = f"{prefix}[{i}]"
                keys.extend(self._extract_json_keys(item, full_key))
        return keys

    def _extract_json_values(self, data) -> List[str]:
        """Extract all string values from JSON."""
        values = []
        if isinstance(data, dict):
            for value in data.values():
                values.extend(self._extract_json_values(value))
        elif isinstance(data, list):
            for item in data:
                values.extend(self._extract_json_values(item))
        elif isinstance(data, str):
            values.append(data)
        return values

    # ===== JAVASCRIPT ANALYSIS METHODS =====

    def _extract_js_imports(self, content: str) -> List[Dict]:
        """Extract import statements from JavaScript/TypeScript."""
        imports = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('import ') or line.startswith('require('):
                imports.append({
                    'statement': line,
                    'line': i + 1,
                    'type': 'es6_import' if line.startswith('import ') else 'commonjs_require'
                })

        return imports

    def _extract_js_functions(self, content: str) -> List[Dict]:
        """Extract function definitions from JavaScript/TypeScript."""
        functions = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('function ') or '=> {' in line or '=>(' in line:
                functions.append({
                    'signature': line,
                    'line': i + 1,
                    'type': 'function_declaration' if line.startswith('function ') else 'arrow_function'
                })

        return functions

    def _extract_js_classes(self, content: str) -> List[Dict]:
        """Extract class definitions from JavaScript/TypeScript."""
        classes = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('class '):
                class_name = line.split(' ')[1].split('{')[0].split('extends')[0].strip()
                classes.append({
                    'name': class_name,
                    'definition': line,
                    'line': i + 1
                })

        return classes

    def _extract_js_comments(self, content: str) -> List[Dict]:
        """Extract comments from JavaScript/TypeScript."""
        comments = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('//'):
                comments.append({
                    'content': stripped[2:].strip(),
                    'line': i + 1,
                    'type': 'single_line'
                })
            elif stripped.startswith('/*') and stripped.endswith('*/'):
                comments.append({
                    'content': stripped[2:-2].strip(),
                    'line': i + 1,
                    'type': 'multi_line'
                })

        return comments

    # ===== METADATA EXTRACTION =====

    def _extract_file_metadata(self, file_path: Path, content: str, file_type: str) -> Dict:
        """Extract comprehensive metadata for abstract linking."""
        metadata = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'file_size': len(content),
            'line_count': len(content.split('\n')),
            'word_count': len(content.split()),
            'file_type': file_type,
            'directory': str(file_path.parent.relative_to(self.workspace)) if file_path.parent != self.workspace else 'root',
            'extension': file_path.suffix,
        }

        # Extract timestamps
        metadata.update(self._extract_timestamps(content))

        # Extract patterns and themes
        metadata['patterns'] = self._extract_content_patterns(content)

        # Extract behavioral metadata
        metadata['behavior'] = self._extract_behavioral_metadata(content, file_type)

        # Enhanced metadata for better connectivity (TASK_0167 Phase 1)
        metadata['semantic_concepts'] = self._extract_semantic_concepts(content, file_type)
        metadata['behavioral_patterns'] = self._extract_behavioral_patterns(content, file_type)
        metadata['dependency_graph'] = self._extract_dependency_graph(content, file_type)
        metadata['relationship_strength'] = self._calculate_relationship_strength(metadata)

        return metadata

    def _extract_timestamps(self, content: str) -> Dict:
        """Extract temporal information from content."""
        import re

        timestamps = {}

        # ISO date patterns
        iso_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?'
        matches = re.findall(iso_pattern, content)
        if matches:
            timestamps['iso_dates'] = matches

        # Relative time patterns
        time_patterns = [
            r'(\d+)\s*(minute|hour|day|week|month|year)s?\s*ago',
            r'last\s+(week|month|year)',
            r'yesterday|today|tomorrow'
        ]

        relative_times = []
        for pattern in time_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            relative_times.extend(matches)

        if relative_times:
            timestamps['relative_times'] = relative_times

        return timestamps

    def _extract_content_patterns(self, content: str) -> List[str]:
        """Extract recurring patterns and themes."""
        patterns = []

        # Technical patterns
        if 'import ' in content or 'from ' in content:
            patterns.append('imports_modules')
        if 'class ' in content:
            patterns.append('defines_classes')
        if 'def ' in content or 'function ' in content:
            patterns.append('defines_functions')
        if 'TODO' in content or 'FIXME' in content:
            patterns.append('has_tasks')
        if 'error' in content.lower() or 'exception' in content.lower():
            patterns.append('handles_errors')
        if 'test' in content.lower():
            patterns.append('testing_related')

        # Content type patterns
        if len(content.split()) > 1000:
            patterns.append('long_document')
        if '```' in content:
            patterns.append('contains_code')
        if '[' in content and '](' in content:
            patterns.append('has_links')

        return patterns

    def _extract_behavioral_metadata(self, content: str, file_type: str) -> Dict:
        """Extract behavioral characteristics for abstract linking."""
        behavior = {}

        # Complexity metrics
        behavior['complexity'] = self._calculate_complexity_score(content, file_type)

        # Change patterns
        behavior['volatility'] = self._assess_volatility(content)

        # Communication patterns
        behavior['communication_style'] = self._assess_communication_style(content)

        # Problem-solving approach
        behavior['problem_solving'] = self._assess_problem_solving_approach(content)

        return behavior

    def _extract_semantic_concepts(self, content: str, file_type: str) -> List[str]:
        """Extract semantic concepts beyond simple keywords."""
        concepts = []
        content_lower = content.lower()
        
        # Domain-specific concept categories
        concept_categories = {
            'ai_ml': ['machine learning', 'artificial intelligence', 'neural network', 'deep learning', 'algorithm', 'model', 'training', 'prediction'],
            'software_dev': ['function', 'class', 'method', 'variable', 'import', 'module', 'package', 'library', 'framework'],
            'data_processing': ['database', 'query', 'data', 'analysis', 'processing', 'storage', 'retrieval', 'indexing'],
            'system_design': ['architecture', 'design', 'pattern', 'structure', 'component', 'system', 'integration'],
            'quality_assurance': ['test', 'validation', 'verification', 'quality', 'reliability', 'performance', 'benchmark'],
            'project_management': ['task', 'milestone', 'deadline', 'planning', 'execution', 'monitoring', 'reporting']
        }
        
        # Extract concepts from each category
        for category, keywords in concept_categories.items():
            for keyword in keywords:
                if keyword in content_lower:
                    concepts.append(f"{category}:{keyword}")
        
        # Extract technical terms (capitalized words that might be concepts)
        import re
        technical_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        for term in technical_terms[:10]:  # Limit to top 10
            if len(term.split()) <= 3:  # Max 3 words
                concepts.append(f"technical:{term.lower()}")
        
        return list(set(concepts))  # Remove duplicates

    def _extract_behavioral_patterns(self, content: str, file_type: str) -> List[str]:
        """Extract behavioral patterns showing how the file interacts."""
        patterns = []
        content_lower = content.lower()
        
        # Usage patterns
        if 'import' in content_lower or 'from' in content_lower:
            patterns.append('consumes_dependencies')
        if 'export' in content_lower or 'return' in content_lower:
            patterns.append('provides_functionality')
        if 'config' in content_lower or 'setting' in content_lower:
            patterns.append('configuration_management')
        if 'log' in content_lower or 'print' in content_lower:
            patterns.append('logging_monitoring')
        if 'error' in content_lower or 'exception' in content_lower:
            patterns.append('error_handling')
        if 'test' in content_lower or 'assert' in content_lower:
            patterns.append('testing_validation')
        
        # Interaction patterns
        if '[ref:' in content or 'reference' in content_lower:
            patterns.append('references_external')
        if 'api' in content_lower or 'endpoint' in content_lower:
            patterns.append('api_integration')
        if 'database' in content_lower or 'db' in content_lower:
            patterns.append('data_persistence')
        if 'user' in content_lower or 'interface' in content_lower:
            patterns.append('user_interaction')
        
        # Evolution patterns
        if 'todo' in content_lower or 'fixme' in content_lower:
            patterns.append('work_in_progress')
        if 'deprecated' in content_lower or 'obsolete' in content_lower:
            patterns.append('legacy_code')
        if 'new' in content_lower or 'feature' in content_lower:
            patterns.append('feature_development')
        
        return patterns

    def _extract_dependency_graph(self, content: str, file_type: str) -> Dict:
        """Extract dependency relationships."""
        import re
        
        dependencies = {
            'imports': [],
            'exports': [],
            'references': [],
            'relationships': {}
        }
        
        if file_type in ['python', 'javascript', 'typescript']:
            # Extract import statements
            import re
            if file_type == 'python':
                import_matches = re.findall(r'^(?:from\s+(\S+)|import\s+(\S+))', content, re.MULTILINE)
                for match in import_matches:
                    dep = match[0] or match[1]
                    dependencies['imports'].append(dep.split('.')[0])  # Get root module
            # Similar for JS/TS
            
        elif file_type == 'markdown':
            # Extract reference links
            ref_matches = re.findall(r'\[ref:([^\]]+)\]', content)
            dependencies['references'] = ref_matches
            
            # Extract file references
            file_refs = re.findall(r'\b\w+\.(md|py|json|txt|yml|yaml)\b', content)
            dependencies['references'].extend(file_refs)
        
        # Build relationship graph
        dependencies['relationships'] = {
            'in_degree': len(dependencies['imports']) + len(dependencies['references']),
            'out_degree': len(dependencies['exports']),
            'centrality': len(set(dependencies['imports'] + dependencies['references'])) / max(1, len(content.split()))
        }
        
        return dependencies

    def _calculate_relationship_strength(self, metadata: Dict) -> Dict:
        """Calculate confidence scores for relationships."""
        strength = {
            'semantic_strength': len(metadata.get('semantic_concepts', [])) / 10.0,  # Normalize
            'behavioral_strength': len(metadata.get('behavioral_patterns', [])) / 10.0,
            'dependency_strength': metadata.get('dependency_graph', {}).get('relationships', {}).get('centrality', 0.0),
            'overall_confidence': 0.0
        }
        
        # Calculate overall confidence as weighted average
        weights = {'semantic': 0.4, 'behavioral': 0.3, 'dependency': 0.3}
        strength['overall_confidence'] = (
            strength['semantic_strength'] * weights['semantic'] +
            strength['behavioral_strength'] * weights['behavioral'] +
            strength['dependency_strength'] * weights['dependency']
        )
        
        return strength

    def _calculate_complexity_score(self, content: str, file_type: str) -> float:
        """Calculate complexity score (0.0-1.0)."""
        score = 0.0

        # Length-based complexity
        word_count = len(content.split())
        if word_count > 1000:
            score += 0.3
        elif word_count > 500:
            score += 0.2
        elif word_count > 100:
            score += 0.1

        # Technical complexity
        technical_indicators = ['algorithm', 'optimization', 'complexity', 'implementation', 'architecture']
        technical_count = sum(1 for indicator in technical_indicators if indicator.lower() in content.lower())
        score += min(technical_count * 0.1, 0.3)

        # Code complexity (for code files)
        if file_type in ['python', 'javascript', 'typescript']:
            if 'class ' in content:
                score += 0.2
            if 'def ' in content or 'function ' in content:
                score += 0.1
            if 'import ' in content or 'from ' in content:
                score += 0.1

        return min(score, 1.0)

    def _assess_volatility(self, content: str) -> str:
        """Assess how volatile/stable the content appears."""
        volatile_indicators = ['temporary', 'experimental', 'draft', 'unstable', 'changing']
        stable_indicators = ['stable', 'mature', 'final', 'permanent', 'established']

        volatile_score = sum(1 for word in volatile_indicators if word.lower() in content.lower())
        stable_score = sum(1 for word in stable_indicators if word.lower() in content.lower())

        if volatile_score > stable_score:
            return 'high_volatility'
        elif stable_score > volatile_score:
            return 'low_volatility'
        else:
            return 'moderate_volatility'

    def _assess_communication_style(self, content: str) -> str:
        """Assess communication style."""
        formal_indicators = ['therefore', 'consequently', 'accordingly', 'furthermore', 'moreover']
        informal_indicators = ['basically', 'actually', 'kinda', 'sorta', 'yeah']

        formal_score = sum(1 for word in formal_indicators if word.lower() in content.lower())
        informal_score = sum(1 for word in informal_indicators if word.lower() in content.lower())

        if formal_score > informal_score:
            return 'formal'
        elif informal_score > formal_score:
            return 'informal'
        else:
            return 'neutral'

    def _assess_problem_solving_approach(self, content: str) -> str:
        """Assess problem-solving approach."""
        analytical_indicators = ['analyze', 'evaluate', 'assess', 'investigate', 'research']
        creative_indicators = ['innovate', 'design', 'create', 'imagine', 'explore']
        practical_indicators = ['implement', 'build', 'fix', 'solve', 'execute']

        analytical_score = sum(1 for word in analytical_indicators if word.lower() in content.lower())
        creative_score = sum(1 for word in creative_indicators if word.lower() in content.lower())
        practical_score = sum(1 for word in practical_indicators if word.lower() in content.lower())

        max_score = max(analytical_score, creative_score, practical_score)

        if analytical_score == max_score:
            return 'analytical'
        elif creative_score == max_score:
            return 'creative'
        elif practical_score == max_score:
            return 'practical'
        else:
            return 'balanced'

    def _classify_report_type(self, node_id: str) -> str:
        """Classify report type from filename."""
        if '_decision_' in node_id:
            return 'decision'
        elif '_analysis_' in node_id:
            return 'analysis'
        elif '_lesson_' in node_id:
            return 'lesson'
        elif '_incident_' in node_id:
            return 'incident'
        else:
            return 'general'

    def _extract_creation_date(self, content: str) -> Optional[str]:
        """Extract creation date from content."""
        lines = content.split('\n')
        for line in lines:
            if '**COMPLETED:**' in line or '**CREATED:**' in line:
                # Extract date after the label
                parts = line.split(':', 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return None

    def dream_context(self, seed_concept: str, dream_depth: int = 3) -> Dict:
        """
        Generate a context dream starting from a seed concept.

        Uses depth-first traversal with mega.md branching factor to explore
        connected contexts and generate novel insights.

        Args:
            seed_concept: Starting concept or file ID
            dream_depth: How deep to explore (default: 3)

        Returns:
            Dream result with explored contexts and generated insights
        """
        print(f"🌙 Starting context dream from: {seed_concept}")
        print(f"📊 Using depth-first exploration (b={self.branching_factor}, d={dream_depth})")

        # Find starting nodes
        start_nodes = self._find_related_nodes(seed_concept)

        if not start_nodes:
            return {
                'success': False,
                'error': f'No nodes found related to: {seed_concept}',
                'dream': None
            }

        # Depth-first exploration
        explored_paths = []
        visited = set()

        for start_node in start_nodes[:self.branching_factor]:  # Limit branching
            path = self._depth_first_explore(start_node, dream_depth, visited.copy())
            if path:
                explored_paths.append(path)

        # Generate insights from explored paths
        insights = self._synthesize_insights(explored_paths, seed_concept)

        dream_result = {
            'success': True,
            'seed_concept': seed_concept,
            'explored_paths': explored_paths,
            'generated_insights': insights,
            'network_stats': {
                'total_nodes': len(self.network_graph),
                'explored_nodes': len(visited),
                'branching_factor_used': self.branching_factor,
                'max_depth': dream_depth
            },
            'timestamp': datetime.now().isoformat()
        }

        return dream_result

    def _find_related_nodes(self, concept: str) -> List[str]:
        """Find nodes related to a concept."""
        related = []

        # Direct filename match
        if concept in self.network_graph:
            related.append(concept)

        # Content search
        for node_id, node_data in self.network_graph.items():
            if concept.lower() in node_data['content_preview'].lower():
                related.append(node_id)

        # Reference search
        for node_id, node_data in self.network_graph.items():
            if any(concept in ref for ref in node_data['references']):
                related.append(node_id)

        return list(set(related))  # Remove duplicates

    def _depth_first_explore(self, start_node: str, max_depth: int, visited: Set[str], current_depth: int = 1) -> List[Dict]:
        """Perform depth-first exploration from a starting node."""
        if start_node in visited or current_depth > max_depth:
            return []

        visited.add(start_node)
        path = []

        if start_node in self.network_graph:
            node_data = self.network_graph[start_node]
            path.append({
                'node_id': start_node,
                'type': node_data['type'],
                'depth': current_depth,
                'references': node_data['references'][:self.branching_factor],  # Limit branching
                'content_preview': node_data['content_preview'][:200]
            })

            # Explore references depth-first
            for ref in node_data['references'][:self.branching_factor]:
                if ref in self.network_graph and ref not in visited:
                    sub_path = self._depth_first_explore(ref, max_depth, visited, current_depth + 1)
                    path.extend(sub_path)

        return path

    def _synthesize_insights(self, explored_paths: List[List], seed_concept: str) -> List[Dict]:
        """Synthesize novel insights from explored paths."""
        insights = []

        # Analyze connectivity patterns
        all_nodes = set()
        node_types = defaultdict(int)
        temporal_connections = []
        causal_chains = []

        for path in explored_paths:
            for node in path:
                all_nodes.add(node['node_id'])
                node_types[node['type']] += 1

                # Look for temporal patterns
                if node.get('created'):
                    temporal_connections.append((node['node_id'], node['created']))

                # Look for causal chains
                if len(node.get('references', [])) >= 2:
                    causal_chains.append(node['references'])

        # Generate insights based on patterns
        if len(all_nodes) > 1:
            insights.append({
                'type': 'connectivity',
                'insight': f"Found {len(all_nodes)} connected concepts from '{seed_concept}' across {len(node_types)} categories",
                'evidence': list(all_nodes),
                'confidence': min(0.9, len(all_nodes) / 10)  # Scale confidence with connectivity
            })

        if temporal_connections:
            sorted_temporal = sorted(temporal_connections, key=lambda x: x[1] or '')
            insights.append({
                'type': 'temporal_evolution',
                'insight': f"Evolution of '{seed_concept}' concepts over time: {len(sorted_temporal)} temporal connections",
                'evidence': [node_id for node_id, _ in sorted_temporal],
                'confidence': 0.8
            })

        if causal_chains:
            insights.append({
                'type': 'causal_patterns',
                'insight': f"Discovered {len(causal_chains)} potential causal chains related to '{seed_concept}'",
                'evidence': causal_chains[:3],  # Show top 3
                'confidence': 0.7
            })

        # Generate novel combinations
        if len(node_types) >= 3:
            type_combo = list(node_types.keys())[:3]
            insights.append({
                'type': 'novel_combination',
                'insight': f"Potential synergy between {', '.join(type_combo)} concepts for '{seed_concept}'",
                'evidence': [f"{t}:{c}" for t, c in node_types.items()],
                'confidence': 0.6
            })

        return insights

    def enhanced_context_dream(self, iterations: int = 10, save_progress: bool = True, target_depth: int = None) -> Dict:
        """
        Enhanced context dreaming with document-level parameters and mathematical optimization.

        Uses depth_vs_breathe.md mathematical targets for optimal vectorization:
        - Optimal depth d=5 (token-safe) or d=7 (superior performance)
        - Branching factor b=3 (mathematically verified)
        - 52× connectivity advantage at d=7

        Args:
            iterations: Number of random analysis iterations
            save_progress: Save profiles after each iteration
            target_depth: Override automatic depth calculation

        Returns:
            Comprehensive dream result with mathematical analysis
        """
        # Calculate optimal depth using mathematical constraints
        if target_depth is None:
            target_depth = self.calculate_optimal_depth()

        vectorization = self.vectorize_dreaming_strategy(target_depth)

        print(f"🌙 Starting enhanced context dreaming: {iterations} iterations")
        print(f"📊 Network contains {len(self.network_graph)} nodes")
        print(f"🎯 Mathematical targets from depth_vs_breathe.md:")
        print(f"   • Optimal depth: d={vectorization['optimal_depth']} (token-safe)")
        print(f"   • Superior depth: d={self.superior_depth} (52× advantage)")
        print(f"   • Branching factor: b={vectorization['branching_factor']} (verified)")
        print(f"   • Expected connectivity gain: {vectorization['expected_connectivity_gain']:.1f}×")
        print(f"   • Inference capability: {vectorization['inference_capability_hops']}-hop transitive")
        print("-" * 70)

        dream_results = {
            'iterations_completed': 0,
            'total_connections_discovered': 0,
            'parameter_evolution': {},
            'connectivity_insights': [],
            'final_profiles': {},
            'mathematical_analysis': vectorization,
            'timestamp': datetime.now().isoformat()
        }

        for iteration in range(iterations):
            print(f"\n🔄 Iteration {iteration + 1}/{iterations}")

            # Randomly select 2-4 files for analysis (comprehensive but not overwhelming)
            sample_size = random.randint(2, 4)
            available_files = list(self.network_graph.keys())
            if len(available_files) < sample_size:
                print(f"⚠️  Not enough files for analysis ({len(available_files)} < {sample_size})")
                break

            selected_files = random.sample(available_files, sample_size)
            print(f"📂 Analyzing {sample_size} files: {', '.join(selected_files)}")

            # Analyze connectivity between selected files
            connectivity_result = self._analyze_file_connectivity(selected_files)

            if connectivity_result['connections_found'] > 0:
                dream_results['total_connections_discovered'] += connectivity_result['connections_found']

                # Update context profiles based on findings
                self._update_profiles_from_connectivity(connectivity_result, selected_files)

                dream_results['connectivity_insights'].append({
                    'iteration': iteration + 1,
                    'files_analyzed': selected_files,
                    'connectivity': connectivity_result
                })

                print(f"🔗 Found {connectivity_result['connections_found']} connections")

            # Track parameter evolution
            for file_id in selected_files:
                if file_id not in dream_results['parameter_evolution']:
                    dream_results['parameter_evolution'][file_id] = []
                if file_id in self.context_profiles:
                    dream_results['parameter_evolution'][file_id].append({
                        'iteration': iteration + 1,
                        'parameters': self.context_profiles[file_id]['parameters'].copy()
                    })

            dream_results['iterations_completed'] = iteration + 1

            if save_progress and (iteration + 1) % 5 == 0:
                self._save_context_profiles()
                print(f"💾 Progress saved at iteration {iteration + 1}")

        # Finalize results
        dream_results['final_profiles'] = self.context_profiles.copy()
        self._save_context_profiles()

        print(f"\n✅ Enhanced dreaming complete!")
        print(f"🔗 Total connections discovered: {dream_results['total_connections_discovered']}")
        print(f"📊 Profiles updated for {len(self.context_profiles)} documents")

        return dream_results

    def test_direct_links_between_two_files(self, max_links: int = 5) -> Dict:
        """
        Test job: Find up to max_links direct connections between two randomly selected files.
        No further depth exploration - just direct 1-1 relationships.

        This tests the foundation for metadata visibility before attempting complex tasks like 152.
        """
        print("🧪 Testing Direct Link Discovery Between Two Files")
        print(f"🎯 Target: Find up to {max_links} direct links between 2 random files")
        print("-" * 60)

        # Select exactly 2 random files
        available_files = list(self.network_graph.keys())
        if len(available_files) < 2:
            return {'error': 'Not enough files in network graph'}

        selected_files = random.sample(available_files, 2)
        file_a, file_b = selected_files[0], selected_files[1]

        print(f"📂 Selected files:")
        print(f"   A: {file_a}")
        print(f"   B: {file_b}")
        print()

        # Get file analyses
        analysis_a = self.network_graph.get(file_a, {})
        analysis_b = self.network_graph.get(file_b, {})

        if not analysis_a or not analysis_b:
            return {'error': 'Missing analysis data for selected files'}

        # Find direct links between these two files only
        direct_links = self._find_direct_links_between_files(file_a, analysis_a, file_b, analysis_b, max_links)

        result = {
            'file_a': file_a,
            'file_b': file_b,
            'links_found': len(direct_links),
            'max_links_requested': max_links,
            'direct_links': direct_links,
            'analysis_summary': {
                'file_a_type': analysis_a.get('file_type', 'unknown'),
                'file_b_type': analysis_b.get('file_type', 'unknown'),
                'file_a_size': analysis_a.get('size', 0),
                'file_b_size': analysis_b.get('size', 0)
            }
        }

        print(f"🔗 Direct links found: {len(direct_links)}/{max_links}")
        if direct_links:
            print("📋 Links discovered:")
            for i, link in enumerate(direct_links, 1):
                print(f"   {i}. {link['type']}: {link['description']}")
                print(f"      Strength: {link['strength']:.3f}")
        else:
            print("❌ No direct links found between these files")

        return result

    def discover_connection_parameters(self, iterations: int = 10) -> Dict:
        """
        Parameter Discovery Engine with Relative Value Matrix.

        This implements the action-reflection-learning cycle with a reference-based
        relative value system:

        1. IDENTIFY REFERENCE: Find the strongest connection in codebase as baseline
        2. MATRIX CONSTRUCTION: Test parameter combinations against reference
        3. RELATIVE ANALYSIS: Understand parameter sensitivity and optimal ranges
        4. LEARNING: Update parameters based on relative performance

        Goal: Teach AI to value connections through calibrated relative understanding.
        """
        print("🔬 Parameter Discovery Engine - Relative Value Matrix")
        print("🎯 Learning connection valuation through reference-based calibration")
        print("=" * 70)

        # PHASE 1: Identify Reference Connection
        print("\n📍 PHASE 1: Finding Reference Connection")
        reference_connection = self._find_reference_connection()
        if not reference_connection:
            print("❌ No suitable reference connection found")
            return {
                'error': 'No reference connection found. Foundation metadata needs strengthening before parameter discovery can run.',
                'recommendations': [
                    'Enhance keyword/concept extraction algorithms',
                    'Add more connection evidence types (semantic, behavioral, dependency)',
                    'Improve file analysis depth and quality',
                    'Consider synthetic high-quality connections for initial testing'
                ]
            }

        print(f"✅ Reference: {reference_connection['file_a']} ↔ {reference_connection['file_b']}")
        print(f"   Strength: {reference_connection['strength']:.3f}")
        print(f"   Type: {reference_connection['type']}")

        # PHASE 2: Construct Relative Value Matrix
        print("\n📊 PHASE 2: Constructing Relative Value Matrix")
        parameter_matrix = self._construct_parameter_matrix(reference_connection, iterations)

        # PHASE 3: Analyze Relative Performance
        print("\n🔍 PHASE 3: Analyzing Relative Performance")
        matrix_analysis = self._analyze_parameter_matrix(parameter_matrix, reference_connection)

        # PHASE 4: Learning from Relative Insights
        print("\n🧠 PHASE 4: Learning from Relative Insights")
        learning_result = self._learn_from_matrix_analysis(matrix_analysis, reference_connection)

        result = {
            'reference_connection': reference_connection,
            'parameter_matrix': parameter_matrix,
            'matrix_analysis': matrix_analysis,
            'learning_result': learning_result,
            'mathematical_foundation': self._calculate_parameter_mathematics(learning_result.get('final_parameters', {}))
        }

        print(f"\n🎓 Relative Learning Complete!")
        print(f"📊 Matrix constructed with {len(parameter_matrix)} parameter combinations")
        print(f"🧮 Reference baseline: {reference_connection['strength']:.3f}")

        return result

    def _find_reference_connection(self) -> Optional[Dict]:
        """
        Find a reference connection using the three superior contextual files:
        1. FEATURE_VALIDATION.md - central truth/reference point
        2. context_profiles.json - parameter navigation
        3. keeper_knowledge.db - semantic search database

        This organizes all connections around these three superior reference points.
        """
        print("   🔍 Scanning for connections to superior reference files...")

        superior_files = [
            'FEATURE_VALIDATION.md',
            'context_profiles.json',
            'keeper_knowledge.db'
        ]

        # Check if superior files exist in network graph
        available_superior = [f for f in superior_files if f in self.network_graph]

        if not available_superior:
            print("   ⚠️  No superior reference files found in network graph")
            return None

        print(f"   📍 Found {len(available_superior)} superior reference files: {available_superior}")

        # Find the most connected file that references at least one superior file
        best_connection = None
        max_connections = 0

        for file_id, analysis in self.network_graph.items():
            if file_id in superior_files:
                continue  # Skip the superior files themselves

            connections_to_superior = 0
            connection_evidence = []

            # Check connections to each superior file
            for superior_file in available_superior:
                if superior_file not in self.network_graph:
                    continue

                superior_analysis = self.network_graph[superior_file]

                # Check for references to superior files
                references = analysis.get('references', [])
                if any(superior_file in ref for ref in references):
                    connections_to_superior += 1
                    connection_evidence.append(f"References {superior_file}")

                # Check for mentions of superior concepts
                mentions = analysis.get('mentions', [])
                superior_basename = superior_file.split('.')[0].lower()
                if any(superior_basename in str(m).lower() for m in mentions):
                    connections_to_superior += 0.5
                    connection_evidence.append(f"Mentions {superior_basename}")

                # Check content similarity with superior files
                content_sim = self._calculate_content_similarity(analysis, superior_analysis)
                if content_sim > 0.3:  # Lower threshold for superior files
                    connections_to_superior += content_sim
                    connection_evidence.append(f"Content similarity {content_sim:.2f} with {superior_file}")

                # Enhanced connection detection using new metadata (TASK_0167 Phase 2)
                metadata_a = analysis.get('metadata', {})
                metadata_b = superior_analysis.get('metadata', {})
                
                # Semantic concept overlap
                concepts_a = set(metadata_a.get('semantic_concepts', []))
                concepts_b = set(metadata_b.get('semantic_concepts', []))
                concept_overlap = len(concepts_a & concepts_b)
                if concept_overlap > 0:
                    connections_to_superior += concept_overlap * 0.2
                    connection_evidence.append(f"Shared {concept_overlap} semantic concepts with {superior_file}")
                
                # Behavioral pattern similarity
                patterns_a = set(metadata_a.get('behavioral_patterns', []))
                patterns_b = set(metadata_b.get('behavioral_patterns', []))
                pattern_overlap = len(patterns_a & patterns_b)
                if pattern_overlap > 0:
                    connections_to_superior += pattern_overlap * 0.15
                    connection_evidence.append(f"Shared {pattern_overlap} behavioral patterns with {superior_file}")
                
                # Dependency graph connections
                dep_a = metadata_a.get('dependency_graph', {})
                dep_b = metadata_b.get('dependency_graph', {})
                dep_refs_a = set(dep_a.get('references', []))
                dep_refs_b = set(dep_b.get('references', []))
                dep_overlap = len(dep_refs_a & dep_refs_b)
                if dep_overlap > 0:
                    connections_to_superior += dep_overlap * 0.1
                    connection_evidence.append(f"Shared {dep_overlap} dependency references with {superior_file}")
                
                # Relationship strength correlation
                strength_a = metadata_a.get('relationship_strength', {}).get('overall_confidence', 0)
                strength_b = metadata_b.get('relationship_strength', {}).get('overall_confidence', 0)
                strength_correlation = min(strength_a, strength_b) * 0.05  # Small bonus for high-confidence files
                connections_to_superior += strength_correlation

            if connections_to_superior > max_connections and connections_to_superior >= 1.0:
                max_connections = connections_to_superior
                best_connection = {
                    'file_a': file_id,
                    'file_b': available_superior[0],  # Use first superior as primary reference
                    'type': 'superior_reference',
                    'strength': connections_to_superior,
                    'description': f"Connected to superior reference files ({len(available_superior)} available)",
                    'evidence': connection_evidence,
                    'superior_files': available_superior,
                    'detailed_scores': {
                        'similarity_score': connections_to_superior * 0.3,  # Mock scores for compatibility
                        'structural_score': connections_to_superior * 0.2,
                        'contextual_score': connections_to_superior * 0.4,
                        'temporal_score': 0.5,
                        'frequency_penalty': 0.1
                    }
                }

        if best_connection:
            print(f"   ✅ Found reference connection: {best_connection['file_a']} ↔ {best_connection['file_b']}")
            print(f"      Strength: {best_connection['strength']:.2f}, Evidence: {best_connection['evidence']}")
            return best_connection

        print("   ❌ No suitable reference connection found to superior files")
        return None

    def _calculate_content_similarity(self, analysis_a: Dict, analysis_b: Dict) -> float:
        """Calculate content similarity between two file analyses."""
        content_a = analysis_a.get('content_preview', '').lower()
        content_b = analysis_b.get('content_preview', '').lower()

        if not content_a or not content_b:
            return 0.0

        # Simple word overlap similarity
        words_a = set(content_a.split())
        words_b = set(content_b.split())
        common_words = words_a & words_b

        similarity = len(common_words) / max(len(words_a | words_b), 1)
        return similarity

    def _construct_parameter_matrix(self, reference_connection: Dict, matrix_size: int = 10) -> List[Dict]:
        """Construct a matrix of parameter combinations tested against the reference."""
        print(f"   🧮 Building {matrix_size}x{matrix_size} parameter matrix...")

        matrix = []

        # Define parameter ranges to test
        param_ranges = {
            'similarity_threshold': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            'structural_weight': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            'contextual_boost': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            'temporal_decay': [0.5, 0.6, 0.7, 0.8, 0.9],  # Fewer values for this
            'frequency_penalty': [0.0, 0.1, 0.2, 0.3, 0.4],  # Fewer values for this
            'punctual_boost': [0.2, 0.4, 0.6, 0.8],  # Situational spike weighting
            'situational_weight': [0.3, 0.5, 0.7, 0.9],  # Context importance
            'specificity_threshold': [0.2, 0.4, 0.6, 0.8],  # Detail precision
        }

        # Generate parameter combinations (limit to matrix_size)
        combinations_tested = 0
        max_combinations = matrix_size * matrix_size

        for sim_thresh in param_ranges['similarity_threshold']:
            for struct_weight in param_ranges['structural_weight']:
                if combinations_tested >= max_combinations:
                    break

                # Use reference values for other parameters initially
                test_params = {
                    'similarity_threshold': sim_thresh,
                    'structural_weight': struct_weight,
                    'contextual_boost': 0.4,  # Reference value
                    'temporal_decay': 0.8,    # Reference value
                    'frequency_penalty': 0.2, # Reference value
                    'punctual_boost': 0.5,    # Reference value for situational spikes
                    'situational_weight': 0.7, # Reference value for context importance
                    'specificity_threshold': 0.4, # Reference value for detail precision
                }

                # Test this parameter combination against the reference connection
                performance = self._test_parameters_against_reference(reference_connection, test_params)

                matrix.append({
                    'parameters': test_params,
                    'reference_performance': performance,
                    'relative_score': performance['connection_strength'] / reference_connection['strength']
                })

                combinations_tested += 1

            if combinations_tested >= max_combinations:
                break

        print(f"   ✅ Matrix constructed: {len(matrix)} parameter combinations tested")
        return matrix

    def _test_parameters_against_reference(self, reference: Dict, test_params: Dict) -> Dict:
        """Test parameter combination against the reference connection."""
        file_a, file_b = reference['file_a'], reference['file_b']
        analysis_a = self.network_graph.get(file_a, {})
        analysis_b = self.network_graph.get(file_b, {})

        if not analysis_a or not analysis_b:
            return {'connection_found': False, 'connection_strength': 0.0}

        # Test connections with these parameters
        connections = self._evaluate_connections_with_parameters(
            file_a, analysis_a, file_b, analysis_b, test_params
        )

        if not connections:
            return {'connection_found': False, 'connection_strength': 0.0}

        # Find the strongest connection (should be the reference type if parameters allow)
        strongest = max(connections, key=lambda x: x['strength'])

        return {
            'connection_found': True,
            'connection_strength': strongest['strength'],
            'connection_type': strongest['type'],
            'relative_to_reference': strongest['strength'] / reference['strength']
        }

    def _analyze_parameter_matrix(self, matrix: List[Dict], reference: Dict) -> Dict:
        """Analyze the parameter matrix to understand relative performance."""
        print("   📈 Analyzing parameter sensitivity and optimal ranges...")

        analysis = {
            'total_combinations': len(matrix),
            'reference_strength': reference['strength'],
            'performance_distribution': [],
            'parameter_sensitivity': {},
            'optimal_ranges': {}
        }

        # Analyze performance distribution
        performances = [entry['reference_performance']['connection_strength'] for entry in matrix]
        if performances:
            max_perf = max(performances) if max(performances) > 0 else 1.0  # Avoid division by zero
            analysis['performance_distribution'] = {
                'min': min(performances),
                'max': max(performances),
                'mean': sum(performances) / len(performances),
                'reference_ratio': reference['strength'] / max_perf
            }
        else:
            analysis['performance_distribution'] = {
                'min': 0,
                'max': 0,
                'mean': 0,
                'reference_ratio': 0
            }

        # Analyze parameter sensitivity
        param_sensitivity = {}
        for param_name in ['similarity_threshold', 'structural_weight', 'contextual_boost',
                          'punctual_boost', 'situational_weight', 'specificity_threshold']:
            param_values = [entry['parameters'][param_name] for entry in matrix]
            param_performances = [entry['reference_performance']['connection_strength'] for entry in matrix]

            # Calculate correlation between parameter value and performance
            if len(set(param_values)) > 1:  # Need variation to calculate correlation
                correlation = self._calculate_correlation(param_values, param_performances)
                param_sensitivity[param_name] = correlation

        analysis['parameter_sensitivity'] = param_sensitivity

        # Find optimal ranges (parameters that maintain reference connection)
        optimal_combinations = [
            entry for entry in matrix
            if entry['reference_performance']['connection_found'] and
            entry['relative_score'] >= 0.8  # Maintains 80% of reference strength
        ]

        analysis['optimal_ranges'] = {
            'count': len(optimal_combinations),
            'ranges': {}
        }

        if optimal_combinations:
            analysis['optimal_ranges']['ranges'] = {
                'similarity_range': [
                    min(c['parameters']['similarity_threshold'] for c in optimal_combinations),
                    max(c['parameters']['similarity_threshold'] for c in optimal_combinations)
                ],
                'structural_range': [
                    min(c['parameters']['structural_weight'] for c in optimal_combinations),
                    max(c['parameters']['structural_weight'] for c in optimal_combinations)
                ],
                'punctual_range': [
                    min(c['parameters']['punctual_boost'] for c in optimal_combinations),
                    max(c['parameters']['punctual_boost'] for c in optimal_combinations)
                ],
                'situational_range': [
                    min(c['parameters']['situational_weight'] for c in optimal_combinations),
                    max(c['parameters']['situational_weight'] for c in optimal_combinations)
                ]
            }

        print(f"   ✅ Analysis complete: {len(optimal_combinations)} optimal parameter ranges found")
        return analysis

    def _calculate_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5

        return numerator / denominator if denominator != 0 else 0.0

    def _learn_from_matrix_analysis(self, analysis: Dict, reference: Dict) -> Dict:
        """Learn optimal parameters from matrix analysis."""
        print("   🧠 Synthesizing learning insights from relative analysis...")

        # Extract optimal parameters from analysis
        optimal_params = {
            'similarity_threshold': 0.3,  # Default fallback
            'structural_weight': 0.6,     # Default fallback
            'contextual_boost': 0.4,      # Default fallback
            'temporal_decay': 0.8,        # Stable
            'frequency_penalty': 0.2,     # Stable
            'punctual_boost': 0.5,        # Default for situational spikes
            'situational_weight': 0.7,    # Default for context importance
            'specificity_threshold': 0.4  # Default for detail precision
        }

        # Use optimal ranges if available
        if 'optimal_ranges' in analysis and analysis['optimal_ranges']['count'] > 0:
            ranges = analysis['optimal_ranges']['ranges']
            optimal_params['similarity_threshold'] = sum(ranges['similarity_range']) / 2
            optimal_params['structural_weight'] = sum(ranges['structural_range']) / 2
            if 'punctual_range' in ranges:
                optimal_params['punctual_boost'] = sum(ranges['punctual_range']) / 2
            if 'situational_range' in ranges:
                optimal_params['situational_weight'] = sum(ranges['situational_range']) / 2

        # Adjust based on sensitivity analysis
        sensitivity = analysis.get('parameter_sensitivity', {})
        for param, correlation in sensitivity.items():
            if param in optimal_params:
                if correlation > 0.5:  # Strong positive correlation
                    optimal_params[param] *= 1.1  # Increase slightly
                elif correlation < -0.5:  # Strong negative correlation
                    optimal_params[param] *= 0.9  # Decrease slightly

        # Ensure parameters stay in valid range
        for param in optimal_params:
            optimal_params[param] = max(0.0, min(1.0, optimal_params[param]))

        learning_result = {
            'final_parameters': optimal_params,
            'learning_method': 'relative_value_matrix',
            'reference_baseline': reference['strength'],
            'optimal_ranges_found': analysis.get('optimal_ranges', {}).get('count', 0),
            'parameter_sensitivity': sensitivity,
            'insights': [
                f"Reference connection strength: {reference['strength']:.3f}",
                f"Optimal parameter ranges found: {analysis.get('optimal_ranges', {}).get('count', 0)}",
                f"Most sensitive parameter: {max(sensitivity, key=sensitivity.get) if sensitivity else 'None'}"
            ]
        }

        print(f"   ✅ Learning complete: Optimal parameters calibrated against reference")
        return learning_result

        # Initialize parameter space
        parameters = {
            'similarity_threshold': 0.3,      # How similar must content be?
            'temporal_decay': 0.8,           # How much does time matter?
            'structural_weight': 0.6,        # Code structure vs content?
            'contextual_boost': 0.4,         # Project context importance?
            'frequency_penalty': 0.2,        # Penalize over-connections?
            'punctual_boost': 0.5,           # Weight for situational spikes?
            'situational_weight': 0.7,       # Current context importance?
            'specificity_threshold': 0.4,    # Detail precision requirement?
        }

        learning_history = []  # Keep only last 50 cycles to prevent memory issues
        parameter_evolution = {k: [v] for k, v in parameters.items()}

        for iteration in range(iterations):
            print(f"\n🔄 Learning Cycle {iteration + 1}/{iterations}")
            print(f"📊 Current Parameters: {parameters}")

            # ACTION: Test current parameters on random file pairs
            test_results = self._test_parameter_hypotheses(parameters, sample_size=5)

            # REFLECTION: Analyze results against expected patterns
            reflection = self._analyze_parameter_performance(test_results, parameters)

            # LEARNING: Update parameters based on reflection
            parameter_updates = self._learn_from_reflection(reflection, parameters)

            # Apply updates
            for param, update in parameter_updates.items():
                if param in parameters:
                    old_val = parameters[param]
                    new_val = max(0.0, min(1.0, old_val + update))  # Clamp to [0,1]
                    parameters[param] = new_val
                    parameter_evolution[param].append(new_val)
                    print(f"   📈 {param}: {old_val:.3f} → {new_val:.3f} ({'+' if update > 0 else ''}{update:.3f})")

            # Store simplified history (limit memory usage)
            simplified_reflection = {
                'performance_score': reflection['performance_score'],
                'avg_connection_quality': reflection.get('avg_connection_quality', 0),
                'parameter_sensitivity': reflection['parameter_sensitivity'],
                'connections_found': sum(r['connections_found'] for r in test_results),
                'rejected_connections': sum(r.get('rejected_connections', 0) for r in test_results)
            }

            learning_history.append({
                'iteration': iteration + 1,
                'parameters': parameters.copy(),
                'reflection': simplified_reflection,
                'updates': parameter_updates
            })

            # Keep only last 50 cycles to prevent memory explosion
            if len(learning_history) > 50:
                learning_history = learning_history[-50:]

        # Final analysis
        final_insights = self._synthesize_learning_insights(learning_history)

        result = {
            'learning_cycles': iterations,
            'final_parameters': parameters,
            'parameter_evolution': parameter_evolution,
            'learning_history': learning_history,
            'insights': final_insights,
            'mathematical_foundation': self._calculate_parameter_mathematics(parameters)
        }

        print(f"\n🎓 Learning Complete!")
        print(f"📊 Final Parameters: {parameters}")
        print(f"🧠 Key Insights: {final_insights.get('key_findings', [])}")

        return result

    def _test_parameter_hypotheses(self, parameters: Dict, sample_size: int = 5) -> List[Dict]:
        """Test current parameters on random file pairs to generate hypotheses."""
        results = []

        for i in range(sample_size):
            # Select random file pair
            available_files = list(self.network_graph.keys())
            if len(available_files) < 2:
                continue

            file_a, file_b = random.sample(available_files, 2)
            analysis_a = self.network_graph.get(file_a, {})
            analysis_b = self.network_graph.get(file_b, {})

            if not analysis_a or not analysis_b:
                continue

            # Test connections with current parameters
            connections = self._evaluate_connections_with_parameters(
                file_a, analysis_a, file_b, analysis_b, parameters
            )

            # QUALITY VALIDATION: Filter out false positives before learning
            # Only accept connections that meet strict quality standards
            validated_connections = []
            for conn in connections:
                # Add detailed scoring for validation
                detailed_conn = conn.copy()
                detailed_conn.update({
                    'similarity_score': self._calculate_similarity_score(file_a, analysis_a, file_b, analysis_b),
                    'structural_score': self._calculate_structural_score(file_a, analysis_a, file_b, analysis_b),
                    'contextual_score': self._calculate_contextual_score(file_a, analysis_a, file_b, analysis_b),
                    'temporal_score': self._calculate_temporal_score(analysis_a, analysis_b),
                    'frequency_penalty': self._calculate_frequency_penalty(file_a, file_b)
                })

                # Only accept if it passes quality validation
                if self._validate_connection_quality(detailed_conn, parameters):
                    validated_connections.append(detailed_conn)

            results.append({
                'file_pair': (file_a, file_b),
                'connections_found': len(validated_connections),  # Use validated count
                'connections': validated_connections,  # Use validated connections
                'rejected_connections': len(connections) - len(validated_connections),  # Track rejections
                'file_types': (analysis_a.get('file_type'), analysis_b.get('file_type')),
                'metadata': {
                    'size_a': analysis_a.get('size', 0),
                    'size_b': analysis_b.get('size', 0),
                    'age_a': analysis_a.get('age_days', 0),
                    'age_b': analysis_b.get('age_days', 0)
                }
            })

        return results

    def _evaluate_connections_with_parameters(self, file_a: str, analysis_a: Dict,
                                           file_b: str, analysis_b: Dict,
                                           parameters: Dict) -> List[Dict]:
        """Evaluate connections using current parameter set with enhanced metadata integration."""
        connections = []

        # Enhanced connection types with parameter weighting AND enhanced metadata
        connection_types = [
            ('structural', self._check_structural_connections, parameters['structural_weight']),
            ('reference_based', self._check_reference_connections, parameters['structural_weight']),
            ('content_similarity', self._check_content_similarity, parameters['similarity_threshold']),
            ('temporal_proximity', self._check_temporal_proximity, parameters['temporal_decay']),
            ('contextual_relevance', self._check_contextual_relevance, parameters['contextual_boost']),
            ('frequency_based', self._check_frequency_patterns, parameters['frequency_penalty']),
            ('punctual_relevance', self._check_punctual_relevance, parameters['similarity_threshold']),
            ('situational_context', self._check_situational_context, parameters['contextual_boost']),
            ('detail_specificity', self._check_detail_specificity, parameters['structural_weight']),
            # ENHANCED METADATA CONNECTIONS - THE MISSING PIECE!
            ('semantic_concepts', self._check_semantic_concept_connections, parameters['similarity_threshold']),
            ('behavioral_patterns', self._check_behavioral_pattern_connections, parameters['contextual_boost']),
            ('dependency_graph', self._check_dependency_graph_connections, parameters['structural_weight']),
            ('relationship_strength', self._check_relationship_strength_connections, parameters['contextual_boost']),
        ]

        # Calculate QKV relevance vector once for the file pair
        qkv_vector = self._calculate_qkv_relevance_vector(file_a, analysis_a, file_b, analysis_b)

        for conn_type, check_func, weight in connection_types:
            try:
                result = check_func(file_a, analysis_a, file_b, analysis_b, parameters)
                if result and result['strength'] > 0.1:  # Lower threshold for learning
                    connection = {
                        'type': conn_type,
                        'strength': result['strength'] * weight,
                        'description': result['description'],
                        'evidence': result.get('evidence', []),
                        'qkv_dimensions': qkv_vector  # Include QKV relevance vector
                    }
                    connections.append(connection)
            except Exception as e:
                continue  # Skip failed checks during learning

        # Sort by strength and return top connections
        connections.sort(key=lambda x: x['strength'], reverse=True)
        return connections[:3]  # Limit to strongest 3 per pair

    def _check_structural_connections(self, file_a: str, analysis_a: Dict,
                                    file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for structural/code-level connections."""
        # Import relationships
        imports_a = set(analysis_a.get('imports', []))
        imports_b = set(analysis_b.get('imports', []))
        common_imports = imports_a & imports_b

        # Function/class relationships
        functions_a = {f.get('name', '') for f in analysis_a.get('functions', [])}
        functions_b = {f.get('name', '') for f in analysis_b.get('functions', [])}

        structural_strength = 0
        evidence = []

        if common_imports:
            structural_strength += len(common_imports) * 0.3
            evidence.append(f"Shared imports: {list(common_imports)[:3]}")

        # Check for function references
        for func_a in functions_a:
            for func_b in functions_b:
                if func_b in func_a or func_a in func_b:
                    structural_strength += 0.4
                    evidence.append(f"Function relationship: {func_a} ↔ {func_b}")
                    break

        if structural_strength > 0:
            return {
                'strength': min(1.0, structural_strength),
                'description': f"Structural connections ({len(evidence)} relationships)",
                'evidence': evidence
            }
        return None

    def _check_reference_connections(self, file_a: str, analysis_a: Dict,
                                   file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for reference-based connections in markdown and documentation files."""

        # Shared references (files that both reference)
        refs_a = set(analysis_a.get('references', []))
        refs_b = set(analysis_b.get('references', []))
        common_refs = refs_a & refs_b
        print(f"  References A: {list(refs_a)[:3]}")
        print(f"  References B: {list(refs_b)[:3]}")
        print(f"  Common refs: {list(common_refs)}")

        # Shared mentions (concepts/tasks mentioned in both)
        mentions_a = set(analysis_a.get('mentions', []))
        mentions_b = set(analysis_b.get('mentions', []))
        common_mentions = mentions_a & mentions_b
        print(f"  Mentions A: {list(mentions_a)[:3]}")
        print(f"  Mentions B: {list(mentions_b)[:3]}")
        print(f"  Common mentions: {list(common_mentions)}")

        # Shared links
        links_a = set(analysis_a.get('links', []))
        links_b = set(analysis_b.get('links', []))
        common_links = links_a & links_b

        if common_links:
            reference_strength += len(common_links) * 0.5
            evidence.append(f"Shared links: {list(common_links)[:3]}")

        # Shared headers/topics
        headers_a = set(h.get('title', '') for h in analysis_a.get('headers', []))
        headers_b = set(h.get('title', '') for h in analysis_b.get('headers', []))
        common_headers = headers_a & headers_b

        if common_headers:
            reference_strength += len(common_headers) * 0.2
            evidence.append(f"Shared headers: {list(common_headers)[:3]}")

        # Code block similarity (shared code patterns)
        code_a = set(cb.get('content', '') for cb in analysis_a.get('code_blocks', []))
        code_b = set(cb.get('content', '') for cb in analysis_b.get('code_blocks', []))
        common_code = code_a & code_b

        if common_code:
            reference_strength += len(common_code) * 0.6
            evidence.append(f"Shared code patterns: {len(common_code)} blocks")

        if reference_strength > 0:
            return {
                'strength': min(1.0, reference_strength),
                'description': f"Reference connections ({len(evidence)} relationships)",
                'evidence': evidence
            }
        return None

    def _check_content_similarity(self, file_a: str, analysis_a: Dict,
                                file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for content similarity using parameter thresholds."""
        content_a = analysis_a.get('content_summary', '').lower()
        content_b = analysis_b.get('content_summary', '').lower()

        if not content_a or not content_b:
            return None

        # Word overlap analysis
        words_a = set(content_a.split())
        words_b = set(content_b.split())
        common_words = words_a & words_b

        similarity = len(common_words) / max(len(words_a | words_b), 1)
        threshold = params['similarity_threshold']

        if similarity > threshold:
            return {
                'strength': similarity,
                'description': f"Content similarity: {len(common_words)} common terms",
                'evidence': [f"Common words: {', '.join(list(common_words)[:5])}"]
            }
        return None

    def _check_temporal_proximity(self, file_a: str, analysis_a: Dict,
                                file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check if files were created/edited around the same time."""
        age_a = analysis_a.get('age_days', 0)
        age_b = analysis_b.get('age_days', 0)

        if age_a == 0 or age_b == 0:
            return None

        # Calculate temporal proximity (newer files = higher proximity)
        max_age = max(age_a, age_b)
        age_diff = abs(age_a - age_b)
        proximity = 1.0 - (age_diff / max_age) if max_age > 0 else 0

        # Apply temporal decay parameter
        decayed_proximity = proximity * params['temporal_decay']

        if decayed_proximity > 0.3:
            return {
                'strength': decayed_proximity,
                'description': f"Temporal proximity: {age_diff} days apart",
                'evidence': [f"Age A: {age_a}d, Age B: {age_b}d"]
            }
        return None

    def _check_contextual_relevance(self, file_a: str, analysis_a: Dict,
                                  file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check if files belong to related project contexts."""
        type_a = analysis_a.get('file_type', '')
        type_b = analysis_b.get('file_type', '')

        # Define contextual relationships
        context_map = {
            'python': ['test', 'config', 'docs', 'template'],
            'markdown': ['docs', 'template', 'task', 'report'],
            'json': ['config', 'data', 'template'],
            'javascript': ['html', 'css', 'config'],
            'typescript': ['html', 'css', 'config']
        }

        relevance = 0
        evidence = []

        # Type compatibility
        if type_a in context_map and type_b in context_map[type_a]:
            relevance += 0.5
            evidence.append(f"Type relationship: {type_a} ↔ {type_b}")

        # Size similarity (similar complexity)
        size_a = analysis_a.get('size', 0)
        size_b = analysis_b.get('size', 0)
        if size_a > 0 and size_b > 0:
            size_ratio = min(size_a, size_b) / max(size_a, size_b)
            relevance += size_ratio * 0.3
            evidence.append(f"Size similarity: {size_ratio:.2f}")

        contextual_strength = relevance * params['contextual_boost']

        if contextual_strength > 0.2:
            return {
                'strength': contextual_strength,
                'description': f"Contextual relevance ({len(evidence)} factors)",
                'evidence': evidence
            }
        return None

    def _check_frequency_patterns(self, file_a: str, analysis_a: Dict,
                                file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for frequency-based connection patterns."""
        # This would analyze how often files are referenced together
        # For now, use a simple co-occurrence approximation
        refs_a = analysis_a.get('reference_count', 0)
        refs_b = analysis_b.get('reference_count', 0)

        if refs_a == 0 or refs_b == 0:
            return None

        # Penalize over-connected files (frequency_penalty parameter)
        frequency_score = min(refs_a, refs_b) / max(refs_a, refs_b)
        penalized_score = frequency_score * (1.0 - params['frequency_penalty'])

        if penalized_score > 0.4:
            return {
                'strength': penalized_score,
                'description': f"Frequency pattern: {refs_a} ↔ {refs_b} references",
                'evidence': [f"Reference counts: A={refs_a}, B={refs_b}"]
            }
        return None

    def _check_punctual_relevance(self, file_a: str, analysis_a: Dict,
                                file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for punctual relevance - situational spikes based on specific content matches."""
        content_a = analysis_a.get('content_preview', '').lower()
        content_b = analysis_b.get('content_preview', '').lower()

        if not content_a or not content_b:
            return None

        punctual_strength = 0
        evidence = []

        # Check for exact phrase matches (high specificity)
        words_a = set(content_a.split())
        words_b = set(content_b.split())

        # Find exact 2-3 word phrases that match
        phrases_a = self._extract_phrases(content_a, 2) + self._extract_phrases(content_a, 3)
        phrases_b = self._extract_phrases(content_b, 2) + self._extract_phrases(content_b, 3)

        exact_phrase_matches = set(phrases_a) & set(phrases_b)
        if exact_phrase_matches:
            punctual_strength += len(exact_phrase_matches) * 0.8
            evidence.append(f"Exact phrase matches: {len(exact_phrase_matches)} phrases")

        # Check for specific technical terms (API names, function names, etc.)
        technical_terms_a = self._extract_technical_terms(content_a)
        technical_terms_b = self._extract_technical_terms(content_b)
        common_technical = technical_terms_a & technical_terms_b

        if common_technical:
            punctual_strength += len(common_technical) * 0.6
            evidence.append(f"Technical term matches: {list(common_technical)[:3]}")

        # Check for specific numbers/dates/versions that match
        specific_matches_a = self._extract_specific_identifiers(content_a)
        specific_matches_b = self._extract_specific_identifiers(content_b)
        common_specific = specific_matches_a & specific_matches_b

        if common_specific:
            punctual_strength += len(common_specific) * 0.7
            evidence.append(f"Specific identifier matches: {list(common_specific)[:3]}")

        # Contextual spike: boost if files mention the same specific entities
        entity_matches = self._find_entity_matches(content_a, content_b)
        if entity_matches:
            punctual_strength += len(entity_matches) * 0.5
            evidence.append(f"Entity matches: {list(entity_matches)[:3]}")

        if punctual_strength > 0:
            return {
                'strength': min(1.0, punctual_strength),
                'description': f"Punctual relevance: {len(evidence)} specific matches",
                'evidence': evidence
            }
        return None

    def _check_situational_context(self, file_a: str, analysis_a: Dict,
                                 file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for situational context relevance - current session/task context."""
        situational_strength = 0
        evidence = []

        # Check if both files are related to current session context
        session_indicators = ['session', 'current', 'active', 'working', 'task', 'loop']
        session_matches_a = any(indicator in analysis_a.get('content_preview', '').lower() for indicator in session_indicators)
        session_matches_b = any(indicator in analysis_b.get('content_preview', '').lower() for indicator in session_indicators)

        if session_matches_a and session_matches_b:
            situational_strength += 0.4
            evidence.append("Both files relate to current session context")

        # Check for recent modification proximity (if age data available)
        age_a = analysis_a.get('age_days', 30)  # Default to 30 days if unknown
        age_b = analysis_b.get('age_days', 30)

        # Recent files get situational boost
        recent_threshold = 7  # 7 days
        if age_a <= recent_threshold and age_b <= recent_threshold:
            situational_strength += 0.3
            evidence.append(f"Both files recently modified (≤{recent_threshold} days)")

        # Check for task-specific context (current loop, task numbers, etc.)
        task_context_a = self._extract_task_context(analysis_a.get('content_preview', ''))
        task_context_b = self._extract_task_context(analysis_b.get('content_preview', ''))

        if task_context_a and task_context_b:
            # Check if they share task context elements
            shared_context = task_context_a & task_context_b
            if shared_context:
                situational_strength += len(shared_context) * 0.2
                evidence.append(f"Shared task context: {list(shared_context)[:2]}")

        # Check for superior file relationships (context_profiles.json, FEATURE_VALIDATION.md)
        superior_boost = self._check_superior_file_relationship(file_a, file_b)
        if superior_boost > 0:
            situational_strength += superior_boost
            evidence.append(f"Superior file relationship boost: {superior_boost:.2f}")

        if situational_strength > 0:
            return {
                'strength': min(1.0, situational_strength),
                'description': f"Situational context: {len(evidence)} contextual factors",
                'evidence': evidence
            }
        return None

    def _check_detail_specificity(self, file_a: str, analysis_a: Dict,
                                file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for detail specificity - exact vs broad matches with precision scoring."""
        content_a = analysis_a.get('content_preview', '')
        content_b = analysis_b.get('content_preview', '')

        if not content_a or not content_b:
            return None

        specificity_score = 0
        evidence = []

        # Check for exact technical term matches (high specificity)
        technical_a = self._extract_technical_terms(content_a)
        technical_b = self._extract_technical_terms(content_b)
        common_technical = technical_a & technical_b

        if common_technical:
            specificity_score += len(common_technical) * 0.4
            evidence.append(f"Technical terms: {list(common_technical)[:3]}")

        # Check for specific identifier matches (numbers, versions, etc.)
        specific_a = self._extract_specific_identifiers(content_a)
        specific_b = self._extract_specific_identifiers(content_b)
        common_specific = specific_a & specific_b

        if common_specific:
            specificity_score += len(common_specific) * 0.5
            evidence.append(f"Specific identifiers: {list(common_specific)[:3]}")

        # Check for exact phrase matches (2-4 word phrases)
        phrases_a = self._extract_phrases(content_a, 2) + self._extract_phrases(content_a, 3) + self._extract_phrases(content_a, 4)
        phrases_b = self._extract_phrases(content_b, 2) + self._extract_phrases(content_b, 3) + self._extract_phrases(content_b, 4)
        common_phrases = set(phrases_a) & set(phrases_b)

        if common_phrases:
            specificity_score += len(common_phrases) * 0.6
            evidence.append(f"Exact phrases: {list(common_phrases)[:2]}")

        if specificity_score > 0:
            return {
                'strength': min(1.0, specificity_score),
                'description': f"Detail specificity: {len(evidence)} specific matches",
                'evidence': evidence
            }
        return None

    def _check_semantic_concept_connections(self, file_a: str, analysis_a: Dict,
                                          file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for semantic concept connections using enhanced metadata."""
        metadata_a = analysis_a.get('metadata', {})
        metadata_b = analysis_b.get('metadata', {})

        concepts_a = set(metadata_a.get('semantic_concepts', []))
        concepts_b = set(metadata_b.get('semantic_concepts', []))

        if not concepts_a or not concepts_b:
            return None

        common_concepts = concepts_a & concepts_b
        if not common_concepts:
            return None

        # Calculate semantic similarity score
        semantic_strength = len(common_concepts) / max(len(concepts_a | concepts_b), 1)

        # Boost for domain-specific concept matches
        domain_matches = [c for c in common_concepts if ':' in c and c.split(':')[0] in ['ai_ml', 'software_dev', 'data_processing']]
        domain_boost = len(domain_matches) * 0.2

        total_strength = min(1.0, semantic_strength + domain_boost)

        return {
            'strength': total_strength,
            'description': f"Semantic concepts: {len(common_concepts)} shared concepts",
            'evidence': [f"Common concepts: {', '.join(list(common_concepts)[:5])}"]
        }

    def _check_behavioral_pattern_connections(self, file_a: str, analysis_a: Dict,
                                            file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for behavioral pattern connections using enhanced metadata."""
        metadata_a = analysis_a.get('metadata', {})
        metadata_b = analysis_b.get('metadata', {})

        patterns_a = set(metadata_a.get('behavioral_patterns', []))
        patterns_b = set(metadata_b.get('behavioral_patterns', []))

        if not patterns_a or not patterns_b:
            return None

        common_patterns = patterns_a & patterns_b
        if not common_patterns:
            return None

        # Calculate behavioral similarity
        behavioral_strength = len(common_patterns) / max(len(patterns_a | patterns_b), 1)

        # Boost for critical behavioral matches
        critical_patterns = ['consumes_dependencies', 'provides_functionality', 'error_handling', 'testing_validation']
        critical_matches = [p for p in common_patterns if p in critical_patterns]
        critical_boost = len(critical_matches) * 0.15

        total_strength = min(1.0, behavioral_strength + critical_boost)

        return {
            'strength': total_strength,
            'description': f"Behavioral patterns: {len(common_patterns)} shared patterns",
            'evidence': [f"Common behaviors: {', '.join(list(common_patterns)[:5])}"]
        }

    def _check_dependency_graph_connections(self, file_a: str, analysis_a: Dict,
                                          file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for dependency graph connections using enhanced metadata."""
        metadata_a = analysis_a.get('metadata', {})
        metadata_b = analysis_b.get('metadata', {})

        dep_graph_a = metadata_a.get('dependency_graph', {})
        dep_graph_b = metadata_b.get('dependency_graph', {})

        if not dep_graph_a or not dep_graph_b:
            return None

        # Check for shared dependencies
        imports_a = set(dep_graph_a.get('imports', []))
        imports_b = set(dep_graph_b.get('imports', []))
        common_imports = imports_a & imports_b

        references_a = set(dep_graph_a.get('references', []))
        references_b = set(dep_graph_b.get('references', []))
        common_references = references_a & references_b

        # Calculate dependency similarity
        total_shared_deps = len(common_imports) + len(common_references)
        total_deps = len(imports_a | imports_b) + len(references_a | references_b)

        if total_deps == 0:
            return None

        dependency_strength = total_shared_deps / total_deps

        # Boost for high centrality matches (important files)
        centrality_a = dep_graph_a.get('relationships', {}).get('centrality', 0)
        centrality_b = dep_graph_b.get('relationships', {}).get('centrality', 0)
        centrality_boost = min(centrality_a, centrality_b) * 0.2

        total_strength = min(1.0, dependency_strength + centrality_boost)

        if total_strength > 0.1:
            evidence = []
            if common_imports:
                evidence.append(f"Shared imports: {list(common_imports)[:3]}")
            if common_references:
                evidence.append(f"Shared references: {list(common_references)[:3]}")

            return {
                'strength': total_strength,
                'description': f"Dependency graph: {total_shared_deps} shared dependencies",
                'evidence': evidence
            }
        return None

    def _check_relationship_strength_connections(self, file_a: str, analysis_a: Dict,
                                               file_b: str, analysis_b: Dict, params: Dict) -> Optional[Dict]:
        """Check for relationship strength connections using enhanced metadata."""
        metadata_a = analysis_a.get('metadata', {})
        metadata_b = analysis_b.get('metadata', {})

        strength_a = metadata_a.get('relationship_strength', {})
        strength_b = metadata_b.get('relationship_strength', {})

        if not strength_a or not strength_b:
            return None

        # Calculate compatibility based on relationship strength profiles
        semantic_compat = 1 - abs(strength_a.get('semantic_strength', 0) - strength_b.get('semantic_strength', 0))
        behavioral_compat = 1 - abs(strength_a.get('behavioral_strength', 0) - strength_b.get('behavioral_strength', 0))
        dependency_compat = 1 - abs(strength_a.get('dependency_strength', 0) - strength_b.get('dependency_strength', 0))

        # Overall compatibility score
        overall_compat = (semantic_compat + behavioral_compat + dependency_compat) / 3

        # Only consider strong relationships (both files must have good relationship potential)
        confidence_a = strength_a.get('overall_confidence', 0)
        confidence_b = strength_b.get('overall_confidence', 0)

        if confidence_a < 0.3 or confidence_b < 0.3:
            return None  # Neither file has strong relationship potential

        # Combined strength based on compatibility and individual strengths
        combined_strength = overall_compat * min(confidence_a, confidence_b)

        if combined_strength > 0.2:
            return {
                'strength': combined_strength,
                'description': f"Relationship strength: {overall_compat:.2f} compatibility",
                'evidence': [
                    f"Semantic compat: {semantic_compat:.2f}",
                    f"Behavioral compat: {behavioral_compat:.2f}",
                    f"Dependency compat: {dependency_compat:.2f}"
                ]
            }
        return None

        if not content_a or not content_b:
            return None

        specificity_strength = 0
        evidence = []

        # Analyze word-level specificity
        words_a = content_a.split()
        words_b = content_b.split()

        # Exact word matches (high specificity)
        exact_matches = set(words_a) & set(words_b)
        if exact_matches:
            # Weight by word rarity/uniqueness
            specificity_score = sum(self._calculate_word_specificity(word) for word in exact_matches)
            specificity_strength += min(0.5, specificity_score)
            evidence.append(f"Exact word specificity: {len(exact_matches)} matches")

        # Check for code block specificity (exact code matches)
        code_a = analysis_a.get('code_blocks', [])
        code_b = analysis_b.get('code_blocks', [])

        code_matches = 0
        for block_a in code_a:
            for block_b in code_b:
                if self._code_blocks_similar(block_a, block_b):
                    code_matches += 1

        if code_matches > 0:
            specificity_strength += code_matches * 0.3
            evidence.append(f"Code block specificity: {code_matches} matches")

        # Check for header hierarchy specificity
        headers_a = analysis_a.get('headers', [])
        headers_b = analysis_b.get('headers', [])

        header_matches = 0
        for h_a in headers_a:
            for h_b in headers_b:
                if h_a.get('title', '').lower() == h_b.get('title', '').lower():
                    # Same level headers are more specific
                    if h_a.get('level') == h_b.get('level'):
                        header_matches += 0.4
                    else:
                        header_matches += 0.2

        if header_matches > 0:
            specificity_strength += min(0.4, header_matches)
            evidence.append(f"Header specificity: {header_matches:.1f} matches")

        # Precision bonus: penalize very generic matches
        total_words = len(set(words_a) | set(words_b))
        if total_words > 100:  # Long documents
            generic_penalty = 0.1 if specificity_strength < 0.2 else 0
            specificity_strength = max(0, specificity_strength - generic_penalty)
            if generic_penalty > 0:
                evidence.append("Generic content penalty applied")

        if specificity_strength > 0:
            return {
                'strength': min(1.0, specificity_strength),
                'description': f"Detail specificity: {len(evidence)} precision factors",
                'evidence': evidence
            }
        return None

    # ===== PUNCTUAL RELEVANCE HELPER METHODS =====

    def _extract_phrases(self, text: str, n: int) -> List[str]:
        """Extract n-word phrases from text."""
        words = text.split()
        phrases = []
        for i in range(len(words) - n + 1):
            phrase = ' '.join(words[i:i+n])
            if len(phrase) > 10:  # Avoid very short phrases
                phrases.append(phrase.lower())
        return phrases

    def _extract_technical_terms(self, text: str) -> Set[str]:
        """Extract technical terms like function names, API calls, etc."""
        import re

        # Patterns for technical terms
        patterns = [
            r'\b[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)',  # Function calls
            r'\b[A-Z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b',  # CamelCase
            r'\b[a-z_]+_[a-z_]+\b',  # snake_case
            r'\b\d+\.\d+\.\d+\b',  # Version numbers
            r'\bAPI\b|\bHTTP\b|\bJSON\b|\bSQL\b',  # Common tech terms
        ]

        terms = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            terms.update(matches)

        return terms

    def _extract_specific_identifiers(self, text: str) -> Set[str]:
        """Extract specific identifiers like dates, numbers, versions."""
        import re

        patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # Dates YYYY-MM-DD
            r'\b\d{2}/\d{2}/\d{4}\b',  # Dates MM/DD/YYYY
            r'\bv\d+\.\d+\b',  # Versions v1.2
            r'\b\d+\.\d+\.\d+\b',  # Versions 1.2.3
            r'\bTASK_\d+\b',  # Task numbers
            r'\bLOOP_\d+\b',  # Loop numbers
        ]

        identifiers = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            identifiers.update(matches)

        return identifiers

    def _find_entity_matches(self, text_a: str, text_b: str) -> Set[str]:
        """Find matching entities (people, organizations, projects) between texts."""
        # Simple entity extraction - could be enhanced with NLP
        entities_a = self._extract_entities(text_a)
        entities_b = self._extract_entities(text_b)
        return entities_a & entities_b

    def _extract_entities(self, text: str) -> Set[str]:
        """Simple entity extraction."""
        import re

        # Look for capitalized words that might be entities
        entities = set()
        words = text.split()

        for word in words:
            # Capitalized words that aren't at sentence start
            if len(word) > 3 and word[0].isupper() and any(c.islower() for c in word):
                entities.add(word)

        return entities

    def _extract_task_context(self, text: str) -> Set[str]:
        """Extract task-related context elements."""
        import re

        context_elements = set()

        # Task numbers
        task_matches = re.findall(r'\bTASK_\d+\b', text, re.IGNORECASE)
        context_elements.update(task_matches)

        # Loop numbers
        loop_matches = re.findall(r'\bLOOP_\d+\b', text, re.IGNORECASE)
        context_elements.update(loop_matches)

        # Session indicators
        session_indicators = ['session', 'current', 'active', 'working']
        for indicator in session_indicators:
            if indicator in text.lower():
                context_elements.add(indicator)

        return context_elements

    def _check_superior_file_relationship(self, file_a: str, file_b: str) -> float:
        """Check if files have relationship to superior reference files."""
        superior_files = ['FEATURE_VALIDATION.md', 'context_profiles.json', 'keeper_knowledge.db']

        boost = 0.0

        # Direct relationship to superior files
        for superior in superior_files:
            if superior in file_a or superior in file_b:
                boost += 0.3

        # Indirect relationship (both reference same superior file)
        # This would require checking references, but for now use filename patterns
        if any('validation' in file_a.lower() and 'validation' in file_b.lower() for f in [file_a, file_b]):
            boost += 0.2

        return boost

    def _calculate_word_specificity(self, word: str) -> float:
        """Calculate how specific/uncommon a word is."""
        # Simple specificity based on word length and character composition
        specificity = 0.1  # Base specificity

        # Longer words are more specific
        specificity += min(0.2, len(word) / 20)

        # Words with numbers/symbols are more specific
        if any(not c.isalpha() for c in word):
            specificity += 0.2

        # Technical words are more specific
        technical_indicators = ['api', 'http', 'json', 'sql', 'func', 'class', 'method']
        if any(indicator in word.lower() for indicator in technical_indicators):
            specificity += 0.3

        return min(0.5, specificity)

    def _code_blocks_similar(self, block_a: Dict, block_b: Dict) -> bool:
        """Check if two code blocks are similar."""
        content_a = block_a.get('content', '').strip()
        content_b = block_b.get('content', '').strip()

        if not content_a or not content_b:
            return False

        # Exact match
        if content_a == content_b:
            return True

        # High similarity (80% common lines)
        lines_a = set(content_a.split('\n'))
        lines_b = set(content_b.split('\n'))

        if lines_a and lines_b:
            common_lines = len(lines_a & lines_b)
            total_lines = len(lines_a | lines_b)
            similarity = common_lines / total_lines if total_lines > 0 else 0
            return similarity > 0.8

        return False

    # ===== QKV-INSPIRED RELEVANCE DIMENSIONS =====

    def _calculate_urgency_dimension(self, file_a: str, analysis_a: Dict,
                                   file_b: str, analysis_b: Dict) -> float:
        """
        Calculate Urgency dimension (U): Temporal criticality and immediacy.

        Higher urgency = more time-critical, recent, or immediately relevant.
        """
        urgency_score = 0.0

        # Recent modification bonus
        age_a = analysis_a.get('age_days', 30)
        age_b = analysis_b.get('age_days', 30)
        avg_age = (age_a + age_b) / 2

        # Exponential decay for recency (newer = more urgent)
        recency_factor = math.exp(-avg_age / 7)  # 7-day half-life
        urgency_score += recency_factor * 0.4

        # Session context urgency
        session_indicators = ['current', 'active', 'working', 'session', 'task']
        session_a = any(indicator in analysis_a.get('content_preview', '').lower() for indicator in session_indicators)
        session_b = any(indicator in analysis_b.get('content_preview', '').lower() for indicator in session_indicators)

        if session_a or session_b:
            urgency_score += 0.3
            if session_a and session_b:  # Both are session-relevant
                urgency_score += 0.2

        # Task criticality indicators
        critical_terms = ['urgent', 'critical', 'immediate', 'priority', 'deadline', 'breaking']
        critical_a = any(term in analysis_a.get('content_preview', '').lower() for term in critical_terms)
        critical_b = any(term in analysis_b.get('content_preview', '').lower() for term in critical_terms)

        if critical_a or critical_b:
            urgency_score += 0.3

        return min(1.0, urgency_score)

    def _calculate_strategic_fit_dimension(self, file_a: str, analysis_a: Dict,
                                         file_b: str, analysis_b: Dict) -> float:
        """
        Calculate Strategic Fit dimension (S): Alignment with project goals and superior references.

        Higher strategic fit = better alignment with project direction and key objectives.
        """
        strategic_score = 0.0

        # Superior file alignment
        superior_files = ['FEATURE_VALIDATION.md', 'context_profiles.json', 'keeper_knowledge.db']
        superior_alignment = 0

        for superior in superior_files:
            if superior in file_a or superior in file_b:
                superior_alignment += 0.4
            # Check for references to superior files
            refs_a = analysis_a.get('references', [])
            refs_b = analysis_b.get('references', [])
            if any(superior in ref for ref in refs_a) or any(superior in ref for ref in refs_b):
                superior_alignment += 0.3

        strategic_score += min(0.6, superior_alignment)

        # Project goal alignment (check for goal-oriented content)
        goal_indicators = ['goal', 'objective', 'strategy', 'milestone', 'roadmap', 'vision', 'mission']
        goal_a = any(indicator in analysis_a.get('content_preview', '').lower() for indicator in goal_indicators)
        goal_b = any(indicator in analysis_b.get('content_preview', '').lower() for indicator in goal_indicators)

        if goal_a or goal_b:
            strategic_score += 0.2
            if goal_a and goal_b:
                strategic_score += 0.2

        # Architecture and design alignment
        arch_terms = ['architecture', 'design', 'framework', 'system', 'infrastructure', 'platform']
        arch_a = any(term in analysis_a.get('content_preview', '').lower() for term in arch_terms)
        arch_b = any(term in analysis_b.get('content_preview', '').lower() for term in arch_terms)

        if arch_a and arch_b:
            strategic_score += 0.2

        return min(1.0, strategic_score)

    def _calculate_historical_reliability_dimension(self, file_a: str, analysis_a: Dict,
                                                  file_b: str, analysis_b: Dict) -> float:
        """
        Calculate Historical Reliability dimension (H): Proven effectiveness and track record.

        Higher reliability = more proven, stable, and historically effective connections.
        """
        reliability_score = 0.0

        # Connection history from context profiles
        profile_a = self.context_profiles.get(file_a, {})
        profile_b = self.context_profiles.get(file_b, {})

        # Past connection success rate
        history_a = profile_a.get('connection_history', [])
        history_b = profile_b.get('connection_history', [])

        if history_a:
            avg_significance_a = sum(h.get('significance_boost', 0) for h in history_a) / len(history_a)
            reliability_score += min(0.3, avg_significance_a)

        if history_b:
            avg_significance_b = sum(h.get('significance_boost', 0) for h in history_b) / len(history_b)
            reliability_score += min(0.3, avg_significance_b)

        # Stability indicators (older, well-established files)
        age_a = analysis_a.get('age_days', 0)
        age_b = analysis_b.get('age_days', 0)

        # Moderate age bonus (not too new, not ancient)
        if 7 <= age_a <= 90:  # 1 week to 3 months
            reliability_score += 0.1
        if 7 <= age_b <= 90:
            reliability_score += 0.1

        # Documentation stability (markdown files tend to be more stable)
        if analysis_a.get('file_type') == 'markdown':
            reliability_score += 0.1
        if analysis_b.get('file_type') == 'markdown':
            reliability_score += 0.1

        # Reference network density (well-connected files are more reliable)
        refs_a = len(analysis_a.get('references', []))
        refs_b = len(analysis_b.get('references', []))
        avg_refs = (refs_a + refs_b) / 2

        # Density bonus (sweet spot around 5-15 references)
        if 3 <= avg_refs <= 20:
            density_factor = 1 - abs(avg_refs - 10) / 10  # Peak at 10 refs
            reliability_score += density_factor * 0.2

        return min(1.0, reliability_score)

    def _calculate_qkv_relevance_vector(self, file_a: str, analysis_a: Dict,
                                      file_b: str, analysis_b: Dict) -> Dict[str, float]:
        """
        Calculate the complete QKV-inspired relevance vector [U, S, H].

        Returns a dictionary with urgency, strategic_fit, and historical_reliability scores.
        """
        return {
            'urgency': self._calculate_urgency_dimension(file_a, analysis_a, file_b, analysis_b),
            'strategic_fit': self._calculate_strategic_fit_dimension(file_a, analysis_a, file_b, analysis_b),
            'historical_reliability': self._calculate_historical_reliability_dimension(file_a, analysis_a, file_b, analysis_b)
        }

    def _analyze_parameter_performance(self, test_results: List[Dict], parameters: Dict) -> Dict:
        """Reflect on how well current parameters performed."""
        total_connections = sum(r['connections_found'] for r in test_results)
        avg_connections = total_connections / len(test_results) if test_results else 0

        # Analyze connection quality
        connection_qualities = []
        for result in test_results:
            for conn in result['connections']:
                quality_score = self._assess_connection_quality(conn, result)
                connection_qualities.append(quality_score)

        avg_quality = sum(connection_qualities) / len(connection_qualities) if connection_qualities else 0

        # Parameter sensitivity analysis
        sensitivity = self._calculate_parameter_sensitivity(test_results, parameters)

        return {
            'total_tests': len(test_results),
            'total_connections': total_connections,
            'avg_connections_per_test': avg_connections,
            'avg_connection_quality': avg_quality,
            'parameter_sensitivity': sensitivity,
            'performance_score': (avg_connections * 0.6) + (avg_quality * 0.4)
        }

    def _assess_connection_quality(self, connection: Dict, test_result: Dict) -> float:
        """Assess the quality/relevance of a discovered connection."""
        quality = connection['strength']

        # Boost quality for certain file type combinations
        type_a, type_b = test_result['file_types']
        if (type_a == 'python' and type_b == 'test') or (type_a == 'test' and type_b == 'python'):
            quality *= 1.2  # Code-test relationships are valuable
        elif type_a == type_b:
            quality *= 1.1  # Same-type files often related
        elif 'template' in [type_a, type_b] and 'python' in [type_a, type_b]:
            quality *= 1.3  # Template-code relationships very valuable

        # Penalize weak evidence
        if len(connection.get('evidence', [])) < 1:
            quality *= 0.8

        return min(1.0, quality)

    def _calculate_parameter_sensitivity(self, test_results: List[Dict], parameters: Dict) -> Dict:
        """Calculate how sensitive results are to parameter changes."""
        sensitivity = {}

        for param_name, param_value in parameters.items():
            # Test small variations
            variations = []
            for delta in [-0.1, 0.1]:
                test_params = parameters.copy()
                test_params[param_name] = max(0, min(1, param_value + delta))

                # Quick re-evaluation with modified parameter
                modified_connections = 0
                for result in test_results:
                    file_a, file_b = result['file_pair']
                    analysis_a = self.network_graph.get(file_a, {})
                    analysis_b = self.network_graph.get(file_b, {})

                    if analysis_a and analysis_b:
                        connections = self._evaluate_connections_with_parameters(
                            file_a, analysis_a, file_b, analysis_b, test_params
                        )
                        modified_connections += len(connections)

                variation = modified_connections / len(test_results) if test_results else 0
                variations.append(variation)

            # Calculate sensitivity as average variation
            baseline = sum(r['connections_found'] for r in test_results) / len(test_results) if test_results else 0
            avg_variation = sum(abs(v - baseline) for v in variations) / len(variations)
            sensitivity[param_name] = avg_variation

        return sensitivity

    def _validate_connection_quality(self, connection: Dict, params: Dict) -> bool:
        """Validate that a connection meets quality standards to prevent false positives."""
        # Quality thresholds - very conservative to ensure correctness
        min_similarity = 0.7  # Must be highly similar
        min_structural_score = 0.6  # Must have strong structural relationship
        min_contextual_score = 0.5  # Must be contextually relevant
        max_frequency_penalty = 0.3  # Not over-connected

        # Calculate weighted scores
        similarity_score = connection.get('similarity_score', 0)
        structural_score = connection.get('structural_score', 0) * params.get('structural_weight', 0.7)
        contextual_score = connection.get('contextual_score', 0) * params.get('contextual_boost', 0.3)
        frequency_penalty = connection.get('frequency_penalty', 0) * params.get('frequency_penalty', 0.2)

        # Quality checks
        if similarity_score < min_similarity:
            return False
        if structural_score < min_structural_score:
            return False
        if contextual_score < min_contextual_score:
            return False
        if frequency_penalty > max_frequency_penalty:
            return False

        # Additional validation: check for temporal coherence
        temporal_score = connection.get('temporal_score', 0)
        if temporal_score < 0.4:  # Must have reasonable temporal relationship
            return False

        return True

    def _calculate_similarity_score(self, file_a: str, analysis_a: Dict, file_b: str, analysis_b: Dict) -> float:
        """Calculate content similarity score between two files."""
        # Simple Jaccard similarity of keywords/concepts
        keywords_a = analysis_a.get('keywords', [])
        keywords_b = analysis_b.get('keywords', [])

        # Ensure we have lists and convert to strings safely
        if isinstance(keywords_a, list) and isinstance(keywords_b, list):
            keywords_a_set = set(str(x) for x in keywords_a if x is not None)
            keywords_b_set = set(str(x) for x in keywords_b if x is not None)
        else:
            return 0.0

        if not keywords_a_set or not keywords_b_set:
            return 0.0

        intersection = len(keywords_a_set & keywords_b_set)
        union = len(keywords_a_set | keywords_b_set)

        return intersection / union if union > 0 else 0.0

    def _calculate_structural_score(self, file_a: str, analysis_a: Dict, file_b: str, analysis_b: Dict) -> float:
        """Calculate structural relationship score."""
        score = 0.0

        # Import relationships - ensure we have lists
        imports_a = analysis_a.get('imports', [])
        imports_b = analysis_b.get('imports', [])
        if isinstance(imports_a, list) and isinstance(imports_b, list):
            imports_a_set = set(str(x) for x in imports_a if x is not None)
            imports_b_set = set(str(x) for x in imports_b if x is not None)
            if imports_a_set & imports_b_set:
                score += 0.4

        # Function/class dependencies - ensure we have lists
        functions_a = analysis_a.get('functions', [])
        functions_b = analysis_b.get('functions', [])
        if isinstance(functions_a, list) and isinstance(functions_b, list):
            functions_a_set = set(str(x) for x in functions_a if x is not None)
            functions_b_set = set(str(x) for x in functions_b if x is not None)
            if functions_a_set & functions_b_set:
                score += 0.3

        # File type compatibility
        type_a = analysis_a.get('file_type', '')
        type_b = analysis_b.get('file_type', '')
        if type_a and type_b and type_a == type_b:
            score += 0.3

        return min(1.0, score)

    def _calculate_contextual_score(self, file_a: str, analysis_a: Dict, file_b: str, analysis_b: Dict) -> float:
        """Calculate contextual relevance score."""
        score = 0.0

        # Project context similarity
        context_a = analysis_a.get('project_context', '')
        context_b = analysis_b.get('project_context', '')
        if context_a and context_b and context_a == context_b:
            score += 0.5

        # Task similarity
        task_a = analysis_a.get('primary_task', '')
        task_b = analysis_b.get('primary_task', '')
        if task_a and task_b and task_a == task_b:
            score += 0.3

        # Directory proximity (same folder = more relevant)
        dir_a = str(Path(file_a).parent)
        dir_b = str(Path(file_b).parent)
        if dir_a == dir_b:
            score += 0.2

        return min(1.0, score)

    def _calculate_temporal_score(self, analysis_a: Dict, analysis_b: Dict) -> float:
        """Calculate temporal relationship score."""
        age_a = analysis_a.get('age_days', 0)
        age_b = analysis_b.get('age_days', 0)

        # Recent files are more likely to be related
        max_age = 30  # 30 days
        recency_a = max(0, 1 - (age_a / max_age))
        recency_b = max(0, 1 - (age_b / max_age))

        # Similar recency = higher temporal score
        return 1 - abs(recency_a - recency_b)

    def _calculate_frequency_penalty(self, file_a: str, file_b: str) -> float:
        """Calculate frequency penalty for over-connected files."""
        # Simple frequency tracking - files connected to many others get penalty
        # This is a placeholder - in real implementation would track connection history
        return 0.0  # Start with no penalty

    def _learn_from_reflection(self, reflection: Dict, current_params: Dict) -> Dict:
        """Learn parameter updates from reflection analysis with correctness-first approach."""
        updates = {}

        performance = reflection['performance_score']
        avg_quality = reflection.get('avg_connection_quality', 0)

        # CORRECTNESS-FIRST LEARNING: Prioritize quality over quantity
        # False positives are catastrophic - missing connections are acceptable

        if performance < 0.3:  # Too few connections found
            # DON'T lower thresholds - that leads to false positives!
            # Instead, increase specificity and wait for better data
            updates['similarity_threshold'] = 0.02  # Slightly increase (be more skeptical)
            updates['structural_weight'] = 0.01     # Small increase for code relationships
            updates['contextual_boost'] = 0.01      # Small increase for context

        elif performance > 0.7:  # Too many connections (potential noise)
            # Increase skepticism - raise thresholds for quality
            updates['similarity_threshold'] = 0.05  # Raise threshold (be more selective)
            updates['frequency_penalty'] = 0.02     # Penalize over-connections more
            updates['temporal_decay'] = 0.02       # Be more skeptical of old connections

        else:  # Moderate performance - fine-tune based on quality
            if avg_quality < 0.6:  # Low quality connections
                # Increase skepticism
                updates['similarity_threshold'] = 0.03
                updates['structural_weight'] = 0.02
            elif avg_quality > 0.8:  # High quality connections
                # Can afford to be slightly less skeptical
                updates['similarity_threshold'] = -0.01  # Small decrease only for proven quality
                updates['contextual_boost'] = 0.01

        # Parameter sensitivity analysis - be more conservative with sensitive parameters
        sensitivity = reflection['parameter_sensitivity']
        for param, sens in sensitivity.items():
            if sens > 0.3:  # Highly sensitive parameter
                # Small, conservative adjustments for sensitive parameters
                current_update = updates.get(param, 0)
                updates[param] = current_update * 0.5  # Reduce adjustment by half

        return updates

    def _synthesize_learning_insights(self, learning_history: List[Dict]) -> Dict:
        """Synthesize key insights from the learning process."""
        if not learning_history:
            return {'key_findings': []}

        # Analyze parameter evolution
        final_params = learning_history[-1]['parameters']
        initial_params = learning_history[0]['parameters']

        param_changes = {}
        for param in final_params:
            change = final_params[param] - initial_params[param]
            param_changes[param] = change

        # Find most important parameters
        sensitivity_trends = []
        for history in learning_history:
            if 'reflection' in history and 'parameter_sensitivity' in history['reflection']:
                sensitivity_trends.append(history['reflection']['parameter_sensitivity'])

        avg_sensitivity = {}
        if sensitivity_trends:
            for param in final_params.keys():
                sensitivities = [trend.get(param, 0) for trend in sensitivity_trends]
                avg_sensitivity[param] = sum(sensitivities) / len(sensitivities)

        # Performance trend
        performance_trend = [h['reflection']['performance_score'] for h in learning_history
                           if 'reflection' in h]

        insights = {
            'parameter_evolution': param_changes,
            'most_sensitive_parameters': sorted(avg_sensitivity.items(), key=lambda x: x[1], reverse=True)[:3],
            'performance_trend': performance_trend,
            'learning_efficiency': len([p for p in performance_trend if p > 0.5]) / len(performance_trend) if performance_trend else 0,
            'key_findings': [
                f"Parameter '{max(param_changes, key=param_changes.get)}' changed most ({param_changes[max(param_changes, key=param_changes.get)]:+.3f})",
                f"Most sensitive parameter: {max(avg_sensitivity, key=avg_sensitivity.get) if avg_sensitivity else 'None'}",
                f"Learning efficiency: {len([p for p in performance_trend if p > 0.5]) / len(performance_trend):.1%} of cycles achieved good performance" if performance_trend else "No performance data"
            ]
        }

        return insights

    def _calculate_parameter_mathematics(self, parameters: Dict) -> Dict:
        """Calculate mathematical properties of the learned parameters."""
        # Parameter interaction analysis
        param_values = list(parameters.values())
        param_mean = sum(param_values) / len(param_values)
        param_variance = sum((v - param_mean) ** 2 for v in param_values) / len(param_values)

        # Parameter balance (how evenly distributed)
        balance_score = 1.0 - (param_variance / 0.25)  # Normalized to [0,1]

        # Connection potential (theoretical maximum connections)
        connection_potential = (
            parameters['similarity_threshold'] * 0.4 +
            parameters['structural_weight'] * 0.3 +
            parameters['contextual_boost'] * 0.2 +
            parameters['temporal_decay'] * 0.1
        )

        return {
            'parameter_balance': balance_score,
            'connection_potential': connection_potential,
            'parameter_diversity': param_variance,
            'optimization_readiness': balance_score * connection_potential
        }

    def _find_direct_links_between_files(self, file_a: str, analysis_a: Dict, file_b: str, analysis_b: Dict, max_links: int) -> List[Dict]:
        """
        Find direct links between exactly two files with conservative thresholds.
        No transitive or indirect connections - only direct relationships.
        """
        links = []

        # Direct link types to check
        link_checks = [
            ('function_reference', self._check_function_references, 1.0),
            ('import_reference', self._check_import_references, 1.0),
            ('code_block_reference', self._check_code_block_references, 0.8),
            ('metadata_similarity', self._check_metadata_similarity, 0.7),
            ('behavioral_pattern', self._check_behavioral_patterns, 0.6),
        ]

        for link_type, check_func, base_strength in link_checks:
            if len(links) >= max_links:
                break

            try:
                link_result = check_func(file_a, analysis_a, file_b, analysis_b)
                if link_result and link_result['strength'] >= 0.5:  # Conservative threshold
                    links.append({
                        'type': link_type,
                        'description': link_result['description'],
                        'strength': link_result['strength'] * base_strength,
                        'evidence': link_result.get('evidence', [])
                    })
            except Exception as e:
                print(f"⚠️  Error checking {link_type}: {e}")
                continue

        # Sort by strength (highest first) and limit to max_links
        links.sort(key=lambda x: x['strength'], reverse=True)
        return links[:max_links]

    def _check_function_references(self, file_a: str, analysis_a: Dict, file_b: str, analysis_b: Dict) -> Optional[Dict]:
        """Check for direct function/method references between files."""
        functions_a = analysis_a.get('functions', [])
        functions_b = analysis_b.get('functions', [])

        # Check if file_a references functions from file_b
        references_found = []
        for func_a in functions_a:
            func_name_a = func_a.get('name', '')
            for func_b in functions_b:
                func_name_b = func_b.get('name', '')
                if func_name_b and func_name_b in func_name_a:
                    references_found.append(f"{func_name_a} references {func_name_b}")

        if references_found:
            return {
                'description': f"Function references: {', '.join(references_found[:3])}",
                'strength': min(1.0, len(references_found) * 0.3),
                'evidence': references_found
            }
        return None

    def _check_import_references(self, file_a: str, analysis_a: Dict, file_b: str, analysis_b: Dict) -> Optional[Dict]:
        """Check for direct import references between files."""
        imports_a = analysis_a.get('imports', [])
        imports_b = analysis_b.get('imports', [])

        # Check if file_a imports from file_b
        import_matches = []
        file_b_name = file_b.split('/')[-1].split('\\')[-1].replace('.py', '').replace('.js', '').replace('.ts', '')

        for imp in imports_a:
            if file_b_name in str(imp):
                import_matches.append(str(imp))

        if import_matches:
            return {
                'description': f"Import references: {', '.join(import_matches[:3])}",
                'strength': min(1.0, len(import_matches) * 0.4),
                'evidence': import_matches
            }
        return None

    def _check_code_block_references(self, file_a: str, analysis_a: Dict, file_b: str, analysis_b: Dict) -> Optional[Dict]:
        """Check for code block content similarity."""
        code_blocks_a = analysis_a.get('code_blocks', [])
        code_blocks_b = analysis_b.get('code_blocks', [])

        similarities = []
        for block_a in code_blocks_a:
            for block_b in code_blocks_b:
                # Simple text similarity check
                text_a = block_a.get('content', '').lower()
                text_b = block_b.get('content', '').lower()
                if len(text_a) > 20 and len(text_b) > 20:
                    # Check for common substrings
                    common_words = set(text_a.split()) & set(text_b.split())
                    if len(common_words) > 3:
                        similarities.append(f"Shared terms: {', '.join(list(common_words)[:5])}")

        if similarities:
            return {
                'description': f"Code block similarities: {similarities[0]}",
                'strength': min(0.8, len(similarities) * 0.2),
                'evidence': similarities[:3]
            }
        return None

    def _check_metadata_similarity(self, file_a: str, analysis_a: Dict, file_b: str, analysis_b: Dict) -> Optional[Dict]:
        """Check for metadata pattern similarities."""
        metadata_a = analysis_a.get('metadata', {})
        metadata_b = analysis_b.get('metadata', {})

        similarities = []
        common_keys = set(metadata_a.keys()) & set(metadata_b.keys())

        for key in common_keys:
            val_a = str(metadata_a[key]).lower()
            val_b = str(metadata_b[key]).lower()
            if val_a == val_b and len(val_a) > 3:
                similarities.append(f"{key}: {val_a}")

        if similarities:
            return {
                'description': f"Metadata matches: {', '.join(similarities[:3])}",
                'strength': min(0.7, len(similarities) * 0.25),
                'evidence': similarities
            }
        return None

    def _check_behavioral_patterns(self, file_a: str, analysis_a: Dict, file_b: str, analysis_b: Dict) -> Optional[Dict]:
        """Check for behavioral pattern similarities."""
        behavior_a = analysis_a.get('behavioral_patterns', {})
        behavior_b = analysis_b.get('behavioral_patterns', {})

        patterns = []
        common_patterns = set(behavior_a.keys()) & set(behavior_b.keys())

        for pattern in common_patterns:
            if behavior_a[pattern] and behavior_b[pattern]:
                patterns.append(f"Shared {pattern} behavior")

        if patterns:
            return {
                'description': f"Behavioral patterns: {', '.join(patterns[:3])}",
                'strength': min(0.6, len(patterns) * 0.2),
                'evidence': patterns
            }
        return None

    def show_mathematical_analysis(self, target_depth: int = None) -> None:
        """
        Display detailed mathematical analysis from depth_vs_breathe.md
        """
        if target_depth is None:
            target_depth = self.calculate_optimal_depth()

        vectorization = self.vectorize_dreaming_strategy(target_depth)
        analysis_d7 = self.calculate_connectivity_advantage(7)
        analysis_d5 = self.calculate_connectivity_advantage(5)

        print("🧮 DEPTH VS BREADTH MATHEMATICAL ANALYSIS")
        print("=" * 50)
        print(f"Branching factor (b): {self.branching_factor}")
        print(f"Token budget: {self.token_budget:,} tokens")
        print(f"Base token cost: {self.token_base}")
        print(f"Metadata token cost: {self.token_metadata}")
        print()

        print("CONNECTIVITY ADVANTAGE ANALYSIS:")
        print("-" * 40)
        for depth_name, depth_val in [("Optimal (d=5)", 5), ("Superior (d=7)", 7), ("Current Target", target_depth)]:
            if depth_val <= self.superior_depth:
                analysis = self.calculate_connectivity_advantage(depth_val)
                print(f"{depth_name}:")
                print(f"   Connectivity advantage: {analysis['connectivity_advantage']:.1f}×")
                print(f"   Token utilization: {analysis['token_utilization']:.1%}")
                print(f"   Inference hops: {analysis['inference_hops']}")
                print()

        print("VECTORIZATION TARGETS:")
        print("-" * 40)
        print(f"Sample size per iteration: {vectorization['sample_size_per_iteration']}")
        print(f"Token budget utilization: {vectorization['token_budget_utilization']:.1%}")
        print(f"Expected connectivity gain: {vectorization['expected_connectivity_gain']:.1f}×")
        print(f"Inference capability: {vectorization['inference_capability_hops']}-hop transitive")
        print(f"Iterations needed for coverage: {vectorization['vectorization_guidelines']['iterations_needed']}")
        print()

        print("IMPLEMENTATION STATUS:")
        print("-" * 40)
        targets = vectorization['mathematical_targets']
        print(f"✓ Branching factor b=3 verified: {targets['branching_factor_3_verified']}")
        print(f"✓ Superior depth d=7 advantage: {targets['superior_depth_7_advantage']:.1f}×")
        print(f"✓ Optimal depth d=5 safety: {targets['optimal_depth_5_safety']:.1f}×")
        print(f"✓ Token-safe depth: d={targets['token_safe_depth']}")
        print()

        print("🎯 KEY INSIGHT: At d=7, depth-first achieves 52× more connections")
        print("   with same token budget, enabling 7-hop transitive inference!")

    def _analyze_file_connectivity(self, file_ids: List[str]) -> Dict:
        """
        Analyze connectivity between a set of files.

        Returns detailed connectivity analysis including relationship types,
        significance scores, and parameter updates.
        """
        connectivity = {
            'connections_found': 0,
            'relationships': [],
            'significance_updates': {},
            'analysis_timestamp': datetime.now().isoformat()
        }

        # Compare each pair of files
        for i, file_a in enumerate(file_ids):
            for j, file_b in enumerate(file_ids):
                if i >= j:  # Avoid duplicate comparisons
                    continue

                relationship = self._assess_relationship(file_a, file_b)
                if relationship['is_connected']:
                    connectivity['connections_found'] += 1
                    connectivity['relationships'].append({
                        'file_a': file_a,
                        'file_b': file_b,
                        'relationship': relationship
                    })

                    # Update significance scores
                    significance_boost = relationship['significance_score'] * 0.1  # Gradual updates
                    for file_id in [file_a, file_b]:
                        if file_id not in connectivity['significance_updates']:
                            connectivity['significance_updates'][file_id] = 0
                        connectivity['significance_updates'][file_id] += significance_boost

        return connectivity

    def _assess_relationship(self, file_a: str, file_b: str) -> Dict:
        """
        Comprehensive relationship assessment using direct and abstract links.

        Implements the multivectoral foundation for meaningful abstract context:
        - Direct links: functions, mentions, references, similar roots, code blocks, discoveries
        - Abstract links: metadata structure, behavioral patterns, lessons learned, risks, setbacks
        """
        if file_a not in self.network_graph or file_b not in self.network_graph:
            return {'is_connected': False}

        node_a = self.network_graph[file_a]
        node_b = self.network_graph[file_b]

        # ===== DIRECT LINKS ANALYSIS =====
        direct_links = self._analyze_direct_links(node_a, node_b)

        # ===== ABSTRACT LINKS ANALYSIS =====
        abstract_links = self._analyze_abstract_links(node_a, node_b)

        # ===== COMBINE SCORES =====
        total_connectivity = direct_links['score'] + abstract_links['score']

        # Apply diminishing returns for very high scores
        if total_connectivity > 2.0:
            total_connectivity = 2.0 + (total_connectivity - 2.0) * 0.5

        # EXTREMELY CONSERVATIVE THRESHOLD: False positives ruin the network
        # Only connections that reveal themselves through close examination
        is_connected = total_connectivity > 1.2  # Much higher threshold - discoveries must be undeniable

        relationship = {
            'is_connected': is_connected,
            'connectivity_score': total_connectivity,
            'relationship_type': self._classify_relationship_type_comprehensive(node_a, node_b),
            'significance_score': total_connectivity * self._calculate_significance_multiplier(node_a, node_b),
            'depth': 'direct' if direct_links['score'] > 0.3 else 'abstract' if abstract_links['score'] > 0.3 else 'inferred',
            'criticality': self._assess_criticality(total_connectivity, direct_links, abstract_links),
            'evidence': {
                'direct_links': direct_links,
                'abstract_links': abstract_links,
                'combined_score': total_connectivity
            }
        }

        return relationship

    def _analyze_direct_links(self, node_a: Dict, node_b: Dict) -> Dict:
        """Analyze direct links between files - EXTREMELY CONSERVATIVE to avoid false positives."""
        score = 0.0
        evidence = {}

        # 1. Explicit references and mentions - REQUIRE MULTIPLE STRONG REFERENCES
        references_a = set(node_a.get('references', []) + node_a.get('mentions', []))
        references_b = set(node_b.get('references', []) + node_b.get('mentions', []))
        
        direct_refs = len(references_a & references_b)
        if direct_refs >= 2:  # Require at least 2 shared references
            score += min(direct_refs * 0.15, 0.4)  # Much lower scoring
            evidence['explicit_references'] = direct_refs

        # 2. Function/class name matches - REQUIRE EXACT MATCHES AND CONTEXT
        if node_a.get('file_type') in ['python', 'javascript', 'typescript']:
            functions_a = {f['name'] for f in node_a.get('functions', [])}
            functions_b = {f['name'] for f in node_b.get('functions', [])}
            classes_a = {c['name'] for c in node_a.get('classes', [])}
            classes_b = {c['name'] for c in node_b.get('classes', [])}

            function_matches = len(functions_a & functions_b)
            class_matches = len(classes_a & classes_b)

            # Only count if there are multiple matches OR the match is very specific
            if function_matches >= 2 or (function_matches == 1 and any(len(f) > 20 for f in functions_a & functions_b)):
                score += min(function_matches * 0.1, 0.25)
                evidence['function_matches'] = function_matches
            if class_matches >= 1:  # Classes are more significant
                score += min(class_matches * 0.2, 0.4)
                evidence['class_matches'] = class_matches

        # 3. Import dependencies - REQUIRE SHARED DEPENDENCIES
        imports_a = {imp['statement'] for imp in node_a.get('imports', [])}
        imports_b = {imp['statement'] for imp in node_b.get('imports', [])}
        import_matches = len(imports_a & imports_b)

        if import_matches >= 2:  # Require multiple shared imports
            score += min(import_matches * 0.12, 0.3)
            evidence['import_matches'] = import_matches

        # 4. Code block similarity - REQUIRE SIGNIFICANT SIMILARITY
        code_blocks_a = {cb['content'] for cb in node_a.get('code_blocks', [])}
        code_blocks_b = {cb['content'] for cb in node_b.get('code_blocks', [])}
        code_similarities = 0

        for block_a in code_blocks_a:
            for block_b in code_blocks_b:
                # Require much more significant similarity
                common_lines = len(set(block_a.split('\n')) & set(block_b.split('\n')))
                total_lines_a = len(block_a.split('\n'))
                total_lines_b = len(block_b.split('\n'))
                
                # Require at least 5 common lines AND significant portion of both blocks
                if common_lines >= 5 and common_lines >= min(total_lines_a, total_lines_b) * 0.3:
                    code_similarities += 1

        if code_similarities > 0:
            score += min(code_similarities * 0.08, 0.2)  # Much lower scoring
            evidence['code_similarities'] = code_similarities

        # 5. Terminal output patterns - REQUIRE MULTIPLE PATTERNS
        content_a = node_a.get('content_preview', '').lower()
        content_b = node_b.get('content_preview', '').lower()

        terminal_patterns = ['error:', 'warning:', 'exception:', 'traceback:', 'command:', 'output:']
        terminal_matches = sum(1 for pattern in terminal_patterns if pattern in content_a and pattern in content_b)

        if terminal_matches >= 3:  # Require multiple terminal patterns
            score += min(terminal_matches * 0.05, 0.15)

        return {
            'score': score,
            'evidence': evidence
        }

    def _analyze_abstract_links(self, node_a: Dict, node_b: Dict) -> Dict:
        """Analyze abstract links - EXTREMELY CONSERVATIVE to prevent false positives."""
        score = 0.0
        evidence = {}

        metadata_a = node_a.get('metadata', {})
        metadata_b = node_b.get('metadata', {})

        # 1. Metadata structure similarity - REQUIRE MULTIPLE SHARED PATTERNS
        patterns_a = set(metadata_a.get('patterns', []))
        patterns_b = set(metadata_b.get('patterns', []))
        pattern_similarity = len(patterns_a & patterns_b)

        if pattern_similarity >= 3:  # Require at least 3 shared patterns
            score += min(pattern_similarity * 0.05, 0.2)  # Much lower scoring
            evidence['pattern_similarities'] = pattern_similarity

        # 2. Behavioral metadata similarity - REQUIRE STRONG SIMILARITIES
        behavior_a = metadata_a.get('behavior', {})
        behavior_b = metadata_b.get('behavior', {})

        behavioral_matches = 0

        # Complexity similarity - only if very close
        complexity_diff = abs(behavior_a.get('complexity', 0.5) - behavior_b.get('complexity', 0.5))
        if complexity_diff < 0.1:  # Very similar complexity
            behavioral_matches += 1
            evidence['complexity_similarity'] = True

        # Volatility compatibility - only exact matches
        volatility_a = behavior_a.get('volatility', 'moderate_volatility')
        volatility_b = behavior_b.get('volatility', 'moderate_volatility')
        if volatility_a == volatility_b and volatility_a != 'moderate_volatility':  # Not default
            behavioral_matches += 1
            evidence['volatility_match'] = volatility_a

        # Communication style compatibility - only non-neutral matches
        comm_a = behavior_a.get('communication_style', 'neutral')
        comm_b = behavior_b.get('communication_style', 'neutral')
        if comm_a == comm_b and comm_a != 'neutral':  # Not default
            behavioral_matches += 1
            evidence['communication_compatibility'] = comm_a

        # Problem-solving approach similarity - only specific matches
        problem_a = behavior_a.get('problem_solving', 'balanced')
        problem_b = behavior_b.get('problem_solving', 'balanced')
        if problem_a == problem_b and problem_a != 'balanced':  # Not default
            behavioral_matches += 1
            evidence['problem_solving_similarity'] = problem_a

        if behavioral_matches >= 2:  # Require at least 2 behavioral matches
            score += min(behavioral_matches * 0.06, 0.18)

        # 3. Content theme analysis - REQUIRE MULTIPLE STRONG THEMES
        content_a = node_a.get('content_preview', '').lower()
        content_b = node_b.get('content_preview', '').lower()

        # Lesson patterns - require multiple specific indicators
        lesson_indicators = ['lesson learned', 'learned that', 'next time', 'mistake', 'improvement']
        lesson_matches = sum(1 for indicator in lesson_indicators if indicator in content_a and indicator in content_b)

        if lesson_matches >= 2:  # Require at least 2 lesson indicators
            score += min(lesson_matches * 0.08, 0.2)
            evidence['lesson_patterns'] = lesson_matches

        # Risk and setback patterns - require multiple specific indicators
        risk_indicators = ['risk', 'setback', 'delay', 'blocker', 'issue', 'problem', 'failure']
        risk_matches = sum(1 for indicator in risk_indicators if indicator in content_a and indicator in content_b)

        if risk_matches >= 3:  # Require at least 3 risk indicators
            score += min(risk_matches * 0.06, 0.18)
            evidence['risk_setback_patterns'] = risk_matches

        # Success/repetition patterns - require multiple specific indicators
        success_indicators = ['success', 'worked', 'solved', 'completed', 'achieved', 'repeat', 'similar']
        success_matches = sum(1 for indicator in success_indicators if indicator in content_a and indicator in content_b)

        if success_matches >= 3:  # Require at least 3 success indicators
            score += min(success_matches * 0.05, 0.15)
            evidence['success_repetition_patterns'] = success_matches

        # 4. Degradation pattern analysis
        degradation_indicators = ['degraded', 'performance', 'slow', 'memory', 'leak', 'optimization needed']
        degradation_matches = sum(1 for indicator in degradation_indicators if indicator in content_a and indicator in content_b)

        if degradation_matches > 0:
            score += min(degradation_matches * 0.18, 0.35)
            evidence['degradation_patterns'] = degradation_matches

        # 5. File growth and code-update patterns
        # Compare file sizes and modification patterns
        size_ratio = min(node_a.get('size', 0), node_b.get('size', 0)) / max(node_a.get('size', 1), node_b.get('size', 1))
        if size_ratio > 0.7:  # Similar file sizes
            score += 0.08
            evidence['size_similarity'] = True

        # Directory proximity (files in same or related directories)
        dir_a = metadata_a.get('directory', '')
        dir_b = metadata_b.get('directory', '')
        if dir_a == dir_b or dir_a in dir_b or dir_b in dir_a:
            score += 0.1
            evidence['directory_proximity'] = True

        return {
            'score': score,
            'evidence': evidence
        }

    def _classify_relationship_type_comprehensive(self, node_a: Dict, node_b: Dict) -> str:
        """Classify relationship type based on comprehensive analysis."""
        type_a = node_a.get('file_type', 'unknown')
        type_b = node_b.get('file_type', 'unknown')

        # Code-to-code relationships
        if type_a in ['python', 'javascript', 'typescript'] and type_b in ['python', 'javascript', 'typescript']:
            return 'code_dependency'

        # Code-to-documentation relationships
        if (type_a in ['python', 'javascript', 'typescript'] and type_b == 'markdown') or \
           (type_b in ['python', 'javascript', 'typescript'] and type_a == 'markdown'):
            return 'implementation_documentation'

        # Documentation-to-documentation relationships
        if type_a == 'markdown' and type_b == 'markdown':
            # Check for task-report relationships
            if ('task_' in node_a.get('file', '') and 'report_' in node_b.get('file', '')) or \
               ('task_' in node_b.get('file', '') and 'report_' in node_a.get('file', '')):
                return 'task_implementation'
            else:
                return 'documentation_reference'

        # Data relationships
        if type_a == 'json' or type_b == 'json':
            return 'data_relationship'

        return 'general_abstract_link'

    def _calculate_significance_multiplier(self, node_a: Dict, node_b: Dict) -> float:
        """Calculate significance multiplier based on file types and metadata."""
        multiplier = 1.0

        # Code files are more significant
        if node_a.get('file_type') in ['python', 'javascript', 'typescript']:
            multiplier *= 1.2
        if node_b.get('file_type') in ['python', 'javascript', 'typescript']:
            multiplier *= 1.2

        # Recent files are more significant
        # (Could be enhanced with actual timestamps)

        # Files with high complexity are more significant
        complexity_a = node_a.get('metadata', {}).get('behavior', {}).get('complexity', 0.5)
        complexity_b = node_b.get('metadata', {}).get('behavior', {}).get('complexity', 0.5)

        avg_complexity = (complexity_a + complexity_b) / 2
        multiplier *= (0.8 + avg_complexity * 0.4)  # 0.8 to 1.2 range

        return multiplier

    def _assess_criticality(self, total_score: float, direct_links: Dict, abstract_links: Dict) -> str:
        """Assess criticality based on connection strength - adjusted for conservative scoring."""
        # With conservative scoring, even "high" connections are significant
        if total_score > 2.0:
            return 'critical'  # Very rare, extremely strong connections
        elif total_score > 1.5:
            return 'high'      # Strong evidence-based connections
        elif total_score > 1.2:
            return 'medium'    # Moderate but valid connections
        elif total_score > 1.0:
            return 'low'       # Weak but potentially valid connections
        else:
            return 'minimal'   # Below connection threshold

    def _assess_type_compatibility(self, type_a: str, type_b: str) -> float:
        """Assess how compatible two document types are for connection."""
        compatibility_matrix = {
            ('decision', 'analysis'): 0.9,
            ('decision', 'lesson'): 0.8,
            ('analysis', 'lesson'): 0.7,
            ('analysis', 'incident'): 0.8,
            ('lesson', 'incident'): 0.6,
            ('general', 'general'): 0.5,
        }

        # Check both orders
        key1 = (type_a, type_b)
        key2 = (type_b, type_a)

        return compatibility_matrix.get(key1, compatibility_matrix.get(key2, 0.3))

    def _classify_relationship_type(self, type_a: str, type_b: str) -> str:
        """Classify the type of relationship between documents."""
        if type_a == 'decision' and type_b == 'analysis':
            return 'decision_based_on_analysis'
        elif type_a == 'lesson' or type_b == 'lesson':
            return 'lesson_applied'
        elif type_a == 'incident' or type_b == 'incident':
            return 'incident_related'
        else:
            return 'general_association'

    def _calculate_temporal_distance(self, date_a: Optional[str], date_b: Optional[str]) -> float:
        """Calculate temporal distance between two dates in days."""
        if not date_a or not date_b:
            return 30  # Default assumption

        try:
            dt_a = datetime.fromisoformat(date_a.replace('Z', '+00:00'))
            dt_b = datetime.fromisoformat(date_b.replace('Z', '+00:00'))
            return abs((dt_a - dt_b).days)
        except:
            return 30  # Fallback

    def _update_profiles_from_connectivity(self, connectivity_result: Dict, analyzed_files: List[str]):
        """Update context profiles based on connectivity analysis."""
        # Update significance scores
        for file_id, significance_boost in connectivity_result['significance_updates'].items():
            if file_id not in self.context_profiles:
                self.context_profiles[file_id] = self._initialize_context_profile(file_id)

            if self.context_profiles[file_id]:
                current_sig = self.context_profiles[file_id]['parameters']['B_significance']
                # Gradual significance increase with diminishing returns
                new_sig = current_sig + (significance_boost * (1 - current_sig))
                self.context_profiles[file_id]['parameters']['B_significance'] = min(1.0, new_sig)

                # Update analysis metadata
                self.context_profiles[file_id]['analysis_count'] += 1
                self.context_profiles[file_id]['last_analyzed'] = datetime.now().isoformat()

                # Add to connection history
                self.context_profiles[file_id]['connection_history'].append({
                    'iteration': connectivity_result['analysis_timestamp'],
                    'connected_files': analyzed_files,
                    'significance_boost': significance_boost
                })

    def save_dream(self, dream_result: Dict, output_file: Optional[str] = None) -> str:
        """Save a context dream to a file with meaningful naming."""
        if not output_file:
            # Generate meaningful filename based on content
            seed_concept = dream_result.get('seed_concept', 'unknown').lower()
            # Clean seed concept for filename
            clean_seed = ''.join(c for c in seed_concept if c.isalnum() or c in ' _-').strip()
            clean_seed = clean_seed.replace(' ', '_')

            # Get primary insight type for additional context
            primary_insight = 'general'
            insights = dream_result.get('generated_insights', [])
            if insights:
                primary_insight = insights[0].get('type', 'general')

            # Create descriptive filename
            output_file = f"context_dream_{clean_seed}_{primary_insight}.json"
        print(f"📝 Generating meaningful filename: {output_file}")

        output_path = self.workspace / output_file

        # Handle filename conflicts by adding counter
        counter = 1
        base_name = output_file
        while output_path.exists():
            name_parts = base_name.rsplit('.', 1)
            if len(name_parts) == 2:
                output_file = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            else:
                output_file = f"{base_name}_{counter}"
            output_path = self.workspace / output_file
            counter += 1

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dream_result, f, indent=2, ensure_ascii=False)

        print(f"💾 Context dream saved to: {output_path}")
        return str(output_path)

    def _detect_code_patterns(self, content: str) -> bool:
        """Detect if content contains code-like patterns."""
        code_indicators = [
            'def ', 'class ', 'import ', 'from ', 'function', 'var ', 'let ', 'const ',
            'if ', 'for ', 'while ', 'return ', 'print(', 'console.log', '<?php', '<script',
            'public class', 'private ', 'void ', 'int ', 'string ', '#include'
        ]
        return any(indicator in content for indicator in code_indicators)

    def _detect_urls(self, content: str) -> bool:
        """Detect if content contains URLs."""
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
        return bool(re.search(url_pattern, content))


def main():
    """CLI interface for context dreaming."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Context Dreaming Engine via Mega.md Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python context_dreamer.py "api integration" --depth 4
  python context_dreamer.py report_L015_decision_042 --output my_custom_dream.json
  python context_dreamer.py "error handling" --depth 2 --save
  python context_dreamer.py --enhanced --iterations 20 --output enhanced_dream.json
  # Enhanced mode: context_dream_enhanced_connectivity.json
        """
    )

    parser.add_argument('seed_concept', nargs='?', help='Starting concept or file ID for the dream (optional in enhanced mode)')
    parser.add_argument('--depth', '-d', type=int, default=3, help='Dream exploration depth (default: 3)')
    parser.add_argument('--output', '-o', help='Output file for the dream results')
    parser.add_argument('--workspace', '-w', default='.', help='Workspace root directory')
    parser.add_argument('--save', action='store_true', help='Save dream to file')
    parser.add_argument('--enhanced', '-e', action='store_true', help='Use enhanced context dreaming with document parameters')
    parser.add_argument('--iterations', '-i', type=int, default=10, help='Number of iterations for enhanced dreaming (default: 10)')
    parser.add_argument('--target-depth', '-td', type=int, help='Target depth for mathematical optimization (default: auto-calculate)')
    parser.add_argument('--show-math', action='store_true', help='Show detailed mathematical analysis')
    parser.add_argument('--test-links', type=int, help='Test direct links between 2 random files (specify number of max links)')
    parser.add_argument('--learn-params', '-l', type=int, help='Run parameter discovery learning cycles (specify number of cycles)')
    args = parser.parse_args()

    # Initialize dreamer
    dreamer = ContextDreamer(args.workspace)

    print("🌙 Context Dreaming Engine")
    print(f"📊 Network contains {len(dreamer.network_graph)} nodes")
    print(f"🎯 Branching factor: {dreamer.branching_factor}")
    print("-" * 50)

    # Handle different modes
    if args.enhanced:
        # Enhanced context dreaming mode
        print("🌟 Enhanced Context Dreaming Mode")
        print(f"🔄 Iterations: {args.iterations}")
        if args.target_depth:
            print(f"📏 Target depth: d={args.target_depth}")

        dream = dreamer.enhanced_context_dream(
            iterations=args.iterations,
            target_depth=args.target_depth
        )

        if args.show_math:
            math_analysis = dream['mathematical_analysis']
            print(f"""
🧮 Mathematical Analysis (depth_vs_breathe.md):
   Optimal depth: d={math_analysis['optimal_depth']}
   Connectivity advantage: {math_analysis['expected_connectivity_gain']:.1f}×
   Token utilization: {math_analysis['token_budget_utilization']:.1%}
   Superior d=7 advantage: {math_analysis['mathematical_targets']['superior_depth_7_advantage']:.1f}×
""")

        if dream['iterations_completed'] > 0:
            print("\n✅ Enhanced dreaming completed!")
            print(f"🔗 Total connections discovered: {dream['total_connections_discovered']}")
            print(f"📊 Documents profiled: {len(dream['final_profiles'])}")

            # Save enhanced dream results
            if args.save or args.output:
                saved_path = dreamer.save_dream(dream, args.output)
                print(f"\n💾 Enhanced dream saved to: {saved_path}")

        else:
            print("❌ Enhanced dreaming failed")
            return 1

    elif args.seed_concept:
        # Traditional seed-based dreaming mode
        print("🌙 Traditional Context Dreaming Mode")
        dream = dreamer.dream_context(args.seed_concept, args.depth)

        if args.show_math:
            print("\n🧮 Mathematical Analysis (depth_vs_breathe.md):")
            dreamer.show_mathematical_analysis(args.target_depth or args.depth)

        if dream['success']:
            print("\n✅ Dream Generated Successfully!")
            print(f"🌟 Explored {dream['network_stats']['explored_nodes']} nodes")
            print(f"💡 Generated {len(dream['generated_insights'])} insights")

            # Display insights
            for i, insight in enumerate(dream['generated_insights'], 1):
                print(f"\n{i}. {insight['type'].upper()}: {insight['insight']}")
                print(f"   Confidence: {insight['confidence']:.1%}")
                if insight.get('evidence'):
                    evidence_preview = str(insight['evidence'])[:100] + "..." if len(str(insight['evidence'])) > 100 else str(insight['evidence'])
                    print(f"   Evidence: {evidence_preview}")

            # Save if requested
            if args.save or args.output:
                saved_path = dreamer.save_dream(dream, args.output)
                print(f"\n💾 Dream saved to: {saved_path}")

        else:
            print(f"❌ Dream failed: {dream['error']}")
            return 1

    elif args.test_links is not None:
        # Test direct links between two random files
        print("🧪 Direct Link Discovery Test")
        print(f"🎯 Finding up to {args.test_links} direct links between 2 random files")

        test_result = dreamer.test_direct_links_between_two_files(args.test_links)

        if 'error' in test_result:
            print(f"❌ Test failed: {test_result['error']}")
            return 1

        print("\n📊 Test Results:")
        print(f"   Files analyzed: {test_result['file_a']} ↔ {test_result['file_b']}")
        print(f"   Links found: {test_result['links_found']}/{test_result['max_links_requested']}")

        if test_result['links_found'] > 0:
            print("\n🔗 Direct Links Discovered:")
            for i, link in enumerate(test_result['direct_links'], 1):
                print(f"   {i}. {link['type']}: {link['description']}")
                print(f"      Strength: {link['strength']:.3f}")
        else:
            print("   ❌ No direct links found - foundation needs strengthening")

        return 0

    elif args.learn_params is not None:
        # Parameter discovery learning mode
        print("🔬 Parameter Discovery Learning Mode")
        print(f"🎯 Running {args.learn_params} learning cycles to discover optimal connection parameters")

        learning_result = dreamer.discover_connection_parameters(args.learn_params)

        # Handle case where no reference connection was found
        if 'error' in learning_result:
            print(f"\n❌ Learning failed: {learning_result['error']}")
            print("\n💡 Recommendation: Strengthen foundation metadata before running parameter discovery")
            print("   - Improve keyword/concept extraction")
            print("   - Add more connection evidence types")
            print("   - Enhance file analysis depth")
            return 1

        print("\n📊 Learning Results:")
        if 'learning_cycles' in learning_result:
            print(f"   Learning cycles completed: {learning_result['learning_cycles']}")
        if 'final_parameters' in learning_result:
            print(f"   Final parameters: {learning_result['final_parameters']}")
        if 'insights' in learning_result and isinstance(learning_result['insights'], dict):
            if 'learning_efficiency' in learning_result['insights']:
                print(f"   Learning efficiency: {learning_result['insights']['learning_efficiency']:.1%}")

        print("\n🔑 Key Insights:")
        if 'insights' in learning_result:
            insights = learning_result['insights']
            if isinstance(insights, dict) and 'key_findings' in insights:
                for finding in insights['key_findings']:
                    print(f"   • {finding}")
            elif isinstance(insights, list):
                for finding in insights:
                    print(f"   • {finding}")

        print("\n🧮 Mathematical Foundation:")
        if 'mathematical_foundation' in learning_result:
            math_foundation = learning_result['mathematical_foundation']
            print(f"   Parameter balance: {math_foundation.get('parameter_balance', 0):.3f}")
            print(f"   Connection potential: {math_foundation.get('connection_potential', 0):.3f}")
            print(f"   Optimization readiness: {math_foundation.get('optimization_readiness', 0):.3f}")

        # Save learning results
        if args.save or args.output:
            import json
            output_file = args.output or f"parameter_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                with open(output_file, 'w') as f:
                    json.dump(learning_result, f, indent=2, default=str, ensure_ascii=False)
                print(f"\n💾 Learning results saved to: {output_file}")
            except Exception as e:
                print(f"\n⚠️  Failed to save results: {e}")
                # Try saving a simplified version
                try:
                    simplified_result = {
                        'learning_cycles': learning_result['learning_cycles'],
                        'final_parameters': learning_result['final_parameters'],
                        'parameter_evolution': learning_result['parameter_evolution'],
                        'insights': learning_result['insights'],
                        'mathematical_foundation': learning_result['mathematical_foundation']
                    }
                    with open(f"{output_file}.simplified", 'w') as f:
                        json.dump(simplified_result, f, indent=2, default=str, ensure_ascii=False)
                    print(f"💾 Simplified results saved to: {output_file}.simplified")
                except Exception as e2:
                    print(f"⚠️  Even simplified save failed: {e2}")

        return 0

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
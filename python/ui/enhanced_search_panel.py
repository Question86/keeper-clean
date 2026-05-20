# MODE: LIBRARY

"""
Enhanced Search Panel - Frontend Integration for Cockpit

Provides web-based UI components for the advanced search system:
- Real-time search with suggestions
- Tag-based filtering
- Result visualization
- Performance metrics display
- Integration with network cockpit

Integrates with cockpit-network.html for seamless UI experience.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timezone

from advanced_search_engine import AdvancedSearchEngine, EnhancedSearchResult, SearchMetrics
from intelligent_tagger import IntelligentTagger, FileTags
from predictive_suggester import PredictiveSuggester, SearchSuggestion


@dataclass
class SearchPanelConfig:
    """Configuration for the search panel."""
    max_results: int = 20
    enable_suggestions: bool = True
    enable_tags: bool = True
    enable_metrics: bool = True
    realtime_search: bool = True
    suggestion_delay_ms: int = 300


class EnhancedSearchPanel:
    """
    Enhanced search panel for web-based cockpit integration.

    Provides REST API endpoints and HTML components for advanced search functionality.
    """

    def __init__(self, app: Flask, workspace_path: Path, config: Optional[SearchPanelConfig] = None):
        self.app = app
        self.workspace = workspace_path
        self.config = config or SearchPanelConfig()

        # Initialize search components
        self.search_engine = AdvancedSearchEngine(workspace_path)
        self.tagger = IntelligentTagger(workspace_path)
        self.suggester = PredictiveSuggester(workspace_path)

        # Register routes
        self._register_routes()

        # Session tracking
        self.active_sessions: Dict[str, Any] = {}

    def _register_routes(self) -> None:
        """Register Flask routes for search panel API."""

        @self.app.route('/api/search/enhanced', methods=['POST'])
        def enhanced_search():
            """Enhanced search endpoint with metadata optimization."""
            try:
                data = request.get_json() or {}
                query = data.get('query', '').strip()
                types = data.get('types', None)
                task_id = data.get('task_id')
                loop_min = data.get('loop_min')
                loop_max = data.get('loop_max')
                limit = min(data.get('limit', self.config.max_results), 50)  # Cap at 50

                if not query:
                    return jsonify({
                        'error': 'Query is required',
                        'results': [],
                        'metrics': {}
                    }), 400

                # Perform enhanced search
                results, metrics = self.search_engine.search(
                    query=query,
                    types=types,
                    task_id=task_id,
                    loop_min=loop_min,
                    loop_max=loop_max,
                    limit=limit,
                    use_metadata_boost=True,
                    use_breadcrumb_boost=True,
                    use_temporal_boost=True
                )

                # Format results for frontend
                formatted_results = [self._format_result(r) for r in results]

                # Record query for learning
                self.suggester.record_query(query)

                return jsonify({
                    'query': query,
                    'results': formatted_results,
                    'metrics': self._format_metrics(metrics),
                    'total_results': len(results)
                })

            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'results': [],
                    'metrics': {}
                }), 500

        @self.app.route('/api/search/suggestions', methods=['GET'])
        def get_suggestions():
            """Get search suggestions for partial query."""
            try:
                partial = request.args.get('q', '').strip()
                limit = min(int(request.args.get('limit', 10)), 20)

                if not partial:
                    return jsonify({'suggestions': []})

                suggestions = self.suggester.get_suggestions(
                    partial_query=partial,
                    max_suggestions=limit,
                    include_ai=True
                )

                formatted_suggestions = [self._format_suggestion(s) for s in suggestions]

                return jsonify({
                    'partial': partial,
                    'suggestions': formatted_suggestions
                })

            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'suggestions': []
                }), 500

        @self.app.route('/api/search/tags', methods=['GET'])
        def get_tags():
            """Get popular tags and tag-based search options."""
            try:
                popular_tags = self.tagger.get_popular_tags(limit=20)

                formatted_tags = [{
                    'tag': tag.tag,
                    'confidence': tag.confidence,
                    'source': tag.source,
                    'frequency': tag.frequency,
                    'category': tag.tag.split(':')[0] if ':' in tag.tag else 'general'
                } for tag in popular_tags]

                return jsonify({
                    'tags': formatted_tags,
                    'categories': list(set(tag['category'] for tag in formatted_tags))
                })

            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'tags': []
                }), 500

        @self.app.route('/api/search/file-tags/<path:file_path>', methods=['GET'])
        def get_file_tags(file_path: str):
            """Get tags for a specific file."""
            try:
                file_tags = self.tagger.generate_tags_for_file(file_path)

                formatted_tags = [{
                    'tag': tag.tag,
                    'confidence': tag.confidence,
                    'source': tag.source,
                    'frequency': tag.frequency
                } for tag in file_tags.tags]

                return jsonify({
                    'file_path': file_path,
                    'tags': formatted_tags,
                    'generated_at': file_tags.generated_at.isoformat()
                })

            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'tags': []
                }), 500

        @self.app.route('/api/search/metrics', methods=['GET'])
        def get_search_metrics():
            """Get search performance metrics."""
            try:
                metrics = self.search_engine.get_performance_stats()

                return jsonify({
                    'performance': metrics,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'performance': {}
                }), 500

        @self.app.route('/api/search/session/start', methods=['POST'])
        def start_search_session():
            """Start a search session for context tracking."""
            try:
                data = request.get_json() or {}
                session_id = data.get('session_id', 'default')
                current_file = data.get('current_file')

                self.suggester.start_session(
                    user_id=session_id,
                    current_file=current_file
                )

                self.active_sessions[session_id] = {
                    'start_time': datetime.now(timezone.utc),
                    'current_file': current_file
                }

                return jsonify({
                    'session_id': session_id,
                    'status': 'started'
                })

            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'status': 'error'
                }), 500

    def _format_result(self, result: EnhancedSearchResult) -> Dict[str, Any]:
        """Format search result for frontend consumption."""
        return {
            'type': result.base_result.type,
            'id': result.base_result.id,
            'relevance': result.base_result.relevance,
            'snippet': result.base_result.snippet,
            'context': result.base_result.context,
            'breadcrumb_relevance': result.breadcrumb_relevance,
            'metadata_score': result.metadata_score,
            'temporal_freshness': result.temporal_freshness,
            'reference_chain_depth': result.reference_chain_depth,
            'combined_score': result.combined_score,
            'score_breakdown': {
                'base': result.base_result.relevance,
                'breadcrumb': result.breadcrumb_relevance,
                'metadata': result.metadata_score,
                'temporal': result.temporal_freshness,
                'references': result.reference_chain_depth * 0.05
            }
        }

    def _format_suggestion(self, suggestion: SearchSuggestion) -> Dict[str, Any]:
        """Format search suggestion for frontend."""
        return {
            'query': suggestion.query,
            'confidence': suggestion.confidence,
            'source': suggestion.source,
            'category': suggestion.category,
            'metadata': suggestion.metadata
        }

    def _format_metrics(self, metrics: SearchMetrics) -> Dict[str, Any]:
        """Format search metrics for frontend."""
        return {
            'query_time_ms': metrics.query_time_ms,
            'result_count': metrics.result_count,
            'cache_hit': metrics.cache_hit,
            'semantic_expansions': metrics.semantic_expansions,
            'quality_score': metrics.quality_score,
            'breadcrumb_boost': metrics.breadcrumb_boost,
            'performance_status': 'good' if metrics.query_time_ms < 500 else 'slow'
        }

    def get_panel_html(self) -> str:
        """Get HTML for the enhanced search panel component."""
        return f"""
        <div id="enhanced-search-panel" class="search-panel">
            <div class="search-header">
                <h3>Advanced Search</h3>
                <div class="search-metrics">
                    <span id="query-time">-</span>ms
                    <span id="result-count">-</span> results
                </div>
            </div>

            <div class="search-input-container">
                <input type="text" id="search-input" placeholder="Search knowledge base..."
                       autocomplete="off" spellcheck="false">
                <div id="search-suggestions" class="suggestions-dropdown" style="display: none;"></div>
            </div>

            <div class="search-filters">
                <div class="filter-group">
                    <label>Types:</label>
                    <div class="checkbox-group">
                        <label><input type="checkbox" value="report" checked> Reports</label>
                        <label><input type="checkbox" value="task" checked> Tasks</label>
                        <label><input type="checkbox" value="lesson" checked> Lessons</label>
                        <label><input type="checkbox" value="archive" checked> Archives</label>
                    </div>
                </div>

                <div class="filter-group">
                    <label>Loop Range:</label>
                    <input type="number" id="loop-min" placeholder="Min" min="1">
                    <span>to</span>
                    <input type="number" id="loop-max" placeholder="Max" min="1">
                </div>
            </div>

            <div class="search-results" id="search-results">
                <div class="no-results" style="display: none;">
                    <p>No results found. Try adjusting your search terms.</p>
                </div>
            </div>

            <div class="search-tags" id="search-tags" style="display: none;">
                <h4>Popular Tags</h4>
                <div class="tag-cloud" id="tag-cloud"></div>
            </div>
        </div>

        <style>
        .search-panel {{
            background: linear-gradient(135deg, rgba(40, 40, 40, 0.95), rgba(20, 20, 20, 0.95));
            border: 2px solid #50c8a0;
            border-radius: 15px;
            padding: 20px;
            margin: 20px;
            box-shadow: 0 8px 32px rgba(80, 200, 160, 0.3);
            backdrop-filter: blur(10px);
            color: #e8e8e8;
        }}

        .search-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}

        .search-header h3 {{
            margin: 0;
            color: #50c8a0;
        }}

        .search-metrics {{
            font-size: 0.9em;
            color: #aaa;
        }}

        .search-input-container {{
            position: relative;
            margin-bottom: 20px;
        }}

        #search-input {{
            width: 100%;
            padding: 12px 15px;
            background: rgba(60, 60, 60, 0.8);
            border: 1px solid #50c8a0;
            border-radius: 8px;
            color: #e8e8e8;
            font-size: 1em;
        }}

        #search-input:focus {{
            outline: none;
            border-color: #3ca080;
            box-shadow: 0 0 10px rgba(80, 200, 160, 0.3);
        }}

        .suggestions-dropdown {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: rgba(40, 40, 40, 0.95);
            border: 1px solid #50c8a0;
            border-radius: 8px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
        }}

        .suggestion-item {{
            padding: 10px 15px;
            cursor: pointer;
            border-bottom: 1px solid rgba(80, 200, 160, 0.2);
        }}

        .suggestion-item:hover {{
            background: rgba(80, 200, 160, 0.1);
        }}

        .suggestion-item:last-child {{
            border-bottom: none;
        }}

        .search-filters {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}

        .filter-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .filter-group label {{
            font-weight: 600;
            color: #50c8a0;
        }}

        .checkbox-group {{
            display: flex;
            gap: 15px;
        }}

        .checkbox-group label {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-weight: normal;
        }}

        .search-results {{
            min-height: 200px;
            max-height: 400px;
            overflow-y: auto;
        }}

        .result-item {{
            background: rgba(60, 60, 60, 0.5);
            border: 1px solid rgba(80, 200, 160, 0.3);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }}

        .result-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .result-type {{
            background: #50c8a0;
            color: #0f0f0f;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
        }}

        .result-score {{
            font-size: 0.9em;
            color: #aaa;
        }}

        .result-snippet {{
            color: #e8e8e8;
            line-height: 1.4;
        }}

        .result-context {{
            margin-top: 8px;
            font-size: 0.9em;
            color: #aaa;
        }}

        .tag-cloud {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }}

        .tag-item {{
            background: rgba(80, 200, 160, 0.2);
            border: 1px solid #50c8a0;
            border-radius: 15px;
            padding: 5px 10px;
            font-size: 0.8em;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .tag-item:hover {{
            background: rgba(80, 200, 160, 0.3);
            transform: translateY(-1px);
        }}
        </style>

        <script>
        class EnhancedSearchPanel {{
            constructor() {{
                this.searchInput = document.getElementById('search-input');
                this.suggestionsDiv = document.getElementById('search-suggestions');
                this.resultsDiv = document.getElementById('search-results');
                this.queryTimeSpan = document.getElementById('query-time');
                this.resultCountSpan = document.getElementById('result-count');
                this.tagCloud = document.getElementById('tag-cloud');

                this.suggestionTimeout = null;
                this.currentQuery = '';

                this.init();
            }}

            init() {{
                // Input event listeners
                this.searchInput.addEventListener('input', (e) => {{
                    this.handleInput(e.target.value);
                }});

                this.searchInput.addEventListener('keydown', (e) => {{
                    if (e.key === 'Enter') {{
                        this.performSearch();
                    }} else if (e.key === 'Escape') {{
                        this.hideSuggestions();
                    }}
                }});

                // Click outside to hide suggestions
                document.addEventListener('click', (e) => {{
                    if (!this.searchInput.contains(e.target) && !this.suggestionsDiv.contains(e.target)) {{
                        this.hideSuggestions();
                    }}
                }});

                // Load popular tags
                this.loadTags();
            }}

            handleInput(value) {{
                this.currentQuery = value.trim();

                if (value.length === 0) {{
                    this.hideSuggestions();
                    return;
                }}

                // Debounce suggestions
                clearTimeout(this.suggestionTimeout);
                this.suggestionTimeout = setTimeout(() => {{
                    this.loadSuggestions(value);
                }}, {self.config.suggestion_delay_ms});
            }}

            async loadSuggestions(partial) {{
                try {{
                    const response = await fetch(`/api/search/suggestions?q=${{encodeURIComponent(partial)}}`);
                    const data = await response.json();

                    if (data.suggestions && data.suggestions.length > 0) {{
                        this.showSuggestions(data.suggestions);
                    }} else {{
                        this.hideSuggestions();
                    }}
                }} catch (error) {{
                    console.error('Error loading suggestions:', error);
                    this.hideSuggestions();
                }}
            }}

            showSuggestions(suggestions) {{
                this.suggestionsDiv.innerHTML = '';

                suggestions.forEach(suggestion => {{
                    const item = document.createElement('div');
                    item.className = 'suggestion-item';
                    item.textContent = suggestion.query;

                    item.addEventListener('click', () => {{
                        this.searchInput.value = suggestion.query;
                        this.currentQuery = suggestion.query;
                        this.hideSuggestions();
                        this.performSearch();
                    }});

                    this.suggestionsDiv.appendChild(item);
                }});

                this.suggestionsDiv.style.display = 'block';
            }}

            hideSuggestions() {{
                this.suggestionsDiv.style.display = 'none';
            }}

            async performSearch() {{
                if (!this.currentQuery) return;

                const types = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
                    .map(cb => cb.value);

                const loopMin = document.getElementById('loop-min').value;
                const loopMax = document.getElementById('loop-max').value;

                const searchData = {{
                    query: this.currentQuery,
                    types: types.length > 0 ? types : null,
                    loop_min: loopMin ? parseInt(loopMin) : null,
                    loop_max: loopMax ? parseInt(loopMax) : null,
                    limit: {self.config.max_results}
                }};

                try {{
                    const startTime = Date.now();
                    const response = await fetch('/api/search/enhanced', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(searchData)
                    }});

                    const data = await response.json();
                    const endTime = Date.now();

                    this.displayResults(data);
                    this.updateMetrics(data.metrics, endTime - startTime);

                }} catch (error) {{
                    console.error('Search error:', error);
                    this.showError('Search failed. Please try again.');
                }}
            }}

            displayResults(data) {{
                this.resultsDiv.innerHTML = '';

                if (!data.results || data.results.length === 0) {{
                    const noResults = document.createElement('div');
                    noResults.className = 'no-results';
                    noResults.innerHTML = '<p>No results found. Try adjusting your search terms.</p>';
                    this.resultsDiv.appendChild(noResults);
                    return;
                }}

                data.results.forEach(result => {{
                    const resultDiv = document.createElement('div');
                    resultDiv.className = 'result-item';

                    const scorePercent = Math.round(result.combined_score * 100);

                    resultDiv.innerHTML = `
                        <div class="result-header">
                            <span class="result-type">${{result.type.toUpperCase()}}</span>
                            <span class="result-score">${{scorePercent}}% relevance</span>
                        </div>
                        <div class="result-snippet">${{result.snippet}}</div>
                        <div class="result-context">
                            ${{(result.context.task_id ? `Task: ${{result.context.task_id}} ` : '')}}
                            ${{(result.context.loop_num ? `Loop: ${{result.context.loop_num}} ` : '')}}
                            ${{(result.context.validation_passed ? '(Validated)' : '')}}
                        </div>
                    `;

                    this.resultsDiv.appendChild(resultDiv);
                }});
            }}

            updateMetrics(metrics, clientTime) {{
                if (metrics) {{
                    this.queryTimeSpan.textContent = metrics.query_time_ms || clientTime;
                    this.resultCountSpan.textContent = metrics.result_count || 0;
                }}
            }}

            async loadTags() {{
                try {{
                    const response = await fetch('/api/search/tags');
                    const data = await response.json();

                    if (data.tags) {{
                        this.displayTags(data.tags);
                    }}
                }} catch (error) {{
                    console.error('Error loading tags:', error);
                }}
            }}

            displayTags(tags) {{
                this.tagCloud.innerHTML = '';

                tags.slice(0, 15).forEach(tag => {{
                    const tagElement = document.createElement('span');
                    tagElement.className = 'tag-item';
                    tagElement.textContent = tag.tag;
                    tagElement.title = `Confidence: ${{Math.round(tag.confidence * 100)}}% | Source: ${{tag.source}}`;

                    tagElement.addEventListener('click', () => {{
                        this.searchInput.value = `tag:${{tag.tag}}`;
                        this.currentQuery = `tag:${{tag.tag}}`;
                        this.performSearch();
                    }});

                    this.tagCloud.appendChild(tagElement);
                }});

                document.getElementById('search-tags').style.display = 'block';
            }}

            showError(message) {{
                this.resultsDiv.innerHTML = `<div class="error">${{message}}</div>`;
            }}
        }}

        // Initialize when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {{
            window.enhancedSearchPanel = new EnhancedSearchPanel();
        }});
        </script>
        """

    def inject_into_cockpit_html(self, cockpit_html_path: Path) -> bool:
        """
        Inject the search panel into cockpit-network.html.

        Returns True if injection was successful.
        """
        try:
            with open(cockpit_html_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find a good place to inject the search panel
            # Look for a container or main content area
            injection_point = content.find('<div class="central-panels">')

            if injection_point == -1:
                # Fallback: inject before closing body tag
                injection_point = content.rfind('</body>')

            if injection_point == -1:
                return False

            # Insert the search panel HTML
            panel_html = self.get_panel_html()
            modified_content = (
                content[:injection_point] +
                f'\n<!-- Enhanced Search Panel -->\n{panel_html}\n' +
                content[injection_point:]
            )

            # Write back the modified content
            with open(cockpit_html_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)

            return True

        except (IOError, UnicodeDecodeError):
            return False
#!/usr/bin/env python3
"""
Search Agent - Dynamic Web Search and Content Extraction

Performs web searches and extracts relevant content for knowledge gaps.
Part of TASK_0185: Autonomous Knowledge Gathering and Database Integration System.
"""

import json
import re
import time
import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlencode, urlparse
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Represents a single search result."""
    title: str
    url: str
    snippet: str
    source: str
    relevance_score: float
    extracted_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SearchAgent:
    """
    Autonomous web search and content extraction agent.

    Performs searches across multiple sources and extracts relevant content.
    Uses simple HTTP requests without external scraping libraries.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Search engines and their configurations
        self.search_engines = {
            'duckduckgo': {
                'url': 'https://duckduckgo.com/html/',
                'params': {'q': '{query}'},
                'parser': self._parse_duckduckgo
            },
            'searx': {
                'url': 'https://searx.org/search',
                'params': {'q': '{query}', 'format': 'json'},
                'parser': self._parse_searx
            }
        }

        # Content extraction patterns
        self.content_patterns = {
            'title': re.compile(r'<title[^>]*>([^<]+)</title>', re.IGNORECASE),
            'paragraphs': re.compile(r'<p[^>]*>([^<]+)</p>', re.IGNORECASE),
            'headings': re.compile(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', re.IGNORECASE),
            'code_blocks': re.compile(r'<code[^>]*>([^<]+)</code>', re.IGNORECASE),
            'pre_blocks': re.compile(r'<pre[^>]*>(.*?)</pre>', re.IGNORECASE | re.DOTALL)
        }

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Perform web search for a query.

        Returns list of search results with extracted content.
        """
        logger.info(f"Searching for: {query}")

        all_results = []

        # Try multiple search engines
        for engine_name, config in self.search_engines.items():
            try:
                results = self._search_engine(engine_name, query, max_results)
                all_results.extend(results)

                if len(all_results) >= max_results:
                    break

            except Exception as e:
                logger.warning(f"Search failed for {engine_name}: {e}")
                continue

        # Limit results
        all_results = all_results[:max_results]

        # Extract content from top results
        for result in all_results:
            try:
                result.extracted_content = self._extract_content(result.url)
            except Exception as e:
                logger.warning(f"Content extraction failed for {result.url}: {e}")

        # Sort by relevance
        all_results.sort(key=lambda r: r.relevance_score, reverse=True)

        logger.info(f"Found {len(all_results)} results for query: {query}")
        return all_results

    def _search_engine(self, engine: str, query: str, max_results: int) -> List[SearchResult]:
        """Search using a specific search engine."""
        config = self.search_engines[engine]
        self._rate_limit()

        # Prepare URL
        params = {k: v.format(query=query) for k, v in config['params'].items()}
        url = config['url']
        if params:
            url += '?' + urlencode(params)

        # Make request
        response = self.session.get(url, timeout=10)
        response.raise_for_status()

        # Parse results
        parser = config['parser']
        return parser(response.text, query, max_results)

    def _parse_duckduckgo(self, html: str, query: str, max_results: int) -> List[SearchResult]:
        """Parse DuckDuckGo HTML results."""
        results = []

        # Simple regex-based parsing (not perfect but works)
        result_pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>([^<]*)</a>',
            re.IGNORECASE | re.DOTALL
        )

        matches = result_pattern.findall(html)
        for url, title, snippet in matches[:max_results]:
            # Clean up
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()

            if title and url:
                relevance = self._calculate_relevance(title + ' ' + snippet, query)
                result = SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source='duckduckgo',
                    relevance_score=relevance
                )
                results.append(result)

        return results

    def _parse_searx(self, json_text: str, query: str, max_results: int) -> List[SearchResult]:
        """Parse SearX JSON results."""
        results = []

        try:
            data = json.loads(json_text)
            search_results = data.get('results', [])[:max_results]

            for item in search_results:
                title = item.get('title', '')
                url = item.get('url', '')
                content = item.get('content', '')

                if title and url:
                    relevance = self._calculate_relevance(title + ' ' + content, query)
                    result = SearchResult(
                        title=title,
                        url=url,
                        snippet=content,
                        source='searx',
                        relevance_score=relevance
                    )
                    results.append(result)

        except json.JSONDecodeError:
            logger.warning("Failed to parse SearX JSON response")

        return results

    def _extract_content(self, url: str) -> Optional[str]:
        """Extract relevant content from a URL."""
        self._rate_limit()

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            html = response.text
            content_parts = []

            # Extract title
            title_match = self.content_patterns['title'].search(html)
            if title_match:
                content_parts.append(f"Title: {title_match.group(1).strip()}")

            # Extract headings
            headings = self.content_patterns['headings'].findall(html)
            if headings:
                content_parts.append("Headings: " + " | ".join(h.strip() for h in headings[:5]))

            # Extract paragraphs (first few meaningful ones)
            paragraphs = self.content_patterns['paragraphs'].findall(html)
            meaningful_paragraphs = [
                p.strip() for p in paragraphs
                if len(p.strip()) > 50  # Meaningful length
            ][:3]  # First 3

            if meaningful_paragraphs:
                content_parts.append("Content: " + " ".join(meaningful_paragraphs))

            # Extract code blocks if present
            code_blocks = self.content_patterns['code_blocks'].findall(html)
            pre_blocks = self.content_patterns['pre_blocks'].findall(html)

            if code_blocks or pre_blocks:
                all_code = code_blocks + pre_blocks
                content_parts.append("Code: " + " ".join(all_code[:2]))

            return "\n".join(content_parts) if content_parts else None

        except Exception as e:
            logger.warning(f"Content extraction failed for {url}: {e}")
            return None

    def _calculate_relevance(self, text: str, query: str) -> float:
        """Calculate relevance score for text against query."""
        text_lower = text.lower()
        query_lower = query.lower()

        # Exact query match
        if query_lower in text_lower:
            base_score = 1.0
        else:
            base_score = 0.5

        # Word overlap
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())
        overlap = len(query_words.intersection(text_words))
        word_score = overlap / len(query_words) if query_words else 0

        # Combine scores
        return (base_score * 0.6) + (word_score * 0.4)

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def search_multiple_queries(self, queries: List[str], max_results_per_query: int = 3) -> List[SearchResult]:
        """
        Search multiple queries and combine results.

        Removes duplicates and sorts by relevance.
        """
        all_results = []

        for query in queries:
            results = self.search(query, max_results_per_query)
            all_results.extend(results)

        # Remove duplicates by URL
        seen_urls = set()
        unique_results = []

        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)

        # Sort by relevance
        unique_results.sort(key=lambda r: r.relevance_score, reverse=True)

        return unique_results


def main():
    """Test the search agent."""
    agent = SearchAgent()

    # Test single search
    results = agent.search("python asyncio tutorial", max_results=3)
    print(f"Found {len(results)} results:")
    for result in results:
        print(f"- {result.title} ({result.relevance_score:.2f})")
        if result.extracted_content:
            print(f"  Content preview: {result.extracted_content[:200]}...")

    # Test multiple queries
    queries = ["python threading", "concurrent.futures"]
    results = agent.search_multiple_queries(queries, max_results_per_query=2)
    print(f"\nCombined search found {len(results)} unique results")


if __name__ == '__main__':
    main()
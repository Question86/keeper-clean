# MODE: SCRIPT

"""Token Efficient Search - Optimized Knowledge Retrieval

This module provides token-efficient search and context building mechanisms
to reduce token consumption while maintaining search quality.
"""

from __future__ import annotations

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import numpy as np

from knowledge_db import KnowledgeDB


@dataclass
class SearchConfig:
    """Configuration for token-efficient search."""
    max_context_tokens: int = 8000
    max_results: int = 10
    compression_ratio: float = 0.7  # Compress to 70% of original
    semantic_weight: float = 0.6
    text_weight: float = 0.4
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour


class ContextCompressor:
    """Compress context to reduce token usage while preserving meaning."""

    def __init__(self, config: SearchConfig = None):
        self.config = config or SearchConfig()

    def compress_context(self, text: str, target_tokens: int = None) -> str:
        """Compress text to target token count."""
        if target_tokens is None:
            target_tokens = int(len(text.split()) * self.config.compression_ratio)

        # Simple compression: remove redundant information
        compressed = self._remove_redundancy(text)
        compressed = self._summarize_paragraphs(compressed)
        compressed = self._extract_key_sentences(compressed)

        # Ensure we don't exceed target
        words = compressed.split()
        if len(words) > target_tokens:
            compressed = ' '.join(words[:target_tokens])

        return compressed

    def _remove_redundancy(self, text: str) -> str:
        """Remove redundant phrases and repeated information."""
        # Remove duplicate sentences (simple approach)
        sentences = re.split(r'[.!?]+', text)
        seen = set()
        unique_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and sentence.lower() not in seen:
                seen.add(sentence.lower())
                unique_sentences.append(sentence)

        return '. '.join(unique_sentences)

    def _summarize_paragraphs(self, text: str) -> str:
        """Summarize long paragraphs."""
        paragraphs = text.split('\n\n')
        summarized = []

        for para in paragraphs:
            words = para.split()
            if len(words) > 100:  # Long paragraph
                # Keep first and last sentences, summarize middle
                sentences = re.split(r'[.!?]+', para)
                if len(sentences) > 3:
                    summary = f"{sentences[0].strip()}. ... {sentences[-1].strip()}."
                else:
                    summary = para
                summarized.append(summary)
            else:
                summarized.append(para)

        return '\n\n'.join(summarized)

    def _extract_key_sentences(self, text: str) -> str:
        """Extract most important sentences."""
        sentences = re.split(r'[.!?]+', text)
        # Simple heuristic: prefer sentences with keywords
        keywords = ['important', 'key', 'critical', 'main', 'primary', 'essential']

        scored_sentences = []
        for sentence in sentences:
            score = sum(1 for word in keywords if word in sentence.lower())
            scored_sentences.append((sentence, score))

        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in scored_sentences[:5]]  # Top 5

        return '. '.join(top_sentences)


class TokenEfficientSearch:
    """Token-efficient knowledge search and retrieval."""

    def __init__(self, workspace_root: Path, config: SearchConfig = None):
        self.workspace_root = workspace_root
        self.config = config or SearchConfig()
        self.knowledge_db = KnowledgeDB(workspace_root)
        self.compressor = ContextCompressor(self.config)
        self.cache: Dict[str, Dict[str, Any]] = {}

    def search(self, query: str, max_tokens: int = None) -> Dict[str, Any]:
        """Perform token-efficient search."""
        if max_tokens is None:
            max_tokens = self.config.max_context_tokens

        # Check cache first
        cache_key = self._get_cache_key(query, max_tokens)
        if self.config.enable_caching and cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < self.config.cache_ttl:
                return cached['result']

        # Perform search
        results = self.knowledge_db.search(query, limit=self.config.max_results)

        # Score and rank results
        scored_results = self._score_results(query, results)

        # Build context with token limit
        context = self._build_context(scored_results, max_tokens)

        result = {
            'query': query,
            'results': scored_results[:self.config.max_results],
            'context': context,
            'tokens_used': self._estimate_tokens(context),
            'compression_applied': len(context) < sum(len(r.get('content', '')) for r in results)
        }

        # Cache result
        if self.config.enable_caching:
            self.cache[cache_key] = {
                'timestamp': time.time(),
                'result': result
            }

        return result

    def _score_results(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score search results using hybrid semantic + text matching."""
        query_lower = query.lower()
        scored = []

        for result in results:
            content = result.get('content', '').lower()

            # Text similarity score
            text_score = 0
            query_words = set(query_lower.split())
            content_words = set(content.split())
            if query_words:
                text_score = len(query_words & content_words) / len(query_words)

            # Semantic score (simplified - in real implementation use embeddings)
            semantic_score = self._calculate_semantic_similarity(query_lower, content)

            # Combined score
            combined_score = (self.config.semantic_weight * semantic_score +
                            self.config.text_weight * text_score)

            result_copy = result.copy()
            result_copy['score'] = combined_score
            result_copy['text_score'] = text_score
            result_copy['semantic_score'] = semantic_score

            scored.append(result_copy)

        # Sort by combined score
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored

    def _calculate_semantic_similarity(self, query: str, content: str) -> float:
        """Calculate semantic similarity (simplified version)."""
        # This is a placeholder - real implementation would use embeddings
        # For now, use Jaccard similarity on word sets
        query_words = set(query.split())
        content_words = set(content.split())

        if not query_words or not content_words:
            return 0.0

        intersection = len(query_words & content_words)
        union = len(query_words | content_words)

        return intersection / union if union > 0 else 0.0

    def _build_context(self, results: List[Dict[str, Any]], max_tokens: int) -> str:
        """Build context string within token limit."""
        context_parts = []
        total_tokens = 0

        for result in results:
            content = result.get('content', '')

            # Compress if needed
            if total_tokens + self._estimate_tokens(content) > max_tokens:
                remaining_tokens = max_tokens - total_tokens
                if remaining_tokens > 100:  # Minimum useful content
                    content = self.compressor.compress_context(content, remaining_tokens)
                else:
                    break

            context_parts.append(content)
            total_tokens += self._estimate_tokens(content)

            if total_tokens >= max_tokens:
                break

        return '\n\n'.join(context_parts)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 1 token ≈ 0.75 words)."""
        words = len(text.split())
        return int(words * 1.33)  # Conservative estimate

    def _get_cache_key(self, query: str, max_tokens: int) -> str:
        """Generate cache key for query."""
        key_data = f"{query}:{max_tokens}:{self.config.compression_ratio}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear search cache."""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get search statistics."""
        return {
            'cache_size': len(self.cache),
            'config': self.config.__dict__
        }


# Global instance
_efficient_search = None

def get_efficient_search(workspace_root: Path = None) -> TokenEfficientSearch:
    """Get or create global efficient search instance."""
    global _efficient_search
    if _efficient_search is None and workspace_root:
        _efficient_search = TokenEfficientSearch(workspace_root)
    return _efficient_search


if __name__ == "__main__":
    # Test the efficient search
    search = TokenEfficientSearch(Path('.'))
    result = search.search("token optimization", max_tokens=2000)
    print(f"Search completed: {len(result['results'])} results, {result['tokens_used']} estimated tokens")
    print(f"Context length: {len(result['context'])} characters")
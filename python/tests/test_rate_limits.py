#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for rate limiting and embedding caching functionality
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch
from rate_limit_handler import RateLimitHandler, EmbeddingCache, RateLimitError
from token_monitor import TokenBudgetGuard, BudgetExceededError
from anthropic_direct import KeeperAgent


class TestRateLimitHandler:
    """Test exponential backoff and retry logic."""
    
    def test_successful_call(self, tmp_path):
        """Test that successful calls work normally."""
        handler = RateLimitHandler(tmp_path)
        
        def success_func():
            return "success"
        
        result = handler.call_with_retry(success_func)
        assert result == "success"
    
    def test_retry_on_rate_limit(self):
        """Test retry logic with rate limit errors."""
        handler = RateLimitHandler(max_retries=3)
        
        call_count = 0
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limited")
            return "success"
        
        result = handler.execute_with_backoff(failing_func)
        assert result == "success"
        assert call_count == 3
    
    def test_max_retries_exceeded(self):
        """Test that max retries are respected."""
        handler = RateLimitHandler(max_retries=2)
        
        call_count = 0
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise RateLimitError("Always fails")
        
        with pytest.raises(RateLimitError):
            handler.execute_with_backoff(always_fails)
        
        assert call_count == 3  # initial + 2 retries
    
    def test_exponential_backoff_timing(self):
        """Test that backoff delays increase exponentially."""
        handler = RateLimitHandler(max_retries=3, base_delay=0.1)
        
        delays = []
        def track_delays():
            nonlocal delays
            now = time.time()
            if delays:
                delays.append(now - delays[-1])
            else:
                delays.append(now)
            raise RateLimitError("Rate limited")
        
        with patch('time.sleep') as mock_sleep:
            try:
                handler.execute_with_backoff(track_delays)
            except RateLimitError:
                pass
        
        # Should have slept with increasing delays
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert len(sleep_calls) >= 2
        # Each delay should be >= previous (accounting for jitter)
        for i in range(1, len(sleep_calls)):
            assert sleep_calls[i] >= sleep_calls[i-1] * 0.5  # Allow some jitter


class TestEmbeddingCache:
    """Test embedding caching functionality."""
    
    def test_cache_miss_and_hit(self, tmp_path):
        """Test basic cache get/put operations."""
        cache = EmbeddingCache(tmp_path / "cache", max_size=10)
        
        content = "test content"
        embedding = [0.1, 0.2, 0.3]
        
        # Cache miss
        assert cache.get(content) is None
        
        # Cache put
        cache.put(content, embedding)
        
        # Cache hit
        cached = cache.get(content)
        assert cached == embedding
    
    def test_cache_size_limit(self, tmp_path):
        """Test that cache respects size limits."""
        cache = EmbeddingCache(tmp_path / "cache", max_size=2)
        
        # Add items beyond limit
        for i in range(5):
            cache.put(f"content{i}", [float(i)] * 10)
        
        # Should only keep recent items
        assert len(cache.index) <= 2
    
    def test_cache_persistence(self, tmp_path):
        """Test that cache persists across instances."""
        cache_dir = tmp_path / "cache"
        content = "persistent content"
        embedding = [0.5, 0.6, 0.7]
        
        # First instance
        cache1 = EmbeddingCache(cache_dir)
        cache1.put(content, embedding)
        
        # Second instance
        cache2 = EmbeddingCache(cache_dir)
        cached = cache2.get(content)
        assert cached == embedding


class TestTokenBudgetGuard:
    """Test token budget guard rails."""
    
    def test_budget_check_success(self):
        """Test successful budget check."""
        mock_tracker = Mock()
        mock_tracker.get_budget_status.return_value = {
            'tokens_used': 500,
            'budget_limit': 1000
        }
        
        guard = TokenBudgetGuard(mock_tracker)
        result = guard.check_budget(300)  # 80% usage
        
        assert result['can_proceed'] is True
        assert result['should_warn'] is True
        assert result['projected_usage'] == 800
    
    def test_budget_check_abort(self):
        """Test budget check that should abort."""
        mock_tracker = Mock()
        mock_tracker.get_budget_status.return_value = {
            'tokens_used': 950,
            'budget_limit': 1000
        }
        
        guard = TokenBudgetGuard(mock_tracker)
        
        with pytest.raises(BudgetExceededError):
            guard.check_budget(60)  # Would be 101% usage
    
    def test_safe_operation_limit(self):
        """Test calculation of safe operation limits."""
        mock_tracker = Mock()
        mock_tracker.get_budget_status.return_value = {
            'tokens_used': 800,
            'budget_limit': 1000
        }
        
        guard = TokenBudgetGuard(mock_tracker)
        limit = guard.get_safe_operation_limit(10)  # 10 tokens per operation
        
        # Should leave 20% buffer: (200 remaining) * 0.8 / 10 = 16
        assert limit == 16


class TestKeeperAgentEmbeddings:
    """Test embedding functionality in KeeperAgent."""
    
    def test_create_embedding_cached(self):
        """Test that embeddings are cached."""
        agent = KeeperAgent()
        
        # Mock the API call
        with patch.object(agent, '_create_embedding_api_call') as mock_api:
            mock_api.return_value = [0.1, 0.2, 0.3]
            
            # First call should hit API
            result1 = agent.create_embedding("test content")
            assert mock_api.call_count == 1
            
            # Second call should use cache
            result2 = agent.create_embedding("test content")
            assert mock_api.call_count == 1  # Still 1
            
            assert result1 == result2 == [0.1, 0.2, 0.3]
    
    def test_create_embeddings_batch(self):
        """Test batch embedding creation."""
        agent = KeeperAgent()
        
        texts = ["content1", "content2", "content3"]
        mock_embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        
        with patch.object(agent, '_create_embeddings_batch_api_call') as mock_batch:
            mock_batch.return_value = mock_embeddings
            
            results = agent.create_embeddings_batch(texts)
            
            assert results == mock_embeddings
            mock_batch.assert_called_once_with(texts, "claude-embedding-3")


class TestIntegration:
    """Integration tests for the complete rate limiting system."""
    
    def test_knowledge_db_with_rate_limiting(self, tmp_path):
        """Test KnowledgeDB rebuild with rate limiting."""
        from knowledge_db import KnowledgeDB
        
        # Create a test workspace
        test_workspace = tmp_path / "test_workspace"
        test_workspace.mkdir()
        
        # Create a mock report
        reports_dir = test_workspace / "reports"
        reports_dir.mkdir()
        report_file = reports_dir / "report_test_L001_v01.md"
        report_file.write_text("""
# TEST REPORT

## OBJECTIVE
Test report for rate limiting integration.

## IMPLEMENTATION
This is a test report.

## RESULTS
Success.
""")
        
        # Mock the anthropic agent to avoid real API calls
        with patch('knowledge_db.KeeperAgent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent.create_embedding.return_value = [0.1, 0.2, 0.3]
            mock_agent_class.return_value = mock_agent
            
            # Create DB and rebuild
            db = KnowledgeDB(test_workspace)
            
            # Should complete without errors
            stats = db.rebuild()
            
            assert stats['reports_indexed'] == 1
            # Should have called embedding creation
            mock_agent.create_embedding.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
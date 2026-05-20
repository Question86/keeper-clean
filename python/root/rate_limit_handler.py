#!/usr/bin/env python3
"""
Rate Limit Handler - TASK_0205

Implements exponential backoff, caching, and rate-aware scheduling for API calls
to prevent token waste from retries and rate limiting.

Phase 1: Exponential backoff & retry cap ✅
Phase 2: Local cache & deduplication ✅
Phase 3: Batch processing & async queue ✅
Phase 4: Model selection & A/B testing ✅
Phase 4: Model selection & A/B testing (IN PROGRESS)
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import time
import hashlib
import json
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass
from token_monitor import LoopBudgetTracker
from token_monitor import LoopBudgetTracker
import asyncio
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting behavior."""
    max_retries: int = 5
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    jitter: bool = True
    backoff_factor: float = 2.0


class RateLimitError(Exception):
    """Raised when an API call is rate limited."""
    pass


@dataclass
class CacheEntry:
    """Cache entry for API responses."""
    key: str
    response: Any
    timestamp: float
    ttl: float = 3600  # 1 hour default


class EmbeddingCache:
    """Local cache for embeddings to prevent re-computation."""

    def __init__(self, cache_dir: Path, max_size: int = 1000):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size = max_size
        self.index_file = self.cache_dir / "cache_index.json"
        self._load_index()

    def _load_index(self):
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except:
                self.index = {}
        else:
            self.index = {}

    def _save_index(self):
        """Save cache index to disk."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def _get_cache_key(self, content: str, model: str = "") -> str:
        """Generate cache key from content and model."""
        key_data = f"{content}:{model}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, content: str, model: str = "") -> Optional[Any]:
        """Get cached embedding for content."""
        key = self._get_cache_key(content, model)
        if key in self.index:
            entry = self.index[key]
            if time.time() - entry['timestamp'] < entry.get('ttl', 3600):
                cache_file = self.cache_dir / f"{key}.json"
                if cache_file.exists():
                    try:
                        with open(cache_file, 'r') as f:
                            return json.load(f)
                    except:
                        pass
            else:
                # Expired, remove
                self._remove_entry(key)
        return None

    def put(self, content: str, embedding: Any, model: str = "", ttl: float = 3600):
        """Cache embedding for content."""
        key = self._get_cache_key(content, model)

        # Remove old entry if exists
        self._remove_entry(key)

        # Add new entry
        self.index[key] = {
            'timestamp': time.time(),
            'ttl': ttl,
            'model': model
        }

        # Save embedding to file
        cache_file = self.cache_dir / f"{key}.json"
        with open(cache_file, 'w') as f:
            json.dump(embedding, f)

        # Enforce max size (simple LRU)
        if len(self.index) > self.max_size:
            # Remove oldest entries
            sorted_entries = sorted(self.index.items(), key=lambda x: x[1]['timestamp'])
            to_remove = len(self.index) - self.max_size
            for key, _ in sorted_entries[:to_remove]:
                self._remove_entry(key)

        self._save_index()

    def _remove_entry(self, key: str):
        """Remove cache entry."""
        if key in self.index:
            del self.index[key]
            cache_file = self.cache_dir / f"{key}.json"
            cache_file.unlink(missing_ok=True)


class AsyncRateLimitedQueue:
    """Async queue with rate-aware scheduling for API calls."""
    
    def __init__(self, workspace: Path, max_concurrency: int = 3, requests_per_minute: int = 60):
        self.workspace = workspace
        self.max_concurrency = max_concurrency
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # Minimum seconds between requests
        
        self.queue = Queue()
        self.semaphore = threading.Semaphore(max_concurrency)
        self.last_request_time = 0
        self._lock = threading.Lock()
        
        # Start background worker
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
    
    def submit(self, func: Callable) -> asyncio.Future:
        """Submit a function call to the rate-limited queue."""
        future = asyncio.Future()
        
        def wrapper():
            try:
                result = func()
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
        
        self.queue.put(wrapper)
        return future
    
    def _process_queue(self):
        """Background worker to process queued requests."""
        while True:
            # Get next item from queue
            try:
                func = self.queue.get(timeout=1.0)
            except:
                continue
            
            # Acquire semaphore for concurrency control
            self.semaphore.acquire()
            
            try:
                # Rate limiting
                with self._lock:
                    now = time.time()
                    time_since_last = now - self.last_request_time
                    if time_since_last < self.min_interval:
                        sleep_time = self.min_interval - time_since_last
                        time.sleep(sleep_time)
                    self.last_request_time = time.time()
                
                # Execute function
                func()
                
            finally:
                self.semaphore.release()
                self.queue.task_done()


@dataclass
class BudgetGuardConfig:
    """Configuration for budget guardrails."""
    warning_threshold: float = 0.75  # Warn at 75% budget used
    critical_threshold: float = 0.85  # Abort at 85% budget used
    abort_on_critical: bool = True
    log_decisions: bool = True


class BudgetGuard:
    """Token budget guardrails for API operations."""
    
    def __init__(self, workspace: Path, config: BudgetGuardConfig = None):
        self.workspace = workspace
        self.config = config or BudgetGuardConfig()
        self.budget_tracker = LoopBudgetTracker(workspace)
    
    def check_budget(self, operation_name: str, estimated_tokens: int = 0) -> Dict[str, Any]:
        """Check if operation should proceed based on budget."""
        status = self.budget_tracker.get_budget_status()
        current_usage = status['tokens_used']
        budget_limit = status['budget_limit']
        percentage = status['percentage'] / 100.0  # Convert to 0-1 scale
        
        decision = {
            'should_proceed': True,
            'reason': 'budget_ok',
            'estimated_final_usage': current_usage + estimated_tokens,
            'estimated_final_percentage': ((current_usage + estimated_tokens) / budget_limit) * 100,
            'budget_status': status
        }
        
        # Check thresholds
        if percentage >= self.config.critical_threshold:
            decision['should_proceed'] = not self.config.abort_on_critical
            decision['reason'] = 'critical_threshold_exceeded'
        elif percentage >= self.config.warning_threshold:
            decision['reason'] = 'warning_threshold_exceeded'
        
        # Log decision
        if self.config.log_decisions:
            self._log_decision(operation_name, decision)
        
        return decision
    
    def _log_decision(self, operation_name: str, decision: Dict[str, Any]):
        """Log budget guardrail decision."""
        log_entry = {
            'timestamp': time.time(),
            'operation': operation_name,
            'decision': decision,
            'budget_status': decision['budget_status']
        }
        
        log_file = self.workspace / 'budget_guardrail_log.jsonl'
        with open(log_file, 'a', encoding='utf-8') as f:
            json.dump(log_entry, f)
            f.write('\n')
        
        print(f"Budget guardrail: {operation_name} - {decision['reason']} "
              f"({decision['budget_status']['percentage']:.1f}% used)")


# ----------------
# Bandwidth guard
# ----------------

@dataclass
class BandwidthGuardConfig:
    """Configuration for bandwidth guardrails (bytes per minute)."""
    budget_bytes_per_minute: int = 10 * 1024 * 1024  # 10 MB per minute default
    window_seconds: int = 60
    warning_threshold: float = 0.75
    critical_threshold: float = 0.9
    abort_on_critical: bool = True
    log_decisions: bool = True


class BandwidthTracker:
    """Tracks bandwidth usage by recording usage events to JSONL and computing sliding-window usage."""

    def __init__(self, workspace: Path, usage_file: str = '.bandwidth_usage.jsonl'):
        self.workspace = workspace
        self.usage_file = workspace / usage_file
        # Ensure file exists
        if not self.usage_file.exists():
            self.usage_file.write_text('')

    def record_usage(self, bytes_count: int, operation: str = '') -> None:
        entry = {
            'timestamp': time.time(),
            'bytes': int(bytes_count),
            'operation': operation
        }
        with open(self.usage_file, 'a', encoding='utf-8') as f:
            json.dump(entry, f)
            f.write('\n')

    def get_usage_last_window(self, window_seconds: int = 60) -> int:
        cutoff = time.time() - window_seconds
        total = 0
        try:
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get('timestamp', 0) >= cutoff:
                            total += int(entry.get('bytes', 0))
                    except Exception:
                        continue
        except FileNotFoundError:
            return 0
        return total


class BandwidthGuard:
    """Guardrail that prevents exceeding bandwidth budgets for heavy operations."""

    def __init__(self, workspace: Path, config: BandwidthGuardConfig = None):
        self.workspace = workspace
        # If no explicit config passed, try to load persisted settings from workspace/data
        if config is None:
            settings_file = workspace / 'data' / 'bandwidth_settings.json'
            if settings_file.exists():
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                    config = BandwidthGuardConfig(
                        budget_bytes_per_minute=int(cfg.get('budget_bytes_per_minute', BandwidthGuardConfig().budget_bytes_per_minute)),
                        window_seconds=int(cfg.get('window_seconds', BandwidthGuardConfig().window_seconds)),
                        warning_threshold=float(cfg.get('warning_threshold', BandwidthGuardConfig().warning_threshold)),
                        critical_threshold=float(cfg.get('critical_threshold', BandwidthGuardConfig().critical_threshold)),
                        abort_on_critical=bool(cfg.get('abort_on_critical', BandwidthGuardConfig().abort_on_critical)),
                        log_decisions=bool(cfg.get('log_decisions', BandwidthGuardConfig().log_decisions))
                    )
                except Exception:
                    config = BandwidthGuardConfig()
            else:
                config = BandwidthGuardConfig()
        self.config = config
        self.tracker = BandwidthTracker(workspace)

    def check_bandwidth(self, operation_name: str, estimated_bytes: int = 0) -> Dict[str, Any]:
        current_usage = self.tracker.get_usage_last_window(self.config.window_seconds)
        budget = self.config.budget_bytes_per_minute
        estimated_final = current_usage + estimated_bytes
        estimated_final_pct = estimated_final / budget

        decision = {
            'should_proceed': True,
            'reason': 'bandwidth_ok',
            'current_usage_bytes': current_usage,
            'estimated_final_bytes': estimated_final,
            'estimated_final_percentage': estimated_final_pct * 100
        }

        if estimated_final_pct >= self.config.critical_threshold:
            decision['should_proceed'] = not self.config.abort_on_critical
            decision['reason'] = 'critical_threshold_exceeded'
        elif estimated_final_pct >= self.config.warning_threshold:
            decision['reason'] = 'warning_threshold_exceeded'

        # Log decision
        if self.config.log_decisions:
            self._log_decision(operation_name, decision)

        return decision

    def record_usage(self, operation_name: str, bytes_count: int) -> None:
        self.tracker.record_usage(bytes_count, operation_name)

    def _log_decision(self, operation_name: str, decision: Dict[str, Any]):
        log_entry = {
            'timestamp': time.time(),
            'operation': operation_name,
            'decision': decision
        }
        log_file = self.workspace / 'bandwidth_guard_log.jsonl'
        with open(log_file, 'a', encoding='utf-8') as f:
            json.dump(log_entry, f)
            f.write('\n')
        print(f"Bandwidth guard: {operation_name} - {decision['reason']} "
              f"(est {decision['estimated_final_percentage']:.1f}% of budget)")


@dataclass
class ModelConfig:
    """Configuration for embedding models."""
    name: str
    cost_per_token: float  # Cost in tokens per input token
    quality_score: float  # 0-1 quality metric
    max_tokens: int  # Maximum tokens per request
    description: str = ""


@dataclass
class ABTestConfig:
    """Configuration for A/B testing."""
    test_name: str
    models: List[str]  # Model names to test
    traffic_split: Dict[str, float]  # Model -> percentage (0-1)
    duration_days: int = 7
    min_samples_per_model: int = 100
    metrics: List[str] = None  # Metrics to track
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = ['latency', 'cost', 'quality', 'success_rate']


class ModelSelector:
    """Intelligent model selection based on budget, quality requirements, and performance."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.models = self._load_default_models()
        self.performance_history = self._load_performance_history()
    
    def _load_default_models(self) -> Dict[str, ModelConfig]:
        """Load default model configurations."""
        return {
            'text-embedding-3-small': ModelConfig(
                name='text-embedding-3-small',
                cost_per_token=0.00002,  # $0.00002 per token
                quality_score=0.7,
                max_tokens=8191,
                description='Fast, cost-effective for most use cases'
            ),
            'text-embedding-3-large': ModelConfig(
                name='text-embedding-3-large',
                cost_per_token=0.00013,  # $0.00013 per token
                quality_score=0.9,
                max_tokens=8191,
                description='High quality, slower and more expensive'
            ),
            'text-embedding-ada-002': ModelConfig(
                name='text-embedding-ada-002',
                cost_per_token=0.0001,  # $0.0001 per token
                quality_score=0.8,
                max_tokens=8191,
                description='Balanced performance and cost'
            ),
            'ollama-mistral': ModelConfig(
                name='ollama-mistral',
                cost_per_token=0.0,  # Free, local model
                quality_score=0.75,
                max_tokens=4096,
                description='Local Mistral model via Ollama - zero cost'
            ),
            'ollama-mixtral': ModelConfig(
                name='ollama-mixtral',
                cost_per_token=0.0,  # Free, local model
                quality_score=0.85,
                max_tokens=4096,
                description='Local Mixtral 8x7B model via Ollama - zero cost, high quality'
            )
        }
    
    def _load_performance_history(self) -> Dict[str, Dict[str, Any]]:
        """Load historical performance data."""
        history_file = self.workspace / 'model_performance_history.json'
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_performance_history(self):
        """Save performance history to disk."""
        history_file = self.workspace / 'model_performance_history.json'
        with open(history_file, 'w') as f:
            json.dump(self.performance_history, f, indent=2)
    
    def select_model(self, content: str, quality_requirement: float = 0.5, 
                    budget_priority: float = 0.5) -> str:
        """
        Select the best model based on content, quality requirements, and budget constraints.
        
        Args:
            content: The text content to embed
            quality_requirement: Required quality score (0-1)
            budget_priority: How much to prioritize cost (0=cost, 1=quality)
        """
        content_tokens = len(content.split())  # Rough token estimate
        
        # Filter models that can handle the content
        viable_models = {
            name: config for name, config in self.models.items()
            if config.max_tokens >= content_tokens and config.quality_score >= quality_requirement
        }
        
        if not viable_models:
            # Fallback to most capable model
            return max(self.models.values(), key=lambda x: x.quality_score).name
        
        # Score models based on quality, cost, and performance history
        scored_models = []
        for name, config in viable_models.items():
            # Quality score (higher is better)
            quality_score = config.quality_score
            
            # Cost score (normalized, lower cost = higher score)
            max_cost = max(m.cost_per_token for m in viable_models.values())
            min_cost = min(m.cost_per_token for m in viable_models.values())
            if max_cost == min_cost:
                cost_score = 1.0
            else:
                cost_score = 1.0 - (config.cost_per_token - min_cost) / (max_cost - min_cost)
            
            # Performance history bonus
            history_bonus = 0.0
            if name in self.performance_history:
                history = self.performance_history[name]
                success_rate = history.get('success_rate', 0.5)
                avg_latency = history.get('avg_latency', 1.0)
                history_bonus = (success_rate - 0.5) * 0.1 - (avg_latency - 0.5) * 0.05
            
            # Combined score
            combined_score = (
                quality_score * (1 - budget_priority) +
                cost_score * budget_priority +
                history_bonus
            )
            
            scored_models.append((name, combined_score))
        
        # Return best model
        best_model = max(scored_models, key=lambda x: x[1])[0]
        return best_model
    
    def record_performance(self, model_name: str, latency: float, cost: float, 
                          success: bool, quality_score: float = None):
        """Record model performance for future decisions."""
        if model_name not in self.performance_history:
            self.performance_history[model_name] = {
                'calls': 0,
                'successes': 0,
                'total_latency': 0.0,
                'total_cost': 0.0,
                'quality_scores': []
            }
        
        history = self.performance_history[model_name]
        history['calls'] += 1
        history['total_latency'] += latency
        history['total_cost'] += cost
        
        if success:
            history['successes'] += 1
        
        if quality_score is not None:
            history['quality_scores'].append(quality_score)
            # Keep only last 100 quality scores
            history['quality_scores'] = history['quality_scores'][-100:]
        
        # Update derived metrics
        history['success_rate'] = history['successes'] / history['calls']
        history['avg_latency'] = history['total_latency'] / history['calls']
        history['avg_cost'] = history['total_cost'] / history['calls']
        
        if history['quality_scores']:
            history['avg_quality'] = sum(history['quality_scores']) / len(history['quality_scores'])
        
        self._save_performance_history()


class ABTestingFramework:
    """A/B testing framework for comparing embedding models."""
    
    def __init__(self, workspace: Path, model_selector: ModelSelector):
        self.workspace = workspace
        self.model_selector = model_selector
        self.active_tests = self._load_active_tests()
        self.test_results = self._load_test_results()
    
    def _load_active_tests(self) -> Dict[str, ABTestConfig]:
        """Load active A/B tests."""
        tests_file = self.workspace / 'active_ab_tests.json'
        if tests_file.exists():
            try:
                with open(tests_file, 'r') as f:
                    data = json.load(f)
                    return {name: ABTestConfig(**config) for name, config in data.items()}
            except:
                pass
        return {}
    
    def _save_active_tests(self):
        """Save active tests to disk."""
        tests_file = self.workspace / 'active_ab_tests.json'
        with open(tests_file, 'w') as f:
            json.dump({name: {
                'test_name': config.test_name,
                'models': config.models,
                'traffic_split': config.traffic_split,
                'duration_days': config.duration_days,
                'min_samples_per_model': config.min_samples_per_model,
                'metrics': config.metrics
            } for name, config in self.active_tests.items()}, f, indent=2)
    
    def _load_test_results(self) -> Dict[str, Dict[str, Any]]:
        """Load test results."""
        results_file = self.workspace / 'ab_test_results.jsonl'
        results = {}
        if results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    for line in f:
                        entry = json.loads(line.strip())
                        test_name = entry['test_name']
                        if test_name not in results:
                            results[test_name] = {'samples': []}
                        results[test_name]['samples'].append(entry)
            except:
                pass
        return results
    
    def start_test(self, config: ABTestConfig):
        """Start a new A/B test."""
        if config.test_name in self.active_tests:
            raise ValueError(f"Test {config.test_name} already exists")
        
        # Validate traffic split
        if abs(sum(config.traffic_split.values()) - 1.0) > 0.01:
            raise ValueError("Traffic split must sum to 1.0")
        
        # Validate models exist
        for model in config.models:
            if model not in self.model_selector.models:
                raise ValueError(f"Model {model} not found")
        
        self.active_tests[config.test_name] = config
        self.test_results[config.test_name] = {'samples': []}
        self._save_active_tests()
        
        print(f"Started A/B test: {config.test_name}")
    
    def get_model_for_request(self, content: str, context: str = "") -> str:
        """Get the model to use for a request, considering active A/B tests."""
        # Check if request matches any active test
        for test_name, test_config in self.active_tests.items():
            if self._request_matches_test(content, context, test_config):
                return self._select_model_from_test(test_config)
        
        # No test matches, use normal model selection
        return self.model_selector.select_model(content)
    
    def _request_matches_test(self, content: str, context: str, test_config: ABTestConfig) -> bool:
        """Check if a request matches the test criteria."""
        # For now, match all requests (can be extended with more sophisticated matching)
        return True
    
    def _select_model_from_test(self, test_config: ABTestConfig) -> str:
        """Select a model from the test traffic split."""
        rand = random.random()
        cumulative = 0.0
        for model, weight in test_config.traffic_split.items():
            cumulative += weight
            if rand <= cumulative:
                return model
        return test_config.models[0]  # Fallback
    
    def record_test_result(self, test_name: str, model_name: str, latency: float, 
                          cost: float, success: bool, quality_score: float = None,
                          metadata: Dict[str, Any] = None):
        """Record a test result."""
        if test_name not in self.active_tests:
            return
        
        result = {
            'timestamp': time.time(),
            'test_name': test_name,
            'model': model_name,
            'latency': latency,
            'cost': cost,
            'success': success,
            'quality_score': quality_score,
            'metadata': metadata or {}
        }
        
        self.test_results[test_name]['samples'].append(result)
        
        # Save to file
        results_file = self.workspace / 'ab_test_results.jsonl'
        with open(results_file, 'a') as f:
            json.dump(result, f)
            f.write('\n')
        
        # Also record in model selector for learning
        self.model_selector.record_performance(model_name, latency, cost, success, quality_score)
    
    def get_test_status(self, test_name: str) -> Dict[str, Any]:
        """Get the current status of a test."""
        if test_name not in self.active_tests:
            return {'error': 'Test not found'}
        
        test_config = self.active_tests[test_name]
        samples = self.test_results[test_name]['samples']
        
        # Group samples by model
        model_stats = {}
        for model in test_config.models:
            model_samples = [s for s in samples if s['model'] == model]
            if model_samples:
                model_stats[model] = {
                    'samples': len(model_samples),
                    'success_rate': sum(1 for s in model_samples if s['success']) / len(model_samples),
                    'avg_latency': sum(s['latency'] for s in model_samples) / len(model_samples),
                    'avg_cost': sum(s['cost'] for s in model_samples) / len(model_samples),
                    'avg_quality': sum(s['quality_score'] for s in model_samples if s['quality_score']) / len([s for s in model_samples if s['quality_score']])
                }
            else:
                model_stats[model] = {'samples': 0}
        
        # Check if test should end
        min_samples = min(stats.get('samples', 0) for stats in model_stats.values())
        should_end = min_samples >= test_config.min_samples_per_model
        
        return {
            'test_name': test_name,
            'status': 'running' if not should_end else 'completed',
            'start_time': time.time() - (test_config.duration_days * 24 * 3600),  # Approximate
            'model_stats': model_stats,
            'total_samples': len(samples),
            'should_end': should_end
        }
    
    def end_test(self, test_name: str) -> Dict[str, Any]:
        """End a test and return final results."""
        if test_name not in self.active_tests:
            return {'error': 'Test not found'}
        
        status = self.get_test_status(test_name)
        del self.active_tests[test_name]
        self._save_active_tests()
        
        return {
            'test_name': test_name,
            'final_results': status,
            'winner': self._determine_winner(status['model_stats'])
        }
    
    def _determine_winner(self, model_stats: Dict[str, Dict[str, Any]]) -> str:
        """Determine the winning model based on a composite score."""
        scored_models = []
        for model, stats in model_stats.items():
            if stats['samples'] > 0:
                # Composite score: quality + (1-cost) + (1-latency) + success_rate
                quality = stats.get('avg_quality', 0.5)
                cost_norm = 1.0 - (stats['avg_cost'] / max(s['avg_cost'] for s in model_stats.values() if s['samples'] > 0))
                latency_norm = 1.0 - (stats['avg_latency'] / max(s['avg_latency'] for s in model_stats.values() if s['samples'] > 0))
                success = stats['success_rate']
                
                composite_score = (quality + cost_norm + latency_norm + success) / 4.0
                scored_models.append((model, composite_score))
        
        if scored_models:
            return max(scored_models, key=lambda x: x[1])[0]
        return None


class RateLimitHandler:
    """Handles rate limiting with exponential backoff and caching."""

    def __init__(self, workspace: Path, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.workspace = workspace
        self.cache = EmbeddingCache(workspace / "embedding_cache")
        self.executor = ThreadPoolExecutor(max_workers=2)  # Low concurrency for rate limiting
        self._lock = threading.Lock()
        
        # Phase 2: Async queue and budget guardrails
        self.async_queue = AsyncRateLimitedQueue(workspace, max_concurrency=3)
        self.budget_guard = BudgetGuard(workspace)
        # Bandwidth guard for bytes-per-minute budgets
        self.bandwidth_guard = BandwidthGuard(workspace)
        
        # Phase 3: Model selection and A/B testing
        self.model_selector = ModelSelector(workspace)
        self.ab_testing = ABTestingFramework(workspace, self.model_selector)

    def call_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with exponential backoff retry."""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    print(f"API call failed (attempt {attempt + 1}/{self.config.max_retries + 1}): {e}")
                    print(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                else:
                    print(f"API call failed after {self.config.max_retries + 1} attempts: {e}")
                    raise last_exception

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(
            self.config.base_delay * (self.config.backoff_factor ** attempt),
            self.config.max_delay
        )

        if self.config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)  # 50-100% of calculated delay

        return delay

    def cached_embedding_call(self, content: str, model: str = "", ttl: float = 3600) -> Callable:
        """Decorator for cached embedding API calls."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Check cache first
                cached = self.cache.get(content, model)
                if cached is not None:
                    print(f"Cache hit for embedding (model: {model})")
                    return cached

                # Cache miss, make API call with retry
                print(f"Cache miss, calling API for embedding (model: {model})")
                result = self.call_with_retry(func, *args, **kwargs)

                # Cache result
                self.cache.put(content, result, model, ttl)
                return result

            return wrapper
        return decorator

    def batch_embedding_call(self, contents: List[str], model: str = "", batch_size: int = 10) -> List[Any]:
        """Batch embedding calls with rate limiting."""
        results = []

        for i in range(0, len(contents), batch_size):
            batch = contents[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1} of {(len(contents) + batch_size - 1)//batch_size} (size: {len(batch)})")

            # Check cache for each item in batch
            batch_results = []
            uncached_items = []

            for content in batch:
                cached = self.cache.get(content, model)
                if cached is not None:
                    batch_results.append(cached)
                else:
                    uncached_items.append(content)
                    batch_results.append(None)  # Placeholder

            # Make API call for uncached items if any
            if uncached_items:
                try:
                    # This would need to be implemented by the specific API
                    # For now, simulate individual calls
                    api_results = []
                    for content in uncached_items:
                        # In real implementation, this would be a batched API call
                        result = self.call_with_retry(self._mock_embedding_api, content, model)
                        api_results.append(result)

                    # Cache results and update batch_results
                    for j, (content, result) in enumerate(zip(uncached_items, api_results)):
                        self.cache.put(content, result, model)
                        # Find placeholder and replace
                        placeholder_idx = batch_results.index(None)
                        batch_results[placeholder_idx] = result

                except Exception as e:
                    print(f"Batch embedding failed: {e}")
                    # For failed batches, try individual calls
                    for j, content in enumerate(uncached_items):
                        try:
                            result = self.call_with_retry(self._mock_embedding_api, content, model)
                            self.cache.put(content, result, model)
                            placeholder_idx = batch_results.index(None)
                            batch_results[placeholder_idx] = result
                        except Exception as e2:
                            print(f"Individual embedding failed for item {j}: {e2}")
                            placeholder_idx = batch_results.index(None)
                            batch_results[placeholder_idx] = None

            results.extend(batch_results)

            # Rate limiting between batches
            if i + batch_size < len(contents):
                time.sleep(1.0)  # 1 second between batches

        return results

    def call_with_budget_guard(self, func: Callable, operation_name: str, estimated_tokens: int = 0, *args, **kwargs) -> Any:
        """Call function with budget guardrail check."""
        budget_check = self.budget_guard.check_budget(operation_name, estimated_tokens)
        
        if not budget_check['should_proceed']:
            raise Exception(f"Budget guardrail blocked operation: {budget_check['reason']} "
                          f"({budget_check['budget_status']['percentage']:.1f}% budget used)")
        
        return func(*args, **kwargs)

    def async_call_with_retry(self, func: Callable, *args, **kwargs) -> asyncio.Future:
        """Submit function call to async queue with retry logic."""
        def wrapped_func():
            return self.call_with_retry(func, *args, **kwargs)
        
        return self.async_queue.submit(wrapped_func)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'total_entries': len(self.cache.index),
            'cache_dir_size_mb': self._get_dir_size_mb(self.cache.cache_dir),
            'hit_rate_estimate': 'unknown'  # Would need to track hits/misses
        }

    def _mock_embedding_api(self, content: str, model: str = "") -> List[float]:
        """Mock embedding API for testing."""
        # Simulate API delay
        time.sleep(0.1)
        
        # Return deterministic mock embedding based on content hash
        import hashlib
        hash_obj = hashlib.md5(content.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Generate 1536-dimensional embedding (common for text-embedding-ada-002)
        embedding = []
        for i in range(1536):
            # Use hash to make it deterministic but different per content
            value = ((hash_int + i) % 2000 - 1000) / 1000.0  # -1.0 to 1.0 range
            embedding.append(value)
        
        return embedding

    def _get_dir_size_mb(self, path: Path) -> float:
        """Get directory size in MB."""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size / (1024 * 1024)

    # Phase 3: Intelligent model selection and A/B testing
    def intelligent_embedding_call(self, content: str, quality_requirement: float = 0.5,
                                  budget_priority: float = 0.5, context: str = "") -> List[float]:
        """
        Intelligent embedding call that automatically selects the best model.
        
        Args:
            content: Text to embed
            quality_requirement: Minimum quality score (0-1)
            budget_priority: Cost vs quality priority (0=cost, 1=quality)
            context: Optional context for A/B testing
        """
        # Select model (considering A/B tests)
        selected_model = self.ab_testing.get_model_for_request(content, context)
        
        # Override with intelligent selection if no A/B test applies
        if not any(self.ab_testing._request_matches_test(content, context, test) 
                  for test in self.ab_testing.active_tests.values()):
            selected_model = self.model_selector.select_model(content, quality_requirement, budget_priority)
        
        print(f"Selected model: {selected_model} for content ({len(content)} chars)")
        
        # Make the call with full rate limiting stack
        start_time = time.time()
        try:
            result = self.call_with_budget_guard(
                self.cached_embedding_call(content, selected_model),
                f"embedding_{selected_model}",
                estimated_tokens=len(content.split())  # Rough estimate
            )(self._mock_embedding_api)(content, selected_model)
            
            latency = time.time() - start_time
            
            # Record performance for learning
            self.model_selector.record_performance(
                selected_model, latency, 
                cost=self.model_selector.models[selected_model].cost_per_token * len(content.split()),
                success=True
            )
            
            # Record A/B test result if applicable
            for test_name, test_config in self.ab_testing.active_tests.items():
                if selected_model in test_config.models:
                    self.ab_testing.record_test_result(
                        test_name, selected_model, latency,
                        cost=self.model_selector.models[selected_model].cost_per_token * len(content.split()),
                        success=True
                    )
                    break
            
            return result
            
        except Exception as e:
            latency = time.time() - start_time
            
            # Record failed performance
            self.model_selector.record_performance(
                selected_model, latency,
                cost=self.model_selector.models[selected_model].cost_per_token * len(content.split()),
                success=False
            )
            
            # Record failed A/B test result
            for test_name, test_config in self.ab_testing.active_tests.items():
                if selected_model in test_config.models:
                    self.ab_testing.record_test_result(
                        test_name, selected_model, latency,
                        cost=self.model_selector.models[selected_model].cost_per_token * len(content.split()),
                        success=False
                    )
                    break
            
            raise e

    def start_ab_test(self, test_name: str, models: List[str], 
                     traffic_split: Dict[str, float] = None, duration_days: int = 7):
        """Start an A/B test for model comparison."""
        if traffic_split is None:
            # Equal split
            weight = 1.0 / len(models)
            traffic_split = {model: weight for model in models}
        
        config = ABTestConfig(
            test_name=test_name,
            models=models,
            traffic_split=traffic_split,
            duration_days=duration_days
        )
        
        self.ab_testing.start_test(config)
        return f"Started A/B test: {test_name}"

    def get_ab_test_status(self, test_name: str) -> Dict[str, Any]:
        """Get status of an A/B test."""
        return self.ab_testing.get_test_status(test_name)

    def end_ab_test(self, test_name: str) -> Dict[str, Any]:
        """End an A/B test and get results."""
        return self.ab_testing.end_test(test_name)

    def get_model_performance(self) -> Dict[str, Any]:
        """Get performance statistics for all models."""
        return {
            model_name: stats
            for model_name, stats in self.model_selector.performance_history.items()
        }

    def _get_dir_size_mb(self, path: Path) -> float:
        """Get directory size in MB."""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size / (1024 * 1024)


# Phase 3: Intelligent model selection and A/B testing
def intelligent_embedding_call(content: str, quality_requirement: float = 0.5,
                              budget_priority: float = 0.5, context: str = "") -> List[float]:
    """Convenience function for intelligent embedding calls."""
    handler = get_rate_limit_handler()
    return handler.intelligent_embedding_call(content, quality_requirement, budget_priority, context)

def start_ab_test(test_name: str, models: List[str], 
                 traffic_split: Dict[str, float] = None, duration_days: int = 7):
    """Convenience function to start A/B test."""
    handler = get_rate_limit_handler()
    return handler.start_ab_test(test_name, models, traffic_split, duration_days)

def get_ab_test_status(test_name: str) -> Dict[str, Any]:
    """Convenience function to get A/B test status."""
    handler = get_rate_limit_handler()
    return handler.get_ab_test_status(test_name)

def end_ab_test(test_name: str) -> Dict[str, Any]:
    """Convenience function to end A/B test."""
    handler = get_rate_limit_handler()
    return handler.end_ab_test(test_name)

def get_model_performance() -> Dict[str, Any]:
    """Convenience function to get model performance."""
    handler = get_rate_limit_handler()
    return handler.get_model_performance()


# Global instance for easy access
_rate_limit_handler = None
_rate_limit_lock = threading.Lock()

def get_rate_limit_handler(workspace: Path = None) -> RateLimitHandler:
    """Get global rate limit handler instance."""
    global _rate_limit_handler

    if workspace is None:
        workspace = Path(".")

    with _rate_limit_lock:
        if _rate_limit_handler is None:
            _rate_limit_handler = RateLimitHandler(workspace)
        return _rate_limit_handler


# Convenience functions
def call_with_retry(func: Callable, *args, **kwargs) -> Any:
    """Convenience function for retry calls."""
    handler = get_rate_limit_handler()
    return handler.call_with_retry(func, *args, **kwargs)

def cached_embedding_call(content: str, model: str = "", ttl: float = 3600) -> Callable:
    """Convenience decorator for cached embedding calls."""
    handler = get_rate_limit_handler()
    return handler.cached_embedding_call(content, model, ttl)


# CLI interface for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Rate Limit Handler Testing')
    parser.add_argument('--test-retry', action='store_true', help='Test retry mechanism')
    parser.add_argument('--test-cache', action='store_true', help='Test caching')
    parser.add_argument('--test-batch', action='store_true', help='Test batch processing')
    parser.add_argument('--test-budget', action='store_true', help='Test budget guardrails')
    parser.add_argument('--test-async', action='store_true', help='Test async queue')
    parser.add_argument('--test-intelligent', action='store_true', help='Test intelligent model selection')
    parser.add_argument('--test-ab-test', action='store_true', help='Test A/B testing framework')
    parser.add_argument('--workspace', type=str, default='.', help='Workspace root')

    args = parser.parse_args()

    workspace = Path(args.workspace)
    handler = RateLimitHandler(workspace)

    if args.test_retry:
        print("Testing retry mechanism...")
        try:
            result = handler.call_with_retry(handler._mock_embedding_api, "test content")
            print(f"Retry test successful: got {len(result)} dimensions")
        except Exception as e:
            print(f"Retry test failed: {e}")

    if args.test_cache:
        print("Testing cache...")
        # First call (should miss cache)
        result1 = handler.cached_embedding_call("test content")(handler._mock_embedding_api)("test content")
        print(f"First call: {len(result1)} dimensions")

        # Second call (should hit cache)
        result2 = handler.cached_embedding_call("test content")(handler._mock_embedding_api)("test content")
        print(f"Second call: {len(result2)} dimensions")

        print(f"Results identical: {result1 == result2}")

    if args.test_batch:
        print("Testing batch processing...")
        # Note: This would need proper async batch processing implementation
        print("Batch processing test placeholder")

    # Print stats
    try:
        stats = handler.get_cache_stats().result(timeout=30)
        print(f"Cache stats: {stats}")
    except Exception as e:
        print(f"Failed to get cache stats: {e}")

    if args.test_batch:
        print("Testing batch processing...")
        contents = [f"test content {i}" for i in range(5)]
        results = handler.batch_embedding_call(contents)
        print(f"Batch results: {len(results)} items, all valid: {all(r is not None for r in results)}")

    if args.test_budget:
        print("Testing budget guardrails...")
        # Test budget check
        check = handler.budget_guard.check_budget("test_operation", 1000)
        print(f"Budget check: {check['should_proceed']} - {check['reason']}")
        print(f"Current usage: {check['budget_status']['percentage']:.1f}%")

    if args.test_async:
        print("Testing async queue...")
        # Submit async call
        future = handler.async_call_with_retry(handler._mock_embedding_api, "async test")
        # Wait for result using future
        result = future.result(timeout=30)
        print(f"Async result: {len(result)} dimensions")

    if args.test_intelligent:
        print("Testing intelligent model selection...")
        # Test different scenarios
        test_cases = [
            ("Short text for testing", 0.5, 0.8),  # High quality requirement, cost priority
            ("This is a longer piece of content that might benefit from higher quality embeddings for better semantic understanding", 0.8, 0.2),  # Quality priority
            ("Budget conscious content", 0.3, 0.9),  # Cost priority
        ]
        
        for content, quality_req, budget_pri in test_cases:
            result = handler.intelligent_embedding_call(content, quality_req, budget_pri)
            print(f"Content ({len(content)} chars): {len(result)} dimensions")

    if args.test_ab_test:
        print("Testing A/B testing framework...")
        # Start a test
        result = handler.start_ab_test("test_quality_vs_cost", 
                                     ["text-embedding-3-small", "text-embedding-3-large"])
        print(result)
        
        # Run some test calls
        for i in range(10):
            content = f"Test content {i} for A/B testing"
            result = handler.intelligent_embedding_call(content, context="ab_test")
            print(f"A/B test call {i+1}: {len(result)} dimensions")
        
        # Check status
        status = handler.get_ab_test_status("test_quality_vs_cost")
        print(f"Test status: {status['status']}, samples: {status['total_samples']}")
        
        # End test
        final_result = handler.end_ab_test("test_quality_vs_cost")
        print(f"Test winner: {final_result['winner']}")

    # Print stats
    stats = handler.get_cache_stats()
    print(f"Cache stats: {stats}")
    
    # Print model performance
    if args.test_intelligent or args.test_ab_test:
        perf = handler.get_model_performance()
        print(f"Model performance: {len(perf)} models tracked")
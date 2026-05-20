#!/usr/bin/env python3
"""
Rate Limit Handler - TASK_0205 (Phase 3: Model Selection & A/B Testing)
Minimal working version for testing Phase 3 functionality.
"""

import time
import json
import random
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ModelConfig:
    name: str
    cost_per_token: float
    quality_score: float
    max_tokens: int
    description: str = ""

@dataclass
class ABTestConfig:
    test_name: str
    models: List[str]
    traffic_split: Dict[str, float]
    duration_days: int = 7
    min_samples_per_model: int = 100
    metrics: List[str] = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = ['latency', 'cost', 'quality', 'success_rate']

class ModelSelector:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.models = self._load_default_models()
        self.performance_history = {}

    def _load_default_models(self):
        return {
            'text-embedding-3-small': ModelConfig(
                name='text-embedding-3-small',
                cost_per_token=0.00002,
                quality_score=0.7,
                max_tokens=8191,
                description='Fast, cost-effective'
            ),
            'text-embedding-3-large': ModelConfig(
                name='text-embedding-3-large',
                cost_per_token=0.00013,
                quality_score=0.9,
                max_tokens=8191,
                description='High quality, expensive'
            ),
            'text-embedding-ada-002': ModelConfig(
                name='text-embedding-ada-002',
                cost_per_token=0.0001,
                quality_score=0.8,
                max_tokens=8191,
                description='Balanced'
            )
        }

    def select_model(self, content: str, quality_requirement: float = 0.5,
                    budget_priority: float = 0.5) -> str:
        viable_models = {
            name: config for name, config in self.models.items()
            if config.quality_score >= quality_requirement
        }

        if not viable_models:
            return max(self.models.values(), key=lambda x: x.quality_score).name

        scored_models = []
        for name, config in viable_models.items():
            quality_score = config.quality_score
            max_cost = max(m.cost_per_token for m in viable_models.values())
            min_cost = min(m.cost_per_token for m in viable_models.values())
            cost_score = 1.0 - (config.cost_per_token - min_cost) / (max_cost - min_cost) if max_cost != min_cost else 1.0

            combined_score = quality_score * (1 - budget_priority) + cost_score * budget_priority
            scored_models.append((name, combined_score))

        return max(scored_models, key=lambda x: x[1])[0]

    def record_performance(self, model_name: str, latency: float, cost: float, success: bool):
        if model_name not in self.performance_history:
            self.performance_history[model_name] = {'calls': 0, 'successes': 0, 'total_latency': 0.0, 'total_cost': 0.0}

        history = self.performance_history[model_name]
        history['calls'] += 1
        history['total_latency'] += latency
        history['total_cost'] += cost
        if success:
            history['successes'] += 1

        history['success_rate'] = history['successes'] / history['calls']
        history['avg_latency'] = history['total_latency'] / history['calls']
        history['avg_cost'] = history['total_cost'] / history['calls']

class ABTestingFramework:
    def __init__(self, workspace: Path, model_selector: ModelSelector):
        self.workspace = workspace
        self.model_selector = model_selector
        self.active_tests = {}
        self.test_results = {}

    def start_test(self, config: ABTestConfig):
        if config.test_name in self.active_tests:
            raise ValueError(f"Test {config.test_name} already exists")

        if abs(sum(config.traffic_split.values()) - 1.0) > 0.01:
            raise ValueError("Traffic split must sum to 1.0")

        for model in config.models:
            if model not in self.model_selector.models:
                raise ValueError(f"Model {model} not found")

        self.active_tests[config.test_name] = config
        self.test_results[config.test_name] = {'samples': []}
        return f"Started A/B test: {config.test_name}"

    def get_model_for_request(self, content: str, context: str = "") -> str:
        for test_name, test_config in self.active_tests.items():
            if True:  # Simplified matching
                return self._select_model_from_test(test_config)
        return self.model_selector.select_model(content)

    def _select_model_from_test(self, test_config: ABTestConfig) -> str:
        rand = random.random()
        cumulative = 0.0
        for model, weight in test_config.traffic_split.items():
            cumulative += weight
            if rand <= cumulative:
                return model
        return test_config.models[0]

    def record_test_result(self, test_name: str, model_name: str, latency: float,
                          cost: float, success: bool):
        if test_name not in self.active_tests:
            return

        result = {
            'timestamp': time.time(),
            'test_name': test_name,
            'model': model_name,
            'latency': latency,
            'cost': cost,
            'success': success
        }

        self.test_results[test_name]['samples'].append(result)
        self.model_selector.record_performance(model_name, latency, cost, success)

    def get_test_status(self, test_name: str):
        if test_name not in self.active_tests:
            return {'error': 'Test not found'}

        test_config = self.active_tests[test_name]
        samples = self.test_results[test_name]['samples']

        model_stats = {}
        for model in test_config.models:
            model_samples = [s for s in samples if s['model'] == model]
            if model_samples:
                model_stats[model] = {
                    'samples': len(model_samples),
                    'success_rate': sum(1 for s in model_samples if s['success']) / len(model_samples),
                    'avg_latency': sum(s['latency'] for s in model_samples) / len(model_samples),
                    'avg_cost': sum(s['cost'] for s in model_samples) / len(model_samples)
                }
            else:
                model_stats[model] = {'samples': 0}

        min_samples = min(stats.get('samples', 0) for stats in model_stats.values())
        should_end = min_samples >= test_config.min_samples_per_model

        return {
            'test_name': test_name,
            'status': 'running' if not should_end else 'completed',
            'model_stats': model_stats,
            'total_samples': len(samples),
            'should_end': should_end
        }

    def end_test(self, test_name: str):
        if test_name not in self.active_tests:
            return {'error': 'Test not found'}

        status = self.get_test_status(test_name)
        del self.active_tests[test_name]

        return {
            'test_name': test_name,
            'final_results': status,
            'winner': self._determine_winner(status['model_stats'])
        }

    def _determine_winner(self, model_stats):
        scored_models = []
        for model, stats in model_stats.items():
            if stats['samples'] > 0:
                quality = 0.8  # Simplified
                cost_norm = 1.0 - (stats['avg_cost'] / max(s['avg_cost'] for s in model_stats.values() if s['samples'] > 0))
                latency_norm = 1.0 - (stats['avg_latency'] / max(s['avg_latency'] for s in model_stats.values() if s['samples'] > 0))
                success = stats['success_rate']
                composite_score = (quality + cost_norm + latency_norm + success) / 4.0
                scored_models.append((model, composite_score))

        if scored_models:
            return max(scored_models, key=lambda x: x[1])[0]
        return None

class RateLimitHandler:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.model_selector = ModelSelector(workspace)
        self.ab_testing = ABTestingFramework(workspace, self.model_selector)

    def _mock_embedding_api(self, content: str, model: str = "") -> List[float]:
        time.sleep(0.01)  # Simulate API call
        import hashlib
        hash_obj = hashlib.md5(content.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        embedding = []
        for i in range(1536):
            value = ((hash_int + i) % 2000 - 1000) / 1000.0
            embedding.append(value)
        return embedding

    def intelligent_embedding_call(self, content: str, quality_requirement: float = 0.5,
                                  budget_priority: float = 0.5, context: str = "") -> List[float]:
        selected_model = self.ab_testing.get_model_for_request(content, context)

        if not any(True for test in self.ab_testing.active_tests.values()):
            selected_model = self.model_selector.select_model(content, quality_requirement, budget_priority)

        print(f"Selected model: {selected_model}")
        start_time = time.time()

        try:
            result = self._mock_embedding_api(content, selected_model)
            latency = time.time() - start_time
            cost = self.model_selector.models[selected_model].cost_per_token * len(content.split())

            self.model_selector.record_performance(selected_model, latency, cost, True)

            for test_name, test_config in self.ab_testing.active_tests.items():
                if selected_model in test_config.models:
                    self.ab_testing.record_test_result(test_name, selected_model, latency, cost, True)
                    break

            return result
        except Exception as e:
            latency = time.time() - start_time
            cost = self.model_selector.models[selected_model].cost_per_token * len(content.split())

            self.model_selector.record_performance(selected_model, latency, cost, False)

            for test_name, test_config in self.ab_testing.active_tests.items():
                if selected_model in test_config.models:
                    self.ab_testing.record_test_result(test_name, selected_model, latency, cost, False)
                    break

            raise e

    def start_ab_test(self, test_name: str, models: List[str], traffic_split: Dict[str, float] = None):
        if traffic_split is None:
            weight = 1.0 / len(models)
            traffic_split = {model: weight for model in models}

        config = ABTestConfig(test_name=test_name, models=models, traffic_split=traffic_split)
        return self.ab_testing.start_test(config)

    def get_ab_test_status(self, test_name: str):
        return self.ab_testing.get_test_status(test_name)

    def end_ab_test(self, test_name: str):
        return self.ab_testing.end_test(test_name)

    def get_model_performance(self):
        return self.model_selector.performance_history
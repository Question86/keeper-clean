# MODE: SCRIPT

'''Token Monitoring System - Based on Prompt-to-Insight Patterns

This module implements LLM observability and token monitoring patterns discovered from
GitHub research on prompt-to-insight, adapted for Keeper-Clean-Loop1's AI workflows.

Key Features:
- Real-time token usage tracking
- Cost monitoring and optimization
- Hallucination detection
- Performance benchmarking
- Token efficiency analytics

Based on: https://github.com/ruvnet/prompt-to-insight
'''

from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import statistics
import re

from knowledge_db import KnowledgeDB
from pathlib import Path


@dataclass
class TokenUsage:
    """Represents token usage for a single LLM interaction."""
    interaction_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    timestamp: float = field(default_factory=time.time)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    task_type: Optional[str] = None
    success: bool = True
    response_quality: float = 0.0  # 0.0 to 1.0
    hallucination_score: float = 0.0  # 0.0 to 1.0 (higher = more likely hallucination)

    @property
    def cost_per_token(self) -> float:
        """Get cost per token based on model."""
        # OpenAI pricing (as of 2024)
        pricing = {
            'gpt-4': {'prompt': 0.03, 'completion': 0.06},  # per 1K tokens
            'gpt-4-turbo': {'prompt': 0.01, 'completion': 0.03},
            'gpt-3.5-turbo': {'prompt': 0.0015, 'completion': 0.002},
            'claude-3-opus': {'prompt': 0.015, 'completion': 0.075},
            'claude-3-sonnet': {'prompt': 0.003, 'completion': 0.015},
            'claude-3-haiku': {'prompt': 0.00025, 'completion': 0.00125}
        }

        if self.model in pricing:
            prompt_cost = (self.prompt_tokens / 1000) * pricing[self.model]['prompt']
            completion_cost = (self.completion_tokens / 1000) * pricing[self.model]['completion']
            return (prompt_cost + completion_cost) / self.total_tokens
        return 0.0

    def efficiency_score(self) -> float:
        """Calculate token efficiency score (0.0 to 1.0)."""
        if self.total_tokens == 0:
            return 0.0

        # Efficiency based on completion ratio and quality
        completion_ratio = self.completion_tokens / self.total_tokens
        quality_weight = self.response_quality

        # Optimal completion ratio is around 0.3-0.7
        ratio_score = 1.0 - abs(completion_ratio - 0.5) * 2

        return (ratio_score + quality_weight) / 2


@dataclass
class ModelPerformance:
    """Performance metrics for a specific model."""
    model_name: str
    total_interactions: int = 0
    successful_interactions: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_response_quality: float = 0.0
    avg_hallucination_score: float = 0.0
    avg_efficiency: float = 0.0
    task_performance: Dict[str, Dict[str, float]] = field(default_factory=lambda: defaultdict(dict))

    def update(self, usage: TokenUsage):
        """Update performance metrics with new usage data."""
        self.total_interactions += 1
        if usage.success:
            self.successful_interactions += 1

        self.total_tokens += usage.total_tokens
        self.total_cost += usage.estimated_cost

        # Update averages
        self.avg_response_quality = (
            (self.avg_response_quality * (self.total_interactions - 1)) + usage.response_quality
        ) / self.total_interactions

        self.avg_hallucination_score = (
            (self.avg_hallucination_score * (self.total_interactions - 1)) + usage.hallucination_score
        ) / self.total_interactions

        self.avg_efficiency = (
            (self.avg_efficiency * (self.total_interactions - 1)) + usage.efficiency_score()
        ) / self.total_interactions

        # Update task-specific performance
        if usage.task_type:
            task_perf = self.task_performance[usage.task_type]
            task_count = task_perf.get('count', 0) + 1
            task_perf['count'] = task_count
            task_perf['avg_quality'] = (
                (task_perf.get('avg_quality', 0) * (task_count - 1)) + usage.response_quality
            ) / task_count
            task_perf['avg_efficiency'] = (
                (task_perf.get('avg_efficiency', 0) * (task_count - 1)) + usage.efficiency_score()
            ) / task_count

    @property
    def success_rate(self) -> float:
        """Get success rate (0.0 to 1.0)."""
        return self.successful_interactions / self.total_interactions if self.total_interactions > 0 else 0.0

    @property
    def cost_per_token(self) -> float:
        """Get average cost per token."""
        return self.total_cost / self.total_tokens if self.total_tokens > 0 else 0.0


class HallucinationDetector:
    """Detect potential hallucinations in LLM responses."""

    def __init__(self):
        # Patterns that might indicate hallucinations
        self.hallucination_patterns = [
            r'\b(?:definitely|certainly|absolutely)\s+(?:true|false|correct|wrong)\b',
            r'\b(?:proven|confirmed|verified)\s+(?:fact|theory|hypothesis)\b',
            r'\b(?:always|never|every|all)\s+(?:time|case|instance)\b',
            r'\b(?:impossible|improbable|inconceivable)\b.*\b(?:without|unless)\b',
            r'\b(?:scientifically|mathematically|logically)\s+(?:proven|disproven)\b'
        ]

        # Contradiction patterns
        self.contradiction_patterns = [
            r'\b(?:however|but|although|despite)\b.*\b(?:also|and|similarly)\b',
            r'\b(?:yes|true|correct)\b.*\b(?:no|false|incorrect)\b',
            r'\b(?:increases|decreases)\b.*\b(?:decreases|increases)\b'
        ]

    def detect_hallucination(self, prompt: str, response: str) -> float:
        """Detect potential hallucinations in response. Returns score 0.0-1.0."""
        score = 0.0

        # Check for overconfident language
        for pattern in self.hallucination_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                score += 0.2

        # Check for contradictions
        for pattern in self.contradiction_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                score += 0.3

        # Check for unsupported claims (simplified heuristic)
        unsupported_indicators = ['according to', 'research shows', 'studies prove', 'experts say']
        supported_claims = sum(1 for indicator in unsupported_indicators if indicator in response.lower())
        total_claims = len(re.findall(r'\b(?:is|are|was|were|has|have|do|does|can|could|will|would|should)\b', response))

        if total_claims > 0:
            support_ratio = supported_claims / total_claims
            if support_ratio < 0.1:  # Low support ratio might indicate hallucination
                score += 0.3

        # Length-based heuristic (very short or very long responses might be problematic)
        response_length = len(response.split())
        if response_length < 10 or response_length > 1000:
            score += 0.1

        return min(1.0, score)


class LoopBudgetTracker:
    """Track token budgets per loop as per mega.md strategy."""
    
    def __init__(self, workspace_root: Path, knowledge_db: Optional[KnowledgeDB] = None):
        self.workspace_root = workspace_root
        self.current_json = workspace_root / "current.json"
        self._budget_file = workspace_root / ".loop_budget.json"
        self.loop_budget = 109000  # Token budget per loop
        self.knowledge_db = knowledge_db
        self.current_task = None
        self.task_start_usage = 0
        self.task_start_time = None
        
    def get_current_loop(self) -> int:
        """Get current loop number from current.json."""
        try:
            if self.current_json.exists():
                data = json.loads(self.current_json.read_text())
                return data.get('STATE', {}).get('loop', 1)
        except:
            pass
        return 1
    
    def start_task_monitoring(self, task_id: str) -> Dict[str, Any]:
        """Start monitoring token usage for a specific task."""
        if self.current_task:
            self.end_task_monitoring()  # End previous task
        
        self.current_task = task_id
        loop_num = self.get_current_loop()
        usage = self.get_loop_usage(loop_num)
        self.task_start_usage = usage["tokens_used"]
        self.task_start_time = time.time()
        
        return {
            "task_id": task_id,
            "start_usage": self.task_start_usage,
            "start_time": self.task_start_time,
            "loop": loop_num
        }
    
    def end_task_monitoring(self) -> Dict[str, Any]:
        """End monitoring for current task and return usage summary."""
        if not self.current_task:
            return {"error": "No active task"}
        
        task_id = self.current_task
        loop_num = self.get_current_loop()
        usage = self.get_loop_usage(loop_num)
        current_usage = usage["tokens_used"]
        task_tokens = current_usage - self.task_start_usage
        duration = time.time() - self.task_start_time
        
        # Record task usage
        data = {}
        if self._budget_file.exists():
            try:
                data = json.loads(self._budget_file.read_text())
            except:
                data = {}
        
        loop_key = f"loop_{loop_num}"
        if loop_key not in data:
            data[loop_key] = {"tokens_used": 0, "start_time": time.time(), "phases": {}, "tasks": {}}
        if "tasks" not in data[loop_key]:
            data[loop_key]["tasks"] = {}
        
        data[loop_key]["tasks"][task_id] = {
            "tokens_used": task_tokens,
            "duration": duration,
            "start_time": self.task_start_time,
            "end_time": time.time(),
            "efficiency": task_tokens / duration if duration > 0 else 0
        }
        
        self._budget_file.write_text(json.dumps(data, indent=2))
        
        # Reset
        result = {
            "task_id": task_id,
            "tokens_used": task_tokens,
            "duration": duration,
            "efficiency": task_tokens / duration if duration > 0 else 0,
            "loop": loop_num
        }
        
        self.current_task = None
        self.task_start_usage = 0
        self.task_start_time = None
        
        return result
    
    def get_current_loop(self) -> int:
        """Get current loop number from current.json."""
        try:
            if self.current_json.exists():
                data = json.loads(self.current_json.read_text())
                return data.get('STATE', {}).get('loop', 1)
        except:
            pass
        return 1
    
    def get_loop_usage(self, loop_num: int) -> Dict[str, Any]:
        """Get token usage for a specific loop."""
        try:
            if self._budget_file.exists():
                data = json.loads(self._budget_file.read_text())
                loop_data = data.get(f"loop_{loop_num}", {
                    "tokens_used": 0,
                    "start_time": time.time(),
                    "phases": {},
                    "tasks": {}
                })
                # Ensure tasks key exists
                if "tasks" not in loop_data:
                    loop_data["tasks"] = {}
                return loop_data
        except:
            pass
        return {
            "tokens_used": 0,
            "start_time": time.time(),
            "phases": {},
            "tasks": {}
        }
    
    def record_usage(self, tokens: int, phase: str = "general") -> Dict[str, Any]:
        """Record token usage for current loop and phase."""
        loop_num = self.get_current_loop()
        loop_key = f"loop_{loop_num}"
        
        # Load existing data
        data = {}
        if self._budget_file.exists():
            try:
                data = json.loads(self._budget_file.read_text())
            except:
                data = {}
        
        if loop_key not in data:
            data[loop_key] = {
                "tokens_used": 0,
                "start_time": time.time(),
                "phases": {},
                "tasks": {}
            }
        
        # Update usage
        data[loop_key]["tokens_used"] += tokens
        if phase not in data[loop_key]["phases"]:
            data[loop_key]["phases"][phase] = 0
        data[loop_key]["phases"][phase] += tokens
        
        # Update current task if active
        if self.current_task and self.current_task in data[loop_key]["tasks"]:
            data[loop_key]["tasks"][self.current_task]["tokens_used"] += tokens
        
        # Save to JSON file
        self._budget_file.write_text(json.dumps(data, indent=2))
        
        # Also write to KnowledgeDB (TASK_0153 integration)
        current_usage = data[loop_key]["tokens_used"]
        try:
            self.knowledge_db.record_token_budget(
                loop_num=loop_num,
                phase=phase,
                budget_tokens=self.loop_budget,
                used_tokens=current_usage
            )
        except Exception as e:
            # Don't fail the whole operation if DB write fails
            print(f"Warning: Failed to write to KnowledgeDB: {e}")
        
        return {
            "loop": loop_num,
            "tokens_used": current_usage,
            "remaining": max(0, self.loop_budget - current_usage),
            "percentage": round(percentage, 1),
            "should_finalize": percentage >= 75,  # Finalize at 75% as per user requirement
            "phase_breakdown": data[loop_key]["phases"],
            "current_task": self.current_task
        }
    
    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status for decision making."""
        loop_num = self.get_current_loop()
        usage = self.get_loop_usage(loop_num)
        
        return {
            "current_loop": loop_num,
            "budget_limit": self.loop_budget,
            "tokens_used": usage["tokens_used"],
            "remaining": max(0, self.loop_budget - usage["tokens_used"]),
            "percentage": round((usage["tokens_used"] / self.loop_budget) * 100, 1),
            "should_finalize": (usage["tokens_used"] / self.loop_budget) >= 0.75,
            "phases": usage["phases"],
            "recommendation": self._get_recommendation(usage["tokens_used"])
        }
    
    def _get_recommendation(self, tokens_used: int) -> str:
        """Get recommendation based on usage."""
        percentage = (tokens_used / self.loop_budget) * 100
        
        if percentage >= 95:
            return "CRITICAL: Finalize loop immediately - risk of incomplete work"
        elif percentage >= 85:
            return "HIGH PRIORITY: Finalize loop soon - approaching red zone"
        elif percentage >= 70:
            return "MODERATE: Monitor closely - yellow zone"
        elif percentage >= 50:
            return "NORMAL: Good progress - continue work"
        else:
            return "LOW: Plenty of budget remaining - full speed ahead"


class TokenMonitor:
    """Token monitoring and LLM observability system."""

    def __init__(self, workspace_root: Path, knowledge_db: Optional[KnowledgeDB] = None):
        self.workspace_root = workspace_root
        self.knowledge_db = knowledge_db or KnowledgeDB(workspace_root)

        # Core monitoring data
        self.usage_history: List[TokenUsage] = []
        self.model_performance: Dict[str, ModelPerformance] = defaultdict(ModelPerformance)
        self.session_usage: Dict[str, List[TokenUsage]] = defaultdict(list)

        # Detection systems
        self.hallucination_detector = HallucinationDetector()

        # Cost tracking
        self.monthly_budget = 100.0  # Default $100/month
        self.current_month_cost = 0.0

        # Performance thresholds
        self.quality_threshold = 0.7
        self.hallucination_threshold = 0.3
        self.efficiency_threshold = 0.6

    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int,
                    prompt: str = "", response: str = "", user_id: Optional[str] = None,
                    session_id: Optional[str] = None, task_type: Optional[str] = None) -> str:
        """Record token usage for an LLM interaction."""

        interaction_id = f"usage_{hashlib.md5(f'{model}_{time.time()}'.encode()).hexdigest()[:8]}"
        total_tokens = prompt_tokens + completion_tokens

        # Estimate cost (simplified)
        estimated_cost = self._estimate_cost(model, prompt_tokens, completion_tokens)

        # Detect hallucinations
        hallucination_score = self.hallucination_detector.detect_hallucination(prompt, response)

        # Estimate response quality (simplified heuristic)
        response_quality = self._estimate_quality(response, hallucination_score)

        usage = TokenUsage(
            interaction_id=interaction_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            user_id=user_id,
            session_id=session_id,
            task_type=task_type,
            response_quality=response_quality,
            hallucination_score=hallucination_score
        )

        # Store usage data
        self.usage_history.append(usage)
        if session_id:
            self.session_usage[session_id].append(usage)

        # Update model performance
        if model not in self.model_performance:
            self.model_performance[model] = ModelPerformance(model)
        self.model_performance[model].update(usage)

        # Update monthly cost
        self.current_month_cost += estimated_cost

        # Keep only recent history (last 10000 interactions)
        if len(self.usage_history) > 10000:
            self.usage_history = self.usage_history[-10000:]

        return interaction_id

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost for token usage."""
        # Simplified cost estimation - in practice would use current API pricing
        base_costs = {
            'gpt-4': 0.036,  # per 1K tokens average
            'gpt-3.5-turbo': 0.00175,
            'claude-3-opus': 0.045,
            'claude-3-sonnet': 0.009,
            'claude-3-haiku': 0.00075
        }

        cost_per_1k = base_costs.get(model, 0.01)
        total_1k_tokens = (prompt_tokens + completion_tokens) / 1000
        return total_1k_tokens * cost_per_1k

    def _estimate_quality(self, response: str, hallucination_score: float) -> float:
        """Estimate response quality (simplified heuristic)."""
        if not response:
            return 0.0

        # Base quality on length and coherence
        length_score = min(1.0, len(response.split()) / 100)  # Prefer substantial responses

        # Penalize for hallucinations
        hallucination_penalty = hallucination_score * 0.5

        # Check for structured responses
        structure_bonus = 0.0
        if any(indicator in response.lower() for indicator in ['however', 'therefore', 'in conclusion', 'summary']):
            structure_bonus = 0.2

        quality = length_score + structure_bonus - hallucination_penalty
        return max(0.0, min(1.0, quality))

    def get_usage_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive usage report."""
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        recent_usage = [u for u in self.usage_history if u.timestamp > cutoff_time]

        if not recent_usage:
            return {'error': 'No usage data available for the specified period'}

        total_tokens = sum(u.total_tokens for u in recent_usage)
        total_cost = sum(u.estimated_cost for u in recent_usage)
        avg_quality = statistics.mean(u.response_quality for u in recent_usage)
        avg_hallucination = statistics.mean(u.hallucination_score for u in recent_usage)

        # Model breakdown
        model_usage = defaultdict(lambda: {'tokens': 0, 'cost': 0, 'interactions': 0})
        for usage in recent_usage:
            model_usage[usage.model]['tokens'] += usage.total_tokens
            model_usage[usage.model]['cost'] += usage.estimated_cost
            model_usage[usage.model]['interactions'] += 1

        # Task breakdown
        task_usage = defaultdict(lambda: {'tokens': 0, 'cost': 0, 'interactions': 0, 'avg_quality': 0})
        for usage in recent_usage:
            if usage.task_type:
                task_usage[usage.task_type]['tokens'] += usage.total_tokens
                task_usage[usage.task_type]['cost'] += usage.estimated_cost
                task_usage[usage.task_type]['interactions'] += 1

        # Update task averages
        for task, data in task_usage.items():
            task_usages = [u for u in recent_usage if u.task_type == task]
            if task_usages:
                data['avg_quality'] = statistics.mean(u.response_quality for u in task_usages)

        return {
            'period_days': days,
            'total_interactions': len(recent_usage),
            'total_tokens': total_tokens,
            'total_cost': round(total_cost, 4),
            'avg_quality': round(avg_quality, 3),
            'avg_hallucination_score': round(avg_hallucination, 3),
            'budget_remaining': round(self.monthly_budget - self.current_month_cost, 2),
            'budget_utilization': round((self.current_month_cost / self.monthly_budget) * 100, 1) if self.monthly_budget > 0 else 0,
            'model_breakdown': dict(model_usage),
            'task_breakdown': dict(task_usage),
            'alerts': self._generate_alerts(recent_usage)
        }

    def _generate_alerts(self, recent_usage: List[TokenUsage]) -> List[str]:
        """Generate alerts based on usage patterns."""
        alerts = []

        if recent_usage:
            avg_quality = statistics.mean(u.response_quality for u in recent_usage)
            avg_hallucination = statistics.mean(u.hallucination_score for u in recent_usage)

            if avg_quality < self.quality_threshold:
                alerts.append(f"Low response quality: {avg_quality:.2f} (threshold: {self.quality_threshold})")

            if avg_hallucination > self.hallucination_threshold:
                alerts.append(f"High hallucination risk: {avg_hallucination:.2f} (threshold: {self.hallucination_threshold})")

            total_cost = sum(u.estimated_cost for u in recent_usage)
            if self.current_month_cost > self.monthly_budget * 0.8:
                alerts.append(f"Budget utilization: {(self.current_month_cost/self.monthly_budget)*100:.1f}%")

        return alerts

    def optimize_model_selection(self, task_type: str, required_quality: float = 0.7) -> List[Tuple[str, float]]:
        """Recommend optimal models for a task type based on performance."""
        candidates = []

        for model, perf in self.model_performance.items():
            if task_type in perf.task_performance:
                task_perf = perf.task_performance[task_type]
                quality = task_perf.get('avg_quality', 0)
                efficiency = task_perf.get('avg_efficiency', 0)
                cost_per_token = perf.cost_per_token

                # Score based on quality, efficiency, and cost
                score = (quality * 0.5) + (efficiency * 0.3) - (cost_per_token * 100)  # Cost penalty

                if quality >= required_quality:
                    candidates.append((model, score))

        return sorted(candidates, key=lambda x: x[1], reverse=True)

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalous usage patterns."""
        anomalies = []

        if len(self.usage_history) < 10:
            return anomalies

        # Check for sudden cost spikes
        recent_costs = [u.estimated_cost for u in self.usage_history[-20:]]
        if len(recent_costs) >= 10:
            recent_avg = statistics.mean(recent_costs[-5:])
            historical_avg = statistics.mean(recent_costs[:-5])

            if historical_avg > 0 and (recent_avg / historical_avg) > 2.0:
                anomalies.append({
                    'type': 'cost_spike',
                    'description': f'Cost spike detected: {recent_avg:.4f} vs historical {historical_avg:.4f}',
                    'severity': 'high'
                })

        # Check for quality degradation
        recent_quality = [u.response_quality for u in self.usage_history[-20:]]
        if len(recent_quality) >= 10:
            recent_avg = statistics.mean(recent_quality[-5:])
            historical_avg = statistics.mean(recent_quality[:-5])

            if recent_avg < historical_avg * 0.7:
                anomalies.append({
                    'type': 'quality_degradation',
                    'description': f'Quality degradation: {recent_avg:.2f} vs historical {historical_avg:.2f}',
                    'severity': 'medium'
                })

        return anomalies


# Integration with knowledge database
def integrate_monitoring_with_knowledge_db(monitor: TokenMonitor) -> None:
    """Integrate monitoring insights with the knowledge database."""
    report = monitor.get_usage_report(days=30)

    monitoring_insights = {
        'token_efficiency': f'Average token efficiency: {report.get("avg_quality", 0):.2f} with {report.get("total_tokens", 0)} total tokens used',
        'cost_optimization': f'Monthly budget utilization: {report.get("budget_utilization", 0):.1f}% with ${report.get("total_cost", 0):.2f} spent',
        'hallucination_detection': f'Average hallucination score: {report.get("avg_hallucination_score", 0):.2f} (threshold: {monitor.hallucination_threshold})',
        'model_performance': f'Top performing models: {list(report.get("model_breakdown", {}).keys())[:3]}'
    }

    for insight_name, description in monitoring_insights.items():
        monitor.knowledge_db.conn.execute('''
            INSERT INTO lessons (source_type, source_id, loop_num, lesson_text, category, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'token_monitor',
            insight_name,
            48,
            description,
            'llm_observability',
            datetime.now(timezone.utc).isoformat()
        ))

    monitor.knowledge_db.conn.commit()


# Example usage and testing
def demo_token_monitoring():
    """Demonstrate token monitoring capabilities."""
    monitor = TokenMonitor(Path('.'))

    print("Token Monitoring Demo")
    print("=" * 50)

    # Simulate various LLM interactions
    interactions = [
        ('gpt-4', 150, 200, "Write a Python function", "def hello(): return 'world'", "coding", "session_1"),
        ('gpt-3.5-turbo', 100, 150, "Explain quantum physics", "Quantum physics is complex...", "explanation", "session_1"),
        ('claude-3-sonnet', 200, 300, "Debug this code", "Found the bug: missing import", "debugging", "session_2"),
        ('gpt-4', 180, 250, "Write documentation", "This module provides...", "documentation", "session_2"),
        ('gpt-3.5-turbo', 120, 180, "Generate test cases", "Test case 1: input validation", "testing", "session_3")
    ]

    for model, prompt_t, comp_t, prompt, response, task, session in interactions:
        interaction_id = monitor.record_usage(
            model=model,
            prompt_tokens=prompt_t,
            completion_tokens=comp_t,
            prompt=prompt,
            response=response,
            task_type=task,
            session_id=session
        )
        print(f"Recorded interaction: {interaction_id} ({model})")

    # Generate report
    report = monitor.get_usage_report(days=1)
    print(f"\nUsage Report (1 day):")
    print(f"Total interactions: {report['total_interactions']}")
    print(f"Total tokens: {report['total_tokens']}")
    print(f"Total cost: ${report['total_cost']}")
    print(f"Average quality: {report['avg_quality']}")
    print(f"Hallucination score: {report['avg_hallucination_score']}")

    # Model optimization recommendations
    recommendations = monitor.optimize_model_selection('coding', 0.6)
    print(f"\nModel recommendations for coding: {recommendations[:2]}")

    # Check for anomalies
    anomalies = monitor.detect_anomalies()
    if anomalies:
        print(f"\nDetected anomalies: {len(anomalies)}")
        for anomaly in anomalies:
            print(f"  - {anomaly['type']}: {anomaly['description']}")

    return monitor


class TokenBudgetGuard:
    """Guard rails for token budget to prevent overruns during expensive operations."""
    
    def __init__(self, tracker: LoopBudgetTracker, warning_threshold: float = 0.8, abort_threshold: float = 0.95):
        self.tracker = tracker
        self.warning_threshold = warning_threshold
        self.abort_threshold = abort_threshold
    
    def check_budget(self, estimated_tokens: int) -> Dict[str, Any]:
        """Check if operation would exceed budget thresholds.
        
        Args:
            estimated_tokens: Estimated tokens the operation will consume
            
        Returns:
            Dict with check results
            
        Raises:
            BudgetExceededError: If operation would exceed abort threshold
        """
        status = self.tracker.get_budget_status()
        projected_usage = status['tokens_used'] + estimated_tokens
        projected_percentage = projected_usage / status['budget_limit']
        
        result = {
            'can_proceed': projected_percentage < self.abort_threshold,
            'should_warn': projected_percentage >= self.warning_threshold,
            'projected_usage': projected_usage,
            'projected_percentage': projected_percentage,
            'remaining_after': status['budget_limit'] - projected_usage
        }
        
        if not result['can_proceed']:
            raise BudgetExceededError(
                f"Operation would exceed {self.abort_threshold*100}% budget "
                f"({projected_usage}/{status['budget_limit']} = {projected_percentage*100:.1f}%)"
            )
        
        return result
    
    def should_degrade(self) -> bool:
        """Check if system should degrade to cheaper operations."""
        status = self.tracker.get_budget_status()
        return status['percentage'] / 100 > 0.9  # 90% usage
    
    def get_safe_operation_limit(self, operation_cost_per_unit: int) -> int:
        """Get maximum number of operations that can be performed safely."""
        status = self.tracker.get_budget_status()
        remaining = status['budget_limit'] - status['tokens_used']
        safe_limit = int(remaining * 0.8 / operation_cost_per_unit)  # Leave 20% buffer
        return max(0, safe_limit)


class BudgetExceededError(Exception):
    """Raised when an operation would exceed the token budget."""
    pass


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Token Monitor for Keeper Loop Budgets")
    parser.add_argument("--budget", action="store_true", help="Show loop budget status")
    parser.add_argument("--record", type=int, help="Record token usage (specify token count)")
    parser.add_argument("--phase", default="general", help="Phase for token recording")
    
    args = parser.parse_args()
    
    if args.budget:
        tracker = LoopBudgetTracker(Path('.'))
        status = tracker.get_budget_status()
        print("Loop Budget Status")
        print("=" * 30)
        print(f"Current Loop: {status['current_loop']}")
        print(f"Budget Limit: {status['budget_limit']:,} tokens")
        print(f"Tokens Used: {status['tokens_used']:,}")
        print(f"Remaining: {status['remaining']:,}")
        print(f"Percentage: {status['percentage']}%")
        print(f"Should Finalize: {status['should_finalize']}")
        print(f"Recommendation: {status['recommendation']}")
        if status['phases']:
            print("\nPhase Breakdown:")
            for phase, tokens in status['phases'].items():
                print(f"  {phase}: {tokens:,} tokens")
    
    elif args.record:
        tracker = LoopBudgetTracker(Path('.'))
        result = tracker.record_usage(args.record, args.phase)
        print(f"Recorded {args.record} tokens for phase '{args.phase}'")
        print(f"Loop {result['loop']}: {result['tokens_used']:,}/{tracker.loop_budget:,} tokens ({result['percentage']}%)")
        print(f"Remaining: {result['remaining']:,} tokens")
        if result['should_finalize']:
            print("⚠️  BUDGET WARNING: Consider finalizing loop")
    
    else:
        demo_token_monitoring()
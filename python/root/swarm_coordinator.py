# MODE: SCRIPT

'''Swarm Intelligence Coordinator - Based on Claude-Flow Patterns

This module implements swarm intelligence coordination patterns discovered from
GitHub research on claude-flow, adapted for Keeper-Clean-Loop1's multi-agent workflows.

Key Features:
- Queen/worker hierarchy coordination
- Byzantine fault-tolerant consensus
- Intelligent task routing (89% accuracy target)
- Self-learning pattern recognition
- Fault-tolerant multi-agent orchestration

Based on: https://github.com/ruvnet/claude-flow
'''

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import statistics

from knowledge_db import KnowledgeDB
from pathlib import Path


class ConsensusAlgorithm(Enum):
    """Consensus algorithms from claude-flow research."""
    RAFT = "raft"
    BYZANTINE = "byzantine"
    GOSSIP = "gossip"
    MAJORITY = "majority"


class SwarmRole(Enum):
    """Agent roles in swarm hierarchy."""
    QUEEN = "queen"
    WORKER = "worker"
    SCOUT = "scout"
    GUARD = "guard"


class TaskStatus(Enum):
    """Task states in swarm orchestration."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CONSENSUS_REQUIRED = "consensus_required"


@dataclass
class SwarmAgent:
    """Represents an agent in the swarm."""
    agent_id: str
    role: SwarmRole
    capabilities: Set[str]
    performance_score: float = 0.0
    task_count: int = 0
    last_active: float = 0.0
    consensus_votes: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if agent is currently active."""
        return time.time() - self.last_active < 300  # 5 minutes

    def update_performance(self, success: bool, execution_time: float):
        """Update agent performance metrics."""
        self.task_count += 1
        if success:
            # Reward faster execution
            time_bonus = max(0, 1.0 - (execution_time / 60.0))  # Bonus for < 60s
            self.performance_score = 0.9 * self.performance_score + 0.1 * (1.0 + time_bonus)
        else:
            self.performance_score = 0.9 * self.performance_score  # Decay on failure

    def can_handle_task(self, task_requirements: Set[str]) -> bool:
        """Check if agent can handle a task with given requirements."""
        return task_requirements.issubset(self.capabilities)


@dataclass
class SwarmTask:
    """Represents a task in the swarm orchestration."""
    task_id: str
    description: str
    requirements: Set[str]
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    consensus_votes: Dict[str, Any] = field(default_factory=dict)
    execution_attempts: int = 0

    def duration(self) -> Optional[float]:
        """Get task execution duration."""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None

    def needs_consensus(self) -> bool:
        """Check if task requires consensus validation."""
        return self.status == TaskStatus.CONSENSUS_REQUIRED or len(self.consensus_votes) > 0


class SwarmCoordinator:
    """Swarm Intelligence Coordinator based on claude-flow patterns.

    Implements:
    - Queen/worker hierarchy
    - Byzantine fault-tolerant consensus (f < n/3)
    - Intelligent task routing with learned patterns
    - Self-learning from successful task assignments
    """

    def __init__(self, workspace_root: Path, knowledge_db: Optional[KnowledgeDB] = None):
        self.workspace_root = workspace_root
        self.knowledge_db = knowledge_db or KnowledgeDB(workspace_root)

        # Swarm state
        self.agents: Dict[str, SwarmAgent] = {}
        self.tasks: Dict[str, SwarmTask] = {}
        self.task_history: List[Dict[str, Any]] = []

        # Learning patterns (agent -> capability -> success rate)
        self.routing_patterns: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Consensus configuration
        self.consensus_algorithm = ConsensusAlgorithm.BYZANTINE
        self.consensus_threshold = 0.67  # 2/3 majority for Byzantine

        # Performance tracking
        self.routing_accuracy = 0.0
        self.total_routings = 0
        self.successful_routings = 0

    def register_agent(self, agent_id: str, capabilities: Set[str], role: SwarmRole = SwarmRole.WORKER) -> SwarmAgent:
        """Register a new agent in the swarm."""
        agent = SwarmAgent(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities,
            last_active=time.time()
        )
        self.agents[agent_id] = agent
        return agent

    def submit_task(self, description: str, requirements: Set[str], priority: int = 1) -> str:
        """Submit a task to the swarm for orchestration."""
        task_id = f"task_{hashlib.md5(f'{description}_{time.time()}'.encode()).hexdigest()[:8]}"

        task = SwarmTask(
            task_id=task_id,
            description=description,
            requirements=requirements,
            priority=priority
        )

        self.tasks[task_id] = task

        # Immediately try to route the task
        self._route_task(task)

        return task_id

    def _route_task(self, task: SwarmTask) -> bool:
        """Route task to best available agent using learned patterns."""
        self.total_routings += 1

        # Find candidate agents
        candidates = [
            agent for agent in self.agents.values()
            if agent.is_active() and agent.can_handle_task(task.requirements)
        ]

        if not candidates:
            return False

        # Use learned routing patterns to select best agent
        best_agent = self._select_best_agent(task, candidates)

        if best_agent:
            task.status = TaskStatus.ASSIGNED
            task.assigned_agent = best_agent.agent_id
            task.started_at = time.time()
            best_agent.last_active = time.time()
            return True

        return False

    def _select_best_agent(self, task: SwarmTask, candidates: List[SwarmAgent]) -> Optional[SwarmAgent]:
        """Select best agent using learned routing patterns and performance scores."""
        if not candidates:
            return None

        # Score candidates based on learned patterns and performance
        scored_candidates = []
        for agent in candidates:
            # Base score from learned patterns
            pattern_score = 0.0
            capability_scores = [
                self.routing_patterns.get(agent.agent_id, {}).get(cap, 0.5)
                for cap in task.requirements
            ]
            if capability_scores:
                pattern_score = statistics.mean(capability_scores)

            # Performance score
            perf_score = agent.performance_score

            # Combined score (weighted average)
            total_score = 0.6 * pattern_score + 0.4 * perf_score

            scored_candidates.append((agent, total_score))

        # Select highest scoring agent
        if scored_candidates:
            best_agent, best_score = max(scored_candidates, key=lambda x: x[1])
            return best_agent

        return None

    def complete_task(self, task_id: str, result: Any, success: bool = True) -> bool:
        """Mark a task as completed and learn from the outcome."""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.completed_at = time.time()
        task.result = result
        task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED

        if task.assigned_agent and task.assigned_agent in self.agents:
            agent = self.agents[task.assigned_agent]
            duration = task.duration() or 60.0  # Default 60s if unknown

            # Update agent performance
            agent.update_performance(success, duration)

            # Learn routing patterns
            if success:
                self.successful_routings += 1
                # Strengthen pattern for successful routing
                for cap in task.requirements:
                    current = self.routing_patterns[agent.agent_id].get(cap, 0.5)
                    self.routing_patterns[agent.agent_id][cap] = 0.9 * current + 0.1 * 1.0
            else:
                # Weaken pattern for failed routing
                for cap in task.requirements:
                    current = self.routing_patterns[agent.agent_id].get(cap, 0.5)
                    self.routing_patterns[agent.agent_id][cap] = 0.9 * current + 0.1 * 0.0

        # Update routing accuracy
        if self.total_routings > 0:
            self.routing_accuracy = self.successful_routings / self.total_routings

        # Store in task history for learning
        self.task_history.append({
            'task_id': task_id,
            'agent_id': task.assigned_agent,
            'requirements': list(task.requirements),
            'success': success,
            'duration': task.duration(),
            'timestamp': task.completed_at
        })

        # Keep only recent history (last 1000 tasks)
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-1000:]

        return True

    def request_consensus(self, task_id: str, proposal: Any, requesting_agent: str) -> bool:
        """Request consensus validation for a task result."""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.status = TaskStatus.CONSENSUS_REQUIRED
        task.consensus_votes[requesting_agent] = proposal

        # Check if we have enough votes for consensus
        return self._check_consensus(task)

    def vote_on_consensus(self, task_id: str, agent_id: str, vote: Any) -> bool:
        """Cast a vote in consensus validation."""
        if task_id not in self.tasks or agent_id not in self.agents:
            return False

        task = self.tasks[task_id]
        task.consensus_votes[agent_id] = vote

        return self._check_consensus(task)

    def _check_consensus(self, task: SwarmTask) -> bool:
        """Check if consensus has been reached using Byzantine fault tolerance."""
        if len(task.consensus_votes) < 3:  # Need at least 3 votes for Byzantine
            return False

        total_votes = len(task.consensus_votes)
        active_agents = len([a for a in self.agents.values() if a.is_active()])

        # Byzantine fault tolerance: f < n/3 where f is max faulty nodes
        max_faulty = (active_agents - 1) // 3
        required_votes = active_agents - max_faulty

        if total_votes >= required_votes:
            # Check for majority agreement (simplified - in practice would be more sophisticated)
            vote_counts = defaultdict(int)
            for vote in task.consensus_votes.values():
                # Normalize vote for comparison (simplified)
                vote_key = json.dumps(vote, sort_keys=True) if isinstance(vote, dict) else str(vote)
                vote_counts[vote_key] += 1

            # Find majority vote
            majority_vote, majority_count = max(vote_counts.items(), key=lambda x: x[1])

            if majority_count >= required_votes:
                task.result = json.loads(majority_vote) if majority_vote.startswith('{') else majority_vote
                task.status = TaskStatus.COMPLETED
                return True

        return False

    def get_swarm_status(self) -> Dict[str, Any]:
        """Get comprehensive swarm status and performance metrics."""
        active_agents = len([a for a in self.agents.values() if a.is_active()])
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])

        return {
            'active_agents': active_agents,
            'total_agents': len(self.agents),
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            'routing_accuracy': self.routing_accuracy,
            'consensus_algorithm': self.consensus_algorithm.value,
            'learned_patterns': dict(self.routing_patterns),
            'performance_stats': {
                agent_id: {
                    'performance_score': agent.performance_score,
                    'task_count': agent.task_count,
                    'role': agent.role.value
                }
                for agent_id, agent in self.agents.items()
            }
        }

    def optimize_routing(self) -> Dict[str, Any]:
        """Optimize routing patterns based on historical performance."""
        optimizations = {
            'patterns_updated': 0,
            'low_performers_identified': [],
            'high_performers_promoted': []
        }

        # Identify low performers (performance < 0.3)
        low_performers = [
            agent_id for agent_id, agent in self.agents.items()
            if agent.performance_score < 0.3 and agent.task_count > 5
        ]
        optimizations['low_performers_identified'] = low_performers

        # Identify high performers (performance > 0.8)
        high_performers = [
            agent_id for agent_id, agent in self.agents.items()
            if agent.performance_score > 0.8 and agent.task_count > 10
        ]
        optimizations['high_performers_promoted'] = high_performers

        # Strengthen patterns for high performers
        for agent_id in high_performers:
            if agent_id in self.routing_patterns:
                for cap in self.routing_patterns[agent_id]:
                    current = self.routing_patterns[agent_id][cap]
                    self.routing_patterns[agent_id][cap] = min(1.0, current + 0.1)
                optimizations['patterns_updated'] += 1

        return optimizations


# Integration with existing knowledge database
def integrate_swarm_with_knowledge_db(coordinator: SwarmCoordinator) -> None:
    """Integrate swarm learning with the knowledge database."""
    # Add swarm patterns to knowledge database
    swarm_patterns = {
        'swarm_coordination': 'Queen/worker hierarchy with Byzantine consensus for fault-tolerant multi-agent orchestration',
        'intelligent_routing': f'Pattern-based task routing with {coordinator.routing_accuracy:.1%} accuracy',
        'consensus_mechanisms': f'{coordinator.consensus_algorithm.value} consensus with f < n/3 fault tolerance',
        'performance_learning': 'Self-learning agent performance optimization with reinforcement patterns'
    }

    for pattern_name, description in swarm_patterns.items():
        coordinator.knowledge_db.conn.execute('''
            INSERT INTO lessons (source_type, source_id, loop_num, lesson_text, category, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'swarm_coordinator',
            pattern_name,
            48,
            description,
            'swarm_intelligence',
            datetime.now(timezone.utc).isoformat()
        ))

    coordinator.knowledge_db.conn.commit()


# Example usage and testing
def demo_swarm_coordination():
    """Demonstrate swarm coordination capabilities."""
    coordinator = SwarmCoordinator(Path('.'))

    # Register agents with different capabilities
    coordinator.register_agent('coder_agent', {'python', 'javascript', 'debugging'}, SwarmRole.WORKER)
    coordinator.register_agent('tester_agent', {'testing', 'validation', 'qa'}, SwarmRole.WORKER)
    coordinator.register_agent('reviewer_agent', {'code_review', 'security', 'documentation'}, SwarmRole.WORKER)
    coordinator.register_agent('queen_agent', {'orchestration', 'planning', 'coordination'}, SwarmRole.QUEEN)

    print("Swarm Coordinator Demo")
    print("=" * 50)

    # Submit tasks
    tasks = [
        ("Implement user authentication in Python", {'python', 'security'}),
        ("Write unit tests for API endpoints", {'testing', 'python'}),
        ("Review code for security vulnerabilities", {'code_review', 'security'}),
        ("Create API documentation", {'documentation', 'javascript'})
    ]

    for desc, reqs in tasks:
        task_id = coordinator.submit_task(desc, reqs)
        print(f"Submitted task: {task_id}")

        # Simulate completion
        success = True  # Assume success for demo
        coordinator.complete_task(task_id, f"Completed: {desc}", success)

    # Show status
    status = coordinator.get_swarm_status()
    print(f"\nSwarm Status: {status['active_agents']} active agents")
    print(f"Routing Accuracy: {status['routing_accuracy']:.1%}")
    print(f"Completed Tasks: {status['completed_tasks']}")

    # Optimize routing
    optimizations = coordinator.optimize_routing()
    print(f"\nOptimizations: {optimizations['patterns_updated']} patterns updated")

    return coordinator


if __name__ == "__main__":
    demo_swarm_coordination()
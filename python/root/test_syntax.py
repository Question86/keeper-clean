from typing import Optional
from pathlib import Path
from loop_guardrails import MultiAgentOrchestrator


def orchestrator_factory(
    workspace_root: Optional[str] = None,
    max_parallel_agents: int = 4
) -> MultiAgentOrchestrator:
    """Factory function to create a MultiAgentOrchestrator instance."""
    path = Path(workspace_root) if workspace_root else None
    return MultiAgentOrchestrator(workspace_root=path, max_parallel_agents=max_parallel_agents)
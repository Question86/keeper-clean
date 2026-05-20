#!/usr/bin/env python3
"""
Milestone-KnowledgeDB Integration with TokenGovernor

Enhances the existing KnowledgeDB system with:
- Priority weighting based on short/mid/long-term planning horizons
- TokenGovernor integration for adaptive resource allocation
- Context-aware search ranking based on current loop position
- Intelligent resource budgeting for knowledge acquisition

Built on top of the existing sophisticated KnowledgeDB infrastructure.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from knowledge_db import KnowledgeDB, SearchResult
from output_safety import safe_print
from token_governor import TokenGovernor, BudgetAllocation, BudgetZone


class PlanningHorizon(Enum):
    """Planning horizons for knowledge prioritization."""
    SHORT_TERM = "short_term"    # Current loop, immediate tasks
    MID_TERM = "mid_term"        # Active milestones, 2-5 loops
    LONG_TERM = "long_term"      # Strategic planning, >5 loops


@dataclass
class PriorityWeights:
    """Priority weighting configuration for knowledge search."""
    short_term: float = 0.6      # High priority for immediate needs
    mid_term: float = 0.3        # Medium priority for milestone work
    long_term: float = 0.1       # Lower priority for strategic planning
    
    recency_factor: float = 0.2   # Boost recent content
    relevance_threshold: float = 0.3  # Minimum relevance to include


@dataclass 
class EnhancedSearchResult:
    """Enhanced search result with priority and planning horizon context."""
    base_result: SearchResult
    planning_horizon: PlanningHorizon
    priority_score: float
    token_cost_estimate: int
    acquisition_recommendation: str


class MilestoneKnowledgeIntegrator:
    """Enhanced knowledge search with milestone awareness and token governance."""
    
    def __init__(self, 
                 workspace_root: Path = None,
                 token_budget: int = 200000):
        """Initialize the integrator.
        
        Args:
            workspace_root: Path to Keeper workspace
            token_budget: Total token budget for loop
        """
        self.workspace_root = Path(workspace_root or ".")
        self.knowledge_db = KnowledgeDB(self.workspace_root)
        self.token_governor = TokenGovernor(budget=token_budget, workspace_root=self.workspace_root)
        self.logger = self._setup_logging()
        
        # Priority weighting configuration
        self.priority_weights = PriorityWeights()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the integrator."""
        logger = logging.getLogger('MilestoneKnowledgeIntegrator')
        logger.setLevel(logging.INFO)
        return logger
        
    def get_current_loop_context(self) -> Dict[str, Any]:
        """Get current loop context for priority calculation."""
        loop_data = self.token_governor.get_loop_progress()
        metrics = self.token_governor.get_current_metrics()
        
        return {
            "loop_number": loop_data.get("STATE", {}).get("loop", 1),
            "status": loop_data.get("STATE", {}).get("status", "UNKNOWN"),
            "token_usage": metrics.percentage,
            "token_zone": metrics.zone,
            "last_task_worked": loop_data.get("lastTaskWorked")
        }

    def _load_milestone_horizon_weights(self, milestone_id: Optional[str]) -> Optional[Dict[str, float]]:
        """Load milestone-specific horizon weights when available."""
        if not milestone_id:
            return None
        mid = str(milestone_id).replace("M", "").zfill(2)
        path = self.workspace_root / f"milestone_{mid}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            horizons = data.get("PLANNING_HORIZONS", {})
            short_w = float(horizons.get("short_term", {}).get("priority_weight", self.priority_weights.short_term))
            mid_w = float(horizons.get("mid_term", {}).get("priority_weight", self.priority_weights.mid_term))
            long_w = float(horizons.get("long_term", {}).get("priority_weight", self.priority_weights.long_term))
            total = short_w + mid_w + long_w
            if total <= 0:
                return None
            return {
                "short_term": short_w / total,
                "mid_term": mid_w / total,
                "long_term": long_w / total,
            }
        except Exception:
            return None
        
    def classify_planning_horizon(self, search_result: SearchResult) -> PlanningHorizon:
        """Classify a search result into planning horizon based on content and context."""
        context = self.get_current_loop_context()
        current_loop = context["loop_number"]
        
        # Check if result is related to current/recent loops (short-term)
        if hasattr(search_result, 'loop_num') and search_result.loop_num:
            loop_diff = current_loop - search_result.loop_num
            if loop_diff <= 1:  # Current or previous loop
                return PlanningHorizon.SHORT_TERM
            elif loop_diff <= 5:  # Recent loops
                return PlanningHorizon.MID_TERM
            else:  # Older loops
                return PlanningHorizon.LONG_TERM
        
        # Check content patterns for horizon classification.
        # SearchResult provides `snippet` + `context`, not `content`.
        snippet = getattr(search_result, "snippet", "") or ""
        context_blob = " ".join(
            str(v) for v in (getattr(search_result, "context", {}) or {}).values()
            if isinstance(v, (str, int, float))
        )
        content_lower = f"{snippet} {context_blob}".lower()
        
        # Short-term indicators
        short_term_patterns = [
            "urgent", "immediate", "current task", "active work",
            "loop " + str(current_loop), "now", "today"
        ]
        
        # Mid-term indicators  
        mid_term_patterns = [
            "milestone", "goal", "phase", "implementation", 
            "next loops", "upcoming", "planned"
        ]
        
        # Long-term indicators
        long_term_patterns = [
            "strategic", "architecture", "future", "vision",
            "long-term", "roadmap", "foundation"
        ]
        
        # Score each horizon
        short_score = sum(1 for pattern in short_term_patterns if pattern in content_lower)
        mid_score = sum(1 for pattern in mid_term_patterns if pattern in content_lower)
        long_score = sum(1 for pattern in long_term_patterns if pattern in content_lower)
        
        # Return highest scoring horizon
        max_score = max(short_score, mid_score, long_score)
        if max_score == 0:
            return PlanningHorizon.MID_TERM  # Default to mid-term
        elif short_score == max_score:
            return PlanningHorizon.SHORT_TERM
        elif mid_score == max_score:
            return PlanningHorizon.MID_TERM
        else:
            return PlanningHorizon.LONG_TERM
            
    def calculate_priority_score(self, 
                                search_result: SearchResult,
                                planning_horizon: PlanningHorizon) -> float:
        """Calculate priority score for a search result."""
        base_relevance = search_result.relevance
        
        # Apply planning horizon weighting
        horizon_weight = {
            PlanningHorizon.SHORT_TERM: self.priority_weights.short_term,
            PlanningHorizon.MID_TERM: self.priority_weights.mid_term, 
            PlanningHorizon.LONG_TERM: self.priority_weights.long_term
        }[planning_horizon]
        
        # Calculate recency boost
        context = self.get_current_loop_context()
        current_loop = context["loop_number"]
        
        recency_boost = 0.0
        if hasattr(search_result, 'loop_num') and search_result.loop_num:
            loop_diff = current_loop - search_result.loop_num
            if loop_diff <= 3:  # Recent loops get boost
                recency_boost = self.priority_weights.recency_factor * (1.0 / (loop_diff + 1))
        
        # Token zone adjustment - prioritize differently based on budget constraints
        zone_adjustment = {
            BudgetZone.SAFE: 1.0,        # Normal weighting
            BudgetZone.CAUTION: 0.9,     # Slight reduction
            BudgetZone.CONSERVATION: 0.7, # Focus on high-value only
            BudgetZone.EMERGENCY: 0.5,   # Strict prioritization
            BudgetZone.ABORT: 0.2        # Emergency only
        }[context["token_zone"]]
        
        # Final priority calculation
        priority_score = (base_relevance * horizon_weight + recency_boost) * zone_adjustment
        
        return min(1.0, max(0.0, priority_score))  # Clamp to [0, 1]
        
    def estimate_token_cost(self, search_result: SearchResult) -> int:
        """Estimate token cost for processing this search result."""
        snippet = getattr(search_result, "snippet", "") or ""
        context_blob = " ".join(
            str(v) for v in (getattr(search_result, "context", {}) or {}).values()
            if isinstance(v, (str, int, float))
        )
        content_length = len(f"{snippet} {context_blob}")
        
        # Rough estimate: 4 characters per token (average)
        base_tokens = content_length // 4
        
        # Add processing overhead
        processing_overhead = 50  # tokens for analysis, summarization
        
        return base_tokens + processing_overhead
        
    def get_acquisition_recommendation(self,
                                     enhanced_result: EnhancedSearchResult) -> str:
        """Get recommendation for whether to acquire this knowledge."""
        priority = enhanced_result.priority_score
        cost = enhanced_result.token_cost_estimate
        context = self.get_current_loop_context()
        
        if priority >= 0.8:
            return "HIGH: Acquire immediately - high relevance and priority"
        elif priority >= 0.6:
            return "MEDIUM: Consider acquisition if budget allows"
        elif priority >= 0.4:
            return "LOW: Defer unless specifically needed"
        elif context["token_zone"] in [BudgetZone.EMERGENCY, BudgetZone.ABORT]:
            return "SKIP: Emergency mode - focus only on critical items"
        else:
            return "MINIMAL: Very low priority - skip unless abundant budget"
            
    def enhanced_search(self,
                       query: str,
                       limit: int = 20,
                       milestone_id: str = None,
                       goal_id: str = None) -> List[EnhancedSearchResult]:
        """Perform enhanced search with priority weighting and token governance."""
        
        # Apply milestone-specific horizon weights when provided.
        baseline = (
            self.priority_weights.short_term,
            self.priority_weights.mid_term,
            self.priority_weights.long_term,
        )
        weights = self._load_milestone_horizon_weights(milestone_id)
        if weights:
            self.priority_weights.short_term = weights["short_term"]
            self.priority_weights.mid_term = weights["mid_term"]
            self.priority_weights.long_term = weights["long_term"]

        # Get base search results from KnowledgeDB
        try:
            if milestone_id or goal_id:
                base_results = self.knowledge_db.search_by_milestone(
                    milestone_id=milestone_id,
                    goal_id=goal_id,
                    query=query,
                    limit=limit * 2  # Get more to allow for filtering
                )
            else:
                base_results = self.knowledge_db.search(query, limit=limit * 2)
        except sqlite3.DatabaseError as e:
            self.logger.error("KnowledgeDB search failed: %s", e)
            return []
        
        try:
            # Enhance results with priority information
            enhanced_results = []
            
            for result in base_results:
                # Classify planning horizon
                horizon = self.classify_planning_horizon(result)
                
                # Calculate priority score
                priority_score = self.calculate_priority_score(result, horizon)
                
                # Skip results below threshold
                if priority_score < self.priority_weights.relevance_threshold:
                    continue
                    
                # Estimate token cost
                token_cost = self.estimate_token_cost(result)
                
                # Create enhanced result
                enhanced_result = EnhancedSearchResult(
                    base_result=result,
                    planning_horizon=horizon,
                    priority_score=priority_score,
                    token_cost_estimate=token_cost,
                    acquisition_recommendation=""
                )
                
                # Add acquisition recommendation
                enhanced_result.acquisition_recommendation = self.get_acquisition_recommendation(enhanced_result)
                
                enhanced_results.append(enhanced_result)
            
            # Sort by priority score (descending)
            enhanced_results.sort(key=lambda x: x.priority_score, reverse=True)
            
            # Apply token budget constraints
            return self._apply_budget_constraints(enhanced_results[:limit])
        finally:
            # Restore default weights after this request.
            (
                self.priority_weights.short_term,
                self.priority_weights.mid_term,
                self.priority_weights.long_term,
            ) = baseline
        
    def _apply_budget_constraints(self, 
                                 results: List[EnhancedSearchResult]) -> List[EnhancedSearchResult]:
        """Apply token budget constraints to filter results."""
        allocation = self.token_governor.calculate_adaptive_allocation()
        context = self.get_current_loop_context()
        
        # Determine available budget based on planning horizon
        available_budgets = {
            PlanningHorizon.SHORT_TERM: allocation.short_term,
            PlanningHorizon.MID_TERM: allocation.mid_term,
            PlanningHorizon.LONG_TERM: allocation.long_term
        }
        
        # Track budget usage per horizon
        used_budgets = {horizon: 0 for horizon in PlanningHorizon}
        filtered_results = []
        
        for result in results:
            horizon = result.planning_horizon
            cost = result.token_cost_estimate
            
            # Check if we have budget for this result
            if used_budgets[horizon] + cost <= available_budgets[horizon]:
                used_budgets[horizon] += cost
                filtered_results.append(result)
            else:
                # Update recommendation to reflect budget constraint
                result.acquisition_recommendation = f"BUDGET_LIMITED: Exceeds {horizon.value} allocation"
                filtered_results.append(result)
        
        return filtered_results

    def _json_safe(self, value: Any) -> Any:
        """Convert nested values (including Enum) into JSON-safe primitives."""
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {k: self._json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._json_safe(v) for v in value]
        if isinstance(value, tuple):
            return [self._json_safe(v) for v in value]
        return value
        
    def generate_knowledge_acquisition_report(self, 
                                            query: str,
                                            results: List[EnhancedSearchResult]) -> Dict[str, Any]:
        """Generate comprehensive knowledge acquisition report."""
        context = self._json_safe(self.get_current_loop_context())
        allocation = self.token_governor.calculate_adaptive_allocation()
        
        # Calculate statistics
        total_results = len(results)
        high_priority = len([r for r in results if r.priority_score >= 0.8])
        medium_priority = len([r for r in results if 0.6 <= r.priority_score < 0.8])
        low_priority = len([r for r in results if r.priority_score < 0.6])
        
        total_cost = sum(r.token_cost_estimate for r in results)
        
        # Horizon distribution
        horizon_distribution = {
            "short_term": len([r for r in results if r.planning_horizon == PlanningHorizon.SHORT_TERM]),
            "mid_term": len([r for r in results if r.planning_horizon == PlanningHorizon.MID_TERM]),
            "long_term": len([r for r in results if r.planning_horizon == PlanningHorizon.LONG_TERM])
        }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "loop_context": context,
            "budget_allocation": self._json_safe(asdict(allocation)),
            "results_summary": {
                "total_results": total_results,
                "high_priority": high_priority,
                "medium_priority": medium_priority,
                "low_priority": low_priority,
                "estimated_total_cost": total_cost
            },
            "horizon_distribution": horizon_distribution,
            "recommendations": self._generate_acquisition_recommendations(results)
        }
        
    def _generate_acquisition_recommendations(self, 
                                           results: List[EnhancedSearchResult]) -> List[str]:
        """Generate actionable recommendations for knowledge acquisition."""
        recommendations = []
        
        context = self.get_current_loop_context()
        high_priority_results = [r for r in results if r.priority_score >= 0.8]
        
        if high_priority_results:
            recommendations.append(f"{len(high_priority_results)} high-priority items identified - prioritize acquisition")
        
        if context["token_zone"] in [BudgetZone.CONSERVATION, BudgetZone.EMERGENCY, BudgetZone.ABORT]:
            recommendations.append("Token budget constrained - focus only on critical knowledge")
        
        # Horizon-specific recommendations
        short_term_count = len([r for r in results if r.planning_horizon == PlanningHorizon.SHORT_TERM])
        if short_term_count > 5:
            recommendations.append("High short-term relevance - prioritize immediate task completion")
        
        return recommendations


def main():
    """CLI interface for MilestoneKnowledgeIntegrator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Milestone-Knowledge Integration with Token Governance")
    parser.add_argument(
        "query",
        nargs="?",
        default="autostart knowledge integration query",
        help="Search query (optional for autostart mode)",
    )
    parser.add_argument("--milestone", help="Milestone ID to search within")
    parser.add_argument("--goal", help="Goal ID within milestone") 
    parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    parser.add_argument("--budget", type=int, default=200000, help="Token budget")
    parser.add_argument("--workspace", default=".", help="Workspace path")
    
    args = parser.parse_args()
    
    integrator = MilestoneKnowledgeIntegrator(
        workspace_root=Path(args.workspace),
        token_budget=args.budget
    )
    
    # Perform enhanced search
    results = integrator.enhanced_search(
        query=args.query,
        limit=args.limit,
        milestone_id=args.milestone,
        goal_id=args.goal
    )
    
    # Generate report
    report = integrator.generate_knowledge_acquisition_report(args.query, results)
    
    # Display results
    safe_print("Enhanced Knowledge Search Results")
    safe_print(f"Query: {args.query}")
    safe_print(f"Results: {len(results)}")
    safe_print()
    
    for i, result in enumerate(results, 1):
        title = getattr(result.base_result, "title", None) or getattr(result.base_result, "source_path", "unknown")
        snippet = getattr(result.base_result, "snippet", "") or ""
        safe_print(f"{i}. {title}")
        safe_print(f"   Priority: {result.priority_score:.2f} | Horizon: {result.planning_horizon.value}")
        safe_print(f"   Cost: {result.token_cost_estimate} tokens")
        safe_print(f"   {result.acquisition_recommendation}")
        safe_print(f"   Snippet: {snippet[:100]}...")
        safe_print()
    
    safe_print("Acquisition Report:")
    safe_print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

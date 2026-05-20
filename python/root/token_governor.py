#!/usr/bin/env python3
"""
TokenGovernor - Adaptive Token Budget Management System

Implements intelligent token budget allocation across planning horizons:
- Short-term (30%): Current loop tasks and immediate work
- Mid-term (50%): Active milestone progress and feature development  
- Long-term (20%): Strategic planning and knowledge base expansion

Integrates with Keeper loop methodology for real-time budget optimization.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum


class BudgetZone(Enum):
    """Token usage zones with associated behavior recommendations."""
    SAFE = "SAFE"           # 0-50%: Normal operation
    CAUTION = "CAUTION"     # 50-75%: Monitor usage
    CONSERVATION = "CONSERVATION"  # 75-85%: Reduce verbosity
    EMERGENCY = "EMERGENCY" # 85-95%: Critical decisions only
    ABORT = "ABORT"         # 95%+: Emergency shutdown


@dataclass
class BudgetAllocation:
    """Budget allocation across planning horizons."""
    short_term: int     # 30% - Current loop immediate tasks
    mid_term: int       # 50% - Active milestone work
    long_term: int      # 20% - Strategic/knowledge building
    
    @property
    def total(self) -> int:
        return self.short_term + self.mid_term + self.long_term


@dataclass
class TokenMetrics:
    """Current token usage metrics."""
    used: int
    remaining: int
    percentage: float
    zone: BudgetZone
    session_tokens: int
    
    
class TokenGovernor:
    """Adaptive token budget management with milestone integration."""
    
    def __init__(self, 
                 budget: int = 200000,
                 workspace_root: Path = None):
        """Initialize TokenGovernor.
        
        Args:
            budget: Total token budget per loop (default 200k)
            workspace_root: Path to Keeper workspace root
        """
        self.budget = budget
        self.workspace_root = Path(workspace_root or ".")
        self.logger = self._setup_logging()
        
        # Default allocation percentages
        self.allocation_ratios = {
            'short_term': 0.30,   # 30%
            'mid_term': 0.50,     # 50% 
            'long_term': 0.20     # 20%
        }
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for TokenGovernor operations."""
        logger = logging.getLogger('TokenGovernor')
        logger.setLevel(logging.INFO)
        return logger
        
    def get_current_metrics(self) -> TokenMetrics:
        """Get current token usage metrics from monitoring system."""
        try:
            from scripts.read_token_csv import get_token_usage
            data = get_token_usage(budget=self.budget)
            
            zone = BudgetZone(data.get('zone', 'SAFE'))
            
            return TokenMetrics(
                used=data.get('current_session', 0),
                remaining=data.get('remaining', self.budget),
                percentage=data.get('percentage', 0.0),
                zone=zone,
                session_tokens=data.get('current_session', 0)
            )
        except Exception as e:
            self.logger.warning(f"Failed to get token metrics: {e}")
            return TokenMetrics(0, self.budget, 0.0, BudgetZone.SAFE, 0)
            
    def get_loop_progress(self) -> Dict[str, Any]:
        """Get current loop progress from current.json."""
        current_json_path = self.workspace_root / "current.json"
        
        try:
            with open(current_json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load current.json: {e}")
            return {"STATE": {"loop": 1, "status": "UNKNOWN"}}
            
    def get_milestone_status(self) -> List[Dict[str, Any]]:
        """Get status of all milestone files."""
        milestones = []
        milestone_pattern = "milestone_*.json"
        
        for milestone_file in self.workspace_root.glob(milestone_pattern):
            try:
                with open(milestone_file, 'r') as f:
                    milestone_data = json.load(f)
                    milestones.append(milestone_data)
            except Exception as e:
                self.logger.warning(f"Failed to load {milestone_file}: {e}")
                
        return milestones
        
    def calculate_adaptive_allocation(self) -> BudgetAllocation:
        """Calculate adaptive budget allocation based on loop progress and milestones."""
        # Get current state
        metrics = self.get_current_metrics()
        loop_data = self.get_loop_progress()
        milestones = self.get_milestone_status()
        
        # Base allocation
        base_short = int(self.budget * self.allocation_ratios['short_term'])
        base_mid = int(self.budget * self.allocation_ratios['mid_term'])
        base_long = int(self.budget * self.allocation_ratios['long_term'])
        
        # Adaptive adjustments based on zone
        if metrics.zone == BudgetZone.CONSERVATION:
            # Shift focus to short-term completion
            base_short = int(self.budget * 0.50)  # Increase to 50%
            base_mid = int(self.budget * 0.40)    # Reduce to 40%
            base_long = int(self.budget * 0.10)   # Reduce to 10%
            
        elif metrics.zone == BudgetZone.EMERGENCY:
            # Focus entirely on current task completion
            base_short = int(self.budget * 0.80)  # Increase to 80%
            base_mid = int(self.budget * 0.20)    # Reduce to 20%
            base_long = 0                         # Eliminate long-term
            
        elif metrics.zone == BudgetZone.ABORT:
            # Emergency completion only
            base_short = metrics.remaining
            base_mid = 0
            base_long = 0
            
        return BudgetAllocation(
            short_term=base_short,
            mid_term=base_mid, 
            long_term=base_long
        )
        
    def get_recommendations(self) -> List[str]:
        """Get contextual recommendations based on current token situation."""
        metrics = self.get_current_metrics()
        allocation = self.calculate_adaptive_allocation()
        recommendations = []
        
        if metrics.zone == BudgetZone.SAFE:
            recommendations.extend([
                "✅ Token usage healthy - continue normal operation",
                f"💡 Budget allocation: Short-term {allocation.short_term:,}, Mid-term {allocation.mid_term:,}, Long-term {allocation.long_term:,}",
                "🎯 Consider exploring knowledge base expansion or documentation"
            ])
            
        elif metrics.zone == BudgetZone.CAUTION:
            recommendations.extend([
                "⚠️ Entering caution zone - monitor token usage carefully",
                "📊 Switch to more focused responses and artifact usage",
                "🎯 Prioritize current task completion over exploration"
            ])
            
        elif metrics.zone == BudgetZone.CONSERVATION:
            recommendations.extend([
                "🟡 Conservation mode activated - reduce response verbosity",
                "📋 Focus on task completion, avoid tangential work",
                "⚡ Use brief acknowledgments and pointer references"
            ])
            
        elif metrics.zone == BudgetZone.EMERGENCY:
            recommendations.extend([
                "🔴 Emergency mode - complete current task immediately",
                "📝 Prepare for loop finalization",
                "⚠️ Avoid starting new work unless critical"
            ])
            
        elif metrics.zone == BudgetZone.ABORT:
            recommendations.extend([
                "🚨 ABORT ZONE - Finalize loop NOW",
                "📋 Write minimal completion report",
                "🛑 Stop all non-essential activities"
            ])
            
        return recommendations
        
    def should_finalize_loop(self) -> Tuple[bool, str]:
        """Determine if loop should be finalized based on token usage."""
        metrics = self.get_current_metrics()
        
        if metrics.zone in [BudgetZone.ABORT]:
            return True, "🚨 CRITICAL: Token budget exhausted"
            
        elif metrics.zone == BudgetZone.EMERGENCY:
            return True, "⚠️ HIGH: Budget critically low, begin finalization"
            
        elif metrics.percentage >= 80:
            return True, "🟡 MEDIUM: Approaching budget limit, wrap up work"
            
        return False, "✅ Continue working"
        
    def generate_budget_report(self) -> Dict[str, Any]:
        """Generate comprehensive budget status report."""
        metrics = self.get_current_metrics()
        allocation = self.calculate_adaptive_allocation()
        recommendations = self.get_recommendations()
        should_finalize, finalize_reason = self.should_finalize_loop()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "token_metrics": {
                "used": metrics.used,
                "remaining": metrics.remaining,
                "percentage": metrics.percentage,
                "zone": metrics.zone.value,
                "budget": self.budget
            },
            "allocation": {
                "short_term": allocation.short_term,
                "mid_term": allocation.mid_term,
                "long_term": allocation.long_term,
                "total": allocation.total
            },
            "recommendations": recommendations,
            "finalization": {
                "should_finalize": should_finalize,
                "reason": finalize_reason
            }
        }


def main():
    """CLI interface for TokenGovernor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Token Governor - Adaptive Budget Management")
    parser.add_argument("--budget", type=int, default=200000, help="Total token budget")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace root path")
    parser.add_argument("--report", action="store_true", help="Generate budget report")
    
    args = parser.parse_args()
    
    governor = TokenGovernor(budget=args.budget, workspace_root=Path(args.workspace))
    
    if args.report:
        report = governor.generate_budget_report()
        print(json.dumps(report, indent=2))
    else:
        # Interactive mode
        metrics = governor.get_current_metrics()
        allocation = governor.calculate_adaptive_allocation()
        recommendations = governor.get_recommendations()
        
        print(f"🎯 Token Governor Status")
        print(f"Used: {metrics.used:,} ({metrics.percentage:.1f}%)")
        print(f"Zone: {metrics.zone.value}")
        print(f"\n💰 Budget Allocation:")
        print(f"  Short-term: {allocation.short_term:,}")
        print(f"  Mid-term: {allocation.mid_term:,}")
        print(f"  Long-term: {allocation.long_term:,}")
        print(f"\n💡 Recommendations:")
        for rec in recommendations:
            print(f"  {rec}")


if __name__ == "__main__":
    main()
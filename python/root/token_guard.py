# MODE: SCRIPT

"""Token Guard - Reactive Protection Mechanism for Token Usage

This module provides automatic detection and mitigation of high token consuming tasks,
preventing rate limit hits and optimizing resource usage.
"""

from __future__ import annotations

import time
import json
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from token_monitor import LoopBudgetTracker


@dataclass
class TokenThreshold:
    """Configuration for token usage thresholds."""
    warning_level: float = 0.60  # Warn at 60% budget
    critical_level: float = 0.80  # Critical at 80% budget
    emergency_level: float = 0.90  # Emergency at 90% budget
    max_task_tokens: int = 5000  # Max tokens per task
    max_operation_tokens: int = 1000  # Max tokens per operation


class TokenGuard:
    """Reactive protection system for token usage management."""

    def __init__(self, workspace_root: Path, config: TokenThreshold = None):
        self.workspace_root = workspace_root
        self.config = config or TokenThreshold()
        self.tracker = LoopBudgetTracker(workspace_root)
        self.alerts: List[Dict[str, Any]] = []
        self.protection_active = True
        self.emergency_mode = False

        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def check_operation(self, operation_name: str, estimated_tokens: int = 0) -> Dict[str, Any]:
        """Check if an operation should proceed based on token budget."""
        status = self.tracker.get_budget_status()
        current_usage = status['tokens_used']
        budget_limit = status['budget_limit']
        percentage = status['percentage'] / 100.0

        decision = {
            'should_proceed': True,
            'reason': 'within_limits',
            'risk_level': 'low',
            'estimated_final_usage': current_usage + estimated_tokens,
            'estimated_final_percentage': ((current_usage + estimated_tokens) / budget_limit) * 100,
            'warnings': []
        }

        # Check thresholds
        if percentage >= self.config.emergency_level:
            decision['should_proceed'] = False
            decision['reason'] = 'emergency_threshold_exceeded'
            decision['risk_level'] = 'emergency'
            self.emergency_mode = True
        elif percentage >= self.config.critical_level:
            decision['risk_level'] = 'critical'
            decision['warnings'].append('Approaching emergency threshold')
        elif percentage >= self.config.warning_level:
            decision['risk_level'] = 'warning'
            decision['warnings'].append('High token usage detected')

        # Check task limits
        if self.tracker.current_task:
            task_info = self.tracker.get_loop_usage(self.tracker.get_current_loop()).get('tasks', {}).get(self.tracker.current_task, {})
            task_tokens = task_info.get('tokens_used', 0) + estimated_tokens
            if task_tokens > self.config.max_task_tokens:
                decision['should_proceed'] = False
                decision['reason'] = 'task_token_limit_exceeded'
                decision['warnings'].append(f'Task would exceed {self.config.max_task_tokens} token limit')

        # Check operation limits
        if estimated_tokens > self.config.max_operation_tokens:
            decision['should_proceed'] = False
            decision['reason'] = 'operation_token_limit_exceeded'
            decision['warnings'].append(f'Operation exceeds {self.config.max_operation_tokens} token limit')

        # Log decision
        self._log_decision(operation_name, decision)

        return decision

    def record_operation(self, operation_name: str, tokens_used: int, success: bool = True) -> None:
        """Record token usage for an operation."""
        phase = "operation"
        if self.tracker.current_task:
            phase = f"task_{self.tracker.current_task}"

        result = self.tracker.record_usage(tokens_used, phase)

        # Check for alerts
        percentage = result['percentage']
        if percentage >= self.config.emergency_level and not self.emergency_mode:
            self._trigger_alert('emergency', f'Emergency threshold reached: {percentage:.1f}%')
            self.emergency_mode = True
        elif percentage >= self.config.critical_level:
            self._trigger_alert('critical', f'Critical threshold reached: {percentage:.1f}%')
        elif percentage >= self.config.warning_level:
            self._trigger_alert('warning', f'Warning threshold reached: {percentage:.1f}%')

    def _trigger_alert(self, level: str, message: str) -> None:
        """Trigger an alert for high token usage."""
        alert = {
            'timestamp': time.time(),
            'level': level,
            'message': message,
            'current_task': self.tracker.current_task,
            'usage': self.tracker.get_budget_status()
        }
        self.alerts.append(alert)

        # Log to file
        alert_file = self.workspace_root / 'token_alerts.jsonl'
        with open(alert_file, 'a') as f:
            json.dump(alert, f)
            f.write('\n')

        print(f"🚨 TOKEN ALERT [{level.upper()}]: {message}")

    def _log_decision(self, operation_name: str, decision: Dict[str, Any]) -> None:
        """Log protection decisions."""
        log_entry = {
            'timestamp': time.time(),
            'operation': operation_name,
            'decision': decision,
            'current_task': self.tracker.current_task
        }

        log_file = self.workspace_root / 'token_protection_log.jsonl'
        with open(log_file, 'a') as f:
            json.dump(log_entry, f)
            f.write('\n')

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self.protection_active:
            try:
                status = self.tracker.get_budget_status()
                percentage = status['percentage']

                # Auto-adjust protection based on usage
                if percentage >= 0.95:
                    self.config.max_operation_tokens = 500  # Very restrictive
                elif percentage >= 0.85:
                    self.config.max_operation_tokens = 750
                elif percentage >= 0.75:
                    self.config.max_operation_tokens = 1000
                else:
                    self.config.max_operation_tokens = 2000  # Normal

            except Exception as e:
                print(f"Token monitoring error: {e}")

            time.sleep(30)  # Check every 30 seconds

    def get_alerts(self, since: float = 0) -> List[Dict[str, Any]]:
        """Get alerts since timestamp."""
        return [alert for alert in self.alerts if alert['timestamp'] >= since]

    def get_protection_status(self) -> Dict[str, Any]:
        """Get current protection status."""
        return {
            'protection_active': self.protection_active,
            'emergency_mode': self.emergency_mode,
            'config': self.config.__dict__,
            'current_alerts': len(self.alerts),
            'budget_status': self.tracker.get_budget_status()
        }


# Global instance for easy access
_token_guard = None

def get_token_guard(workspace_root: Path = None) -> TokenGuard:
    """Get or create global token guard instance."""
    global _token_guard
    if _token_guard is None and workspace_root:
        _token_guard = TokenGuard(workspace_root)
    return _token_guard


if __name__ == "__main__":
    # Test the token guard
    guard = TokenGuard(Path('.'))
    print("Token Guard initialized")
    print(guard.get_protection_status())
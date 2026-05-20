"""Deterministic write-policy gate for knowledge database operations.

Fail-closed by default: if policy cannot be loaded or validated, writes are denied.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


_STATE_LOCK = threading.Lock()
_DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "config" / "db_write_policy.json"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    policy_path: str


def _read_json(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("Policy/state JSON must be an object")
    return obj


def _resolve_policy_path(workspace_root: Path) -> Optional[Path]:
    candidate = workspace_root / "config" / "db_write_policy.json"
    if candidate.exists():
        return candidate
    if _DEFAULT_POLICY_PATH.exists():
        return _DEFAULT_POLICY_PATH
    return None


def _load_policy(workspace_root: Path) -> Tuple[Optional[Dict[str, Any]], str]:
    policy_path = _resolve_policy_path(workspace_root)
    if policy_path is None:
        return None, "policy file not found"
    try:
        policy = _read_json(policy_path)
    except Exception as e:
        return None, f"policy unreadable: {e}"
    if not isinstance(policy.get("operations"), dict):
        return None, "policy invalid: missing operations map"
    return policy, str(policy_path)


def _load_loop_state(workspace_root: Path) -> Tuple[int, str]:
    state_path = workspace_root / "current.json"
    if not state_path.exists():
        return 0, "UNKNOWN"
    try:
        data = _read_json(state_path)
        state = data.get("STATE", {})
        loop_num = int(state.get("loop", 0))
        status = str(state.get("status", "UNKNOWN"))
        return loop_num, status
    except Exception:
        return 0, "UNKNOWN"


def _read_counter_state(state_path: Path) -> Dict[str, Any]:
    if not state_path.exists():
        return {"counters": {}}
    try:
        data = _read_json(state_path)
    except Exception:
        return {"counters": {}}
    if not isinstance(data.get("counters"), dict):
        data["counters"] = {}
    return data


def _counter_key(loop_num: int, operation: str, actor: str) -> str:
    return f"L{loop_num}:{operation}:{actor}"


def _check_target_path(workspace_root: Path, target_path: Optional[Path], allowed_prefixes: Any) -> bool:
    if not allowed_prefixes:
        return True
    if target_path is None:
        return False
    try:
        rel = target_path.resolve().relative_to(workspace_root.resolve())
        rel_str = str(rel).replace("\\", "/")
    except Exception:
        return False
    for prefix in allowed_prefixes:
        if rel_str.startswith(str(prefix)):
            return True
    return False


def _get_actor_tier(policy: Dict[str, Any], actor: str) -> Optional[int]:
    tiers = policy.get("actor_tiers", {})
    if not isinstance(tiers, dict):
        return None
    raw = tiers.get(actor)
    if isinstance(raw, int):
        return raw
    try:
        return int(raw)
    except Exception:
        return None


def enforce_db_write_policy(
    workspace_root: Path,
    operation: str,
    actor: str,
    target_path: Optional[Path] = None,
) -> PolicyDecision:
    """Check and record whether a DB write operation is permitted."""
    workspace_root = Path(workspace_root)
    policy, policy_path = _load_policy(workspace_root)
    policy_path = policy_path or "unresolved"
    if policy is None:
        return PolicyDecision(False, "POLICY_DENY: fail-closed (missing/invalid policy)", policy_path)

    if not bool(policy.get("enabled", True)):
        return PolicyDecision(False, "POLICY_DENY: policy disabled", policy_path)

    op_rules = policy["operations"].get(operation)
    if not isinstance(op_rules, dict):
        return PolicyDecision(False, f"POLICY_DENY: unknown operation '{operation}'", policy_path)

    allowed_actors = op_rules.get("actors", [])
    if actor not in allowed_actors:
        return PolicyDecision(False, f"POLICY_DENY: actor '{actor}' not allowed", policy_path)

    actor_tier = _get_actor_tier(policy, actor)
    min_actor_tier = op_rules.get("min_actor_tier")
    if min_actor_tier is not None:
        try:
            required_tier = int(min_actor_tier)
        except Exception:
            return PolicyDecision(False, "POLICY_DENY: invalid min_actor_tier configuration", policy_path)
        if actor_tier is None:
            return PolicyDecision(False, f"POLICY_DENY: actor '{actor}' has no configured tier", policy_path)
        if actor_tier < required_tier:
            return PolicyDecision(
                False,
                f"POLICY_DENY: actor tier {actor_tier} below required tier {required_tier}",
                policy_path,
            )

    loop_num, status = _load_loop_state(workspace_root)
    allowed_states = op_rules.get("states") or policy.get("allowed_states") or []
    if status not in allowed_states:
        return PolicyDecision(False, f"POLICY_DENY: state '{status}' not allowed", policy_path)

    if not _check_target_path(workspace_root, target_path, op_rules.get("allowed_path_prefixes")):
        return PolicyDecision(False, "POLICY_DENY: target path outside allowed prefixes", policy_path)

    max_per_loop = op_rules.get("max_per_loop")
    state_path = workspace_root / "logs" / "policy_gate_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    with _STATE_LOCK:
        state = _read_counter_state(state_path)
        counters = state["counters"]
        key = _counter_key(loop_num, operation, actor)
        current = int(counters.get(key, 0))
        if isinstance(max_per_loop, int) and current >= max_per_loop:
            return PolicyDecision(
                False,
                f"POLICY_DENY: quota exceeded ({current}/{max_per_loop}) for {operation}",
                policy_path,
            )
        counters[key] = current + 1
        state["last_decision"] = {
            "operation": operation,
            "actor": actor,
            "actor_tier": actor_tier,
            "required_tier": op_rules.get("min_actor_tier"),
            "loop": loop_num,
            "state": status,
            "target_path": str(target_path) if target_path else None,
            "allowed": True,
        }
        tmp_path = state_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp_path.replace(state_path)

    return PolicyDecision(True, "POLICY_ALLOW", policy_path)


def get_policy_gate_status(workspace_root: Path) -> Dict[str, Any]:
    """Return read-only policy gate status snapshot for diagnostics."""
    workspace_root = Path(workspace_root)
    policy, policy_path = _load_policy(workspace_root)
    loop_num, status = _load_loop_state(workspace_root)
    state_path = workspace_root / "logs" / "policy_gate_state.json"
    counter_state = _read_counter_state(state_path)
    counters = counter_state.get("counters", {})

    loop_prefix = f"L{loop_num}:"
    loop_counters = {
        key: int(value)
        for key, value in counters.items()
        if isinstance(key, str) and key.startswith(loop_prefix)
    }

    operations: Dict[str, Any] = {}
    if isinstance(policy, dict):
        for op_name, rules in (policy.get("operations") or {}).items():
            if not isinstance(rules, dict):
                continue
            operations[op_name] = {
                "actors": list(rules.get("actors", [])),
                "states": list(rules.get("states", [])),
                "max_per_loop": rules.get("max_per_loop"),
                "min_actor_tier": rules.get("min_actor_tier"),
            }

    return {
        "policy_loaded": policy is not None,
        "policy_path": policy_path,
        "loop": loop_num,
        "state": status,
        "enabled": bool(policy.get("enabled", True)) if isinstance(policy, dict) else False,
        "actor_tiers": dict(policy.get("actor_tiers", {})) if isinstance(policy, dict) else {},
        "operations": operations,
        "loop_counters": loop_counters,
        "last_decision": counter_state.get("last_decision"),
    }

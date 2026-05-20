# MODE: SCRIPT
"""Read token usage from Clawdbot sessions.json (live) or Claude API CSV (fallback)."""

import csv
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any
import os

def get_token_usage_from_clawdbot(budget: int = 200000) -> Dict[str, Any]:
    """Read live token usage from Clawdbot sessions.json.
    
    This is the PRIMARY source - reads directly from Clawdbot's session state.
    """
    # Find sessions.json
    sessions_path = Path(os.path.expanduser("~/.clawdbot/agents/main/sessions/sessions.json"))
    
    if not sessions_path.exists():
        return {"error": f"Clawdbot sessions.json not found at {sessions_path}"}
    
    try:
        with open(sessions_path, 'r', encoding='utf-8') as f:
            sessions = json.load(f)
    except Exception as e:
        return {"error": f"Failed to read sessions.json: {e}"}
    
    # Get main session (agent:main:main)
    main_session = sessions.get("agent:main:main", {})
    
    if not main_session:
        return {"error": "No main session found"}
    
    total_tokens = main_session.get("totalTokens", 0)
    # FIXED: Always use our budget instead of session contextTokens (was incorrectly 300)
    context_limit = budget  # Force use of 200k budget
    input_tokens = main_session.get("inputTokens", 0)
    output_tokens = main_session.get("outputTokens", 0)
    
    remaining = max(0, context_limit - total_tokens)
    percentage = min(100, (total_tokens / context_limit) * 100) if context_limit > 0 else 0
    
    # Determine zone
    if percentage < 50:
        zone = "SAFE"
        zone_color = "#50c8a0"
    elif percentage < 75:
        zone = "CAUTION"
        zone_color = "#f0c040"
    elif percentage < 85:
        zone = "CONSERVATION"
        zone_color = "#f08040"
    elif percentage < 95:
        zone = "EMERGENCY"
        zone_color = "#f04040"
    else:
        zone = "ABORT"
        zone_color = "#ff0000"
    
    return {
        "source": "clawdbot",
        "current_session": total_tokens,
        "total_used": total_tokens,
        "remaining": remaining,
        "limit": context_limit,
        "percentage": round(percentage, 1),
        "zone": zone,
        "zone_color": zone_color,
        "breakdown": {
            "last_input": input_tokens,
            "last_output": output_tokens,
            "context_used": total_tokens
        },
        "model": main_session.get("model", "unknown"),
        "compactions": main_session.get("compactionCount", 0),
        "last_updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    }

def get_token_usage_from_csv(csv_path: Path = None, budget: int = 200000) -> Dict[str, Any]:
    """Read Claude API token CSV and calculate current usage.
    
    Args:
        csv_path: Path to CSV file (auto-detects if None)
        budget: Token budget per loop (default 200k)
    
    Returns:
        Dict with usage stats for cockpit display
    """
    if csv_path is None:
        # Auto-detect CSV in workspace
        root = Path(__file__).resolve().parent.parent
        # Find most recent claude_api_tokens CSV
        csvs = list(root.glob("claude_api_tokens_*.csv"))
        if not csvs:
            return {"error": "No token CSV found"}
        csv_path = max(csvs, key=lambda p: p.stat().st_mtime)
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        return {"error": f"CSV read failed: {e}"}
    
    if not rows:
        return {"error": "Empty CSV"}
    
    # Filter to today's usage for "Sammy" (Clawdbot)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sammy_rows = [r for r in rows if r.get('api_key') == 'Sammy' and r.get('usage_date_utc') == today]
    
    # Calculate totals
    total_input = 0
    total_output = 0
    total_cache_write = 0
    total_cache_read = 0
    
    for row in sammy_rows:
        total_input += int(row.get('usage_input_tokens_no_cache', 0) or 0)
        total_cache_write += int(row.get('usage_input_tokens_cache_write_5m', 0) or 0)
        total_cache_read += int(row.get('usage_input_tokens_cache_read', 0) or 0)
        total_output += int(row.get('usage_output_tokens', 0) or 0)
    
    # Total tokens = input + cache_write + cache_read + output
    # Note: cache_read is cheaper but still counts toward context
    total_used = total_input + total_cache_write + total_cache_read + total_output
    remaining = max(0, budget - total_used)
    percentage = min(100, (total_used / budget) * 100) if budget > 0 else 0
    
    # Determine zone
    if percentage < 50:
        zone = "SAFE"
        zone_color = "#50c8a0"  # Green
    elif percentage < 75:
        zone = "CAUTION"
        zone_color = "#f0c040"  # Yellow
    elif percentage < 85:
        zone = "CONSERVATION"
        zone_color = "#f08040"  # Orange
    elif percentage < 95:
        zone = "EMERGENCY"
        zone_color = "#f04040"  # Red
    else:
        zone = "ABORT"
        zone_color = "#ff0000"  # Bright red
    
    return {
        "current_session": total_used,
        "total_used": total_used,
        "remaining": remaining,
        "limit": budget,
        "percentage": round(percentage, 1),
        "zone": zone,
        "zone_color": zone_color,
        "breakdown": {
            "input": total_input,
            "cache_write": total_cache_write,
            "cache_read": total_cache_read,
            "output": total_output
        },
        "last_updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "csv_path": str(csv_path),
        "rows_today": len(sammy_rows)
    }

def get_token_usage(budget: int = 200000) -> Dict[str, Any]:
    """Get token usage - Clawdbot primary, CSV fallback."""
    # Try Clawdbot first (live data)
    result = get_token_usage_from_clawdbot(budget)
    if "error" not in result:
        # Add finalization recommendation
        result["should_finalize"] = result["percentage"] >= 75
        result["finalize_urgency"] = _get_finalize_urgency(result["percentage"])
        return result
    
    # Fallback to CSV
    csv_result = get_token_usage_from_csv(budget=budget)
    csv_result["source"] = "csv_fallback"
    csv_result["clawdbot_error"] = result.get("error")
    csv_result["should_finalize"] = csv_result.get("percentage", 0) >= 75
    csv_result["finalize_urgency"] = _get_finalize_urgency(csv_result.get("percentage", 0))
    return csv_result

def _get_finalize_urgency(percentage: float) -> str:
    """Get finalization urgency level."""
    if percentage >= 95:
        return "CRITICAL"  # Must finalize NOW
    elif percentage >= 85:
        return "HIGH"      # Finalize immediately
    elif percentage >= 75:
        return "MEDIUM"    # Start wrapping up
    elif percentage >= 60:
        return "LOW"       # Consider progress
    return "NONE"          # Continue working

if __name__ == "__main__":
    import json
    result = get_token_usage()
    print(json.dumps(result, indent=2))

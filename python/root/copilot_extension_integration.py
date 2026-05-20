# Copilot Token Tracker Extension Integration
# Integrates with robbos.copilot-token-tracker VS Code extension

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time

class CopilotTokenTracker:
    """Integration with Copilot Token Tracker VS Code extension."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.extension_cache_dir = self._find_extension_cache()
        self.session_files = []
        self.cached_data = {}

    def _find_extension_cache(self) -> Optional[Path]:
        """Find the extension's cache directory."""
        # Extension stores data in VS Code global state
        appdata = os.environ.get('APPDATA', '')
        if not appdata:
            return None

        vscode_global = Path(appdata) / 'Code' / 'User' / 'globalStorage'
        extension_dir = vscode_global / 'robbos.copilot-token-tracker'

        if extension_dir.exists():
            return extension_dir
        return None

    def scan_session_files(self) -> Dict[str, Any]:
        """Scan all Copilot session files for token usage data."""
        session_files = []
        total_stats = {
            "total_files": 0,
            "cached_files": 0,
            "total_tokens": 0,
            "sessions_by_workspace": {},
            "model_usage": {},
            "time_range": {},
            "scan_method": "manual" if not self.extension_cache_dir else "extension_cache"
        }

        # Scan workspace storage directories
        workspace_storage = Path(os.environ.get('APPDATA', '')) / 'Code' / 'User' / 'workspaceStorage'

        if workspace_storage.exists():
            for ws_dir in workspace_storage.iterdir():
                if ws_dir.is_dir():
                    chat_sessions = ws_dir / 'chatSessions'
                    if chat_sessions.exists():
                        workspace_sessions = []
                        for session_file in chat_sessions.glob('*.json*'):
                            try:
                                stat = session_file.stat()
                                file_info = {
                                    "path": str(session_file),
                                    "size": stat.st_size,
                                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                                    "workspace": ws_dir.name
                                }
                                session_files.append(file_info)
                                workspace_sessions.append(file_info)
                            except Exception as e:
                                continue

                        if workspace_sessions:
                            total_stats["sessions_by_workspace"][ws_dir.name] = workspace_sessions

        # Also check global sessions
        global_sessions = workspace_storage.parent / 'globalStorage' / 'github.copilot-chat'
        if global_sessions.exists():
            workspace_sessions = []
            for session_file in global_sessions.glob('*.json*'):
                try:
                    stat = session_file.stat()
                    file_info = {
                        "path": str(session_file),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "workspace": "global"
                    }
                    session_files.append(file_info)
                    workspace_sessions.append(file_info)
                except Exception as e:
                    continue

            if workspace_sessions:
                total_stats["sessions_by_workspace"]["global"] = workspace_sessions

        total_stats["total_files"] = len(session_files)
        total_stats["session_files"] = session_files[:20]  # First 20 for summary

        return total_stats

    def get_extension_status(self) -> Dict[str, Any]:
        """Get the status of the Copilot Token Tracker extension."""
        status = {
            "extension_found": self.extension_cache_dir is not None,
            "cache_directory": str(self.extension_cache_dir) if self.extension_cache_dir else None,
            "vscode_version": self._get_vscode_version(),
            "last_scan": datetime.now(timezone.utc).isoformat()
        }

        if self.extension_cache_dir:
            # Check for cache files
            cache_files = list(self.extension_cache_dir.glob('*.json'))
            status["cache_files"] = len(cache_files)
            status["cache_size"] = sum(f.stat().st_size for f in cache_files) if cache_files else 0

        return status

    def _get_vscode_version(self) -> str:
        """Get VS Code version."""
        try:
            # This is a simplified check - in practice we'd need to query VS Code
            return "1.109.3"  # From the diagnostic report
        except:
            return "unknown"

    def sync_with_monitor(self, token_monitor) -> Dict[str, Any]:
        """Sync extension data with our token monitor."""
        print(f"[SYNC] Starting sync with monitor at {datetime.now(timezone.utc).isoformat()}")
        extension_data = self.scan_session_files()

        if "error" in extension_data:
            print(f"[SYNC] Error in extension data: {extension_data['error']}")
            return extension_data

        print(f"[SYNC] Found {extension_data['total_files']} session files")
        print(f"[SYNC] Extension total tokens: {extension_data.get('total_tokens', 'unknown')}")

        # If no token data available, don't sync
        if extension_data.get('total_tokens', 0) == 0 and extension_data['total_files'] == 0:
            print("[SYNC] No extension data available, skipping sync")
            return {
                "extension_sync": "skipped",
                "reason": "no_data_available",
                "session_files_found": 0,
                "workspaces_found": 0,
                "recommendations": [
                    "Install and configure Copilot Token Tracker extension",
                    "Ensure extension has collected token usage data",
                    "Check VS Code global storage for extension data"
                ]
            }

        # Get current monitor status
        current_loop = token_monitor.get_current_loop()
        current_usage = token_monitor.get_loop_usage(current_loop)
        monitor_tokens = current_usage.get("tokens_used", 0)
        print(f"[SYNC] Monitor current tokens: {monitor_tokens}")

        # Here we could correlate extension data with our monitoring
        # For now, just return the extension statistics
        result = {
            "extension_sync": "completed",
            "session_files_found": extension_data["total_files"],
            "workspaces_found": len(extension_data["sessions_by_workspace"]),
            "monitor_tokens": monitor_tokens,
            "extension_tokens": extension_data.get("total_tokens", 0),
            "sync_timestamp": datetime.now(timezone.utc).isoformat(),
            "recommendations": [
                "Extension provides historical token usage analysis",
                "Consider integrating session file parsing for detailed metrics",
                "Extension cache can be cleared to force re-analysis"
            ]
        }
        print(f"[SYNC] Sync completed: {result}")
        return result


def get_copilot_tracker(workspace_root: Path = None) -> CopilotTokenTracker:
    """Factory function for CopilotTokenTracker."""
    if workspace_root is None:
        workspace_root = Path('.')
    return CopilotTokenTracker(workspace_root)
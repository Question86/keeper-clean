# MODE: SCRIPT

'''ClawdBot Integration - AI Assistant Gateway

This module integrates ClawdBot as an AI assistant within the Keeper ecosystem.
ClawdBot provides advanced AI capabilities through its Node.js gateway.

Features:
- Gateway communication bridge (Python ↔ Node.js)
- AI assistant routing and session management
- Multi-channel messaging integration
- Voice and canvas capabilities
- Local AI processing with model failover

Integration with Keeper's existing Flask application and event mesh.
'''

from flask import Blueprint, jsonify, request, render_template_string
from typing import Dict, Any, Optional
import json
import subprocess
import threading
import time
import requests
import websocket
from pathlib import Path
import os
from datetime import datetime, timezone

# Create blueprint for ClawdBot integration
clawdbot_bp = Blueprint('clawdbot', __name__, url_prefix='/api/clawdbot')

# Global instance
_clawdbot_instance = None

class ClawdBotIntegration:
    """Integration layer between Keeper and ClawdBot."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.clawdbot_path = self._find_clawdbot_path()
        self.gateway_process = None
        # Use host.docker.internal for Docker containers, localhost for direct execution
        self.gateway_host = self._get_gateway_host()
        self.gateway_port = 18789  # Browser control port
        self.is_running = False
        self.health_check_interval = 30
        self._health_thread = None
        self.ws = None

    def _find_clawdbot_path(self) -> Optional[Path]:
        """Find ClawdBot installation path."""
        # Check common locations
        potential_paths = [
            self.workspace_root / "clawdbot",
            Path.home() / "Documents" / "GitHub" / "clawdbot",
            Path.home() / "GitHub" / "clawdbot",
            Path("C:") / "Users" / os.getenv("USERNAME", "") / "Documents" / "GitHub" / "clawdbot",
            Path.home() / ".clawdbot",  # User's specified location
            Path("C:") / "Users" / "ambas" / ".clawdbot",  # Specific path mentioned
            Path("C:") / "Users" / "ambas" / ".clawdbot-dev",  # Dev path
            Path("C:") / "Users" / "ambas" / "Documents" / "GitHub" / "clawdbot",  # Documents path
        ]

        for path in potential_paths:
            if path.exists() and (path / "clawdbot.json").exists():
                return path
        return None

    def _get_gateway_host(self) -> str:
        """Determine the correct host for ClawdBot gateway (handles Docker networking)."""
        # Check if we're running in Docker
        try:
            with open('/.dockerenv', 'r') as f:
                return 'host.docker.internal'  # Docker for Windows/Mac
        except FileNotFoundError:
            return 'localhost'  # Direct execution

    def start_gateway(self) -> bool:
        """Start the ClawdBot Node.js gateway."""
        if self.is_running:
            return True

        if not self.clawdbot_path:
            print("ClawdBot path not found")
            return False

        try:
            # Start the gateway process
            self.gateway_process = subprocess.Popen(
                ["node", "scripts/run-node.mjs", "--dev", "gateway"],
                cwd=self.clawdbot_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "CLAWDBOT_SKIP_CHANNELS": "1"}
            )

            # Wait for startup
            time.sleep(2)

            if self.gateway_process.poll() is None:
                self.is_running = True
                self._start_health_check()
                return True
            else:
                print("Failed to start ClawdBot gateway")
                return False

        except Exception as e:
            print(f"Error starting ClawdBot gateway: {e}")
            return False

    def stop_gateway(self):
        """Stop the ClawdBot gateway."""
        if self.gateway_process:
            self.gateway_process.terminate()
            self.gateway_process.wait()
            self.gateway_process = None

        self.is_running = False
        if self._health_thread:
            self._health_thread.join()

    def _start_health_check(self):
        """Start health check thread."""
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()

    def _health_check_loop(self):
        """Health check loop to monitor gateway."""
        while self.is_running:
            try:
                # Simple health check - try to connect to WebSocket
                ws = websocket.create_connection(f"ws://localhost:{self.gateway_port}", timeout=5)
                ws.close()
            except:
                # If health check fails, mark as not running
                self.is_running = False
                break

            time.sleep(self.health_check_interval)

    def send_message_ws(self, message: str, session_id: str = 'main') -> Dict[str, Any]:
        """Send message via HTTP API to ClawdBot gateway."""
        try:
            # Get the auth token from config
            config_path = Path.home() / '.clawdbot' / 'clawdbot.json'
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            auth_token = config['gateway']['auth']['token']
            
            # Prepare the chat completion request
            url = f"http://{self.gateway_host}:{self.gateway_port}/v1/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {auth_token}'
            }
            
            payload = {
                'model': 'claude-sonnet-4-5',
                'messages': [
                    {
                        'role': 'user',
                        'content': message
                    }
                ],
                'max_tokens': 4096
            }
            
            # Make the HTTP request
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the assistant's message
            if 'choices' in result and len(result['choices']) > 0:
                assistant_message = result['choices'][0]['message']['content']
                return {
                    'success': True,
                    'response': {'message': assistant_message},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'No response from assistant',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

# Blueprint routes
@clawdbot_bp.route('/status')
def get_status():
    if _clawdbot_instance:
        return jsonify({
            'running': _clawdbot_instance.is_running,
            'port': _clawdbot_instance.gateway_port,
            'path': str(_clawdbot_instance.clawdbot_path) if _clawdbot_instance.clawdbot_path else None
        })
    return jsonify({'running': False, 'error': 'Not initialized'})

def clawdbot_dashboard():
    return "<h1>ClawdBot Dashboard</h1><p>Status: <a href='/api/clawdbot/status'>Check</a></p>"

def integrate_clawdbot(app):
    """Integrate ClawdBot into the Flask app."""
    global _clawdbot_instance

    workspace_root = Path(__file__).parent
    _clawdbot_instance = ClawdBotIntegration(workspace_root)

    # Register blueprint
    app.register_blueprint(clawdbot_bp, url_prefix='/api/clawdbot')

    # Add routes
    app.add_url_rule('/clawdbot', 'clawdbot_dashboard', clawdbot_dashboard)

    return app

@clawdbot_bp.route('/start', methods=['POST'])
def start_gateway():
    if _clawdbot_instance:
        success = _clawdbot_instance.start_gateway()
        return jsonify({
            'success': success,
            'message': 'Gateway started' if success else 'Failed to start gateway'
        })
    return jsonify({'success': False, 'message': 'Not initialized'})

@clawdbot_bp.route('/stop', methods=['POST'])
def stop_gateway():
    if _clawdbot_instance:
        _clawdbot_instance.stop_gateway()
        return jsonify({'success': True, 'message': 'Gateway stopped'})
    return jsonify({'success': False, 'message': 'Not initialized'})

@clawdbot_bp.route('/message', methods=['POST'])
def send_message():
    if not _clawdbot_instance:
        return jsonify({'success': False, 'error': 'Gateway not initialized'})

    data = request.get_json()
    message = data.get('message', '')
    session_id = data.get('sessionId', 'main')

    # Use WebSocket instead of HTTP
    result = _clawdbot_instance.send_message_ws(message, session_id)
    return jsonify(result)
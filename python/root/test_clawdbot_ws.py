#!/usr/bin/env python3
"""Test ClawdBot WebSocket integration directly."""

import websocket
import json
from datetime import datetime, timezone

def test_clawdbot_websocket():
    """Test ClawdBot via WebSocket."""
    try:
        # Connect to WebSocket
        ws = websocket.create_connection("ws://localhost:18789", timeout=10)
        print("✅ WebSocket connected")

        # Send test message
        message = "Hello from WebSocket test"
        payload = {
            'type': 'chat',
            'message': message,
            'sessionId': 'test_session',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        print(f"Sending: {json.dumps(payload, indent=2)}")
        ws.send(json.dumps(payload))

        # Receive response
        response = ws.recv()
        print(f"Received: {response}")

        ws.close()
        print("✅ WebSocket test completed successfully")

        # Parse response
        try:
            response_data = json.loads(response)
            return True
        except json.JSONDecodeError:
            print("Response is not JSON, but connection worked")
            return True

    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_clawdbot_websocket()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")
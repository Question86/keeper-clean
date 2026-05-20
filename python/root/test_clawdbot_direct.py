#!/usr/bin/env python3
"""Test ClawdBot integration directly without Flask server."""

import requests
import json
from datetime import datetime, timezone

def test_clawdbot_direct():
    """Test ClawdBot HTTP API directly."""
    gateway_url = "http://localhost:18789"

    print("Testing ClawdBot direct integration...")
    print(f"Gateway URL: {gateway_url}")

    # Test 1: Check if gateway is running
    try:
        response = requests.get(f"{gateway_url}/health", timeout=5)
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ Gateway is running")
        else:
            print("❌ Gateway not responding properly")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to gateway: {e}")
        return False

    # Test 2: Send a test message
    test_message = "Hello from direct test"
    payload = {
        'message': test_message,
        'sessionId': 'test_session',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    try:
        response = requests.post(
            f"{gateway_url}/api/chat",
            json=payload,
            timeout=10
        )

        print(f"Message send: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ Message sent successfully")
            print(f"Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Message failed: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Message send failed: {e}")
        return False

if __name__ == "__main__":
    success = test_clawdbot_direct()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")
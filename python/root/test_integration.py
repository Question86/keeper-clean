#!/usr/bin/env python3
"""Test the updated ClawdBot integration with WebSocket."""

from clawdbot_integration import ClawdBotIntegration
from pathlib import Path
import json

def test_integration():
    """Test the ClawdBot integration class directly."""
    workspace_root = Path(__file__).parent
    integration = ClawdBotIntegration(workspace_root)

    print("Testing ClawdBot integration...")
    print(f"ClawdBot path: {integration.clawdbot_path}")

    # Start gateway if not running
    if not integration.is_running:
        print("Starting gateway...")
        success = integration.start_gateway()
        if not success:
            print("❌ Failed to start gateway")
            return False
        print("✅ Gateway started")

    # Test WebSocket message
    print("Sending test message via WebSocket...")
    result = integration.send_message_ws("Hello from integration test", "test_session")

    print(f"Result: {json.dumps(result, indent=2)}")

    if result.get('success'):
        print("✅ Integration test PASSED")
        return True
    else:
        print("❌ Integration test FAILED")
        return False

if __name__ == "__main__":
    success = test_integration()
    print(f"\nOverall result: {'PASSED' if success else 'FAILED'}")
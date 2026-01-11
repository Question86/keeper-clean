#!/usr/bin/env python3
"""Test agent spawning flow."""

import requests
import json
import time

COCKPIT_URL = "http://localhost:5000"

def test_session_endpoints():
    """Test the session endpoints."""
    print("[TEST] Testing session endpoints...")
    
    # 1. Check pending sessions (should be empty initially)
    print("\n1. GET /api/orchestrator/sessions/pending")
    response = requests.get(f"{COCKPIT_URL}/api/orchestrator/sessions/pending")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Sessions: {data.get('count', 0)}")
    
    # 2. Execute parallel to create sessions
    print("\n2. POST /api/orchestrator/execute")
    payload = {
        "taskIds": ["TASK_0105", "TASK_0106"],
        "autoMerge": False,
        "autoCleanup": False
    }
    response = requests.post(f"{COCKPIT_URL}/api/orchestrator/execute", json=payload)
    print(f"   Status: {response.status_code}")
    result = response.json()
    print(f"   Success: {result.get('success')}")
    if result.get('success'):
        print(f"   Agents spawned: {result['result']['agents_spawned']}")
    
    # 3. Check pending sessions (should have 2 now)
    print("\n3. GET /api/orchestrator/sessions/pending (after execute)")
    time.sleep(0.5)
    response = requests.get(f"{COCKPIT_URL}/api/orchestrator/sessions/pending")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Sessions: {data.get('count', 0)}")
    
    if data.get('sessions'):
        for session in data['sessions']:
            print(f"   - {session['agentId']}: status={session['status']}, taskId={session['taskId']}")
            
            # 4. Claim first session
            if session['status'] == 'pending':
                print(f"\n4. POST /api/orchestrator/sessions/{session['agentId']}/claim")
                response = requests.post(f"{COCKPIT_URL}/api/orchestrator/sessions/{session['agentId']}/claim", json={})
                print(f"   Status: {response.status_code}")
                claim_result = response.json()
                if claim_result.get('success'):
                    print(f"   Session status updated to: {claim_result['session']['status']}")
                else:
                    print(f"   Error: {claim_result.get('error')}")
    
    # 5. Check pending sessions again (should show spawned status)
    print("\n5. GET /api/orchestrator/sessions/pending (after claim)")
    time.sleep(0.5)
    response = requests.get(f"{COCKPIT_URL}/api/orchestrator/sessions/pending")
    data = response.json()
    print(f"   Sessions: {data.get('count', 0)}")
    
    print("\n✅ Test completed!")
    print("\nExpected behavior:")
    print("- Initially: 0 pending sessions")
    print("- After execute: 2 spawned sessions")
    print("- After claim: 2 spawned sessions (still visible for agent pickup)")
    print("\nNext step: Extension polls these sessions, claims, and spawns agents")

if __name__ == "__main__":
    test_session_endpoints()

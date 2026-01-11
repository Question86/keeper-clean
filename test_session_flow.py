"""Test script to verify session flow works end-to-end."""
import requests
import json
import time

COCKPIT_URL = "http://localhost:5000"

def test_session_flow():
    """Test the complete session flow."""
    print("=" * 60)
    print("Testing Session Flow")
    print("=" * 60)
    
    # 1. Get orchestrator status
    print("\n1. Getting orchestrator status...")
    resp = requests.get(f"{COCKPIT_URL}/api/orchestrator")
    print(f"   Status: {resp.status_code}")
    print(f"   Data: {json.dumps(resp.json(), indent=2)}")
    
    # 2. Analyze tasks
    print("\n2. Analyzing tasks...")
    resp = requests.get(f"{COCKPIT_URL}/api/orchestrator/analyze")
    data = resp.json()
    print(f"   Status: {resp.status_code}")
    print(f"   Parallelizable tasks: {len(data.get('parallelizable_tasks', []))}")
    
    if not data.get('parallelizable_tasks'):
        print("   No parallelizable tasks found!")
        return
    
    # 3. Create session (execute with 1 task)
    task_to_test = data['parallelizable_tasks'][0]
    print(f"\n3. Creating session for task: {task_to_test}")
    resp = requests.post(
        f"{COCKPIT_URL}/api/orchestrator/execute",
        json={
            "taskIds": [task_to_test],
            "autoMerge": False,
            "autoCleanup": False
        }
    )
    print(f"   Status: {resp.status_code}")
    print(f"   Result: {json.dumps(resp.json(), indent=2)}")
    
    # 4. Check pending sessions
    print("\n4. Checking pending sessions...")
    time.sleep(1)  # Give it a moment
    resp = requests.get(f"{COCKPIT_URL}/api/orchestrator/sessions/pending")
    data = resp.json()
    print(f"   Status: {resp.status_code}")
    print(f"   Sessions: {len(data.get('sessions', []))}")
    
    if data.get('sessions'):
        session = data['sessions'][0]
        print(f"   First session:")
        print(f"      Agent ID: {session['agentId']}")
        print(f"      Task ID: {session['taskId']}")
        print(f"      Status: {session['status']}")
        print(f"      Worktree: {session['worktreePath']}")
        
        # 5. Claim the session (simulate extension claiming it)
        agent_id = session['agentId']
        print(f"\n5. Claiming session {agent_id}...")
        resp = requests.post(f"{COCKPIT_URL}/api/orchestrator/sessions/{agent_id}/claim")
        print(f"   Status: {resp.status_code}")
        print(f"   Result: {json.dumps(resp.json(), indent=2)}")
        
        # 6. Check pending again (should be empty or show as working)
        print("\n6. Checking pending sessions again...")
        resp = requests.get(f"{COCKPIT_URL}/api/orchestrator/sessions/pending")
        data = resp.json()
        print(f"   Status: {resp.status_code}")
        print(f"   Pending sessions: {len(data.get('sessions', []))}")
        
        # 7. Report progress
        print(f"\n7. Reporting progress for {agent_id}...")
        resp = requests.post(
            f"{COCKPIT_URL}/api/orchestrator/sessions/{agent_id}/status",
            json={
                "status": "working",
                "progress": 50,
                "message": "Test agent is working..."
            }
        )
        print(f"   Status: {resp.status_code}")
        print(f"   Result: {json.dumps(resp.json(), indent=2)}")
        
        # 8. Complete the session
        print(f"\n8. Completing session {agent_id}...")
        resp = requests.post(
            f"{COCKPIT_URL}/api/orchestrator/sessions/{agent_id}/status",
            json={
                "status": "completed",
                "progress": 100,
                "result_summary": "Test completed successfully"
            }
        )
        print(f"   Status: {resp.status_code}")
        print(f"   Result: {json.dumps(resp.json(), indent=2)}")
        
        # 9. Check orchestrator status
        print("\n9. Final orchestrator status...")
        resp = requests.get(f"{COCKPIT_URL}/api/orchestrator")
        data = resp.json()
        print(f"   Status: {resp.status_code}")
        print(f"   Sessions by status: {data.get('sessions_by_status', {})}")
        
        # 10. Rollback to clean up
        print("\n10. Rolling back to clean up...")
        resp = requests.post(f"{COCKPIT_URL}/api/orchestrator/rollback")
        print(f"   Status: {resp.status_code}")
        print(f"   Result: {json.dumps(resp.json(), indent=2)}")
    
    print("\n" + "=" * 60)
    print("Session flow test complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_session_flow()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

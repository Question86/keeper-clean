#!/usr/bin/env python3
"""Quick test to send 'hi' to ClawdBot."""

import requests
import json

def test_clawdbot():
    try:
        # Call through Flask API
        response = requests.post(
            'http://localhost:5000/api/clawdbot/message',
            json={
                'message': 'hi',
                'sessionId': 'test'
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print("Model response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"HTTP {response.status_code}: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        print("Flask server or ClawdBot gateway may not be running")

if __name__ == '__main__':
    test_clawdbot()
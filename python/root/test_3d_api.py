#!/usr/bin/env python3
"""Quick test to see what /api/project-structure returns for archives."""

import requests

try:
    r = requests.get('http://localhost:5000/api/project-structure')
    r.raise_for_status()
    data = r.json()
    
    print(f"Total files: {len(data.get('files', []))}")
    print(f"Total references: {len(data.get('references', []))}")
    print()
    
    archives = [f for f in data.get('files', []) if f.get('type') == 'archive']
    print(f"Found {len(archives)} archive nodes:")
    for arc in archives[:5]:
        print(f"  name={arc.get('name')!r}, path={arc.get('path')!r}, type={arc.get('type')!r}")
    
    print()
    print("Testing /api/open-file with archive path...")
    if archives:
        test_path = archives[0].get('path') or archives[0].get('name')
        r2 = requests.post('http://localhost:5000/api/open-file', json={'path': test_path})
        print(f"POST /api/open-file with path={test_path!r}")
        print(f"Status: {r2.status_code}")
        print(f"Response: {r2.json()}")

except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to http://localhost:5000")
    print("Make sure the cockpit server is running!")
except Exception as e:
    print(f"ERROR: {e}")

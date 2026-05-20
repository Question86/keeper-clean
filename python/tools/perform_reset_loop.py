# MODE: SCRIPT\n\n"""Perform reset loop by calling Flask endpoint /api/reset-loop."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from loop_cockpit import app

with app.test_client() as client:
    resp = client.post('/api/reset-loop', json={})
    print('Status code:', resp.status_code)
    print('JSON:', resp.get_json())

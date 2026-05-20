# MODE: SCRIPT

"""Perform canonical bootstrap by calling the loop_cockpit Flask app endpoint.

This uses Flask's test client to POST to /api/confirm-bootstrap so the operation is executed
within the same process and environment (no external HTTP call needed).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from loop_cockpit import app

with app.test_client() as client:
    resp = client.post('/api/confirm-bootstrap')
    print('Status code:', resp.status_code)
    print('JSON:', resp.get_json())

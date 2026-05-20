# MODE: SCRIPT

import json
import pathlib
from loop_cockpit import app

with app.test_client() as c:
    resp = c.post('/api/ack-incident', json={'id':'INCIDENT_0002','ack_by':'human_signoff','notes':'testing ack'})
    print(resp.status_code, resp.get_json())

print(json.dumps(json.loads(pathlib.Path('current.json').read_text()), indent=2))
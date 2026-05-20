# MODE: SCRIPT\n\nimport sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from loop_cockpit import app
with app.test_client() as c:
    r = c.get('/api/status')
    print('Status Code:', r.status_code)
    print(json.dumps(r.get_json(), indent=2))

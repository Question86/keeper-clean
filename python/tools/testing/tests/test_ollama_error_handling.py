# MODE: TEST\n\nimport requests
import pytest
from loop_cockpit import app


def test_generate_code_handles_ollama_unreachable(monkeypatch):
    def fake_post(*args, **kwargs):
        raise requests.exceptions.ConnectionError("simulated unreachable")

    monkeypatch.setattr(requests, "post", fake_post)

    with app.test_client() as client:
        resp = client.post('/api/generate-code', json={'prompt': 'build a test', 'model': 'mistral:latest'})
        assert resp.status_code == 500
        data = resp.get_json()
        assert data is not None
        assert data.get('success') is False
        assert 'Ollama' in data.get('error', '')

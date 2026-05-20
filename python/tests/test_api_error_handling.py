# test_api_error_handling.py - Contract tests for API error envelope

import json


class TestApiErrorHandling:
    """Ensure /api endpoints return structured error payloads."""

    def test_api_404_returns_json_error_payload(self, client):
        response = client.get("/api/this-endpoint-does-not-exist")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert data.get("success") is False
        assert data.get("status") == 404
        assert data.get("code") == "HTTP_404"
        assert "error" in data

    def test_api_400_returns_json_error_payload(self, client):
        response = client.post(
            "/api/autostart/control",
            data=json.dumps({"action": "invalid_action"}),
            content_type="application/json",
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data.get("success") is False
        assert data.get("status") == 400
        assert data.get("code") in {"HTTP_400", "BAD_REQUEST"}
        assert "error" in data

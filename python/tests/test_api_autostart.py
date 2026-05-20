# test_api_autostart.py - Tests for autostart API endpoints

import json


class TestAutostartEndpoints:
    """Test suite for autostart-related API endpoints."""

    def test_api_autostart_status_get(self, client):
        """GET /api/autostart/status returns structured payload."""
        response = client.get("/api/autostart/status")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "success" in data
        assert "summary" in data
        assert "supervisor" in data
        assert "analysis_signals" in data
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_api_autostart_control_refresh(self, client):
        """POST /api/autostart/control with refresh returns status payload."""
        response = client.post(
            "/api/autostart/control",
            data=json.dumps({"action": "refresh"}),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data.get("action") == "refresh"
        assert "action_result" in data
        assert isinstance(data["action_result"], dict)
        assert data["action_result"].get("success") is True

    def test_api_autostart_control_invalid_action(self, client):
        """POST /api/autostart/control rejects unsupported action."""
        response = client.post(
            "/api/autostart/control",
            data=json.dumps({"action": "invalid_action"}),
            content_type="application/json",
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data.get("success") is False
        assert "Unsupported action" in data.get("error", "")

    def test_api_autostart_job_control_missing_job(self, client):
        """POST /api/autostart/job-control requires 'job' field."""
        response = client.post(
            "/api/autostart/job-control",
            data=json.dumps({"action": "run_now"}),
            content_type="application/json",
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data.get("success") is False
        assert "Missing 'job' field" in data.get("error", "")

    def test_api_autostart_job_control_invalid_action(self, client):
        """POST /api/autostart/job-control rejects unsupported action."""
        response = client.post(
            "/api/autostart/job-control",
            data=json.dumps({"job": "knowledge_health_monitor", "action": "noop"}),
            content_type="application/json",
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data.get("success") is False
        assert "Unsupported action" in data.get("error", "")

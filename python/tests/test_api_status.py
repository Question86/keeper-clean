# test_api_status.py - Tests for status-related API endpoints

import pytest
import json
from pathlib import Path


class TestStatusEndpoints:
    """Test suite for status and health endpoints."""

    def test_api_status_get(self, client, sample_current_json, temp_workspace):
        """Test GET /api/status endpoint."""
        # Setup current.json
        current_path = Path("current.json")
        current_path.write_text(json.dumps(sample_current_json), encoding="utf-8")

        response = client.get('/api/status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data
        assert "loop" in data
        assert "summary" in data
        assert data["status"] == "ACTIVE"
        assert data["loop"] == 124

    def test_api_status_missing_current_json(self, client, temp_workspace):
        """Test GET /api/status when current.json is missing."""
        # Remove current.json
        current_path = Path("current.json")
        if current_path.exists():
            current_path.unlink()

        response = client.get('/api/status')
        # Should still return 200 with default values
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data

    def test_health_endpoint(self, client):
        """Test GET /health endpoint."""
        response = client.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data
        assert data["status"] == "healthy"

    def test_api_service_status(self, client, sample_current_json, temp_workspace):
        """Test GET /api/service-status endpoint."""
        # Setup current.json
        current_path = Path("current.json")
        current_path.write_text(json.dumps(sample_current_json), encoding="utf-8")

        response = client.get('/api/service-status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data
        assert "services" in data

    def test_api_life_coordinates(self, client):
        """Test GET /api/life-coordinates endpoint."""
        response = client.get('/api/life-coordinates')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_api_breadcrumbs(self, client):
        """Test GET /api/breadcrumbs endpoint."""
        response = client.get('/api/breadcrumbs')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_api_finalization_status(self, client):
        """Test GET /api/finalization-status endpoint."""
        response = client.get('/api/finalization-status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_api_finalization_check(self, client):
        """Test GET /api/finalization-check endpoint."""
        response = client.get('/api/finalization-check')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_api_validate_gates(self, client):
        """Test GET /api/validate-gates endpoint."""
        response = client.get('/api/validate-gates')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_api_metadata_lint(self, client):
        """Test GET /api/metadata-lint endpoint."""
        response = client.get('/api/metadata-lint')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "errors" in data
        assert "warnings" in data
        assert isinstance(data["errors"], list)
        assert isinstance(data["warnings"], list)

    def test_api_transaction_log(self, client):
        """Test GET /api/transaction-log endpoint."""
        response = client.get('/api/transaction-log')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_api_validate_schemas(self, client):
        """Test GET /api/validate-schemas endpoint."""
        response = client.get('/api/validate-schemas')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, dict)
        """Test GET /api/service-status endpoint."""
        # Setup current.json
        current_path = Path("current.json")
        current_path.write_text(json.dumps(sample_current_json), encoding="utf-8")

        response = client.get('/api/service-status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "services" in data
        assert isinstance(data["services"], dict)  # Services is a dict, not list

    def test_api_status_fields_completeness(self, client, sample_current_json, temp_workspace):
        """Test that /api/status returns all expected fields."""
        current_path = Path("current.json")
        current_path.write_text(json.dumps(sample_current_json), encoding="utf-8")

        response = client.get('/api/status')
        assert response.status_code == 200

        data = json.loads(response.data)

        expected_fields = [
            "loop", "status", "lastTaskWorked", "summary",
            "lastUpdate", "canReset", "bootstrapExists"
        ]

        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


class TestStatusEdgeCases:
    """Test edge cases for status endpoints."""

    def test_api_status_corrupted_json(self, client, temp_workspace):
        """Test GET /api/status with corrupted current.json."""
        current_path = Path("current.json")
        current_path.write_text("{ invalid json", encoding="utf-8")

        response = client.get('/api/status')
        # Should handle gracefully
        assert response.status_code in [200, 500]

    def test_api_status_empty_json(self, client, temp_workspace):
        """Test GET /api/status with empty current.json."""
        current_path = Path("current.json")
        current_path.write_text("{}", encoding="utf-8")

        response = client.get('/api/status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data
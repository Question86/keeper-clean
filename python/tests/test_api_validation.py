# test_api_validation.py - Tests for validation API endpoints

import pytest
import json
from pathlib import Path


class TestValidationEndpoints:
    """Test suite for validation endpoints."""

    def test_api_validate_gates_get(self, client, temp_workspace):
        """Test GET /api/validate-gates endpoint."""
        # Create _LOOP_GATE.md
        gate_content = """# LOOP GATE

STATUS: PASS
TIMESTAMP: 2024-01-01T00:00:00Z
LOOP: 124
BOOTSTRAP_READY: true
"""

        gate_path = Path("_LOOP_GATE.md")
        gate_path.write_text(gate_content, encoding="utf-8")

        response = client.get('/api/validate-gates')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data
        assert "valid" in data
        assert isinstance(data["valid"], bool)

    def test_api_validate_schemas_get(self, client, temp_workspace, sample_current_json):
        """Test GET /api/validate-schemas endpoint."""
        # Create current.json
        current_path = Path("current.json")
        current_path.write_text(json.dumps(sample_current_json), encoding="utf-8")

        response = client.get('/api/validate-schemas')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "valid" in data
        assert "errors" in data
        assert isinstance(data["valid"], bool)
        assert isinstance(data["errors"], list)

    def test_api_metadata_lint_get(self, client, temp_workspace):
        """Test GET /api/metadata-lint endpoint."""
        # Create some test files with metadata
        task_content = """---
title: Test Task
id: TASK_0230
version: 1
tags: [test]
---

# Test Task

This is a test task.
"""

        task_path = Path("tasks/task_TASK_0230.md")
        task_path.parent.mkdir(exist_ok=True)
        task_path.write_text(task_content, encoding="utf-8")

        response = client.get('/api/metadata-lint')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_api_transaction_log_get(self, client, temp_workspace):
        """Test GET /api/transaction-log endpoint."""
        # Create _transaction_log.jsonl
        log_content = """{"timestamp": "2024-01-01T00:00:00Z", "action": "test", "details": {"key": "value"}}
{"timestamp": "2024-01-01T00:01:00Z", "action": "another_test", "details": {"key2": "value2"}}
"""

        log_path = Path("_transaction_log.jsonl")
        log_path.write_text(log_content, encoding="utf-8")

        response = client.get('/api/transaction-log')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert len(data["entries"]) >= 0

    def test_api_validate_bootstrap_exit_get(self, client, temp_workspace, sample_current_json):
        """Test GET /api/validate-bootstrap-exit endpoint."""
        # Create current.json with bootstrap ready state
        current_path = Path("current.json")
        current_path.write_text(json.dumps(sample_current_json), encoding="utf-8")

        # Create _BOOTSTRAP.md to indicate bootstrap in progress
        bootstrap_content = """# BOOTSTRAP SESSION

Started: 2024-01-01T00:00:00Z
Status: ACTIVE
"""

        bootstrap_path = Path("_BOOTSTRAP.md")
        bootstrap_path.write_text(bootstrap_content, encoding="utf-8")

        response = client.get('/api/validate-bootstrap-exit')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "can_exit" in data
        assert "reasons" in data
        assert isinstance(data["can_exit"], bool)
        assert isinstance(data["reasons"], list)


class TestValidationEdgeCases:
    """Test edge cases for validation endpoints."""

    def test_api_validate_gates_missing_file(self, client, temp_workspace):
        """Test GET /api/validate-gates when gate file is missing."""
        gate_path = Path("_LOOP_GATE.md")
        if gate_path.exists():
            gate_path.unlink()

        response = client.get('/api/validate-gates')
        # Should handle gracefully
        assert response.status_code in [200, 500]

    def test_api_validate_schemas_invalid_json(self, client, temp_workspace):
        """Test GET /api/validate-schemas with invalid JSON."""
        current_path = Path("current.json")
        current_path.write_text("invalid json content", encoding="utf-8")

        response = client.get('/api/validate-schemas')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "valid" in data
        assert data["valid"] == False
        assert "errors" in data

    def test_api_metadata_lint_no_files(self, client, temp_workspace):
        """Test GET /api/metadata-lint when no task files exist."""
        tasks_dir = Path("tasks")
        if tasks_dir.exists():
            import shutil
            shutil.rmtree(tasks_dir)

        response = client.get('/api/metadata-lint')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_api_transaction_log_missing_file(self, client, temp_workspace):
        """Test GET /api/transaction-log when log file doesn't exist."""
        log_path = Path("_transaction_log.jsonl")
        if log_path.exists():
            log_path.unlink()

        response = client.get('/api/transaction-log')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "entries" in data
        assert isinstance(data["entries"], list)
        # Should return empty list or handle gracefully

    def test_api_validate_bootstrap_exit_no_bootstrap(self, client, temp_workspace):
        """Test GET /api/validate-bootstrap-exit when no bootstrap file exists."""
        bootstrap_path = Path("_BOOTSTRAP.md")
        if bootstrap_path.exists():
            bootstrap_path.unlink()

        response = client.get('/api/validate-bootstrap-exit')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "can_exit" in data
        assert isinstance(data["can_exit"], bool)
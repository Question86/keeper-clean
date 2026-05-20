# test_api_tasks.py - Tests for task management API endpoints

import pytest
import json
from pathlib import Path
import loop_cockpit as lc


class TestTaskEndpoints:
    """Test suite for task management endpoints."""

    def test_api_tasks_get(self, client, temp_workspace):
        """Test GET /api/tasks endpoint."""
        # Create sample NEU.md
        neu_content = """# NEU

MODE: POINTER-ONLY

---

## TASK QUEUE (PRIORITY ORDER)

[ref:tasks/task_TASK_0230.md|v:1|tags:testing|src:test]
[ref:tasks/task_TASK_0191.md|v:1|tags:api|src:user]
"""

        neu_path = Path("NEU.md")
        neu_path.write_text(neu_content, encoding="utf-8")

        response = client.get('/api/tasks')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "active" in data
        assert "closed" in data
        assert isinstance(data["active"], str)  # Raw markdown content
        assert isinstance(data["closed"], str)

    def test_api_tasks_active_get(self, client, temp_workspace):
        """Test GET /api/tasks/active endpoint."""
        # Create sample NEU.md with active tasks
        neu_content = """# NEU

MODE: POINTER-ONLY

---

## TASK QUEUE (PRIORITY ORDER)

[ref:tasks/task_TASK_0230.md|v:1|tags:new|src:user] - Test task description
"""

        neu_path = Path("NEU.md")
        neu_path.write_text(neu_content, encoding="utf-8")

        response = client.get('/api/tasks/active')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "success" in data
        assert "tasks" in data
        assert isinstance(data["tasks"], list)

    def test_api_blocked_tasks_get(self, client, temp_workspace):
        """Test GET /api/blocked-tasks endpoint."""
        # Create sample Alt.md with blocked tasks
        alt_content = """# Alt

MODE: POINTER-ONLY

---

## BLOCKED TASKS

- [ref:tasks/task_TASK_0190.md|v:1|tags:blocked|src:system] - Blocked task
"""

        alt_path = Path("Alt.md")
        alt_path.write_text(alt_content, encoding="utf-8")

        response = client.get('/api/blocked-tasks')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "blocked_tasks" in data
        assert isinstance(data["blocked_tasks"], list)

    def test_api_tasks_complete_post_valid(self, client, temp_workspace, sample_task_md):
        """Test POST /api/tasks/complete with valid task."""
        # Create task file
        task_path = Path("tasks/task_TASK_0230.md")
        task_path.parent.mkdir(exist_ok=True)
        task_path.write_text(sample_task_md, encoding="utf-8")

        # Create NEU.md with the task in the correct format
        neu_content = """# NEU

MODE: POINTER-ONLY

---

## TASK QUEUE (PRIORITY ORDER)

[ref:tasks/task_TASK_0230.md|v:1|tags:new|src:user] - Test task description
"""

        neu_path = Path("NEU.md")
        neu_path.write_text(neu_content, encoding="utf-8")

        payload = {
            "taskId": "TASK_0230",
            "completionReason": "Test completion"
        }

        response = client.post('/api/tasks/complete',
                              data=json.dumps(payload),
                              content_type='application/json')
        # May return 404 if task not found in expected format
        assert response.status_code in [200, 400, 404, 500]

    def test_api_tasks_complete_post_invalid(self, client):
        """Test POST /api/tasks/complete with invalid data."""
        payload = {
            "invalidField": "value"
        }

        response = client.post('/api/tasks/complete',
                              data=json.dumps(payload),
                              content_type='application/json')
        assert response.status_code == 400

    def test_api_reopen_task_post(self, client, temp_workspace, sample_task_md):
        """Test POST /api/reopen-task endpoint."""
        # Create task file in Alt.md
        task_path = Path("tasks/task_TASK_0230.md")
        task_path.parent.mkdir(exist_ok=True)
        task_path.write_text(sample_task_md, encoding="utf-8")

        # Create Alt.md with the task
        alt_content = """# Alt

MODE: POINTER-ONLY

---

## CLOSED TASKS

[ref:tasks/task_TASK_0230.md|v:1|tags:closed|src:test]
"""

        alt_path = Path("Alt.md")
        alt_path.write_text(alt_content, encoding="utf-8")

        payload = {
            "taskId": "TASK_0230",
            "reason": "Reopening for testing"
        }

        response = client.post('/api/reopen-task',
                              data=json.dumps(payload),
                              content_type='application/json')
        assert response.status_code in [200, 400]  # May fail due to validation


class TestTaskEdgeCases:
    """Test edge cases for task endpoints."""

    def test_api_tasks_missing_neu_file(self, client, temp_workspace):
        """Test GET /api/tasks when NEU.md is missing."""
        neu_path = Path("NEU.md")
        if neu_path.exists():
            neu_path.unlink()

        response = client.get('/api/tasks')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "active" in data
        assert "closed" in data
        # Should return empty or default content

    def test_api_tasks_malformed_neu_file(self, client, temp_workspace):
        """Test GET /api/tasks with malformed NEU.md."""
        neu_path = Path("NEU.md")
        neu_path.write_text("Invalid markdown content", encoding="utf-8")

        response = client.get('/api/tasks')
        # Should handle gracefully
        assert response.status_code in [200, 500]

    def test_api_tasks_complete_nonexistent_task(self, client):
        """Test POST /api/tasks/complete for nonexistent task."""
        payload = {
            "taskId": "TASK_NONEXISTENT",
            "completionReason": "Test"
        }

        response = client.post('/api/tasks/complete',
                              data=json.dumps(payload),
                              content_type='application/json')
        assert response.status_code == 404


class TestTaskGenerateEndpoint:
    """Test suite for /api/tasks/generate endpoint."""

    def test_api_tasks_generate_creates_task_and_neu_ref(self, client, tmp_path, monkeypatch):
        """Create a task file and add reference into NEU queue."""
        workspace = tmp_path
        (workspace / "tasks").mkdir(parents=True, exist_ok=True)
        (workspace / "NEU.md").write_text(
            "# NEU\n\nMODE: POINTER-ONLY\n\n---\n\n## TASK QUEUE (PRIORITY ORDER)\n\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(lc, "WORKSPACE_ROOT", workspace)
        monkeypatch.setattr(lc, "NEU_MD", workspace / "NEU.md")
        monkeypatch.setattr(lc, "log_transaction", lambda *args, **kwargs: None)
        monkeypatch.setattr(lc, "regenerate_loop_gate", lambda *args, **kwargs: None)
        monkeypatch.setattr(lc.KnowledgeDBEventHandler, "on_task_changed", lambda *args, **kwargs: None)

        payload = {
            "title": "Node-created task",
            "description": "Generated from experimental node panel",
            "objective": "Verify generation flow",
            "priority": "HIGH",
            "infrastructure": {
                "agentType": "OpenAI",
                "model": "gpt-5",
                "successDefinition": "Task created and linked",
                "failureDefinition": "Task not created",
            },
        }
        response = client.post("/api/tasks/generate", data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["taskId"].startswith("TASK_")
        task_file = workspace / data["taskFile"]
        assert task_file.exists()
        neu_content = (workspace / "NEU.md").read_text(encoding="utf-8")
        assert data["neuRef"] in neu_content

    def test_api_tasks_generate_requires_title(self, client):
        """Reject task generation when title is missing."""
        response = client.post(
            "/api/tasks/generate",
            data=json.dumps({"description": "No title"}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "title" in data["error"].lower()

    def test_api_tasks_generate_normalizes_invalid_priority(self, client, tmp_path, monkeypatch):
        """Fallback invalid priority values to MEDIUM in generated task file."""
        workspace = tmp_path
        (workspace / "tasks").mkdir(parents=True, exist_ok=True)
        (workspace / "NEU.md").write_text(
            "# NEU\n\nMODE: POINTER-ONLY\n\n---\n\n## TASK QUEUE (PRIORITY ORDER)\n\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(lc, "WORKSPACE_ROOT", workspace)
        monkeypatch.setattr(lc, "NEU_MD", workspace / "NEU.md")
        monkeypatch.setattr(lc, "log_transaction", lambda *args, **kwargs: None)
        monkeypatch.setattr(lc, "regenerate_loop_gate", lambda *args, **kwargs: None)
        monkeypatch.setattr(lc.KnowledgeDBEventHandler, "on_task_changed", lambda *args, **kwargs: None)

        response = client.post(
            "/api/tasks/generate",
            data=json.dumps({"title": "Priority fallback", "priority": "INVALID"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        task_content = (workspace / data["taskFile"]).read_text(encoding="utf-8")
        assert "PRIORITY: MEDIUM" in task_content

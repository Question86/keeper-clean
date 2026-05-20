# MODE: TEST

import importlib
import json
from pathlib import Path
import tempfile

import pytest


def _write_current(path: Path, status: str = "ACTIVE", loop: int = 999):
    data = {
        "STATE": {
            "loop": loop,
            "status": status,
            "archiveCurrent": "archive/ARCHIV_0001.md",
            "archiveInProgress": None,
            "lastTaskWorked": None,
            "lastUpdate": "2026-01-01T00:00:00Z",
            "summary": "test",
            "validationHash": None,
            "transitionTrigger": None
        }
    }
    (path / "current.json").write_text(json.dumps(data, indent=2))


def _write_neu_md(path: Path, content: str = ""):
    neu_content = f"""# NEU

MODE: POINTER-ONLY
CONTENT: FORBIDDEN

Process Rules:
[ref:docs/OPS_PROTOCOLS.md#INDEX_UPDATE|v:1|tags:ops,index|src:doc]

---

## TASK QUEUE (PRIORITY ORDER)

{content}

---

END OF DOCUMENT
"""
    (path / "NEU.md").write_text(neu_content)


def test_seed_idea_deduplication_blocks_duplicate(tmp_path, monkeypatch):
    """Test that submitting a duplicate seed idea is blocked."""
    # Arrange: create isolated workspace with existing task in NEU.md
    ws = tmp_path / "ws"
    ws.mkdir()
    _write_current(ws, "ACTIVE", loop=51)
    
    existing_idea = "Browse archives, reports, Neu.md and Alt.md on your own and search for mockups/false-positive reports and uncomplete/inconsistence work or broken links that needs to be addressed. When you found potential work, solve at least one structural problem as task."
    _write_neu_md(ws, f"[ref:tasks/task_TASK_0068.md|v:1|tags:new|src:user] - {existing_idea}")

    monkeypatch.setenv("LOOP_WORKSPACE", str(ws))

    # Reload modules to pick up new WORKSPACE_ROOT
    import loop_cockpit as lc
    importlib.reload(lc)

    app = lc.app
    with app.test_client() as client:
        # Act: try to submit the same idea
        resp = client.post('/api/seed-idea', 
                          json={'idea': existing_idea})
        
        # Assert: should be blocked with 409
        assert resp.status_code == 409
        data = resp.get_json()
        assert data is not None
        assert data.get('success') is False
        assert "already exists" in data.get('error', '')


def test_seed_idea_deduplication_allows_unique(tmp_path, monkeypatch):
    """Test that submitting a unique seed idea succeeds."""
    # Arrange: create isolated workspace with existing task in NEU.md
    ws = tmp_path / "ws"
    ws.mkdir()
    _write_current(ws, "ACTIVE", loop=51)
    
    existing_idea = "Browse archives, reports, Neu.md and Alt.md on your own and search for mockups/false-positive reports and uncomplete/inconsistence work or broken links that needs to be addressed. When you found potential work, solve at least one structural problem as task."
    _write_neu_md(ws, f"[ref:tasks/task_TASK_0068.md|v:1|tags:new|src:user] - {existing_idea}")

    monkeypatch.setenv("LOOP_WORKSPACE", str(ws))

    # Reload modules to pick up new WORKSPACE_ROOT
    import loop_cockpit as lc
    importlib.reload(lc)

    app = lc.app
    with app.test_client() as client:
        # Act: submit a different idea
        new_idea = "Create a new feature for better task management"
        resp = client.post('/api/seed-idea', 
                          json={'idea': new_idea})
        
        # Assert: should succeed
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert data.get('success') is True
        assert 'taskId' in data
        assert data['taskId'].startswith('TASK_')
        
        # Verify task file was created
        task_file = ws / "tasks" / f"task_{data['taskId']}.md"
        assert task_file.exists()
        
        # Verify NEU.md was updated
        neu_content = (ws / "NEU.md").read_text()
        assert new_idea in neu_content


def test_seed_idea_empty_idea_rejected(tmp_path, monkeypatch):
    """Test that empty seed ideas are rejected."""
    # Arrange
    ws = tmp_path / "ws"
    ws.mkdir()
    _write_current(ws, "ACTIVE", loop=51)
    _write_neu_md(ws)

    monkeypatch.setenv("LOOP_WORKSPACE", str(ws))

    import loop_cockpit as lc
    importlib.reload(lc)

    app = lc.app
    with app.test_client() as client:
        # Act: submit empty idea
        resp = client.post('/api/seed-idea', json={'idea': ''})
        
        # Assert: should be rejected
        assert resp.status_code == 400
        data = resp.get_json()
        assert data is not None
        assert data.get('success') is False
        assert "cannot be empty" in data.get('error', '')
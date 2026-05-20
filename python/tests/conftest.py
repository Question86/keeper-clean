# conftest.py - Shared test fixtures for API testing suite

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loop_cockpit import app as flask_app


@pytest.fixture
def app():
    """Flask app fixture for testing."""
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def temp_workspace():
    """Temporary workspace directory for testing."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_workspace_"))

    # Copy essential files
    workspace_root = Path(__file__).parent.parent
    essential_files = [
        "current.json",
        "NEU.md",
        "Alt.md",
        "_LOOP_GATE.md",
        "PROJECT_TECH_BASELINE.md"
    ]

    for file in essential_files:
        src = workspace_root / file
        if src.exists():
            shutil.copy2(src, temp_dir / file)

    # Create empty directories
    (temp_dir / "tasks").mkdir()
    (temp_dir / "reports").mkdir()
    (temp_dir / "archive").mkdir()

    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(temp_dir)

    yield temp_dir

    # Cleanup
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_openai():
    """Mock OpenAI integration."""
    with patch('loop_cockpit.openai_integration') as mock:
        mock.OpenAIIntegration.return_value = None
        yield mock


@pytest.fixture
def mock_external_apis():
    """Mock external API calls."""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        mock_get.return_value = Mock(status_code=200, json=lambda: {})
        mock_post.return_value = Mock(status_code=200, json=lambda: {})
        yield mock_get, mock_post


@pytest.fixture
def sample_current_json():
    """Sample current.json data."""
    return {
        "STATE": {
            "loop": 124,
            "status": "ACTIVE",
            "archiveCurrent": "archive/ARCHIV_0123.md",
            "lastTaskWorked": "TASK_0230",
            "lastUpdate": "2026-02-14T22:30:00Z",
            "summary": "Testing active",
            "finalizationStatus": "ready",
            "bootstrapReady": True
        }
    }


@pytest.fixture
def sample_task_md():
    """Sample task markdown content."""
    return """# TASK_0230

MODE: TASK SPECIFICATION
STATUS: NEW
CREATED: 2026-02-14T22:18:04Z

---

## OBJECTIVE

Test task implementation.

---

END OF TASK
"""
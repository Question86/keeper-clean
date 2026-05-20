import pytest
from adaptive_bootstrap import BootstrapPredictor
from pathlib import Path


def test_predict_returns_list(tmp_path):
    # Use workspace root for tests
    workspace = Path(".")
    predictor = BootstrapPredictor(workspace)
    selected = predictor.predict_needed_files("Test bootstrap prediction for TASK_0156", task_type="implementation", budget_tokens=60000)

    assert isinstance(selected, list)
    # All returned files should exist relative to workspace
    for f in selected:
        assert (workspace / f).exists(), f"Predicted file does not exist: {f}"


def test_predict_respects_budget():
    workspace = Path(".")
    predictor = BootstrapPredictor(workspace)
    selected = predictor.predict_needed_files("Large budget test", budget_tokens=200)
    # With small budget, selected files should be limited
    total_est = sum(predictor._estimate_token_cost(f) for f in selected)
    assert total_est <= 200


def test_relevance_uses_search():
    workspace = Path('.')
    predictor = BootstrapPredictor(workspace)
    # Use a known file that mentions 'bootstrap' to ensure relevance > 0
    rel = predictor._calculate_relevance('tasks/task_TASK_0156.md', 'bootstrap predictor prediction')
    assert rel >= 0.0
    # We expect at least some signal for a file that clearly contains task-related words
    assert rel > 0.01, f"Expected small but non-zero relevance, got {rel}"

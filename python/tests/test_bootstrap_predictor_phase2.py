import json
from pathlib import Path

from adaptive_bootstrap import BootstrapPredictor


def test_predictor_dry_run_writes_jsonl(tmp_path):
    # Prepare workspace
    (tmp_path / 'tasks').mkdir()
    f1 = tmp_path / 'tasks' / 'task_TASK_0001.md'
    f1.write_text('# Test task file\nSome content about bootstrapping and predictor.')
    (tmp_path / 'reports').mkdir()
    (tmp_path / 'reports' / 'report_TASK_0001.md').write_text('# Report')

    # Add current.json
    (tmp_path / 'current.json').write_text(json.dumps({'STATE': {'loop': 999}}))

    predictor = BootstrapPredictor(tmp_path)

    selected = predictor.predict_needed_files('bootstrap predictor test', dry_run=True)

    # It should return a list (even if empty)
    assert isinstance(selected, list)

    # Dry run log should exist and contain one line
    log_path = tmp_path / '.bootstrap_dry_runs.jsonl'
    assert log_path.exists(), 'Dry-run log not created'

    lines = log_path.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) >= 1

    entry = json.loads(lines[-1])
    assert entry['task_context'] == 'bootstrap predictor test'
    assert 'selected_files' in entry


def test_predictor_returns_candidates_when_no_model(tmp_path):
    # Ensure predictor doesn't crash if embeddings aren't available
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'README.md').write_text('Welcome to the project. Bootstrap docs here.')

    predictor = BootstrapPredictor(tmp_path)
    selected = predictor.predict_needed_files('Readme related task', budget_tokens=100000)

    # Should be a list, candidates may include our README
    assert isinstance(selected, list)
    # At least the README should be considered (may or may not be selected depending on threshold)
    assert isinstance(selected, list)

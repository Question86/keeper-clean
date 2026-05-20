# MODE: TEST\n\nimport os
import requests
import pytest
from tasks.poc_task_0022 import run


def test_poc_mock_creates_files(tmp_path):
    outdir = tmp_path / "samples"
    rc = run(str(outdir), mode="mock")
    assert rc == 0
    cal = outdir / "calendar.ics"
    readme = outdir / "README.md"
    assert cal.exists()
    assert readme.exists()
    txt = readme.read_text(encoding="utf-8")
    assert "POC TASK_0022" in txt


def test_poc_real_handles_unreachable(monkeypatch, tmp_path):
    # Simulate requests.post raising ConnectionError
    def fake_post(*args, **kwargs):
        raise requests.exceptions.ConnectionError("simulated unreachable")

    monkeypatch.setattr(requests, "post", fake_post)
    outdir = tmp_path / "samples2"
    rc = run(str(outdir), mode="real")
    # Expect failure code 2 and error README
    assert rc == 2
    readme = outdir / "README.md"
    assert readme.exists()
    txt = readme.read_text(encoding="utf-8")
    assert "Ollama generation failed" in txt

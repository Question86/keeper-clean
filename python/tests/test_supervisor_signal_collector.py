import json
from pathlib import Path

from scripts.supervisor_signal_collector import collect_supervisor_signals


def _write_archive(path: Path, loop_num: int) -> None:
    content = (
        f"# ARCHIV_{loop_num:04d}\n\n"
        "## TASKS AT FINALIZATION\n"
        "[ref:tasks/task_TASK_0001.md|v:1|tags:completed|src:test]\n"
        "[ref:reports/report_TASK_0001_L01_v01.md|v:1|tags:report|src:test]\n"
    )
    path.write_text(content, encoding="utf-8")


def _write_tx_log(path: Path) -> None:
    lines = [
        {"timestamp": "2026-02-16T01:00:00Z", "operation": "confirm-bootstrap", "outcome": "SUCCESS", "loop": 1},
        {"timestamp": "2026-02-16T01:10:00Z", "operation": "file_write", "outcome": "SUCCESS", "loop": 1},
        {"timestamp": "2026-02-16T01:20:00Z", "operation": "file_write", "outcome": "FAILED", "loop": 1},
    ]
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")


def test_collect_supervisor_signals_minimal_workspace(tmp_path):
    (tmp_path / "analysis").mkdir(parents=True, exist_ok=True)
    (tmp_path / "archive").mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)

    (tmp_path / "analysis" / "code_bloat_detector.py").write_text(
        "import os\n\ndef hello():\n    return 1\n",
        encoding="utf-8",
    )
    _write_archive(tmp_path / "archive" / "ARCHIV_0001.md", 1)
    _write_tx_log(tmp_path / "_transaction_log.jsonl")

    payload = collect_supervisor_signals(tmp_path, loops=4)
    assert "generated_at" in payload
    assert "signals" in payload

    signals = payload["signals"]
    assert set(signals.keys()) == {
        "code_bloat",
        "trend_analysis",
        "loop_insights",
        "behavioral_zone",
        "breadcrumb_gaps",
    }

    assert signals["code_bloat"]["ok"] is True
    assert "average_bloat_score" in signals["code_bloat"]
    assert "zone" in signals["behavioral_zone"] or signals["behavioral_zone"]["ok"] is False


def test_collect_supervisor_signals_handles_missing_inputs(tmp_path):
    payload = collect_supervisor_signals(tmp_path, loops=2)
    signals = payload["signals"]
    assert signals["code_bloat"]["ok"] is False
    assert signals["trend_analysis"]["ok"] is False
    assert signals["loop_insights"]["ok"] is False

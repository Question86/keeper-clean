import json
from pathlib import Path

from scripts.prepare_finalization import prepare_finalization


def _write_current_json(root: Path, loop: int, status: str = "ACTIVE") -> None:
    payload = {"STATE": {"loop": loop, "status": status}}
    (root / "current.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_hash_and_secret(root: Path) -> None:
    (root / "validation_hashes.json").write_text(json.dumps({"a": "b"}), encoding="utf-8")
    key_dir = root / "validation_keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    (key_dir / "approval_secret").write_bytes(b"test-secret")


def test_prepare_finalization_success_path(tmp_path):
    _write_current_json(tmp_path, loop=141, status="ACTIVE")
    _write_hash_and_secret(tmp_path)

    result = prepare_finalization(tmp_path, signer="tester")
    assert result["success"] is True
    assert result["gates"]["approval"]["ok"] is True

    report_path = tmp_path / "reports" / "report_LOOP_141_FINALIZATION_v01.md"
    assert report_path.exists()
    assert Path(str(report_path) + ".ready").exists()
    assert (tmp_path / "_BOOTSTRAP.md").exists()
    assert (tmp_path / "Littleboot.md").exists()
    assert (tmp_path / "approvals" / "FINALIZE_APPROVAL_L141.json").exists()


def test_prepare_finalization_failure_missing_loop_resolution(tmp_path):
    result = prepare_finalization(tmp_path)
    assert result["success"] is False
    assert result["gates"]["loop_resolution"]["ok"] is False


def test_prepare_finalization_failure_missing_approval_secret(tmp_path):
    _write_current_json(tmp_path, loop=141, status="ACTIVE")
    (tmp_path / "validation_hashes.json").write_text(json.dumps({"a": "b"}), encoding="utf-8")

    result = prepare_finalization(tmp_path, signer="tester")
    assert result["success"] is False
    assert result["gates"]["approval"]["ok"] is False
    assert "missing validation_keys/approval_secret" in result["gates"]["approval"]["message"]


def test_prepare_finalization_failure_invalid_state_status(tmp_path):
    _write_current_json(tmp_path, loop=141, status="FINALIZED")
    _write_hash_and_secret(tmp_path)

    result = prepare_finalization(tmp_path, signer="tester")
    assert result["success"] is False
    assert result["gates"]["state_status"]["ok"] is False

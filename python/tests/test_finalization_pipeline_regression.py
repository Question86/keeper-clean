import hashlib
import hmac
import json
import sys
import types
from pathlib import Path

import pytest

import loop_cockpit
import validation_integrity as vi


def test_finalize_rejects_duplicate_when_loop_already_finalized(monkeypatch):
    monkeypatch.setattr(
        loop_cockpit,
        "read_json_file",
        lambda _path: {"STATE": {"loop": 142, "status": "FINALIZED"}},
    )
    with pytest.raises(ValueError, match="ACTIVE or READY_FOR_FINALIZATION"):
        loop_cockpit.finalize_loop_procedure()


def test_finalize_rolls_back_archive_on_current_json_write_failure(tmp_path, monkeypatch):
    current_path = tmp_path / "current.json"
    neu_path = tmp_path / "NEU.md"
    alt_path = tmp_path / "Alt.md"
    tx_log = tmp_path / "_transaction_log.jsonl"
    session_md = tmp_path / "_SESSION.md"

    current_path.write_text(
        json.dumps(
            {
                "STATE": {
                    "loop": 142,
                    "status": "ACTIVE",
                    "lastTaskWorked": "TASK_0275",
                }
            }
        ),
        encoding="utf-8",
    )
    neu_path.write_text("# NEU\n", encoding="utf-8")
    alt_path.write_text("# ALT\n", encoding="utf-8")
    session_md.write_text("# SESSION\n", encoding="utf-8")
    tx_log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-02-16T01:00:00Z",
                        "operation": "confirm-bootstrap",
                        "outcome": "SUCCESS",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-02-16T01:01:00Z",
                        "operation": "file_write",
                        "outcome": "SUCCESS",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(loop_cockpit, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(loop_cockpit, "CURRENT_JSON", current_path)
    monkeypatch.setattr(loop_cockpit, "NEU_MD", neu_path)
    monkeypatch.setattr(loop_cockpit, "ALT_MD", alt_path)
    monkeypatch.setattr(loop_cockpit, "TRANSACTION_LOG", tx_log)
    monkeypatch.setattr(loop_cockpit, "SESSION_MD", session_md)
    monkeypatch.setattr(loop_cockpit, "validate_finalization_entry_gates", lambda: (True, ""))
    monkeypatch.setattr(loop_cockpit, "get_report_files", lambda: [])
    monkeypatch.setattr(loop_cockpit, "regenerate_loop_gate", lambda reason="": None)
    monkeypatch.setattr(loop_cockpit, "create_phase_checkpoint", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(loop_cockpit, "log_transaction", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(loop_cockpit.KnowledgeDBEventHandler, "on_archive_changed", staticmethod(lambda _p: None))

    class _DummyKnowledgeDB:
        def __init__(self, _root):
            pass

        def search(self, **_kwargs):
            return [{"id": 1}]

    class _DummyIntegrityProtector:
        def __init__(self, _root):
            pass

        def validate_state_transition(self, **_kwargs):
            return (True, "ok")

    monkeypatch.setitem(sys.modules, "knowledge_db", types.SimpleNamespace(KnowledgeDB=_DummyKnowledgeDB))
    monkeypatch.setitem(
        sys.modules,
        "ai_integrity_protector",
        types.SimpleNamespace(AIIntegrityProtector=_DummyIntegrityProtector),
    )

    def _fail_current_write(path, _payload):
        if Path(path) == current_path:
            raise RuntimeError("simulated current.json write failure")
        return None

    monkeypatch.setattr(loop_cockpit, "write_json_file", _fail_current_write)

    with pytest.raises(RuntimeError, match="simulated current.json write failure"):
        loop_cockpit.finalize_loop_procedure()

    archive_path = tmp_path / "ARCHIV_0142.md"
    assert not archive_path.exists()
    current_data = json.loads(current_path.read_text(encoding="utf-8"))
    assert current_data["STATE"]["status"] == "ACTIVE"


def test_verify_approval_detects_stale_hash_mismatch(tmp_path, monkeypatch):
    approvals = tmp_path / "approvals"
    keys = tmp_path / "validation_keys"
    approvals.mkdir(parents=True, exist_ok=True)
    keys.mkdir(parents=True, exist_ok=True)

    hash_file = tmp_path / "validation_hashes.json"
    hash_file.write_text(json.dumps({"finalization_validations.py": "hash-a"}), encoding="utf-8")
    secret = b"test-secret"
    (keys / "approval_secret").write_bytes(secret)

    loop_num = 142
    validation_hash = hashlib.sha256(hash_file.read_bytes()).hexdigest()
    payload = {
        "loop": loop_num,
        "timestamp": "2026-02-16T02:00:00Z",
        "signer": "tester",
        "validation_hash": validation_hash,
    }
    canonical = (
        f"loop={payload['loop']}&timestamp={payload['timestamp']}"
        f"&validation_hash={payload['validation_hash']}&signer={payload['signer']}"
    )
    payload["signature"] = hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    (approvals / "FINALIZE_APPROVAL_L142.json").write_text(json.dumps(payload), encoding="utf-8")

    # Simulate stale approval by mutating the hash source after approval issuance.
    hash_file.write_text(json.dumps({"finalization_validations.py": "hash-b"}), encoding="utf-8")

    monkeypatch.setattr(vi, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(vi, "HASH_FILE", hash_file)
    monkeypatch.setattr(vi, "KEY_DIR", keys)
    monkeypatch.setattr(vi, "APPROVAL_SECRET_FILE", keys / "approval_secret")

    ok, msg = vi.verify_approval_for_loop(loop_num)
    assert not ok
    assert "validation_hash" in msg

import hashlib
import hmac
import json
from pathlib import Path

import artifact_naming_contract as anc
import validation_integrity as vi


def test_bootstrap_resolver_prefers_canonical_then_alias(tmp_path):
    alias = tmp_path / "bootstrap.md"
    alias.write_text("# legacy bootstrap", encoding="utf-8")
    assert anc.resolve_bootstrap_path(tmp_path) == alias

    canonical = tmp_path / "_BOOTSTRAP.md"
    canonical.write_text("# canonical bootstrap", encoding="utf-8")
    assert anc.resolve_bootstrap_path(tmp_path) == canonical


def test_find_finalization_reports_supports_canonical_and_legacy(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    canonical = reports / "report_LOOP_141_FINALIZATION_v01.md"
    legacy = reports / "report_LOOP_141_FINALIZATION_L141_v01.md"
    canonical.write_text("ok", encoding="utf-8")
    legacy.write_text("ok", encoding="utf-8")

    found = anc.find_finalization_reports(tmp_path, 141)
    names = {p.name for p in found}
    assert "report_LOOP_141_FINALIZATION_v01.md" in names
    assert "report_LOOP_141_FINALIZATION_L141_v01.md" in names


def test_normalize_legacy_artifacts_plans_and_applies_moves(tmp_path):
    (tmp_path / "bootstrap.md").write_text("legacy", encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "report_LOOP_141_FINALIZATION_L141_v01.md").write_text("legacy", encoding="utf-8")

    dry = anc.normalize_legacy_artifacts(tmp_path, apply_changes=False)
    assert any(src.endswith("bootstrap.md") for src, _ in dry["actions"])
    assert any("FINALIZATION_L141" in src for src, _ in dry["actions"])

    anc.normalize_legacy_artifacts(tmp_path, apply_changes=True)
    assert (tmp_path / "_BOOTSTRAP.md").exists()
    assert (reports / "report_LOOP_141_FINALIZATION_v01.md").exists()


def test_verify_approval_accepts_legacy_alias_filename(tmp_path, monkeypatch):
    approvals = tmp_path / "approvals"
    keys = tmp_path / "validation_keys"
    approvals.mkdir(parents=True, exist_ok=True)
    keys.mkdir(parents=True, exist_ok=True)

    hash_file = tmp_path / "validation_hashes.json"
    hash_file.write_text(json.dumps({"a": "b"}), encoding="utf-8")
    secret = b"test-secret"
    (keys / "approval_secret").write_bytes(secret)

    loop_num = 141
    validation_hash = hashlib.sha256(hash_file.read_bytes()).hexdigest()
    payload = {
        "loop": loop_num,
        "timestamp": "2026-02-16T00:00:00Z",
        "signer": "test",
        "validation_hash": validation_hash,
    }
    canonical = (
        f"loop={payload['loop']}&timestamp={payload['timestamp']}"
        f"&validation_hash={payload['validation_hash']}&signer={payload['signer']}"
    )
    payload["signature"] = hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    # Legacy alias path accepted via explicit mapping.
    legacy_path = approvals / f"finalize_approval_L{loop_num}.json"
    legacy_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(vi, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(vi, "HASH_FILE", hash_file)
    monkeypatch.setattr(vi, "KEY_DIR", keys)
    monkeypatch.setattr(vi, "APPROVAL_SECRET_FILE", keys / "approval_secret")

    ok, msg = vi.verify_approval_for_loop(loop_num)
    assert ok, msg

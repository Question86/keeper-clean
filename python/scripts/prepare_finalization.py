#!/usr/bin/env python3
import argparse
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from artifact_naming_contract import (
    canonical_approval_path,
    canonical_bootstrap_path,
    canonical_finalization_report_path,
    canonical_littleboot_path,
)
from output_safety import safe_print


def _read_current_state(workspace_root: Path) -> Dict[str, Any]:
    current_path = workspace_root / "current.json"
    if not current_path.exists():
        return {}
    try:
        return json.loads(current_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_loop_num(state: Dict[str, Any], loop_override: Optional[int]) -> Optional[int]:
    if loop_override is not None:
        return int(loop_override)
    try:
        return int(state.get("STATE", {}).get("loop"))
    except Exception:
        return None


def _write_file(path: Path, content: str, dry_run: bool, actions: list) -> None:
    actions.append(f"write:{path}")
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_or_validate_approval(
    workspace_root: Path,
    loop_num: int,
    signer: Optional[str],
    dry_run: bool,
    actions: list,
) -> Dict[str, Any]:
    gate = {"ok": False, "message": "", "path": str(canonical_approval_path(workspace_root, loop_num))}
    approval_path = canonical_approval_path(workspace_root, loop_num)
    key_path = workspace_root / "validation_keys" / "approval_secret"
    hash_path = workspace_root / "validation_hashes.json"

    def _hash_summary() -> str:
        if not hash_path.exists():
            return ""
        return hashlib.sha256(hash_path.read_bytes()).hexdigest()

    def _verify(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"ok": False, "message": "approval file missing"}
        if not key_path.exists():
            return {"ok": False, "message": "missing validation_keys/approval_secret for approval verification"}
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"ok": False, "message": "invalid approval JSON"}
        expected_hash = _hash_summary()
        if not expected_hash:
            return {"ok": False, "message": "missing validation_hashes.json summary for approval verification"}
        if int(obj.get("loop", -1)) != int(loop_num):
            return {"ok": False, "message": "approval loop mismatch"}
        if obj.get("validation_hash") != expected_hash:
            return {"ok": False, "message": "approval validation_hash mismatch"}
        canonical = (
            f"loop={obj['loop']}&timestamp={obj['timestamp']}"
            f"&validation_hash={obj['validation_hash']}&signer={obj['signer']}"
        )
        expected_sig = hmac.new(key_path.read_bytes(), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        if obj.get("signature") != expected_sig:
            return {"ok": False, "message": "approval signature invalid"}
        return {"ok": True, "message": "existing approval valid"}

    if approval_path.exists():
        verification = _verify(approval_path)
        gate["ok"] = verification["ok"]
        gate["message"] = verification["message"]
        return gate

    if not signer:
        gate["message"] = "missing approval and no --signer provided"
        return gate

    if not key_path.exists():
        gate["message"] = "missing validation_keys/approval_secret for approval signing"
        return gate

    validation_hash = _hash_summary()
    if not validation_hash:
        gate["message"] = "missing validation_hashes.json summary for approval signing"
        return gate

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "loop": int(loop_num),
        "timestamp": timestamp,
        "signer": signer,
        "validation_hash": validation_hash,
    }
    canonical = (
        f"loop={payload['loop']}&timestamp={payload['timestamp']}"
        f"&validation_hash={payload['validation_hash']}&signer={payload['signer']}"
    )
    secret = key_path.read_bytes()
    payload["signature"] = hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    _write_file(approval_path, json.dumps(payload, indent=2), dry_run=dry_run, actions=actions)

    if dry_run:
        gate["ok"] = True
        gate["message"] = "approval would be created (dry-run)"
        return gate

    verification = _verify(approval_path)
    gate["ok"] = verification["ok"]
    gate["message"] = "approval created and verified" if verification["ok"] else verification["message"]
    return gate


def prepare_finalization(
    workspace_root: Path,
    loop_override: Optional[int] = None,
    dry_run: bool = False,
    signer: Optional[str] = None,
) -> Dict[str, Any]:
    actions = []
    state = _read_current_state(workspace_root)
    loop_num = _resolve_loop_num(state, loop_override)

    gates: Dict[str, Dict[str, Any]] = {}

    if loop_num is None:
        gates["loop_resolution"] = {"ok": False, "message": "could not resolve loop (set --loop)"}
        return {"success": False, "dry_run": dry_run, "actions": actions, "gates": gates}
    gates["loop_resolution"] = {"ok": True, "message": f"loop={loop_num}"}

    status = state.get("STATE", {}).get("status")
    gates["state_status"] = {
        "ok": status in (None, "ACTIVE", "READY_FOR_FINALIZATION"),
        "message": f"status={status}",
    }

    bootstrap_path = canonical_bootstrap_path(workspace_root)
    if not bootstrap_path.exists():
        content = "# _BOOTSTRAP\n\nPrepared by prepare-finalization utility.\n"
        _write_file(bootstrap_path, content, dry_run=dry_run, actions=actions)
    gates["bootstrap"] = {"ok": True, "path": str(bootstrap_path)}

    littleboot_path = canonical_littleboot_path(workspace_root)
    if not littleboot_path.exists():
        content = (
            "# LITTLEBOOT\n\n"
            "Prepared by prepare-finalization utility.\n\n"
            "Contains minimal transfer context for next bootstrap.\n"
        )
        _write_file(littleboot_path, content, dry_run=dry_run, actions=actions)
    gates["littleboot"] = {"ok": True, "path": str(littleboot_path)}

    report_path = canonical_finalization_report_path(workspace_root, loop_num, version=1)
    report_created = False
    if not report_path.exists():
        report_created = True
        report_content = (
            f"# REPORT: LOOP {loop_num} FINALIZATION\n\n"
            f"**Loop:** {loop_num}\n"
            f"**Status:** 🔄 IN_PROGRESS\n"
            f"**Created:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n"
            "---\n\n"
            "Prepared by `scripts/prepare_finalization.py`.\n"
        )
        _write_file(report_path, report_content, dry_run=dry_run, actions=actions)

    ready_marker = Path(str(report_path) + ".ready")
    if report_created and not ready_marker.exists():
        _write_file(ready_marker, "ready\n", dry_run=dry_run, actions=actions)
    gates["finalization_report"] = {
        "ok": True,
        "path": str(report_path),
        "ready_marker": str(ready_marker),
        "generated": report_created,
    }

    gates["approval"] = _create_or_validate_approval(
        workspace_root=workspace_root,
        loop_num=loop_num,
        signer=signer,
        dry_run=dry_run,
        actions=actions,
    )

    overall_success = all(g.get("ok") is True for g in gates.values())
    return {
        "success": overall_success,
        "dry_run": dry_run,
        "loop": loop_num,
        "actions": actions,
        "gates": gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare all required finalization artifacts in one run.")
    parser.add_argument("--loop", type=int, default=None, help="Explicit loop override.")
    parser.add_argument("--dry-run", action="store_true", help="Plan actions without writing files.")
    parser.add_argument("--signer", type=str, default=None, help="Signer name used to auto-create approval token.")
    parser.add_argument(
        "--workspace",
        type=str,
        default=".",
        help="Workspace root path (defaults to current directory).",
    )
    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    result = prepare_finalization(
        workspace_root=workspace_root,
        loop_override=args.loop,
        dry_run=args.dry_run,
        signer=args.signer,
    )
    safe_print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

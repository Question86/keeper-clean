from pathlib import Path
import hashlib
import json
import hmac
import os
from typing import Tuple
from artifact_naming_contract import approval_candidates

WORKSPACE_ROOT = Path(__file__).parent
HASH_FILE = WORKSPACE_ROOT / 'validation_hashes.json'
APPROVALS_DIR = WORKSPACE_ROOT / 'approvals'
KEY_DIR = WORKSPACE_ROOT / 'validation_keys'
APPROVAL_SECRET_FILE = KEY_DIR / 'approval_secret'


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def load_expected_hashes() -> dict:
    if not HASH_FILE.exists():
        return {}
    try:
        return json.loads(HASH_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def get_validation_hash_summary() -> str:
    """Return a SHA256 hex digest summarizing the `validation_hashes.json` contents.

    Used by approval tokens to bind approval to a particular set of validation rules.
    """
    if not HASH_FILE.exists():
        return ""
    data = HASH_FILE.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _load_approval_secret() -> bytes:
    try:
        if not KEY_DIR.exists():
            return b''
        if not APPROVAL_SECRET_FILE.exists():
            return b''
        return APPROVAL_SECRET_FILE.read_bytes()
    except Exception:
        return b''


def verify_approval_for_loop(loop_num: int) -> Tuple[bool, str]:
    """Verify that an approval file exists and is HMAC-signed with the current validation hash.

    Approval file expected at `approvals/FINALIZE_APPROVAL_L{loop_num}.json` with fields:
      {"loop": <int>, "timestamp": <iso>, "signer": <str>, "validation_hash": <hex>, "signature": <hex>}

    Returns (True, '') when verification passes.
    """
    try:
        approvals_dir = (WORKSPACE_ROOT / 'approvals').resolve()
        approvals_dir.mkdir(parents=True, exist_ok=True)
        candidates = approval_candidates(WORKSPACE_ROOT, int(loop_num))
        fname = next((p for p in candidates if p.exists()), None)
        if fname is None:
            expected = ", ".join(str(p) for p in candidates)
            return (False, f"Missing approval file. Accepted names: {expected}")

        try:
            obj = json.loads(fname.read_text(encoding='utf-8'))
        except Exception:
            return (False, f"Invalid approval file JSON: {fname}")

        required = ('loop', 'timestamp', 'signer', 'validation_hash', 'signature')
        if not all(k in obj for k in required):
            return (False, f"Approval file missing required fields: {fname}")

        # Check loop matches
        if int(obj.get('loop', -1)) != int(loop_num):
            return (False, f"Approval loop mismatch: expected {loop_num}, got {obj.get('loop')}")

        # Verify validation_hash matches current validation_hashes.json
        current_hash = get_validation_hash_summary()
        if not current_hash:
            return (False, "No validation_hashes.json present to bind approval to")
        if obj.get('validation_hash') != current_hash:
            return (False, "Approval validation_hash does not match current validation_hashes.json")

        # Verify HMAC signature
        secret = _load_approval_secret()
        if not secret:
            return (False, "No approval secret available for verification (validation_keys/approval_secret missing)")

        # Recreate canonical message
        canonical = f"loop={obj['loop']}&timestamp={obj['timestamp']}&validation_hash={obj['validation_hash']}&signer={obj['signer']}"
        sig = obj.get('signature')
        if not sig:
            return (False, "Approval signature missing")
        computed = hmac.new(secret, canonical.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, sig):
            return (False, "Approval signature invalid")

        return (True, '')
    except Exception as e:
        return (False, f"Approval verification error: {e}")


def verify_validation_files() -> (bool, str):
    """Verify validation-related source files match recorded hashes.

    Returns (True, '') if OK, otherwise (False, message).
    """
    expected = load_expected_hashes()
    if not expected:
        return (False, f"No validation_hashes.json found at {HASH_FILE}")

    mismatches = []
    for rel, exp in expected.items():
        p = WORKSPACE_ROOT / rel
        if not p.exists():
            mismatches.append(f"Missing file: {rel}")
            continue
        actual = compute_sha256(p)
        if actual != exp:
            mismatches.append(f"Hash mismatch: {rel}")

    if mismatches:
        return (False, '; '.join(mismatches))
    return (True, '')

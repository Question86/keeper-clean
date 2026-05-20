"""Create an approval token for loop finalization.

Usage:
    python scripts/sign_approval.py <loop_num> <signer_name>

Creates `approvals/FINALIZE_APPROVAL_L<loop_num>.json` with HMAC-SHA256 signature.
"""
import sys
from pathlib import Path
import json
import hmac
import hashlib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / 'validation_keys'
SECRET_FILE = KEY_DIR / 'approval_secret'
APPROVALS_DIR = ROOT / 'approvals'
APPROVALS_DIR.mkdir(parents=True, exist_ok=True)

if len(sys.argv) < 3:
    print("Usage: python scripts/sign_approval.py <loop_num> <signer_name>")
    sys.exit(2)

loop = int(sys.argv[1])
signer = sys.argv[2]

if not SECRET_FILE.exists():
    print(f"Missing secret file: {SECRET_FILE}. Run scripts/create_signing_key.py first.")
    sys.exit(1)

secret = SECRET_FILE.read_bytes()

# Compute current validation_hash (digest of validation_hashes.json)
HASH_FILE = ROOT / 'validation_hashes.json'
if not HASH_FILE.exists():
    print("validation_hashes.json not found in repo root. Generate it first via scripts/generate_validation_hashes.py")
    sys.exit(1)

validation_hash = hashlib.sha256(HASH_FILE.read_bytes()).hexdigest()

ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
canonical = f"loop={loop}&timestamp={ts}&validation_hash={validation_hash}&signer={signer}"
signature = hmac.new(secret, canonical.encode('utf-8'), hashlib.sha256).hexdigest()

obj = {
    'loop': loop,
    'timestamp': ts,
    'signer': signer,
    'validation_hash': validation_hash,
    'signature': signature
}

out = APPROVALS_DIR / f"FINALIZE_APPROVAL_L{loop}.json"
out.write_text(json.dumps(obj, indent=2), encoding='utf-8')
print(f"Wrote approval file: {out}")
print("Keep this file in approvals/ and ensure it is committed to audit if appropriate.")

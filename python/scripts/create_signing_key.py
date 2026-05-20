"""Create HMAC approval secret for finalization approvals.

Writes `validation_keys/approval_secret` with random bytes and prints instructions.
"""
import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / 'validation_keys'
KEY_DIR.mkdir(parents=True, exist_ok=True)
SECRET_FILE = KEY_DIR / 'approval_secret'

if SECRET_FILE.exists():
    print(f"approval_secret already exists at: {SECRET_FILE}")
    print("If you want to rotate the secret, delete the file and run this script again.")
else:
    secret = secrets.token_bytes(32)
    SECRET_FILE.write_bytes(secret)
    os.chmod(SECRET_FILE, 0o600)
    print(f"Created approval secret at: {SECRET_FILE}")
    print("Keep this file secure. Use scripts/sign_approval.py to create approval tokens using this secret.")

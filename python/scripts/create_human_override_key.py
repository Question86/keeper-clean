#!/usr/bin/env python3
"""Create human override password hash for master override system.

Generates PBKDF2 hash of password and stores in validation_keys/human_override_hash.
Use strong password - this cannot be recovered if lost.
"""
import os
import json
import base64
import hashlib
import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / 'validation_keys'
HASH_FILE = KEY_DIR / 'human_override_hash'

import sys

def main():
    KEY_DIR.mkdir(parents=True, exist_ok=True)

    if HASH_FILE.exists():
        print(f"Warning: {HASH_FILE} already exists. Overwrite? (y/N)")
        response = input().strip().lower()
        if response != 'y':
            print("Aborted.")
            return

    password = input("Enter human override password: ")
    confirm = input("Confirm password: ")

    if password != confirm:
        print("Passwords do not match.")
        return

    if len(password) < 12:
        print("Password too short. Use at least 12 characters.")
        return

    # Generate random salt
    salt = os.urandom(32)
    iterations = 100000

    # Derive key
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)

    # Store as JSON
    data = {
        'salt': base64.b64encode(salt).decode('utf-8'),
        'hash': base64.b64encode(key).decode('utf-8'),
        'iterations': iterations
    }

    HASH_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
    HASH_FILE.chmod(0o600)  # Restrict permissions

    print(f"Human override hash created at {HASH_FILE}")
    print("Keep password secure - it cannot be recovered.")

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""Create human master password hash for override reset system.

Generates PBKDF2 hash of master password and stores in validation_keys/human_master_hash.
Use very strong password - this enables password reset.
"""
import os
import json
import base64
import hashlib
import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / 'validation_keys'
HASH_FILE = KEY_DIR / 'human_master_hash'

import sys

def main():
    KEY_DIR.mkdir(parents=True, exist_ok=True)

    if HASH_FILE.exists():
        print(f"Warning: {HASH_FILE} already exists. Overwrite? (y/N)")
        response = input().strip().lower()
        if response != 'y':
            print("Aborted.")
            return

    password = input("Enter human master password: ")
    confirm = input("Confirm password: ")

    if password != confirm:
        print("Passwords do not match.")
        return

    if len(password) < 20:
        print("Password too short. Use at least 20 characters.")
        return

    # Generate random salt
    salt = os.urandom(32)
    iterations = 200000  # Higher for master

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

    print(f"Human master hash created at {HASH_FILE}")
    print("Keep master password secure - it enables password reset.")

if __name__ == '__main__':
    main()
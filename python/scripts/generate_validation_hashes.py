#!/usr/bin/env python3
from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'finalization_validations.py',
    'validations_core.py',
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    out = {}
    for f in FILES:
        p = ROOT / f
        if not p.exists():
            print('Missing', p)
            continue
        out[f] = sha256(p)

    (ROOT / 'validation_hashes.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print('Wrote validation_hashes.json')


if __name__ == '__main__':
    main()

# MODE: SCRIPT\n\n"""Verify Ollama model blob: existence, size and SHA256 checksum."""
import sys
import hashlib
from pathlib import Path

CHUNK = 8 * 1024 * 1024


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(CHUNK)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python tools/verify_ollama_blob.py <path> [<path> ...]')
        sys.exit(2)

    for p in sys.argv[1:]:
        path = Path(p)
        print('PATH:', path)
        if not path.exists():
            print('EXISTS: False')
            print('-----')
            continue
        st = path.stat()
        print('EXISTS: True')
        print('SIZE:', st.st_size)
        try:
            s = sha256_file(path)
            print('SHA256:', s)
        except Exception as e:
            print('SHA256: ERROR', e)
        print('LAST_MODIFIED:', st.st_mtime)
        print('-----')

lines = open('_transaction_log.jsonl', 'r').readlines()
print(f'Total lines: {len(lines)}')

bad_lines = [i+1 for i, line in enumerate(lines) if not line.strip()]
print(f'Empty lines: {bad_lines}')

import json
for i, line in enumerate(lines[:5]):
    try:
        json.loads(line)
        print(f'Line {i+1}: OK')
    except Exception as e:
        print(f'Line {i+1}: BAD - {repr(line.strip())} - Error: {e}')
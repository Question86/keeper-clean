#!/usr/bin/env python3
from context_dreamer import ContextDreamer

dreamer = ContextDreamer()
print('Testing updated relative value matrix system...')

reference = dreamer._find_reference_connection()
if reference:
    print(f'Found reference: {reference["file_a"]} ↔ {reference["file_b"]}')
    print(f'Strength: {reference["strength"]:.3f}')
    print(f'Evidence: {reference["evidence"]}')
    print(f'Superior files: {reference.get("superior_files", [])}')
else:
    print('No reference connection found')
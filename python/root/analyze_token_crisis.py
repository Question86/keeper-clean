#!/usr/bin/env python3
"""Emergency token cost analysis"""
import csv
from pathlib import Path

csv_path = Path(r"D:\Keeper-Clean-Loop1\claude_api_tokens_2026_01_27_03h_UTC.csv")

total_input = 0
total_output = 0
total_cache_read = 0
total_cache_write = 0

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        no_cache = int(row['usage_input_tokens_no_cache'] or 0)
        cache_write = int(row['usage_input_tokens_cache_write_5m'] or 0)
        cache_read = int(row['usage_input_tokens_cache_read'] or 0)
        output = int(row['usage_output_tokens'] or 0)
        
        total_input += (no_cache + cache_write + cache_read)
        total_output += output
        total_cache_read += cache_read
        total_cache_write += cache_write

print("TOKEN CRISIS ANALYSIS - Hour 03 UTC")
print("=" * 60)
print(f"Total Input:       {total_input:,} tokens")
print(f"  - Cache Read:    {total_cache_read:,} tokens ({total_cache_read/total_input*100:.1f}%)")
print(f"  - Cache Write:   {total_cache_write:,} tokens ({total_cache_write/total_input*100:.1f}%)")
print(f"Total Output:      {total_output:,} tokens")
print(f"GRAND TOTAL:       {total_input + total_output:,} tokens")
print("=" * 60)
print()
print("COST BREAKDOWN (est. at $3/M input, $15/M output):")
print(f"  Input cost:  ${total_input * 3 / 1_000_000:.2f}")
print(f"  Output cost: ${total_output * 15 / 1_000_000:.2f}")
print(f"  TOTAL COST:  ${(total_input * 3 + total_output * 15) / 1_000_000:.2f}")

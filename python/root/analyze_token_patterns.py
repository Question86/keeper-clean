#!/usr/bin/env python3
"""
TOKEN PATTERN ANALYZER
TASK: TASK_0149 Phase 1
PURPOSE: Analyze token cost patterns from claude_api_tokens CSV
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def analyze_token_csv(csv_path: Path):
    """Parse CSV and analyze token patterns."""
    
    data_by_date = defaultdict(list)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row['usage_date_utc']
            data_by_date[date].append(row)
    
    print("TOKEN PATTERN ANALYSIS - TASK_0149 Phase 1")
    print("=" * 60)
    print()
    
    # Analyze recent entries
    sorted_dates = sorted(data_by_date.keys(), reverse=True)
    
    for date in sorted_dates[:5]:  # Last 5 days
        print(f"\n[DATE] {date}")
        print("-" * 60)
        
        entries = data_by_date[date]
        for entry in entries:
            model = entry['model_version']
            workspace = entry['workspace']
            
            # Parse token counts
            no_cache = int(entry['usage_input_tokens_no_cache'] or 0)
            cache_write_5m = int(entry['usage_input_tokens_cache_write_5m'] or 0)
            cache_write_1h = int(entry.get('usage_input_tokens_cache_write_1h', 0) or 0)
            cache_read = int(entry['usage_input_tokens_cache_read'] or 0)
            output = int(entry['usage_output_tokens'] or 0)
            
            total_input = no_cache + cache_write_5m + cache_write_1h + cache_read
            
            if total_input == 0:
                continue  # Skip empty entries
            
            print(f"\n  Model: {model}")
            print(f"  Workspace: {workspace}")
            print(f"  Input Tokens:")
            print(f"    - No cache: {no_cache:,}")
            print(f"    - Cache write (5m): {cache_write_5m:,}")
            if cache_write_1h > 0:
                print(f"    - Cache write (1h): {cache_write_1h:,}")
            print(f"    - Cache read: {cache_read:,}")
            print(f"    TOTAL INPUT: {total_input:,}")
            print(f"  Output Tokens: {output:,}")
            
            # Calculate efficiency metrics
            if cache_write_5m > 0:
                cache_efficiency = cache_read / cache_write_5m
                print(f"  [METRIC] Cache Efficiency: {cache_efficiency:.2f}x reuse")
            
            if no_cache > 0:
                cache_ratio = (cache_write_5m + cache_read) / no_cache
                print(f"  [METRIC] Cache vs Fresh: {cache_ratio:.2f}x")
            
            compression = total_input / max(output, 1)
            print(f"  [METRIC] Compression: {compression:.2f}x input->output")
    
    print("\n" + "=" * 60)
    print("\nANALYSIS COMPLETE")

if __name__ == "__main__":
    workspace = Path(r"D:\Keeper-Clean-Loop1")
    csv_file = workspace / "claude_api_tokens_2026_01.csv"
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        exit(1)
    
    analyze_token_csv(csv_file)

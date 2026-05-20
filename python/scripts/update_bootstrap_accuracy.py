#!/usr/bin/env python3
"""Update bootstrap prediction accuracy using breadcrumb trail.

Usage: python scripts/update_bootstrap_accuracy.py --prediction-id 123

This script will look up the prediction, read breadcrumbs since the prediction timestamp,
collect target files, and call `update_bootstrap_prediction_accuracy` in the DB.
"""
import argparse
import json
from pathlib import Path
from knowledge_db import KnowledgeDB
from ai_breadcrumb_tracker import get_breadcrumb_tracker

parser = argparse.ArgumentParser()
parser.add_argument('--prediction-id', type=int, help='Prediction record ID to update')
parser.add_argument('--hours-window', type=float, default=6.0, help='Time window (hours) after prediction to collect breadcrumbs')
args = parser.parse_args()

if not args.prediction_id:
    parser.print_help()
    raise SystemExit(1)

workspace = Path('.')
db = KnowledgeDB(workspace)

# Look up prediction record
cur = db.conn.execute('SELECT id, timestamp FROM bootstrap_predictions WHERE id = ?', (args.prediction_id,))
row = cur.fetchone()
if not row:
    print('Prediction id not found in database')
    raise SystemExit(1)

pred_ts = row['timestamp']
# Load breadcrumbs and filter those with timestamp >= pred_ts and within window
tracker = get_breadcrumb_tracker(workspace)
bcs = tracker.get_breadcrumb_trail(limit=2000)

# ISO timestamp parsing
from datetime import datetime, timedelta

try:
    pred_dt = datetime.fromisoformat(pred_ts.replace('Z', '+00:00'))
except Exception:
    print('Invalid prediction timestamp format:', pred_ts)
    raise SystemExit(1)

window_end = pred_dt + timedelta(hours=args.hours_window)
actual_files = set()
for bc in bcs:
    try:
        ts = datetime.fromisoformat(bc.timestamp.replace('Z', '+00:00'))
        if pred_dt <= ts <= window_end:
            actual_files.add(bc.target_file)
    except Exception:
        continue

actual_files = sorted(actual_files)
print('Found', len(actual_files), 'accessed files in breadcrumb trail for this prediction')
if not actual_files:
    print('No actual files found; nothing to update')
    raise SystemExit(0)

ok = db.update_bootstrap_prediction_accuracy(args.prediction_id, actual_files)
print('Update success:' if ok else 'Update failed')
print('Actual files:', actual_files)

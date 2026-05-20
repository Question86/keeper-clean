#!/usr/bin/env python3
"""Simple evaluator for BootstrapPredictor Phase 2

Usage: python scripts/evaluate_bootstrap_predictor.py --context "Implement auth with JWT"
"""
import argparse
from pathlib import Path
from adaptive_bootstrap import BootstrapPredictor

parser = argparse.ArgumentParser()
parser.add_argument('--context', required=True)
parser.add_argument('--budget', type=int, default=60000)
parser.add_argument('--workspace', default='.')
args = parser.parse_args()

workspace = Path(args.workspace).resolve()
predictor = BootstrapPredictor(workspace)
selected = predictor.predict_needed_files(args.context, budget_tokens=args.budget, dry_run=True)

print('Dry-run prediction:')
for p in selected:
    print(' -', p)

print('\nDry-run log: ', workspace / '.bootstrap_dry_runs.jsonl')

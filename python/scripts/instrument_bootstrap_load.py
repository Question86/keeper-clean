#!/usr/bin/env python3
"""Instrumented bootstrap loader (safe demo)

Simulates loading files selected by the adaptive bootstrap predictor and records
actual accesses using the AI breadcrumb tracker. This is a non-invasive utility
for testing Phase 2 usage tracking and data collection.
"""

from pathlib import Path
import sys

# Ensure repository root is on sys.path when running as a script inside scripts/
parent = Path(__file__).resolve().parent.parent
if str(parent) not in sys.path:
    sys.path.insert(0, str(parent))

from adaptive_bootstrap import BootstrapPredictor
from ai_breadcrumb_tracker import track_file_access


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/instrument_bootstrap_load.py \"<task_context>\" [budget_tokens]")
        sys.exit(1)

    task_context = sys.argv[1]
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 60000

    workspace = Path.cwd()
    predictor = BootstrapPredictor(workspace)

    selected = predictor.predict_needed_files(task_context, budget_tokens=budget)

    print(f"Selected {len(selected)} files for context '{task_context}':")
    for f in selected:
        print(f"  - {f}")

    # Bandwidth guard: estimate total bytes to read
    try:
        from rate_limit_handler import get_rate_limit_handler
        handler = get_rate_limit_handler(workspace)
        est_bytes = 0
        for f in selected:
            p = workspace / f
            try:
                est_bytes += p.stat().st_size if p.exists() else 0
            except Exception:
                continue

        bw_check = handler.bandwidth_guard.check_bandwidth('instrument_bootstrap_load', estimated_bytes=est_bytes)
        if not bw_check['should_proceed']:
            print(f"Bandwidth guard blocked instrumented load: {bw_check['reason']}. Aborting instrumentation.")
            return
    except Exception:
        handler = None

    # Simulate loading and record actual access
    for f in selected:
        path = str(workspace / f)
        try:
            track_file_access(path, source_context=f"bootstrap_load_TASK_0156")
            # Record actual bytes read for the file
            if handler is not None:
                try:
                    p = workspace / f
                    bytes_read = p.stat().st_size if p.exists() else 0
                    handler.bandwidth_guard.record_usage('instrument_bootstrap_load_file_read', int(bytes_read))
                except Exception:
                    pass
        except Exception as e:
            print(f"Warning: failed to track access for {f}: {e}")

    print("Instrumented bootstrap load complete. Breadcrumbs recorded.")


if __name__ == '__main__':
    main()

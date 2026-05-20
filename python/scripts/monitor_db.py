#!/usr/bin/env python3

import argparse
import datetime
import time
from pathlib import Path


def utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def sample(path: Path) -> tuple[int, str]:
    size = path.stat().st_size
    mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.UTC).isoformat()
    return size, mtime


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor knowledge DB file size/mtime changes.")
    parser.add_argument("--path", default="keeper_knowledge.db", help="DB path to monitor")
    parser.add_argument("--interval", type=float, default=5.0, help="Sampling interval in seconds")
    parser.add_argument("--duration", type=float, default=60.0, help="Total monitor duration in seconds")
    parser.add_argument("--once", action="store_true", help="Print one sample and exit")
    args = parser.parse_args()

    db_path = Path(args.path)
    print("monitor_start:", utc_now())

    if not db_path.exists():
        print(f"ERROR: file not found: {db_path}")
        print("monitor_end:", utc_now())
        return 0

    prev_size = None

    if args.once:
        try:
            size, mtime = sample(db_path)
            print(utc_now(), "size", size, "mtime", mtime)
        except Exception as e:
            print("ERROR", e)
        print("monitor_end:", utc_now())
        return 0

    end_ts = time.time() + max(0.0, args.duration)
    interval = max(0.1, args.interval)

    while time.time() < end_ts:
        try:
            size, mtime = sample(db_path)
            if prev_size is None or size != prev_size:
                print(utc_now(), "size", size, "mtime", mtime)
                prev_size = size
        except Exception as e:
            print("ERROR", e)
        time.sleep(interval)

    print("monitor_end:", utc_now())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

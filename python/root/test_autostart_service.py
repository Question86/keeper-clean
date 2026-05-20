#!/usr/bin/env python3
"""
Test Autostart Service
A simple service for testing the autostart framework
"""

import time
import signal
import sys
import os

def signal_handler(signum, frame):
    print("Test service received signal, shutting down...")
    sys.exit(0)

def main():
    print("Test autostart service starting...")

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    print("Test service running (PID: {})".format(os.getpid()))

    # Simple health check file
    health_file = "test_service_health.txt"
    with open(health_file, 'w') as f:
        f.write("healthy")

    try:
        while True:
            # Update health file
            with open(health_file, 'w') as f:
                f.write("healthy:{}".format(int(time.time())))

            time.sleep(10)  # Check every 10 seconds

    except KeyboardInterrupt:
        print("Test service interrupted")
    finally:
        # Cleanup
        if os.path.exists(health_file):
            os.remove(health_file)
        print("Test service stopped")

if __name__ == "__main__":
    main()
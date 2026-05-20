"""
Bootstrap Integration for Autostart Services
Integrates autostart system with loop bootstrap sequence
"""

import sys
import time
from pathlib import Path

# Add autostart directory to path
sys.path.insert(0, str(Path(__file__).parent / "autostart"))

from autostart_orchestrator import orchestrator


def integrate_with_bootstrap():
    """
    Integrate autostart services with bootstrap sequence.
    This function should be called during loop initialization.
    """
    print("🔄 Integrating autostart services with bootstrap...")

    try:
        # Start all autostart services
        results = orchestrator.start_all_services()

        if "error" in results:
            print(f"❌ Autostart integration failed: {results['error']}")
            if "details" in results:
                for detail in results["details"]:
                    print(f"   {detail}")
            return False

        # Wait a bit for services to stabilize
        print("⏳ Waiting for services to stabilize...")
        time.sleep(5)

        # Get final status
        status = orchestrator.get_status_summary()
        successful = status['running_services']
        total = status['enabled_services']

        if successful == total:
            print(f"✅ Autostart integration complete: {successful}/{total} services running")
            return True
        else:
            print(f"⚠️ Autostart integration partial: {successful}/{total} services running")
            failed_services = [name for name, s in status['services'].items()
                             if s['enabled'] and s['status'] != 'running']
            if failed_services:
                print(f"   Failed services: {', '.join(failed_services)}")
            return successful > 0  # Return True if at least some services started

    except Exception as e:
        print(f"❌ Autostart integration error: {e}")
        return False


def get_autostart_status():
    """Get current autostart services status for monitoring"""
    try:
        return orchestrator.get_status_summary()
    except Exception as e:
        return {"error": str(e)}


def emergency_stop():
    """Emergency stop all autostart services"""
    try:
        orchestrator.stop_all_services()
        return True
    except Exception as e:
        print(f"Error during emergency stop: {e}")
        return False


if __name__ == "__main__":
    # Allow direct execution for testing
    success = integrate_with_bootstrap()
    sys.exit(0 if success else 1)
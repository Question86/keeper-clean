#!/usr/bin/env python3
"""
Bootstrap Rule: AI Breadcrumb Tracking Injection

TASK_0174: AI Decision Path Tracking
Automatically injects breadcrumb tracking into the AI's file operations.

This rule ensures that every file access, creation, or modification by the AI
is tracked with unique hash-based breadcrumbs that can be extracted later
to understand the AI's logical decision paths.
"""

import sys
from pathlib import Path

# Add breadcrumb tracking to the system path
workspace_root = Path(__file__).parent.resolve()

def inject_breadcrumb_tracking():
    """Inject breadcrumb tracking into key system functions."""

    print("🗺️  Injecting AI Breadcrumb Tracking System...")

    try:
        # Import the breadcrumb tracker
        sys.path.insert(0, str(workspace_root))
        from ai_breadcrumb_tracker import get_breadcrumb_tracker, bootstrap_breadcrumb_tracking

        # Initialize the system
        bootstrap_breadcrumb_tracking()
        tracker = get_breadcrumb_tracker(workspace_root)

        # Set initial context
        tracker.set_current_context("bootstrap_rule_injection")

        print("✅ AI Breadcrumb Tracking injected successfully")
        print("   - File operations will be automatically tracked")
        print("   - Breadcrumbs logged to: breadcrumb_trail.jsonl")
        print("   - Use analyze_breadcrumb_trails.py to extract insights")

        return True

    except ImportError as e:
        print(f"⚠️  Breadcrumb tracking not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Breadcrumb injection failed: {e}")
        return False

# Auto-execute when imported
if __name__ != "__main__":
    inject_breadcrumb_tracking()
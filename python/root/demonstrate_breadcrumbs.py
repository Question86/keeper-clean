#!/usr/bin/env python3
"""
AI Breadcrumb Tracking Demonstration

Demonstrates TASK_0174: AI Decision Path Tracking
Shows how the breadcrumb system tracks AI file operations and decision paths.
"""

import tempfile
import time
from pathlib import Path

from ai_breadcrumb_tracker import (
    get_breadcrumb_tracker,
    track_file_access,
    track_file_creation,
    track_file_modification,
    bootstrap_breadcrumb_tracking
)


def demonstrate_breadcrumb_tracking():
    """Demonstrate the AI breadcrumb tracking system."""

    print("🗺️  AI Breadcrumb Tracking System Demonstration")
    print("=" * 60)

    # Create a temporary workspace for demonstration
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)

        # Initialize the breadcrumb system with the correct workspace
        from ai_breadcrumb_tracker import AIBreadcrumbTracker
        tracker = AIBreadcrumbTracker(workspace)
        tracker.set_current_context("demonstration_script")

        print("✅ Breadcrumb system initialized")
        print()

        # Create some test files
        print("📝 Creating demonstration files...")

        # File 1: Python module
        py_file = workspace / "example_module.py"
        py_content = '''"""
Example Python module for breadcrumb demonstration.

This file demonstrates how breadcrumbs are embedded in different file types.
"""

def example_function():
    """An example function."""
    return "Hello from breadcrumb demo!"

if __name__ == "__main__":
    print(example_function())
'''
        py_file.write_text(py_content)
        tracker.inject_breadcrumb_into_file(py_file, tracker.create_breadcrumb("example_module.py", 'create', {'context': 'demo_file_creation'}))

        # File 2: Markdown document
        md_file = workspace / "README.md"
        md_content = '''# Breadcrumb Tracking Demo

This document demonstrates AI breadcrumb tracking.

## Features

- Unique hash-based breadcrumbs
- Source context tracking
- Decision path analysis
- Extractable trail data

## Usage

Run the analysis script to see breadcrumb trails:

```bash
python analyze_breadcrumb_trails.py
```
'''
        md_file.write_text(md_content)
        tracker.inject_breadcrumb_into_file(md_file, tracker.create_breadcrumb("README.md", 'create', {'context': 'demo_documentation'}))

        # File 3: JSON configuration
        json_file = workspace / "config.json"
        json_data = {
            "project": "breadcrumb_demo",
            "version": "1.0.0",
            "features": ["tracking", "analysis", "logging"],
            "settings": {
                "enabled": True,
                "log_level": "INFO"
            }
        }
        import json
        json_file.write_text(json.dumps(json_data, indent=2))
        tracker.inject_breadcrumb_into_file(json_file, tracker.create_breadcrumb("config.json", 'create', {'context': 'demo_configuration'}))

        print("✅ Created 3 demonstration files")
        print()

        # Simulate file access patterns
        print("🔍 Simulating AI file access patterns...")

        # Access the Python file (like reading for analysis)
        tracker.set_current_context("code_analysis_task")
        tracker.inject_breadcrumb_into_file(py_file, tracker.create_breadcrumb("example_module.py", 'access'))

        # Access the README (like checking documentation)
        tracker.set_current_context("documentation_review")
        tracker.inject_breadcrumb_into_file(md_file, tracker.create_breadcrumb("README.md", 'access'))

        # Modify the config (like updating settings)
        tracker.set_current_context("configuration_update")
        tracker.inject_breadcrumb_into_file(json_file, tracker.create_breadcrumb("config.json", 'modify'))

        # Access files again with different contexts
        tracker.set_current_context("integration_check")
        tracker.inject_breadcrumb_into_file(py_file, tracker.create_breadcrumb("example_module.py", 'access'))

        tracker.set_current_context("final_verification")
        tracker.inject_breadcrumb_into_file(md_file, tracker.create_breadcrumb("README.md", 'access'))

        print("✅ Simulated file operations with different contexts")
        print()

        # Show current breadcrumb trail
        print("📊 Current Breadcrumb Trail:")
        breadcrumbs = tracker.get_breadcrumb_trail(limit=20)

        for i, bc in enumerate(breadcrumbs, 1):
            print(f"  {i:2d}. {bc.timestamp} | {bc.operation:>8} | {bc.target_file}")
            print(f"      ← {bc.source_context}")
        print()

        # Analyze the trails
        print("🔬 Trail Analysis:")
        analysis = tracker.analyze_decision_paths()

        print(f"  Total breadcrumbs: {analysis['total_breadcrumbs']}")
        print(f"  Unique files accessed: {analysis['unique_files']}")
        print(f"  Operation types: {analysis['operation_counts']}")
        print(f"  Source contexts: {len(analysis['source_contexts'])}")
        print()

        # Extract breadcrumbs from files
        print("📂 Extracting breadcrumbs embedded in files...")

        total_extracted = 0
        for file_path in [py_file, md_file, json_file]:
            extracted = tracker.extract_breadcrumbs_from_file(file_path)
            if extracted:
                print(f"  {file_path.name}: {len(extracted)} breadcrumbs")
                total_extracted += len(extracted)

        print(f"✅ Total breadcrumbs extracted from files: {total_extracted}")
        print()

        # Show breadcrumb log file
        log_file = workspace / "breadcrumb_trail.jsonl"
        if log_file.exists():
            print("📝 Breadcrumb log file contents:")
            with open(log_file, 'r') as f:
                lines = f.readlines()[:5]  # Show first 5 entries
                for i, line in enumerate(lines, 1):
                    try:
                        data = json.loads(line)
                        print(f"  {i}. {data['operation']} {data['target_file']} ← {data['source_context']}")
                    except json.JSONDecodeError:
                        print(f"  {i}. [Invalid JSON]")
            print("  ... (truncated)")
            print()

        print("🎯 Key Benefits Demonstrated:")
        print("  • Unique hash-based breadcrumb identification")
        print("  • Source context tracking for decision paths")
        print("  • Multiple file type support (Python, Markdown, JSON)")
        print("  • Extractable breadcrumb data from files")
        print("  • Comprehensive trail logging")
        print("  • Analysis capabilities for understanding AI behavior")
        print()

        print("📋 Usage in Real Scenarios:")
        print("  1. AI accesses files during task execution")
        print("  2. Breadcrumbs automatically track each access")
        print("  3. Source context shows why the file was accessed")
        print("  4. Later analysis reveals decision-making patterns")
        print("  5. Helps debug AI behavior and improve navigation")
        print()

    print("✨ AI Breadcrumb Tracking demonstration complete!")


if __name__ == "__main__":
    demonstrate_breadcrumb_tracking()
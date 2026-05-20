#!/usr/bin/env python3
"""
Start Services with Local Mistral Agent
Uses local Ollama Mistral model to start specified scripts if not already running
"""

from local_mistral_agent import LocalMistralAgent
import subprocess
import sys
import os
from pathlib import Path

def is_script_running(script_name):
    """Check if a script is already running."""
    try:
        result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq python.exe', '/FO', 'CSV'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        for line in lines[1:]:  # Skip header
            if script_name in line:
                return True
    except:
        pass
    return False

def start_script(script_path, description, args=None):
    """Start a script if not already running."""
    script_name = Path(script_path).name
    if is_script_running(script_name):
        print(f"✓ {description} already running")
        return True

    print(f"Starting: {description}")
    try:
        # Start in background
        cmd = ['python', script_path]
        if args:
            cmd.extend(args)
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✓ Started {description} (PID: {process.pid})")
        return True
    except Exception as e:
        print(f"✗ Failed to start {description}: {e}")
        return False

def main():
    # Initialize the local Mistral agent
    agent = LocalMistralAgent()

    # Scripts to start (with optional arguments)
    scripts = [
        ("token_monitor.py", "Token Monitor Service"),
        ("adaptive_bootstrap.py", "Adaptive Bootstrap Service"),
        ("performance_benchmark.py", "Performance Benchmark Service"),
        ("loop_guardrails.py", "Loop Guardrails Service"),
        ("bootstrap_parameter_sweep.py", "Bootstrap Parameter Sweep Service"),
        ("local_mistral_agent.py", "Local Mistral Agent Service"),
        ("metadata_database_pipeline.py", "Metadata Database Pipeline Service"),
        ("checkpoint_manager.py", "Checkpoint Manager Service"),
        ("lazy_loader.py", "Lazy Loader Service"),
        ("service_orchestrator.py", "Service Orchestrator Service"),
        ("consistency_auditor.py", "Consistency Auditor Service"),
        ("ai_integrity_protector.py", "AI Integrity Protector Service"),
        ("check_services.py", "Check Services Service"),
        ("behavioral_telemetry_analyzer.py", "Behavioral Telemetry Analyzer Service"),
        ("global_events_observer.py", "Global Events Observer Service"),
        ("prediction_scorer.py", "Prediction Scorer Service"),
        ("backup/backup_manager.py", "Backup Manager Service", ["--start-auto"]),
    ]

    # Note: venv\Lib\site-packages\pygments\token.py is a library file, not a script to run

    print("Starting Services with Local Mistral Agent")
    print("=" * 50)

    # Have the agent analyze the task
    task_prompt = f"""
You are a local AI assistant tasked with starting project services.

Your task is to start the following scripts if they are not already running:
{chr(10).join(f"- {item[0]}: {item[1]}" for item in scripts)}

Check each script to see if it's already running before starting it.
Start them in the background so they continue running.

The pygments token.py file is a library file and should not be started as a script.
"""

    try:
        response = agent.generate(task_prompt, max_tokens=1000)
        print("Agent Analysis:")
        print(response)
        ai_available = not response.startswith("Error:")
    except KeyboardInterrupt:
        print("Agent call interrupted")
        response = "Error: Timeout"
        ai_available = False
    except Exception as e:
        print(f"Agent call failed: {e}")
        response = f"Error: {e}"
        ai_available = False

    if not ai_available:
        print("AI agent not available, proceeding with direct service startup...")
    else:
        print("AI agent analysis complete, proceeding with service startup...")

    print("\n" + "=" * 50)

    # Execute the starts
    print("Starting services...")

    started_count = 0
    for item in scripts:
        if len(item) == 2:
            script, desc = item
            args = None
        else:
            script, desc, args = item
        script_path = Path(__file__).parent / script
        if script_path.exists():
            if start_script(str(script_path), desc, args):
                started_count += 1
        else:
            print(f"✗ {script} not found")

    print("\n" + "=" * 50)
    print(f"Service Startup Complete! Started {started_count} new services.")

if __name__ == "__main__":
    main()
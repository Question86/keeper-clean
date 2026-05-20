#!/usr/bin/env python3
"""
Update Index Files with Local Mistral Agent
Uses local Ollama Mistral model to browse archives and update index files
"""

from local_mistral_agent import LocalMistralAgent
import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a shell command and return output"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            print(f"✓ Success: {description}")
            return result.stdout.strip()
        else:
            print(f"✗ Failed: {description}")
            print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"✗ Exception: {description} - {e}")
        return None

def main():
    # Initialize the local Mistral agent
    agent = LocalMistralAgent()

    # Task description for the agent
    task_prompt = """
You are a local AI assistant tasked with updating project index files.

Your task is to:
1. Browse the archives in the 'archive/' directory
2. Identify any missing links to tasks and reports in the index files
3. Update 'docs/HISTORY_INDEX.json' and 'docs/QUERY_INDEX.json' with any missing links

The project uses these CLI commands to regenerate indices:
- python loop_cockpit.py --generate-history-index  (generates docs/HISTORY_INDEX.md)
- python loop_cockpit.py --generate-query-index    (generates docs/QUERY_INDEX.json)
- python regenerate_index.py                       (regenerates docs/HISTORY_INDEX.json)

You should run these commands to update the indices with current archive data.

Start by checking the current state of the index files, then run the regeneration commands.
"""

    print("Starting Local Mistral Agent for Index Update Task")
    print("=" * 50)

    # Have the agent analyze and execute the task
    response = agent.generate(task_prompt, max_tokens=2000)

    print("Agent Analysis:")
    print(response)
    print("\n" + "=" * 50)

    # Execute the regeneration commands as suggested
    print("Executing index regeneration commands...")

    # Regenerate HISTORY_INDEX.json
    result1 = run_command("python regenerate_index.py", "Regenerate HISTORY_INDEX.json")

    # Regenerate QUERY_INDEX.json
    result2 = run_command("python loop_cockpit.py --generate-query-index", "Regenerate QUERY_INDEX.json")

    # Also regenerate HISTORY_INDEX.md for completeness
    result3 = run_command("python loop_cockpit.py --generate-history-index", "Regenerate HISTORY_INDEX.md")

    print("\n" + "=" * 50)
    print("Index Update Complete!")
    print(f"HISTORY_INDEX.json: {'Updated' if result1 else 'Failed'}")
    print(f"QUERY_INDEX.json: {'Updated' if result2 else 'Failed'}")
    print(f"HISTORY_INDEX.md: {'Updated' if result3 else 'Failed'}")

if __name__ == "__main__":
    main()
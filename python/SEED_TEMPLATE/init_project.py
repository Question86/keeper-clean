"""Initialize a new project with the loop-based workflow system.

This script sets up all core files with project-specific customization.
Run this script in an empty directory to bootstrap your project.

Usage:
    python init_project.py
    
The script will prompt for project details interactively.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import shutil


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def prompt_with_default(prompt_text, default):
    response = input(f"{prompt_text} [{default}]: ").strip()
    return response if response else default


def main():
    print("=" * 60)
    print("LOOP WORKFLOW SYSTEM - PROJECT INITIALIZATION")
    print("=" * 60)
    print()
    
    # Get project details
    print("Enter project details (or press Enter to use defaults):\n")
    
    project_name = prompt_with_default("Project name", "MyProject")
    project_description = prompt_with_default("Project description", "A project using loop-based workflow")
    project_goal = prompt_with_default("Project goal", "Build reliable software with deterministic workflow")
    
    print("\nTech stack details:\n")
    languages = prompt_with_default("Languages", "Python, JavaScript")
    frameworks = prompt_with_default("Frameworks", "Flask, React")
    runtime = prompt_with_default("Runtime", "Python 3.x, Node.js")
    database = prompt_with_default("Database", "SQLite")
    infrastructure = prompt_with_default("Infrastructure", "Desktop/Web app")
    deployment = prompt_with_default("Deployment", "Manual")
    
    print("\nAPI and data details:\n")
    api_style = prompt_with_default("API style", "REST")
    auth_model = prompt_with_default("Auth model", "Token-based")
    data_formats = prompt_with_default("Data formats", "JSON")
    versioning = prompt_with_default("Versioning", "Semantic")
    
    print("\nMilestone details:\n")
    milestone_name = prompt_with_default("First milestone name", "Project Foundation")
    goal_1_description = prompt_with_default("First goal description", "Establish basic infrastructure")
    
    # Prepare substitutions
    timestamp = utc_now_iso()
    today = get_today()
    
    substitutions = {
        "{{PROJECT_NAME}}": project_name,
        "{{PROJECT_DESCRIPTION}}": project_description,
        "{{PROJECT_GOAL}}": project_goal,
        "{{LANGUAGES}}": languages,
        "{{FRAMEWORKS}}": frameworks,
        "{{RUNTIME}}": runtime,
        "{{DATABASE}}": database,
        "{{INFRASTRUCTURE}}": infrastructure,
        "{{DEPLOYMENT}}": deployment,
        "{{API_STYLE}}": api_style,
        "{{AUTH_MODEL}}": auth_model,
        "{{DATA_FORMATS}}": data_formats,
        "{{VERSIONING}}": versioning,
        "{{INIT_TIMESTAMP}}": timestamp,
        "{{INIT_DATE}}": today,
        "{{MILESTONE_NAME}}": milestone_name,
        "{{GOAL_1_DESCRIPTION}}": goal_1_description,
    }
    
    # Confirm with user
    print("\n" + "=" * 60)
    print("Configuration summary:")
    print("=" * 60)
    for key, value in substitutions.items():
        print(f"{key:30} -> {value}")
    print("=" * 60)
    
    confirm = input("\nProceed with initialization? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("Initialization cancelled.")
        return
    
    # Create directory structure
    print("\nCreating directory structure...")
    target_dir = Path.cwd()
    
    dirs = ["archive", "tasks", "reports", "docs", "templates"]
    for d in dirs:
        (target_dir / d).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created {d}/")
    
    # Copy and process files
    print("\nCopying and customizing files...")
    template_dir = Path(__file__).parent
    
    # Files to copy with substitution
    text_files = [
        "PROJECT_TECH_BASELINE.md",
        "NEURAL_CORTEX.md",
        "NEU.md",
        "Alt.md",
        "current.json",
        "knownissues.json",
        "milestone_01.json",
        "tasks/task_TASK_0001.md",
        "docs/OPS_PROTOCOLS.md",
        "docs/ARCHITECTURE.md",
    ]
    
    for file_path in text_files:
        src = template_dir / file_path
        dst = target_dir / file_path
        
        if src.exists():
            content = src.read_text(encoding="utf-8")
            for key, value in substitutions.items():
                content = content.replace(key, value)
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, encoding="utf-8")
            print(f"  ✓ Created {file_path}")
        else:
            print(f"  ⚠ Warning: Template file not found: {file_path}")
    
    # Files to copy without substitution
    binary_files = [
        "loop_guardrails.py",
        "loop_cockpit.py",
        "requirements_cockpit.txt",
        "START_COCKPIT.bat",
        "START_COCKPIT.sh",
        "templates/cockpit.html",
    ]
    
    for file_path in binary_files:
        src = template_dir / file_path
        dst = target_dir / file_path
        
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  ✓ Copied {file_path}")
        else:
            print(f"  ⚠ Warning: File not found: {file_path}")
    
    # Generate initial _LOOP_GATE.md
    print("\nGenerating initial loop gate...")
    gate_content = f"""# LOOP GATE - PRE-ENTRY VALIDATION

MODE: SYSTEM VALIDATOR
UPDATE: Cockpit automation only

**STATUS: PASS**
**CHECKED_AT: {timestamp}**
**CHECKED_BY: init_project**
**REASON: initial-setup**

---

## CHECKS

✓ **CURRENT_JSON**
  - loop=1 status=READY_FOR_RESET

✓ **LINT**
  - Initial setup

---

## VERDICT

**GATE STATUS: PASS**

---

END OF DOCUMENT
"""
    (target_dir / "_LOOP_GATE.md").write_text(gate_content, encoding="utf-8")
    print("  ✓ Created _LOOP_GATE.md")
    
    print("\n" + "=" * 60)
    print("✅ Project initialization complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Install Python dependencies: pip install -r requirements_cockpit.txt")
    print("2. Start the cockpit: python loop_cockpit.py (or use START_COCKPIT.bat/.sh)")
    print("3. Click 'Reset Loop' in the cockpit UI to create _BOOTSTRAP.md")
    print("4. Start a fresh AI chat session and say: 'Read _BOOTSTRAP.md'")
    print("\nFor more information, see docs/ARCHITECTURE.md and docs/OPS_PROTOCOLS.md")
    print()


if __name__ == "__main__":
    main()

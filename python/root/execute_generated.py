#!/usr/bin/env python3
"""
Execute Generated Tool Calls from Keeper Agent Output

This script takes the output from the Keeper Agent (generated code with tool calls)
and executes them using the Keeper Agent's tool system.

Usage:
    python execute_generated.py "generated_code_here"
"""

import sys
import ast
import re
import json
import os
from datetime import datetime
from pathlib import Path
from keeper_agent import KeeperAgent

LOGS_DIR = Path("logs")
STORAGE_DIR = Path("storage")
OUTPUT_DIR = Path("output")
BUGS_DIR = Path("bugs")

def parse_tool_call(code_str):
    """Parse a simple tool call from generated code string."""
    # Remove print wrapper if present
    code_str = code_str.strip()
    if code_str.startswith('print("""') and code_str.endswith('""")'):
        code_str = code_str[8:-4]  # Remove print(""" and """)
    elif code_str.startswith('print(') and code_str.endswith(')'):
        code_str = code_str[6:-1]  # Remove print( and )

    # Clean up extra quotes
    code_str = code_str.strip('"').strip("'")

    # Parse the function call
    match = re.match(r'(\w+)\s*\(\s*(.*)\s*\)', code_str)
    if not match:
        raise ValueError(f"Could not parse tool call: {code_str}")

    func_name = match.group(1)
    args_str = match.group(2)

    # Parse arguments (simple key=value pairs)
    args = {}
    for arg in args_str.split(','):
        arg = arg.strip()
        if '=' in arg:
            key, value = arg.split('=', 1)
            key = key.strip()
            value = value.strip()
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            args[key] = value

    return func_name, args

def log_execution(generated_code, func_name, args, result, file_id, related_files=None):
    """Log the execution to the logs directory in report format."""
    LOGS_DIR.mkdir(exist_ok=True)
    
    log_file = LOGS_DIR / f"execution_report_task_unknown_loop_unknown_file_{file_id}.md"
    
    status = "✅ SUCCESS" if result.get('success') else "❌ FAILED"
    completed_date = datetime.now().strftime('%Y-%m-%d')
    
    # Format as markdown report
    report_content = f"""# REPORT: EXECUTION_task_unknown_loop_unknown_file_{file_id}

**TASK:** Tool Execution - {func_name}
**LOOP:** unknown
**STATUS:** {status}
**COMPLETED:** {completed_date}

---

## EXECUTION DETAILS

**Tool:** {func_name}
**Arguments:** {json.dumps(args, indent=2)}
**Generated Code:** {generated_code}

## RESULT

{json.dumps(result, indent=2, ensure_ascii=False)}

## FILES CREATED/MODIFIED

"""
    
    # Add file info if applicable
    if func_name == 'write_file' and result.get('success'):
        report_content += f"- **File:** {result.get('path')}\n"
        report_content += f"- **Bytes Written:** {result.get('bytes_written')}\n"

    # Add pointers to related files
    report_content += f"""

## RELATED FILES

- **Code File:** {related_files.get('code', f'storage/code_output_task_unknown_loop_unknown_file_{file_id}.txt')}
"""
    if result.get('success'):
        report_content += f"- **Success Report:** {related_files.get('success_report', f'output/success_report_task_unknown_loop_unknown_file_{file_id}.json')}\n"
    else:
        report_content += f"- **Bug Report:** {related_files.get('bug_report', f'bugs/bug_report_task_unknown_loop_unknown_file_{file_id}.json')}\n"
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"📝 Execution report logged to: {log_file}")

def sanitize_filename(name):
    """Sanitize filename by replacing invalid characters."""
    return name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')

def get_file_identifier(args):
    """Get file identifier from args."""
    if 'path' in args:
        return sanitize_filename(args['path'])
    return 'unknown'

def main():
    if len(sys.argv) < 2:
        print("Usage: python execute_generated.py 'generated_code'")
        sys.exit(1)

    generated_code = sys.argv[1]

    # Ensure directories exist
    STORAGE_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    BUGS_DIR.mkdir(exist_ok=True)

    try:
        # Initialize Keeper Agent
        agent = KeeperAgent(provider='gemini')
        print("🤖 Keeper Agent initialized for tool execution")

        # Parse the tool call
        func_name, args = parse_tool_call(generated_code)
        print(f"🔧 Executing tool: {func_name} with args: {args}")

        # Get file identifier
        file_id = get_file_identifier(args)

        # Execute the tool
        result = agent._execute_tool(func_name, args)
        print("✅ Tool execution result:")
        print(result)

        # Store generated code with pointers
        storage_file = STORAGE_DIR / f"code_output_task_unknown_loop_unknown_file_{file_id}.txt"
        code_content = f"""# Code Output for: {file_id}
# Generated: {datetime.now().isoformat()}
# Success Report: output/success_report_task_unknown_loop_unknown_file_{file_id}.json
# Execution Report: logs/execution_report_task_unknown_loop_unknown_file_{file_id}.md

{generated_code}
"""
        with open(storage_file, 'w', encoding='utf-8') as f:
            f.write(code_content)
        print(f"💾 Generated code stored in: {storage_file}")

        # Store result in appropriate directory with pointers
        if result.get('success'):
            result_file = OUTPUT_DIR / f"success_report_task_unknown_loop_unknown_file_{file_id}.json"
            success_data = {
                "file_id": file_id,
                "timestamp": datetime.now().isoformat(),
                "result": result,
                "related_files": {
                    "code": str(storage_file),
                    "execution_report": str(LOGS_DIR / f"execution_report_task_unknown_loop_unknown_file_{file_id}.md")
                }
            }
            print(f"📁 Success result stored in: {result_file}")
        else:
            result_file = BUGS_DIR / f"bug_report_task_unknown_loop_unknown_file_{file_id}.json"
            bug_data = {
                "file_id": file_id,
                "timestamp": datetime.now().isoformat(),
                "result": result,
                "related_files": {
                    "code": str(storage_file),
                    "execution_report": str(LOGS_DIR / f"execution_report_task_unknown_loop_unknown_file_{file_id}.md")
                }
            }
            print(f"🐛 Bug result stored in: {result_file}")

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(success_data if result.get('success') else bug_data, f, indent=2, ensure_ascii=False)

        # Log the execution
        if result.get('success'):
            log_execution(generated_code, func_name, args, result, file_id, success_data["related_files"])
        else:
            log_execution(generated_code, func_name, args, result, file_id, bug_data["related_files"])

    except Exception as e:
        print(f"❌ Error: {e}")
        # Get file identifier from args if possible
        try:
            func_name, args = parse_tool_call(generated_code)
            file_id = get_file_identifier(args)
        except:
            file_id = 'unknown'
        
        # Log errors
        error_result = {"success": False, "error": str(e)}
        bug_file = BUGS_DIR / f"bug_report_task_unknown_loop_unknown_file_{file_id}.json"
        bug_data = {
            "file_id": file_id,
            "timestamp": datetime.now().isoformat(),
            "result": error_result,
            "related_files": {
                "code": str(STORAGE_DIR / f"code_output_task_unknown_loop_unknown_file_{file_id}.txt"),
                "execution_report": str(LOGS_DIR / f"execution_report_task_unknown_loop_unknown_file_{file_id}.md")
            }
        }
        with open(bug_file, 'w', encoding='utf-8') as f:
            json.dump(bug_data, f, indent=2, ensure_ascii=False)
        print(f"🐛 Error logged in: {bug_file}")
        
        try:
            log_execution(generated_code, "unknown", {}, error_result, file_id, bug_data["related_files"])
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
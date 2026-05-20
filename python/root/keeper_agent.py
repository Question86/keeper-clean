#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keeper Agent with Gemini API + OpenAI API + Tool Support
Supports both Google Gemini and OpenAI GPT models with unified interface
"""

import os
import json
import subprocess
from pathlib import Path

# Import both API clients
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = False  # Disabled to prevent rate limiting
except ImportError:
    OPENAI_AVAILABLE = False

WORKSPACE = Path(__file__).parent

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Tool definitions (compatible with both APIs)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents with optional line limit to control token usage",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file (relative or absolute)"},
                    "limit": {"type": "integer", "description": "Max lines to read (default: 50)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "exec_command",
            "description": "Execute shell command in workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Search for text patterns within files using regex",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text or regex pattern to search for"},
                    "include_pattern": {"type": "string", "description": "File pattern to search in (e.g., '*.py', '*.md')"},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return (default: 20)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List contents of a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list (default: current workspace)"}
                }
            }
        }
    }
]

class KeeperAgent:
    """Agent with controlled context + file/exec tools supporting Gemini and OpenAI"""

    def __init__(self, max_history_pairs=3, provider="gemini", reasoning_effort=None):
        self.provider = provider.lower()
        self.max_history_pairs = max_history_pairs
        self.conversation = []
        self.system_prompt = self._build_system_prompt()
        self.reasoning_effort = reasoning_effort

        # Initialize appropriate client
        if self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ImportError("Google GenAI package not available. Install with: pip install google-genai")
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY env var required for provider=gemini")
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.model = "gemini-2.0-flash"
        elif self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI package not available. Install with: pip install openai")
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY env var required for provider=openai")
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            # Use reasoning model if reasoning effort is specified
            if reasoning_effort:
                if reasoning_effort == "low":
                    self.model = "gpt-5-nano"
                elif reasoning_effort == "medium":
                    self.model = "gpt-5-mini"
                elif reasoning_effort == "high":
                    self.model = "gpt-5.2"
            else:
                self.model = "gpt-4o"
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'gemini' or 'openai'")

        print(f"🤖 KeeperAgent initialized with {self.provider.upper()} ({self.model})")
        
    def _build_system_prompt(self):
        """Load minimal system prompt from session pack"""
        session_file = WORKSPACE / "_SESSION.md"
        if session_file.exists():
            content = session_file.read_text(encoding='utf-8')
            return f"""{content}

TOOLS AVAILABLE:
- read_file(path, limit=50): Read file with line limit
- write_file(path, content): Write/overwrite file
- exec_command(command): Run shell command
- grep_search(query, include_pattern='*', max_results=20): Search text in files
- list_dir(path='.'): List directory contents

CRITICAL: Always use limit= on read_file to control tokens.
"""
        return "You are an AI assistant with file and command execution tools."
    
    def _trim_history(self):
        """Keep only recent conversation pairs"""
        # Keep last N user+assistant pairs (2 messages per pair)
        max_messages = self.max_history_pairs * 2
        if len(self.conversation) > max_messages:
            self.conversation = self.conversation[-max_messages:]
    
    def _execute_tool(self, tool_name, tool_input):
        """Execute tool and return result"""
        try:
            if tool_name == "read_file":
                path = Path(tool_input['path'])
                if not path.is_absolute():
                    path = WORKSPACE / path
                
                limit = tool_input.get('limit', 50)
                
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if limit and len(lines) > limit:
                        content = ''.join(lines[:limit])
                        content += f"\n\n[{len(lines) - limit} more lines not shown. Use higher limit if needed]"
                    else:
                        content = ''.join(lines)
                
                return {"success": True, "content": content, "lines_shown": min(len(lines), limit), "total_lines": len(lines)}
            
            elif tool_name == "write_file":
                path = Path(tool_input['path'])
                if not path.is_absolute():
                    path = WORKSPACE / path
                
                path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(tool_input['content'])
                
                return {"success": True, "bytes_written": len(tool_input['content']), "path": str(path)}
            
            elif tool_name == "exec_command":
                result = subprocess.run(
                    tool_input['command'],
                    shell=True,
                    cwd=WORKSPACE,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            
            elif tool_name == "grep_search":
                import glob
                import re
                
                query = tool_input['query']
                include_pattern = tool_input.get('include_pattern', '*')
                max_results = tool_input.get('max_results', 20)
                
                # Find files matching pattern
                pattern = WORKSPACE / include_pattern if not Path(include_pattern).is_absolute() else include_pattern
                files = glob.glob(str(pattern), recursive=True)
                
                results = []
                for file_path in files[:50]:  # Limit files to search
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines = content.split('\n')
                            
                            for i, line in enumerate(lines):
                                if re.search(query, line, re.IGNORECASE):
                                    results.append({
                                        "file": str(Path(file_path).relative_to(WORKSPACE)),
                                        "line": i + 1,
                                        "content": line.strip()
                                    })
                                    if len(results) >= max_results:
                                        break
                    except:
                        continue
                    
                    if len(results) >= max_results:
                        break
                
                return {
                    "success": True,
                    "results": results,
                    "total_found": len(results),
                    "searched_files": len(files)
                }
            
            elif tool_name == "list_dir":
                path = tool_input.get('path', '.')
                dir_path = Path(path)
                if not dir_path.is_absolute():
                    dir_path = WORKSPACE / dir_path
                
                if not dir_path.exists():
                    return {"success": False, "error": f"Directory {path} does not exist"}
                
                try:
                    items = []
                    for item in dir_path.iterdir():
                        items.append({
                            "name": item.name,
                            "type": "directory" if item.is_dir() else "file",
                            "path": str(item.relative_to(WORKSPACE)) if item.is_relative_to(WORKSPACE) else str(item)
                        })
                    
                    return {
                        "success": True,
                        "path": str(dir_path.relative_to(WORKSPACE)) if dir_path.is_relative_to(WORKSPACE) else str(dir_path),
                        "items": items,
                        "count": len(items)
                    }
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send(self, user_message):
        """Send message using configured AI provider"""

        if self.provider == "gemini":
            return self._send_gemini(user_message)
        elif self.provider == "openai":
            return self._send_openai(user_message)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _send_gemini(self, user_message):
        """Send message with Gemini API"""

        self.conversation.append({
            "role": "user",
            "parts": [user_message]
        })

        self._trim_history()

        # Build contents with system prompt + conversation
        contents = []

        # Add system prompt as first user message
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=self.system_prompt)]
        ))

        # Add conversation history
        for msg in self.conversation:
            contents.append(types.Content(
                role=msg["role"],
                parts=[types.Part(text=part) for part in msg["parts"]]
            ))

        tool_call_count = 0
        MAX_TOOL_CALLS = 10

        while tool_call_count < MAX_TOOL_CALLS:
            # Convert tools format for Gemini
            gemini_tools = [{
                "function_declarations": [tool["function"] for tool in TOOLS]
            }]

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config={"tools": gemini_tools}
            )

            # Check for function calls
            has_function_calls = False
            function_results = []

            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    has_function_calls = True
                    tool_call_count += 1

                    func_name = part.function_call.name
                    func_args = part.function_call.args

                    print(f"\n[Tool: {func_name}({json.dumps(func_args, indent=2)})]")
                    result = self._execute_tool(func_name, func_args)

                    function_results.append({
                        "name": func_name,
                        "content": json.dumps(result, ensure_ascii=False)
                    })

            if not has_function_calls:
                # No more tool calls, get final response
                text_response = ""
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_response += part.text

                # Add assistant response to conversation
                self.conversation.append({
                    "role": "model",
                    "parts": [text_response]
                })

                return {
                    "message": text_response,
                    "usage": {
                        "tokens": getattr(response, 'usage_metadata', {}).candidates_token_count or 0
                    }
                }

            # Add function results to conversation
            for result in function_results:
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=f"Tool result ({result['name']}): {result['content']}")]
                ))

        return {
            "message": "Maximum tool calls exceeded",
            "usage": {"tokens": 0}
        }

    def _send_openai(self, user_message):
        """Send message with OpenAI API"""

        # Build messages for OpenAI
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history (convert from Gemini format)
        for msg in self.conversation[-self.max_history_pairs*2:]:  # Keep recent history
            role = msg["role"]
            if role == "model":  # Convert Gemini's "model" to OpenAI's "assistant"
                role = "assistant"
            content = msg["parts"][0] if isinstance(msg["parts"], list) else str(msg["parts"])
            messages.append({"role": role, "content": content})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        tool_call_count = 0
        MAX_TOOL_CALLS = 10

        while tool_call_count < MAX_TOOL_CALLS:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=4000
            )

            message = response.choices[0].message

            # Check for tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_call_count += len(message.tool_calls)

                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": message.tool_calls
                })

                # Execute tools and add results
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    print(f"\n[Tool: {func_name}({json.dumps(func_args, indent=2)})]")
                    result = self._execute_tool(func_name, func_args)

                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False),
                        "tool_call_id": tool_call.id
                    })
            else:
                # No tool calls, final response
                # Add to conversation history
                self.conversation.append({
                    "role": "user",
                    "parts": [user_message]
                })
                self.conversation.append({
                    "role": "model",
                    "parts": [message.content or ""]
                })

                return {
                    "message": message.content or "",
                    "usage": {
                        "tokens": response.usage.total_tokens if response.usage else 0
                    }
                }

        return {
            "message": "Maximum tool calls exceeded",
            "usage": {"tokens": 0}
        }


def interactive_mode():
    """Interactive CLI"""
    agent = KeeperAgent(max_history_pairs=3)
    
    print("Keeper Agent with Gemini API - Type 'exit' to quit")
    print(f"Context limit: {agent.max_history_pairs} conversation pairs\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
            
            if not user_input:
                continue
            
            # Send message
            response = agent.send(user_input)
            
            # Print response
            print(f"\nAssistant: {response['message']}")
            print(f"\n[Tokens: {response['usage']['tokens']} total]")
            
        except EOFError:
            # Handle piped input
            print("\nReceived EOF, exiting...")
            break
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    interactive_mode()


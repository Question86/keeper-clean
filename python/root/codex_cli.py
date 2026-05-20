#!/usr/bin/env python3
"""
Keeper OpenAI Codex CLI - Modern AI-Powered Coding Assistant

A command-line interface for AI-powered coding assistance using OpenAI's GPT-4.
Provides intelligent code generation, completion, and analysis capabilities.

Usage:
    python codex_cli.py --help
    python codex_cli.py "Write a Python function to calculate fibonacci numbers"
    python codex_cli.py --file example.py --task "Add error handling"
    python codex_cli.py --interactive

Requirements:
    - OpenAI API key (set OPENAI_API_KEY environment variable)
    - Python 3.8+
    - openai package

Author: Keeper AI Assistant
Date: 2026-01-27
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import time
from datetime import datetime

try:
    import openai
    from openai import OpenAI
except ImportError:
    print("❌ Error: openai package not installed")
    print("Install with: pip install openai")
    sys.exit(1)

try:
    import google.genai as genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from PIL import Image
    import base64
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class CodexCLI:
    """OpenAI Codex CLI - Modern AI Coding Assistant"""

    def __init__(self, api_key: Optional[str] = None, provider: str = 'openai', use_keeper_agent: bool = False, reasoning_effort: Optional[str] = None):
        self.provider = provider
        self.use_keeper_agent = use_keeper_agent
        self.reasoning_effort = reasoning_effort

        if use_keeper_agent:
            # Use Keeper Agent backend
            try:
                from keeper_agent import KeeperAgent
                self.agent = KeeperAgent(provider=provider, reasoning_effort=self.reasoning_effort)
                print(f"🤖 Using Keeper Agent with {provider.upper()}")
            except ImportError as e:
                raise ImportError(f"Keeper Agent not available: {e}")
        else:
            # Use direct API calls
            if provider == 'openai':
                self.api_key = api_key or os.getenv('OPENAI_API_KEY')
                if not self.api_key:
                    raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or use --api-key")
                self.client = OpenAI(api_key=self.api_key)
                self.model = "gpt-4o"
            elif provider == 'gemini':
                if not GOOGLE_GENAI_AVAILABLE:
                    raise ImportError("google-genai package not installed. Install with: pip install google-genai")
                self.api_key = api_key or os.getenv("GEMINI_API_KEY")
                if not self.api_key:
                    raise ValueError("Gemini API key required. Set GEMINI_API_KEY env var or use --api-key")
                self.client = genai.Client(api_key=self.api_key)
                self.model = "gemini-2.0-flash"
            else:
                raise ValueError(f"Direct API calls support OpenAI and Gemini. For other providers, use --keeper-agent")

        self.max_tokens = 2000
        self.temperature = 0.1
        self.stream = False
        self.reasoning_effort = None
        self.reasoning_summary = False
        self.temperature = 0.1

    def analyze_image(self, image_path: str, prompt: str = "What's in this image?") -> Dict[str, Any]:
        """Analyze an image using GPT-4 Vision"""

        if not PIL_AVAILABLE:
            return {"success": False, "error": "PIL (Pillow) not installed. Install with: pip install Pillow"}

        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image file not found: {image_path}"}

        try:
            # Open and encode image
            image = Image.open(image_path)

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize if too large (API limit is 20MB)
            max_size = (2048, 2048)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Convert to base64
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Call GPT-4 Vision
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens
            )

            return {
                "success": True,
                "analysis": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model": "gpt-4-vision-preview"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def web_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Perform web search using SerpAPI or similar (requires API key)"""

        serpapi_key = os.getenv('SERPAPI_KEY')
        if not serpapi_key:
            return {
                "success": False,
                "error": "Web search requires SERPAPI_KEY environment variable. Get one at https://serpapi.com/"
            }

        if not REQUESTS_AVAILABLE:
            return {"success": False, "error": "requests package not installed"}

        try:
            # Use SerpAPI for web search
            params = {
                'api_key': serpapi_key,
                'q': query,
                'num': num_results,
                'engine': 'google'
            }

            response = requests.get('https://serpapi.com/search', params=params)
            data = response.json()

            if 'error' in data:
                return {"success": False, "error": data['error']}

            # Format results
            results = []
            for result in data.get('organic_results', [])[:num_results]:
                results.append({
                    'title': result.get('title', ''),
                    'link': result.get('link', ''),
                    'snippet': result.get('snippet', '')
                })

            return {
                "success": True,
                "query": query,
                "results": results,
                "total_results": len(results)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def code_review(self, file_path: str, review_type: str = "general") -> Dict[str, Any]:
        """Perform comprehensive code review on a file or directory"""

        if not os.path.exists(file_path):
            return {"success": False, "error": f"Path not found: {file_path}"}

        path = Path(file_path)

        if path.is_file():
            # Single file review
            return self._review_single_file(file_path, review_type)
        elif path.is_dir():
            # Directory review
            return self._review_directory(file_path, review_type)
        else:
            return {"success": False, "error": f"Invalid path: {file_path}"}

    def _review_single_file(self, file_path: str, review_type: str) -> Dict[str, Any]:
        """Review a single file"""

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Determine language from extension
            ext = Path(file_path).suffix.lower()
            lang_map = {
                '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
                '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.cs': 'C#',
                '.php': 'PHP', '.rb': 'Ruby', '.go': 'Go', '.rs': 'Rust'
            }
            language = lang_map.get(ext, 'Unknown')

            # Create review prompt based on type
            review_prompts = {
                "general": f"Perform a comprehensive code review of this {language} file. Analyze code quality, potential bugs, security issues, performance optimizations, and best practices.",
                "security": f"Review this {language} code for security vulnerabilities, injection attacks, authentication issues, and other security concerns.",
                "performance": f"Analyze this {language} code for performance bottlenecks, memory leaks, inefficient algorithms, and optimization opportunities.",
                "maintainability": f"Review this {language} code for maintainability, code structure, naming conventions, documentation, and readability.",
                "bugs": f"Look for potential bugs, logic errors, edge cases, and error handling issues in this {language} code."
            }

            prompt = review_prompts.get(review_type, review_prompts["general"])

            full_prompt = f"""{prompt}

File: {file_path}
Language: {language}

Code:
``` {language.lower()}
{content}
```

Please provide:
1. Overall assessment (1-10 scale)
2. Key issues found (with severity: Critical/High/Medium/Low)
3. Specific recommendations for improvement
4. Code quality metrics
5. Best practices compliance"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert code reviewer with years of experience. Provide thorough, actionable feedback."},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=3000,
                temperature=0.2
            )

            return {
                "success": True,
                "file": file_path,
                "language": language,
                "review_type": review_type,
                "review": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _review_directory(self, dir_path: str, review_type: str) -> Dict[str, Any]:
        """Review all code files in a directory"""

        try:
            path = Path(dir_path)
            code_files = []

            # Find all code files
            extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go', '.rs']
            for ext in extensions:
                code_files.extend(path.rglob(f'*{ext}'))

            if not code_files:
                return {"success": False, "error": "No code files found in directory"}

            # Limit to first 10 files for performance
            code_files = code_files[:10]

            reviews = []
            total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            for file_path in code_files:
                review = self._review_single_file(str(file_path), review_type)
                if review["success"]:
                    reviews.append(review)
                    for key in total_usage:
                        total_usage[key] += review["usage"].get(key, 0)

            return {
                "success": True,
                "directory": dir_path,
                "review_type": review_type,
                "files_reviewed": len(reviews),
                "reviews": reviews,
                "summary": f"Reviewed {len(reviews)} files in {dir_path}",
                "total_usage": total_usage
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_programmatic(self, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run multiple commands programmatically"""
        results = []
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for cmd in commands:
            cmd_type = cmd.get('type')
            try:
                if cmd_type == 'generate':
                    result = self.generate_code(cmd.get('prompt', ''), cmd.get('language'))
                elif cmd_type == 'analyze_file':
                    result = self.analyze_file(cmd.get('file', ''), cmd.get('task', ''))
                elif cmd_type == 'analyze_image':
                    result = self.analyze_image(cmd.get('image', ''), cmd.get('prompt', ''))
                elif cmd_type == 'web_search':
                    result = self.web_search(cmd.get('query', ''), cmd.get('results', 5))
                elif cmd_type == 'code_review':
                    result = self.code_review(cmd.get('path', ''), cmd.get('review_type', 'general'))
                else:
                    result = {"success": False, "error": f"Unknown command type: {cmd_type}"}

                if result.get('success'):
                    results.append({"command": cmd, "result": result})
                    if result.get('usage'):
                        for key in total_usage:
                            total_usage[key] += result['usage'].get(key, 0)
                    elif result.get('total_usage'):
                        for key in total_usage:
                            total_usage[key] += result['total_usage'].get(key, 0)
                else:
                    results.append({"command": cmd, "error": result.get('error')})

            except Exception as e:
                results.append({"command": cmd, "error": str(e)})

        return {
            "success": True,
            "commands_executed": len(results),
            "results": results,
            "total_usage": total_usage
        }

    def generate_code(self, prompt: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Generate code based on a natural language prompt"""

        if not self.use_keeper_agent and self.provider == 'gemini':
            # Direct Gemini API call for single response
            system_prompt = f"""You are an expert programmer and coding assistant. Generate high-quality, well-documented code.

{"If the user asks for code in a specific language, use " + language + "." if language else "Use the most appropriate programming language for the task."}

Guidelines:
- Write clean, readable, and well-documented code
- Include proper error handling where appropriate
- Add comments explaining complex logic
- Follow language-specific best practices and conventions
- Make code production-ready when possible

Return only the code without additional explanation."""

            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[types.Content(role="user", parts=[types.Part(text=f"{system_prompt}\n\n{prompt}")])],
                    config={"tools": []}
                )
                text_response = ""
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_response += part.text
                code = text_response.strip()
                return {
                    "success": True,
                    "code": code,
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},  # Gemini doesn't provide token counts
                    "model": "gemini-2.0-flash",
                    "provider": "Gemini Direct"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "code": None
                }

        if self.use_keeper_agent:
            # Use Keeper Agent (includes tool support)
            full_prompt = f"""Please provide the code for: {prompt}. Just return the code, no explanations or file operations.

Format your response with a reference header like this:

# CODE_SUGGESTION: TASK_XXXX - Code suggestion for [brief description]

**TASK:** [task description if known]
**LOOP:** [current loop if known]
**TYPE:** Code Generation
**GENERATED:** {datetime.now().strftime('%Y-%m-%d')}

---

## CODE OUTPUT

[Your generated code here]"""
            if language:
                full_prompt = f"Please provide the {language} code for: {prompt}. Just return the code, no explanations or file operations."

            result = self.agent.send(full_prompt)
            return {
                "success": True,
                "code": result.get("message", ""),
                "usage": {
                    "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": result.get("usage", {}).get("total_tokens", 0)
                },
                "model": f"keeper-{self.provider}",
                "provider": "Keeper Agent"
            }
        else:
            # Use direct OpenAI API
            system_prompt = f"""You are an expert programmer and coding assistant. Generate high-quality, well-documented code.

{f"If the user asks for code in a specific language, use {language}." if language else "Use the most appropriate programming language for the task."}

Guidelines:
- Write clean, readable, and well-documented code
- Include proper error handling where appropriate
- Add comments explaining complex logic
- Follow language-specific best practices and conventions
- Make code production-ready when possible

Return only the code without additional explanation unless asked."""

            try:
                if self.stream:
                    # Streaming mode
                    print("🚀 Generating code (streaming)...")
                    stream = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        stream=True
                    )

                    full_response = ""
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            print(content, end="", flush=True)
                            full_response += content

                    print("\n")  # New line after streaming

                    result = {
                        "success": True,
                        "code": full_response.strip(),
                        "usage": {"tokens": 0},  # Streaming doesn't provide usage info
                        "model": self.model,
                        "provider": "OpenAI Direct (Streaming)"
                    }
                else:
                    # Regular mode
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=self.max_tokens,
                        temperature=self.temperature
                    )

                    result = {
                        "success": True,
                        "code": response.choices[0].message.content.strip(),
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        },
                        "model": self.model,
                        "provider": "OpenAI Direct"
                    }

                return result

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "code": None
                }

    def analyze_file(self, file_path: str, task: str) -> Dict[str, Any]:
        """Analyze an existing file and perform a task on it"""

        if not Path(file_path).exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            prompt = f"""Analyze this code file and {task}:

File: {file_path}
Content:
{file_content}

Please provide the updated code with the requested changes."""

            return self.generate_code(prompt)

        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading file: {str(e)}"
            }

    def interactive_mode(self):
        """Run in interactive mode for conversational coding assistance"""

        print("🤖 Keeper Codex CLI - Interactive Mode")
        print("Type 'exit' or 'quit' to end session")
        print("Type 'help' for available commands")
        print("-" * 50)

        conversation_history = []

        while True:
            try:
                user_input = input("\n💻 You: ").strip()

                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye!")
                    break

                if user_input.lower() == 'help':
                    self.show_help()
                    continue

                if user_input.lower() == 'clear':
                    conversation_history = []
                    print("🧹 Conversation history cleared")
                    continue

                if not user_input:
                    continue

                # Add user message to history
                conversation_history.append({"role": "user", "content": user_input})

                # Generate response
                print("🤖 Thinking...")

                system_prompt = """You are an expert coding assistant. Help with programming tasks, code generation, debugging, and technical questions.
Be concise but thorough. Provide working code examples when relevant."""

                messages = [{"role": "system", "content": system_prompt}] + conversation_history[-10:]  # Keep last 10 messages

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )

                ai_response = response.choices[0].message.content.strip()

                # Add AI response to history
                conversation_history.append({"role": "assistant", "content": ai_response})

                # Display response
                print(f"\n🤖 Assistant: {ai_response}")

                # Show token usage
                usage = response.usage
                print(f"\n📊 Tokens: {usage.total_tokens} (Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens})")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    def show_help(self):
        """Show available commands in interactive mode"""

        help_text = """
Available Commands:
  help          - Show this help message
  clear         - Clear conversation history
  exit/quit/q   - Exit interactive mode

Examples:
  "Write a Python function to reverse a string"
  "Debug this JavaScript code: [paste code]"
  "Explain how recursion works"
  "Create a REST API in Flask"

Tips:
  - Be specific about the programming language
  - Include error messages when debugging
  - Ask for code reviews or optimizations
  - Request explanations of complex concepts
"""
        print(help_text)


def main():
    parser = argparse.ArgumentParser(
        description="Keeper OpenAI Codex CLI - AI-Powered Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Write a Python function to calculate fibonacci numbers"
  %(prog)s --file script.py --task "Add type hints and error handling"
  %(prog)s --language javascript --interactive
  %(prog)s --model gpt-4-turbo "Optimize this SQL query"
  %(prog)s --image photo.jpg "Describe this image"
  %(prog)s --web-search "Python async best practices"
  %(prog)s --code-review src/ --review-type security
  %(prog)s --programmatic commands.json
  %(prog)s --stream "Generate a complex algorithm"
  %(prog)s --reasoning-effort high --model gpt-5.2 "Solve this math problem"
        """
    )

    parser.add_argument('prompt', nargs='?', help='Natural language prompt for code generation')
    parser.add_argument('--file', '-f', help='Analyze and modify an existing file')
    parser.add_argument('--task', '-t', help='Task to perform on the file (used with --file)')
    parser.add_argument('--language', '-l', help='Programming language for code generation')
    parser.add_argument('--model', '-m', default='gpt-4o', help='OpenAI model to use (default: gpt-4o)')
    parser.add_argument('--image', help='Analyze an image file (GPT-4 Vision)')
    parser.add_argument('--image-prompt', help='Prompt for image analysis (default: "What\'s in this image?")')
    parser.add_argument('--web-search', '-w', help='Perform web search for the query')
    parser.add_argument('--search-results', type=int, default=5, help='Number of web search results (default: 5)')
    parser.add_argument('--code-review', '-r', help='Perform code review on file or directory')
    parser.add_argument('--review-type', choices=['general', 'security', 'performance', 'maintainability', 'bugs'],
                       default='general', help='Type of code review to perform')
    parser.add_argument('--programmatic', help='Run commands from a JSON file programmatically')
    parser.add_argument('--stream', action='store_true', help='Stream the response in real-time')
    parser.add_argument('--reasoning-effort', choices=['low', 'medium', 'high'], help='Reasoning effort for reasoning models (low=fast, high=accurate)')
    parser.add_argument('--reasoning-summary', action='store_true', help='Include reasoning summary in response')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('--max-tokens', type=int, default=2000, help='Maximum tokens for response')
    parser.add_argument('--temperature', type=float, default=0.1, help='Creativity level (0.0-1.0)')
    parser.add_argument('--output', '-o', help='Save output to file')
    parser.add_argument('--api-key', help='OpenAI API key (can also be set via OPENAI_API_KEY env var)')
    parser.add_argument('--provider', choices=['openai', 'gemini'], default='gemini', help='AI provider to use')
    parser.add_argument('--keeper-agent', action='store_true', help='Use Keeper Agent framework')

    args = parser.parse_args()

    # Initialize CLI
    cli = CodexCLI(api_key=args.api_key, provider=args.provider, use_keeper_agent=args.keeper_agent, reasoning_effort=args.reasoning_effort)

    # Set model for direct API calls (not used with Keeper Agent)
    if not args.keeper_agent:
        cli.model = args.model
        cli.max_tokens = args.max_tokens
        cli.temperature = args.temperature
        cli.stream = args.stream
    cli.reasoning_effort = args.reasoning_effort
    cli.reasoning_summary = args.reasoning_summary

    # Handle different modes
    if args.interactive:
        cli.interactive_mode()
        return

    if args.image:
        # Image analysis mode
        prompt = args.image_prompt or "What's in this image?"
        print(f"🖼️  Analyzing image: {args.image}")
        print(f"💭 Prompt: {prompt}")
        result = cli.analyze_image(args.image, prompt)

    elif args.web_search:
        # Web search mode
        print(f"🌐 Searching web for: {args.web_search}")
        print(f"📊 Results limit: {args.search_results}")
        result = cli.web_search(args.web_search, args.search_results)

    elif args.code_review:
        # Code review mode
        print(f"🔍 Reviewing code: {args.code_review}")
        print(f"📋 Review type: {args.review_type}")
        result = cli.code_review(args.code_review, args.review_type)

    elif args.programmatic:
        # Programmatic mode
        print(f"⚙️  Running commands from: {args.programmatic}")
        try:
            with open(args.programmatic, 'r', encoding='utf-8') as f:
                commands = json.load(f)
            result = cli.run_programmatic(commands)
        except Exception as e:
            result = {"success": False, "error": f"Failed to load or execute commands: {str(e)}"}

    elif args.file and args.task:
        # File analysis mode
        print(f"📁 Analyzing file: {args.file}")
        print(f"🎯 Task: {args.task}")
        result = cli.analyze_file(args.file, args.task)

    elif args.prompt:
        # Code generation mode
        print(f"🚀 Generating code for: {args.prompt}")
        if args.language:
            print(f"💻 Language: {args.language}")
        result = cli.generate_code(args.prompt, args.language)

    else:
        parser.print_help()
        return

    # Display results
    if result['success']:
        print("\n✅ Success!")
        print("=" * 50)

        if result.get('code'):
            # Display code with syntax highlighting hint
            code = result['code']
            print(code)

            # Save to file if requested
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(code)
                    print(f"\n💾 Code saved to: {args.output}")
                except Exception as e:
                    print(f"\n❌ Error saving file: {str(e)}")

        elif result.get('analysis'):
            # Display analysis results
            analysis = result['analysis']
            print(analysis)

        elif result.get('search_results'):
            # Display web search results
            search_results = result['search_results']
            for i, result_item in enumerate(search_results, 1):
                print(f"\n{i}. {result_item['title']}")
                print(f"   {result_item['link']}")
                if result_item.get('snippet'):
                    print(f"   {result_item['snippet'][:200]}...")

        elif result.get('reviews'):
            # Display code review results
            reviews = result['reviews']
            print(f"📋 Code Review Summary: {result.get('summary', '')}")
            print(f"📁 Files reviewed: {result.get('files_reviewed', 0)}")

            for review in reviews:
                print(f"\n🔍 File: {review.get('file', 'unknown')}")
                print(f"📊 Score: {review.get('score', 'N/A')}/10")
                if review.get('issues'):
                    print("⚠️  Issues found:")
                    for issue in review['issues'][:5]:  # Show first 5 issues
                        print(f"   • {issue}")
                if review.get('recommendations'):
                    print("💡 Recommendations:")
                    for rec in review['recommendations'][:3]:  # Show first 3 recommendations
                        print(f"   • {rec}")

        elif result.get('results'):
            # Display programmatic results
            prog_results = result['results']
            print(f"⚙️  Programmatic Execution Summary: {result.get('commands_executed', 0)} commands executed")

            for i, res in enumerate(prog_results, 1):
                cmd = res.get('command', {})
                print(f"\n{i}. {cmd.get('type', 'unknown')} command:")
                if res.get('result') and res['result'].get('success'):
                    print("   ✅ Success")
                    # Show brief result info
                    r = res['result']
                    if r.get('code'):
                        print(f"   📝 Generated {len(r['code'])} characters of code")
                    elif r.get('analysis'):
                        print(f"   📊 Analysis completed")
                    elif r.get('search_results'):
                        print(f"   🌐 Found {len(r['search_results'])} search results")
                    elif r.get('reviews'):
                        print(f"   🔍 Reviewed {len(r['reviews'])} files")
                else:
                    print(f"   ❌ Error: {res.get('error', 'Unknown error')}")

        # Show usage stats
        if result.get('usage'):
            usage = result['usage']
            print(f"\n📊 Token Usage: {usage['total_tokens']} total "
                  f"({usage['prompt_tokens']} prompt, {usage['completion_tokens']} completion)")

        elif result.get('total_usage'):
            # For code review with multiple files
            usage = result['total_usage']
            print(f"\n📊 Total Token Usage: {usage['total_tokens']} total "
                  f"({usage['prompt_tokens']} prompt, {usage['completion_tokens']} completion)")

        print(f"🤖 Model: {result.get('model', 'unknown')}")

    else:
        print(f"\n❌ Error: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()

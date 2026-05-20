#!/usr/bin/env python3
"""
Code Cleaner & Writer using Local Mistral
Automatically reads, improves, and writes code files
"""

import os
import re
from pathlib import Path
from local_mistral_agent import LocalMistralAgent
from typing import List, Dict, Any

class CodeCleaner:
    """Uses local Mistral to clean and improve code"""

    def __init__(self, model: str = "codellama:latest"):
        self.agent = LocalMistralAgent(model)
        self.workspace = Path(__file__).parent

    def read_file(self, file_path: str) -> str:
        """Read file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    def write_file(self, file_path: str, content: str) -> bool:
        """Write content to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing file: {e}")
            return False

    def improve_code(self, code: str, file_path: str) -> str:
        """Use Mistral to improve code"""
        prompt = f"""Analyze and improve this Python code from {file_path}:

{code}

Requirements:
1. Fix any bugs or issues
2. Improve code quality, readability, and efficiency
3. Add proper comments and docstrings
4. Follow Python best practices
5. Maintain the same functionality
6. Return only the improved code, no explanations

Improved code:"""

        return self.agent.generate(prompt, max_tokens=2000, temperature=0.3)

    def clean_file(self, file_path: str, backup: bool = True) -> bool:
        """Clean and improve a single file"""
        print(f"Cleaning {file_path}...")

        # Read current code
        current_code = self.read_file(file_path)
        if current_code.startswith("Error"):
            print(f"Failed to read {file_path}")
            return False

        # Backup if requested
        if backup:
            backup_path = f"{file_path}.backup"
            self.write_file(backup_path, current_code)
            print(f"Backup created: {backup_path}")

        # Improve code
        improved_code = self.improve_code(current_code, file_path)

        # Write back
        if self.write_file(file_path, improved_code):
            print(f"Successfully cleaned {file_path}")
            return True
        else:
            print(f"Failed to write {file_path}")
            return False

    def clean_directory(self, dir_path: str = ".", extensions: List[str] = [".py"], recursive: bool = False) -> Dict[str, bool]:
        """Clean all files in directory"""
        results = {}
        path = Path(dir_path)

        if recursive:
            files = path.rglob("*")
        else:
            files = path.iterdir()

        for file_path in files:
            if file_path.is_file() and file_path.suffix in extensions:
                results[str(file_path)] = self.clean_file(str(file_path))

        return results

    def analyze_and_suggest(self, file_path: str) -> str:
        """Analyze file and suggest improvements without writing"""
        code = self.read_file(file_path)
        if code.startswith("Error"):
            return code

        # Limit to first 2000 characters for analysis
        code_sample = code[:2000] + "..." if len(code) > 2000 else code

        prompt = f"""Analyze this Python code sample and suggest specific improvements:

{code_sample}

Provide:
1. Code quality assessment
2. Specific improvement suggestions
3. Potential bugs or issues
4. Best practice recommendations

Keep response under 500 words.

Analysis:"""

        return self.agent.generate(prompt, max_tokens=500, temperature=0.2)

def main():
    import sys
    cleaner = CodeCleaner()

    if len(sys.argv) < 2:
        print("Usage: python code_cleaner.py <file_path> [--analyze-only] [--recursive]")
        print("Examples:")
        print("  python code_cleaner.py analysis/pattern_recognizer.py")
        print("  python code_cleaner.py . --recursive  # Clean all .py files")
        print("  python code_cleaner.py analysis/pattern_recognizer.py --analyze-only")
        return

    file_path = sys.argv[1]
    analyze_only = "--analyze-only" in sys.argv
    recursive = "--recursive" in sys.argv

    if recursive or Path(file_path).is_dir():
        print(f"Cleaning directory: {file_path}")
        results = cleaner.clean_directory(file_path, recursive=recursive)
        success_count = sum(results.values())
        print(f"Cleaned {success_count}/{len(results)} files")
    elif analyze_only:
        analysis = cleaner.analyze_and_suggest(file_path)
        print(f"Analysis for {file_path}:")
        print(analysis)
    else:
        success = cleaner.clean_file(file_path)
        if success:
            print("File cleaned successfully!")
        else:
            print("Failed to clean file")

if __name__ == "__main__":
    main()
clean_code = '''# MODE: SCRIPT

"""
AI Code Generator Desktop App
Connects to Ollama LLM and automatically writes generated code to your PC
"""

import os
import json
import requests
from flask import Flask, render_template_string, request, jsonify
from pathlib import Path
import threading
import webbrowser

app = Flask(__name__)

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OUTPUT_DIR = Path.home() / "AIGeneratedCode"  # Saves to ~/AGeneratedCode
OUTPUT_DIR.mkdir(exist_ok=True)

# HTML Template
HTML_TEMPLATE_FILE = "template.html"

def call_ollama(prompt, model="llama2"):
    """Call Ollama API to generate code"""
    system_prompt = """You are a code generation assistant. When the user requests code, you must respond ONLY with a JSON object in this exact format:

{
    "filename": "descriptive_name.ext",
    "code": "the actual code here",
    "explanation": "brief explanation of what the code does"
}

Rules:
- Choose appropriate file extensions (.py, .js, .html, .cpp, etc.)
- Make the code complete and ready to run
- Keep explanations concise (1-2 sentences)
- ONLY output valid JSON, nothing else"""

    payload = {
        "model": model,
        "prompt": f"{system_prompt}\\n\\nUser request: {prompt}",
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '')
    except Exception as e:
        raise Exception(f"Ollama API error: {str(e)}")


def parse_llm_response(response_text):
    """Parse LLM response to extract code"""
    try:
        # Try to find JSON in the response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start != -1 and end > start:
            json_str = response_text[start:end]
            data = json.loads(json_str)
            return data
    except:
        pass
    
    # Fallback
    return {
        "filename": "generated_code.py",
        "code": response_text,
        "explanation": "Generated code"
    }


def save_code_to_file(filename, code):
    """Save generated code to file system"""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
    return filepath


@app.route('/')
def index():
    with open(HTML_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    return render_template_string(html_content, output_dir=str(OUTPUT_DIR))


@app.route('/models')
def get_models():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        models = [model['name'] for model in data.get('models', [])]
        return jsonify({'models': models})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        user_prompt = data.get('prompt', '')
        model = data.get('model', 'llama2')  # Default to llama2 if not specified
        
        # Call Ollama
        llm_response = call_ollama(user_prompt, model)
        
        # Parse response
        parsed = parse_llm_response(llm_response)
        
        # Save to file
        filepath = save_code_to_file(parsed['filename'], parsed['code'])
        
        return jsonify({
            'success': True,
            'filename': parsed['filename'],
            'code': parsed['code'],
            'explanation': parsed['explanation'],
            'filepath': filepath
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def open_browser():
    """Open browser after a short delay"""
    import time
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    print("=" * 60)
    print("🤖 AI Code Generator Starting...")
    print("=" * 60)
    print(f"📁 Output Directory: {OUTPUT_DIR}")
    print(f"🌐 Web Interface: http://localhost:5000")
    print(f"🔗 Ollama API: {OLLAMA_API_URL}")
    print("=" * 60)
    print("\nMake sure Ollama is running!")
    print("Start Ollama with: ollama serve")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    
    # Open browser in separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start Flask server
    app.run(debug=False, port=5000)
'''

with open('ai-code-gen-app-clean.py', 'w', encoding='utf-8') as f:
    f.write(clean_code)

print('Clean version created')
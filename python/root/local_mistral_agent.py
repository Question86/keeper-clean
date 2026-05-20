#!/usr/bin/env python3
"""
Local Mistral Integration for Keeper
Uses Ollama for local, token-free AI operations
"""

import requests
import json
from typing import Optional, Dict, Any

OLLAMA_URL = "http://localhost:11434/api/generate"

class LocalMistralAgent:
    """Agent using local Ollama Mistral model"""

    def __init__(self, model: str = "codellama:latest"):
        self.model = model
        self.conversation = []

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate response using local Ollama Mistral"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=10)  # Short timeout for testing
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            return f"Error: {str(e)}"

    def chat(self, message: str) -> str:
        """Simple chat interface"""
        self.conversation.append(f"User: {message}")
        context = "\n".join(self.conversation[-10:])  # Keep last 10 messages
        prompt = f"Context:\n{context}\n\nAssistant: Respond helpfully."
        response = self.generate(prompt)
        self.conversation.append(f"Assistant: {response}")
        return response

# Example usage
if __name__ == "__main__":
    agent = LocalMistralAgent()
    print("Local Mistral Agent ready. Type 'quit' to exit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
        response = agent.chat(user_input)
        print(f"Mistral: {response}")
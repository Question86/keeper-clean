#!/usr/bin/env python3
"""
Public Mistral.ai Integration for Keeper
Uses Mistral API for cloud-based operations
"""

import requests
import os
from typing import Optional, Dict, Any, List

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_EMBED_URL = "https://api.mistral.ai/v1/embeddings"

class MistralAIAgent:
    """Agent using public Mistral.ai API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY required. Get from https://mistral.ai/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate(self, prompt: str, model: str = "mistral-small-latest", max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate response using Mistral API"""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            response = requests.post(MISTRAL_API_URL, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {str(e)}"

    def embed(self, texts: List[str], model: str = "mistral-embed") -> List[List[float]]:
        """Get embeddings using Mistral API"""
        payload = {
            "model": model,
            "input": texts
        }

        try:
            response = requests.post(MISTRAL_EMBED_URL, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            return [emb["embedding"] for emb in result["data"]]
        except Exception as e:
            print(f"Embedding error: {e}")
            return []

    def chat(self, message: str, model: str = "mistral-small-latest") -> str:
        """Simple chat interface"""
        return self.generate(message, model)

# Example usage
if __name__ == "__main__":
    # Set your API key: export MISTRAL_API_KEY="your_key_here"
    try:
        agent = MistralAIAgent()
        print("Mistral.ai Agent ready. Type 'quit' to exit.")
        while True:
            user_input = input("You: ")
            if user_input.lower() == 'quit':
                break
            response = agent.chat(user_input)
            print(f"Mistral: {response}")
    except ValueError as e:
        print(f"Setup error: {e}")
        print("Get API key from https://mistral.ai/ (free tier available)")
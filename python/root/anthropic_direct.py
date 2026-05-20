#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct Anthropic API integration for Keeper environment
Bypasses Clawdbot to control token usage precisely
"""

import os
import json
import anthropic
from pathlib import Path
from rate_limit_handler import RateLimitHandler, EmbeddingCache
from typing import List

WORKSPACE = Path(__file__).parent
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
DISABLE_API = True  # Set to True to disable Claude API calls

class KeeperAgent:
    """Direct Anthropic API agent with controlled context"""
    
    def __init__(self, max_context_tokens=50000, workspace=None):
        if DISABLE_API:
            self.client = None
        else:
            if not API_KEY:
                raise ValueError("ANTHROPIC_API_KEY env var required when DISABLE_API=False")
            self.client = anthropic.Anthropic(api_key=API_KEY)
        self.max_context_tokens = max_context_tokens
        self.conversation = []
        self.system_prompt = self._build_system_prompt()
        
        # Rate limiting and caching
        if workspace:
            self.rate_handler = RateLimitHandler(workspace)
            self.embedding_cache = EmbeddingCache(workspace / "embedding_cache")
        else:
            self.rate_handler = None
            self.embedding_cache = None
        
    def _build_system_prompt(self):
        """Build minimal system prompt from session pack"""
        session_file = WORKSPACE / "_SESSION.md"
        if session_file.exists():
            return session_file.read_text(encoding='utf-8')
        return "You are a helpful AI assistant working in the Keeper-Clean-Loop1 project."
    
    def _estimate_tokens(self, text):
        """Rough token estimate (4 chars ≈ 1 token)"""
        return len(text) // 4
    
    def _trim_context(self):
        """Keep only recent conversation to stay under token budget"""
        while len(self.conversation) > 2:
            # Always keep last user message and last assistant response
            if self._estimate_tokens(json.dumps(self.conversation)) > self.max_context_tokens:
                # Remove oldest messages (but keep at least 2)
                self.conversation.pop(0)
            else:
                break
    
    def send(self, user_message, temperature=1.0, max_tokens=4096):
        """Send message and get response"""
        
        if self.client is None:
            return "API disabled - Claude calls are shut down."
        
        # Add user message
        self.conversation.append({
            "role": "user",
            "content": user_message
        })
        
        # Trim if needed
        self._trim_context()
        
        # Call API
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=max_tokens,
            temperature=temperature,
            system=self.system_prompt,
            messages=self.conversation
        )
        
        # Add assistant response
        assistant_message = response.content[0].text
        self.conversation.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # Return response with usage stats
        return {
            "message": assistant_message,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            "stop_reason": response.stop_reason
        }
    
    def create_embedding(self, text: str, model: str = "claude-embedding-3"):
        """Create embedding for text with caching and rate limiting."""
        if self.embedding_cache is None:
            return self._create_embedding_api_call(text, model)
        
        # Check cache first
        cached = self.embedding_cache.get(text, model)
        if cached is not None:
            return cached
        
        # Create embedding with rate limiting
        embedding = self.rate_handler.call_with_retry(
            self._create_embedding_api_call, text, model
        )
        
        # Cache the result
        self.embedding_cache.put(text, embedding, model)
        
        return embedding
    
    def create_embeddings_batch(self, texts: List[str], model: str = "claude-embedding-3"):
        """Create embeddings for multiple texts with batching and rate limiting."""
        if self.embedding_cache is None:
            return [self._create_embedding_api_call(text, model) for text in texts]
        
        embeddings = []
        
        # Check cache for each text
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cached = self.embedding_cache.get(text, model)
            if cached is not None:
                embeddings.append(cached)
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
                embeddings.append(None)  # Placeholder
        
        # Process uncached texts in batches
        if uncached_texts:
            batch_embeddings = self.rate_handler.call_with_retry(
                self._create_embeddings_batch_api_call, uncached_texts, model
            )
            
            # Fill in the results
            for idx, embedding in zip(uncached_indices, batch_embeddings):
                embeddings[idx] = embedding
                # Cache the result
                self.embedding_cache.put(uncached_texts[uncached_indices.index(idx)], embedding, model)
        
        return embeddings
    
    def _create_embedding_api_call(self, text: str, model: str):
        """Make actual API call for single embedding."""
        if self.client is None:
            # Return mock embedding for testing
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            # Create deterministic mock embedding based on text hash
            mock_embedding = [float(int(hash_obj.hexdigest()[i:i+2], 16) - 128) / 128.0 
                            for i in range(0, 32, 2)]  # 1536 dimensions would be too much, use 16
            return mock_embedding
        
        # Note: Anthropic doesn't have embedding API yet, this is placeholder
        # When available, implement actual API call
        raise NotImplementedError("Anthropic embedding API not yet available")
    
    def _create_embeddings_batch_api_call(self, texts: List[str], model: str):
        """Make actual API call for batch embeddings."""
        # For now, process individually (Anthropic doesn't have batch embedding)
        return [self._create_embedding_api_call(text, model) for text in texts]
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation = []
    
    def save_session(self, filepath):
        """Save conversation to file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "system": self.system_prompt,
                "conversation": self.conversation
            }, f, indent=2, ensure_ascii=False)
    
    def load_session(self, filepath):
        """Load conversation from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.system_prompt = data.get("system", self.system_prompt)
            self.conversation = data.get("conversation", [])


def interactive_mode():
    """Interactive CLI for chatting with agent"""
    agent = KeeperAgent(max_context_tokens=10000)  # Keep context small
    
    print("Keeper Direct API - Type 'exit' to quit, '/clear' to reset context")
    print(f"System prompt loaded: {len(agent.system_prompt)} chars\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
            
            if user_input == '/clear':
                agent.clear_conversation()
                print("Context cleared.")
                continue
            
            if user_input == '/save':
                filepath = input("Save to (default: session.json): ").strip() or "session.json"
                agent.save_session(filepath)
                print(f"Session saved to {filepath}")
                continue
            
            if user_input == '/load':
                filepath = input("Load from (default: session.json): ").strip() or "session.json"
                agent.load_session(filepath)
                print(f"Session loaded from {filepath}")
                continue
            
            if not user_input:
                continue
            
            # Send message
            response = agent.send(user_input)
            
            # Print response
            print(f"\nAssistant: {response['message']}")
            print(f"\n[Tokens: {response['usage']['input_tokens']} in / {response['usage']['output_tokens']} out / {response['usage']['total_tokens']} total]")
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        print("Usage:")
        print("  python anthropic_direct.py --interactive    # Start interactive chat")
        print("\nOr use in code:")
        print("  from anthropic_direct import KeeperAgent")
        print("  agent = KeeperAgent()")
        print("  response = agent.send('Your message here')")


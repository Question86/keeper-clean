#!/usr/bin/env python3
"""
OpenAI Advanced Features Integration for Keeper System

Integrates OpenAI's Realtime WebSocket, Speech-to-Text, and Embeddings APIs
"""

import os
import json
import asyncio
import websockets
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path
import openai
from openai import OpenAI

class OpenAIIntegration:
    """Main OpenAI integration class"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.realtime_ws = None
        self.realtime_connected = False

    # ===== REALTIME WEBSOCKET API =====

    async def connect_realtime(self) -> bool:
        """Connect to OpenAI Realtime WebSocket API"""
        try:
            url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }

            self.realtime_ws = await websockets.connect(url, extra_headers=headers)
            self.realtime_connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to Realtime API: {e}")
            return False

    async def disconnect_realtime(self):
        """Disconnect from Realtime WebSocket"""
        if self.realtime_ws:
            await self.realtime_ws.close()
            self.realtime_connected = False

    async def send_realtime_message(self, message: Dict[str, Any]):
        """Send message to Realtime API"""
        if not self.realtime_connected:
            return None

        try:
            await self.realtime_ws.send(json.dumps(message))
            response = await self.realtime_ws.recv()
            return json.loads(response)
        except Exception as e:
            print(f"Realtime message error: {e}")
            return None

    async def start_realtime_session(self, instructions: str = ""):
        """Start a realtime conversation session"""
        session_message = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": instructions or "You are a helpful AI assistant.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {"type": "server_vad"},
                "tools": [],
                "tool_choice": "auto",
                "temperature": 0.8,
                "max_response_output_tokens": 4096
            }
        }
        return await self.send_realtime_message(session_message)

    # ===== SPEECH-TO-TEXT API =====

    def transcribe_audio(self, audio_file_path: str, model: str = "whisper-1") -> Optional[str]:
        """Transcribe audio file to text using OpenAI Whisper"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file
                )
            return transcription.text
        except Exception as e:
            print(f"Speech-to-text error: {e}")
            return None

    def transcribe_audio_base64(self, audio_base64: str, model: str = "whisper-1") -> Optional[str]:
        """Transcribe base64 encoded audio to text"""
        try:
            # Decode base64 to bytes
            audio_bytes = base64.b64decode(audio_base64)

            # Save to temporary file (required by OpenAI API)
            temp_path = f"/tmp/audio_{hash(audio_base64)}.wav"
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)

            result = self.transcribe_audio(temp_path, model)

            # Clean up temp file
            os.remove(temp_path)

            return result
        except Exception as e:
            print(f"Base64 speech-to-text error: {e}")
            return None

    # ===== EMBEDDINGS API =====

    def create_embeddings(self, texts: List[str], model: str = "text-embedding-3-small") -> Optional[List[List[float]]]:
        """Create embeddings for a list of texts"""
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=model
            )
            return [embedding.embedding for embedding in response.data]
        except Exception as e:
            print(f"Embeddings creation error: {e}")
            return None

    def create_single_embedding(self, text: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
        """Create embedding for a single text"""
        embeddings = self.create_embeddings([text], model)
        return embeddings[0] if embeddings else None

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        import numpy as np
        from numpy.linalg import norm

        a = np.array(embedding1)
        b = np.array(embedding2)

        cosine_similarity = np.dot(a, b) / (norm(a) * norm(b))
        return cosine_similarity

    # ===== UTILITY METHODS =====

    def test_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            # Simple embeddings test
            test_embedding = self.create_single_embedding("test")
            return test_embedding is not None
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    async def realtime_conversation_loop(self, on_message_callback=None):
        """Main loop for realtime conversation"""
        if not self.realtime_connected:
            print("Not connected to realtime API")
            return

        try:
            async for message in self.realtime_ws:
                data = json.loads(message)

                if on_message_callback:
                    await on_message_callback(data)

                # Handle different message types
                msg_type = data.get("type")

                if msg_type == "error":
                    print(f"Realtime error: {data}")
                elif msg_type == "conversation.item.created":
                    print("New conversation item created")
                elif msg_type == "response.done":
                    print("Response completed")

        except Exception as e:
            print(f"Realtime loop error: {e}")
        finally:
            await self.disconnect_realtime()


# ===== FLASK INTEGRATION =====

def create_openai_endpoints(app, openai_integration: OpenAIIntegration):
    """Add OpenAI endpoints to Flask app"""

    @app.route('/api/openai/transcribe', methods=['POST'])
    def transcribe_endpoint():
        """Endpoint for speech-to-text transcription"""
        try:
            data = request.get_json()

            if 'audio_file' in data:
                # File path
                result = openai_integration.transcribe_audio(data['audio_file'])
            elif 'audio_base64' in data:
                # Base64 encoded audio
                result = openai_integration.transcribe_audio_base64(data['audio_base64'])
            else:
                return jsonify({"error": "No audio provided"}), 400

            if result:
                return jsonify({"transcription": result})
            else:
                return jsonify({"error": "Transcription failed"}), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/openai/embeddings', methods=['POST'])
    def embeddings_endpoint():
        """Endpoint for creating embeddings"""
        try:
            data = request.get_json()
            texts = data.get('texts', [])

            if not texts:
                return jsonify({"error": "No texts provided"}), 400

            embeddings = openai_integration.create_embeddings(texts)

            if embeddings:
                return jsonify({"embeddings": embeddings})
            else:
                return jsonify({"error": "Embeddings creation failed"}), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/openai/test', methods=['GET'])
    def test_openai_endpoint():
        """Test OpenAI API connection"""
        success = openai_integration.test_connection()
        return jsonify({"connected": success})


# ===== STANDALONE USAGE =====

async def demo_realtime():
    """Demo realtime WebSocket functionality"""
    integration = OpenAIIntegration()

    # Connect
    connected = await integration.connect_realtime()
    if not connected:
        return

    # Start session
    await integration.start_realtime_session("You are a helpful assistant for the Keeper system.")

    # Send a test message
    test_message = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Hello, can you help me with the Keeper system?"}]
        }
    }

    response = await integration.send_realtime_message(test_message)
    print("Realtime response:", response)

    # Start conversation loop (would run indefinitely)
    # await integration.realtime_conversation_loop()

    await integration.disconnect_realtime()


def demo_speech_to_text():
    """Demo speech-to-text functionality"""
    integration = OpenAIIntegration()

    # This would require an actual audio file
    # transcription = integration.transcribe_audio("path/to/audio.wav")
    # print("Transcription:", transcription)

    print("Speech-to-text demo: Would transcribe audio file if provided")


def demo_embeddings():
    """Demo embeddings functionality"""
    integration = OpenAIIntegration()

    texts = [
        "The Keeper system is a complex AI workflow management tool.",
        "OpenAI provides advanced AI APIs for various tasks.",
        "Embeddings help with semantic search and similarity matching."
    ]

    embeddings = integration.create_embeddings(texts)
    if embeddings:
        print(f"Created {len(embeddings)} embeddings")

        # Calculate similarity between first two
        similarity = integration.calculate_similarity(embeddings[0], embeddings[1])
        print(f"Similarity between texts 1&2: {similarity:.3f}")
    else:
        print("Failed to create embeddings")


if __name__ == "__main__":
    # Demo functions (uncomment to test)
    # demo_speech_to_text()
    # demo_embeddings()
    # asyncio.run(demo_realtime())

    print("OpenAI Integration module loaded. Use create_openai_endpoints() to integrate with Flask app.")

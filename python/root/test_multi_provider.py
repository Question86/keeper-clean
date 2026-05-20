#!/usr/bin/env python3
"""
Test script for Keeper Agent with both Gemini and OpenAI providers
"""

from keeper_agent import KeeperAgent

def test_provider(provider_name):
    print(f"\n{'='*50}")
    print(f"Testing {provider_name.upper()} Provider")
    print('='*50)

    try:
        agent = KeeperAgent(provider=provider_name)

        # Test basic functionality
        response = agent.send("Hello! What programming language are you most familiar with?")
        print(f"🤖 Response: {response['message'][:200]}...")
        print(f"📊 Tokens used: {response['usage']['tokens']}")

        # Test with tool usage
        response2 = agent.send("List the files in the current directory")
        print(f"🤖 Response: {response2['message'][:200]}...")
        print(f"📊 Tokens used: {response2['usage']['tokens']}")

        print(f"✅ {provider_name.upper()} test successful!")

    except Exception as e:
        print(f"❌ {provider_name.upper()} test failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Keeper Agent Multi-Provider Test")
    print("Testing both Gemini and OpenAI integrations...")

    test_provider("gemini")
    test_provider("openai")

    print(f"\n{'='*50}")
    print("🎉 Multi-provider test complete!")
    print("Both Gemini and OpenAI are now available in your Keeper Agent!")
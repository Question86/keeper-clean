# Test the full chain with the new personal API key
import requests
import json
import time

print('🧪 Testing personal API key with ClawdBot integration...')
print('')

test_message = {
    'message': 'Hello! I am testing my personal Anthropic account.',
    'sessionId': f'personal-test-{int(time.time())}',
    'tools': True
}

print(f'Sending: {test_message["message"]}')

try:
    response = requests.post(
        'http://localhost:5000/api/clawdbot/message',
        json=test_message,
        timeout=30
    )

    print(f'✅ Status: {response.status_code}')

    if response.status_code == 200:
        data = response.json()
        meta = data['full_response']['meta']['agentMeta']

        print(f'🤖 Model: {meta.get("model", "unknown")}')
        print(f'🏢 Provider: {meta.get("provider", "unknown")}')

        usage = meta.get('usage', {})
        input_tokens = usage.get('input', 0)
        output_tokens = usage.get('output', 0)
        cache_read = usage.get('cacheRead', 0)
        cache_write = usage.get('cacheWrite', 0)

        # Personal account pricing
        cost = (
            input_tokens * 0.015 / 1000 +
            output_tokens * 0.075 / 1000 +
            cache_read * 0.0015 / 1000 +
            cache_write * 0.00375 / 1000
        )

        print(f'💰 Usage: {usage}')
        print(f'💵 Estimated cost: ${cost:.4f} (personal pricing)')

        if 'full_response' in data and 'payloads' in data['full_response']:
            payloads = data['full_response']['payloads']
            if payloads:
                text = payloads[0].get('text', '')
                print(f'\n💬 Response: {text[:100]}...' if len(text) > 100 else f'💬 Response: {text}')

        print('')
        print('🎉 SUCCESS: Personal API key is working!')
        print('💡 Your costs should now be ~80% lower than organization pricing')

    else:
        print(f'❌ Error: {response.text}')

except Exception as e:
    print(f'❌ Error: {e}')
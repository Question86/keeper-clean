# Test the full chain: VS Code extension simulation -> Cockpit -> ClawdBot
import requests
import json
import time

print('Testing full chain...')

# Simulate what VS Code extension sends
test_message = {
    'message': 'What is 2+2?',
    'sessionId': f'vscode-test-{int(time.time())}',
    'tools': True
}

print(f'Sending: {json.dumps(test_message, indent=2)}')

try:
    response = requests.post(
        'http://localhost:5000/api/clawdbot/message',
        json=test_message,
        timeout=60
    )

    print(f'Status: {response.status_code}')
    print(f'Content-Type: {response.headers.get("content-type", "unknown")}')

    if response.headers.get('content-type', '').startswith('application/json'):
        data = response.json()
        print(f'Response keys: {list(data.keys())}')

        if 'full_response' in data and 'meta' in data['full_response'] and 'agentMeta' in data['full_response']['meta']:
            meta = data['full_response']['meta']['agentMeta']
            print(f'Model: {meta.get("model", "unknown")}')
            print(f'Provider: {meta.get("provider", "unknown")}')
            print(f'Usage: {meta.get("usage", {})}')

            # Calculate approximate cost
            usage = meta.get('usage', {})
            input_tokens = usage.get('input', 0)
            output_tokens = usage.get('output', 0)
            cache_read = usage.get('cacheRead', 0)
            cache_write = usage.get('cacheWrite', 0)

            # Claude pricing (approximate)
            cost = (
                input_tokens * 0.015 / 1000 +
                output_tokens * 0.075 / 1000 +
                cache_read * 0.0015 / 1000 +
                cache_write * 0.00375 / 1000
            )
            print(f'Approximate cost: ${cost:.4f}')

        if 'full_response' in data and 'payloads' in data['full_response']:
            payloads = data['full_response']['payloads']
            if payloads and len(payloads) > 0:
                text = payloads[0].get('text', 'No text')
                print(f'Response text (first 200 chars): {text[:200]}...')

    else:
        print(f'Raw response: {response.text[:500]}')

except Exception as e:
    print(f'Error: {e}')
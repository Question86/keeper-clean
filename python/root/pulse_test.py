import requests
import time
import json

print('=== AI Life Monitor Pulse Analysis ===')
print('Testing API over 20 seconds...')
print()

readings = []
start_time = time.time()

for i in range(20):
    try:
        r = requests.get('http://localhost:5000/api/life-coordinates', timeout=2)
        if r.status_code == 200:
            data = r.json()
            timestamp = time.time() - start_time
            confidence = data.get('confidence', 0)
            arousal = data.get('arousal', 0)

            readings.append({
                'time': timestamp,
                'confidence': confidence,
                'arousal': arousal
            })

            print(f'{timestamp:.1f}s: Conf {confidence:.3f}, Arou {arousal:.3f}')
        else:
            print(f'{time.time()-start_time:.1f}s: HTTP {r.status_code}')

    except Exception as e:
        print(f'{time.time()-start_time:.1f}s: Error {e}')

    time.sleep(1)

print()
print('=== Pulse Analysis ===')

if readings:
    confidence_values = [r['confidence'] for r in readings]
    arousal_values = [r['arousal'] for r in readings]

    conf_range = max(confidence_values) - min(confidence_values)
    arou_range = max(arousal_values) - min(arousal_values)

    print(f'Total readings: {len(readings)}')
    print(f'Confidence range: {min(confidence_values):.3f} - {max(confidence_values):.3f} (Δ{conf_range:.3f})')
    print(f'Arousal range: {min(arousal_values):.3f} - {max(arousal_values):.3f} (Δ{arou_range:.3f})')

    # Count significant changes
    conf_changes = sum(1 for i in range(1, len(confidence_values)) if abs(confidence_values[i] - confidence_values[i-1]) > 0.01)
    arou_changes = sum(1 for i in range(1, len(arousal_values)) if abs(arousal_values[i] - arousal_values[i-1]) > 0.01)

    print(f'Confidence changes >0.01: {conf_changes}/{len(readings)-1}')
    print(f'Arousal changes >0.01: {arou_changes}/{len(readings)-1}')

    # Pulse ratio (changes per minute)
    total_changes = conf_changes + arou_changes
    pulse_ratio = total_changes / (len(readings) / 60)
    print(f'Pulse ratio: {pulse_ratio:.2f} significant changes per minute')

    # Stability assessment
    if pulse_ratio < 1:
        stability = 'Very stable'
    elif pulse_ratio < 5:
        stability = 'Stable'
    elif pulse_ratio < 15:
        stability = 'Moderate activity'
    elif pulse_ratio < 30:
        stability = 'High activity'
    else:
        stability = 'Very high activity'

    print(f'Behavioral stability: {stability}')

else:
    print('No readings collected')
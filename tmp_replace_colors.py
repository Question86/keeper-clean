from pathlib import Path

path = Path('D:/Keeper-Clean/templates/cockpit.html')
text = path.read_text(encoding='utf-8')
replacements = {
    '#0a0e27': '#050505',
    '#1a1a2e': '#151515',
    '#2a2a3e': '#252525',
    '#8892a0': '#8a8a8a',
    '#7ba3c7': '#9d9d9d',
    '#f0f8ff': '#f2f2f2',
    '#e74c3c': '#b0b0b0',
    '#f39c12': '#d0d0d0',
    '#27ae60': '#9f9f9f',
    '#f5a85a': '#cdcdcd',
    '#e67e73': '#bdbdbd',
    '#5dbd7a': '#a8a8a8',
    '#fadbd8': '#e2e2e2',
    '#e67e22': '#c8c8c8',
    '#c0392b': '#909090'
}
replacements.update({
    'rgba(44, 62, 80, 0.95)': 'rgba(60, 60, 60, 0.95)',
    'rgba(39, 174, 96, 0.2)': 'rgba(170, 170, 170, 0.2)',
    'rgba(39, 174, 96, 0.15)': 'rgba(170, 170, 170, 0.15)',
    'rgba(39, 174, 96, 0.1)': 'rgba(170, 170, 170, 0.1)',
    'rgba(243, 156, 18, 0.15)': 'rgba(200, 200, 200, 0.15)',
    'rgba(243, 156, 18, 0.1)': 'rgba(200, 200, 200, 0.1)',
    'rgba(255, 170, 0, 0.2)': 'rgba(210, 210, 210, 0.2)',
    'rgba(74, 144, 226, 0.25)': 'rgba(150, 150, 150, 0.25)',
    'rgba(74, 144, 226, 0.15)': 'rgba(150, 150, 150, 0.15)',
    'rgba(74, 144, 226, 0.1)': 'rgba(150, 150, 150, 0.1)',
    'rgba(0, 255, 136, 0.2)': 'rgba(180, 180, 180, 0.2)',
    'rgba(0, 255, 136, 0.3)': 'rgba(180, 180, 180, 0.3)'
})
for old, new in replacements.items():
    text = text.replace(old, new)
path.write_text(text, encoding='utf-8')

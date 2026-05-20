#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test encoding fixes for Windows console (TASK_0155)"""

import sys

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_unicode_output():
    """Test that Unicode characters render without errors."""
    print("=== Unicode Encoding Test ===\n")
    
    test_chars = [
        ("✓", "Checkmark (U+2713)"),
        ("✗", "Cross mark (U+2717)"),
        ("→", "Right arrow (U+2192)"),
        ("←", "Left arrow (U+2190)"),
        ("≤", "Less than or equal (U+2264)"),
        ("≥", "Greater than or equal (U+2265)"),
        ("≠", "Not equal (U+2260)"),
        ("📊", "Chart emoji (U+1F4CA)"),
        ("🔍", "Magnifying glass (U+1F50D)"),
        ("⚠", "Warning sign (U+26A0)"),
    ]
    
    print("Testing common Unicode characters:")
    for char, desc in test_chars:
        try:
            print(f"  {char}  {desc}")
        except Exception as e:
            print(f"  ✗  FAILED: {desc} - {e}")
            return False
    
    print("\n✓ All Unicode characters rendered successfully!")
    print(f"\nSystem info:")
    print(f"  Platform: {sys.platform}")
    print(f"  Default encoding: {sys.getdefaultencoding()}")
    print(f"  Stdout encoding: {sys.stdout.encoding}")
    print(f"  Python version: {sys.version}")
    
    return True

if __name__ == '__main__':
    success = test_unicode_output()
    sys.exit(0 if success else 1)

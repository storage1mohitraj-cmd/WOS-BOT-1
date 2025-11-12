#!/usr/bin/env python3
"""Debug script to find where the nonce is hidden on the timeline page"""

import requests
import re
from bs4 import BeautifulSoup

resp = requests.get('https://whiteoutsurvival.pl/state-timeline/', timeout=10)
text = resp.text

print("[*] Searching for nonce patterns in timeline page...\n")

# Try various patterns
patterns = [
    ('name-value input field', r'name=["\']?nonce["\']?\s+value=["\']([^"\']+)["\']'),
    ('data-nonce attribute', r'data-nonce=["\']([^"\']+)["\']'),
    ('JS nonce variable (any name)', r'(stp_nonce|wp_nonce|_wpnonce)["\']?\s*[:=]\s*["\']([a-f0-9]{6,})["\']'),
    ('JSON nonce field', r'"(stp_nonce|nonce|wp_nonce)"\s*:\s*"([a-f0-9]{6,})"'),
    ('_ajax_nonce', r'_ajax_nonce["\']?\s*[:=]\s*["\']([a-f0-9]+)["\']'),
    ('Generic nonce hex', r'nonce\s*[:=]\s*["\']([a-f0-9]{6,})["\']'),
]

found_any = False
for desc, pat in patterns:
    matches = re.findall(pat, text, re.I)
    if matches:
        print(f"✓ Found {desc}:")
        for m in matches[:3]:  # show first 3
            if isinstance(m, tuple):
                print(f"    - {m}")
            else:
                print(f"    - {m}")
        print()
        found_any = True

if not found_any:
    print("✗ No obvious nonce patterns found")
    print("\nSearching in HTML structure...")
    soup = BeautifulSoup(text, 'html.parser')
    
    # Look for form fields
    inputs = soup.find_all('input', type=['hidden', 'text'])
    print(f"Found {len(inputs)} input fields")
    for inp in inputs[:5]:
        print(f"  {inp.get('name')}: {inp.get('value', '')[:50]}")
    
    # Look for script tags that might have nonce
    scripts = soup.find_all('script')
    print(f"\nFound {len(scripts)} script tags")
    for i, script in enumerate(scripts[:3]):
        content = script.string if script.string else ""
        if 'nonce' in content.lower():
            print(f"  Script {i} contains 'nonce': {content[:100]}...")

print(f"\nTotal page length: {len(text)} chars")
print(f"Response status: {resp.status_code}")

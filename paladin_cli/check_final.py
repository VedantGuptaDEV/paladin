#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check specific chars
for target_cp, name in [(0x00A2, 'cent sign'), (0x00ED, 'i-acute'), (0x0192, 'f-hook')]:
    ch = chr(target_cp)
    count = content.count(ch)
    if count:
        print(f"U+{target_cp:04X} ({ch}) {name} x{count}:")
        for i, c in enumerate(content):
            if c == ch:
                ctx_start = max(0, i-40)
                ctx_end = min(len(content), i+40)
                print(f"  {content[ctx_start:ctx_end]!r}")

# Also show the LOGO more carefully  
print()
print("LOGO content:")
logo_idx = content.find('LOGO = [')
logo_end = content.find('\n]', logo_idx) + 2
logo = content[logo_idx:logo_end]
for line in logo.split('\n'):
    print(f"  {line}")

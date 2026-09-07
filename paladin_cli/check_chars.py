#!/usr/bin/env python3
"""
Figure out what the mojibake characters actually ARE and what they should be.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the LOGO section
logo_idx = content.find('LOGO = [')
logo_end = content.find(']', logo_idx)
logo_section = content[logo_idx:logo_end]

# Print codepoints of every unique non-ASCII char
unique = {}
for ch in logo_section:
    if ord(ch) > 127 and ch not in unique:
        unique[ch] = ord(ch)

print("Unique non-ASCII chars in LOGO:")
for ch, cp in sorted(unique.items(), key=lambda x: x[1]):
    print(f"  U+{cp:04X} = {ch!r}")

# These chars ARE the box drawing chars. The question is: does the
# terminal support them? Let's check what Unicode block they come from.
# U+2588 = FULL BLOCK (█)
# U+2554 = BOX DRAWINGS DOUBLE DOWN AND RIGHT (╔)  
# etc.

# The chars in the file might actually be correct Unicode box chars.
# Let's check some:
print()
print("Checking if these are valid Unicode box/block chars:")
for ch, cp in sorted(unique.items(), key=lambda x: x[1]):
    import unicodedata
    try:
        name = unicodedata.name(ch)
        print(f"  U+{cp:04X} = {name}")
    except:
        print(f"  U+{cp:04X} = (no unicode name)")

# Also show the file's first 3 bytes (BOM check)
with open(r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py', 'rb') as f:
    first_bytes = f.read(4)
print(f"\nFile starts with: {first_bytes.hex()} (BOM: {first_bytes[:3] == bytes([0xef,0xbb,0xbf])})")
print(f"CRLF: {chr(13)+chr(10)} in file: ", end='')
with open(r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py', 'rb') as f:
    print(b'\r\n' in f.read())

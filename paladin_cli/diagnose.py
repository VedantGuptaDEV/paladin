#!/usr/bin/env python3
"""
Diagnose the exact mojibake pattern in paladin.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py', 'rb') as f:
    raw = f.read()

# Strip BOM
if raw[:3] == b'\xef\xbb\xbf':
    raw = raw[3:]

# Find LOGO section
logo_idx = raw.find(b'LOGO = [')
quote_idx = raw.find(b'"', logo_idx)
# Get the first line of the LOGO
eol = raw.find(b'\n', quote_idx)
first_logo_line = raw[quote_idx:eol]
print("First LOGO line bytes:", first_logo_line.hex())
print()

# The visible text we see is: Γûê Γòù etc.
# Let's decode the file as UTF-8 and show each non-ASCII character's codepoint
content = raw.decode('utf-8')
logo_start = content.find('LOGO = [')
logo_end = content.find(']', logo_start)
logo_section = content[logo_start:logo_end+1]

unique_chars = {}
for ch in logo_section:
    if ord(ch) > 127:
        cp = ord(ch)
        if cp not in unique_chars:
            unique_chars[cp] = ch

print("Non-ASCII chars in LOGO section:")
for cp in sorted(unique_chars):
    ch = unique_chars[cp]
    print(f"  U+{cp:04X} ({ch}) -> latin1/cp1252 byte: ", end='')
    try:
        b = ch.encode('latin-1')
        print(f"0x{b[0]:02X}")
    except:
        try:
            # cp1252 values
            if 0x80 <= cp <= 0x9F:
                # These are cp1252 chars, need special table
                cp1252_map = {
                    0x2018: 0x91, 0x2019: 0x92, 0x201C: 0x93, 0x201D: 0x94,
                    0x2013: 0x96, 0x2014: 0x97, 0x2022: 0x95,
                    0x0152: 0x8C, 0x0153: 0x9C, 0x0160: 0x8A, 0x0161: 0x9A,
                    0x0178: 0x9F, 0x017D: 0x8E, 0x017E: 0x9E,
                    0x0192: 0x83, 0x02C6: 0x88, 0x02DC: 0x98,
                    0x0393: 0x93,  # Gamma -> right curly quote byte
                }
                bval = cp1252_map.get(cp, 0)
                print(f"0x{bval:02X} (cp1252)")
            else:
                print("N/A")
        except Exception as e:
            print(f"error: {e}")
print()

# Now let's try to reverse: for each high codepoint, try encoding as cp1252 to get the original byte
print("Attempting reverse-decode (cp1252 byte -> utf-8):")

# Build cp1252 encode table
cp1252_enc = {}
for bval in range(0x80, 0x100):
    try:
        ch = bytes([bval]).decode('cp1252')
        cp1252_enc[ch] = bval
    except:
        pass

for cp in sorted(unique_chars):
    ch = unique_chars[cp]
    byte_val = None
    try:
        byte_val = ch.encode('latin-1')[0]
    except:
        if ch in cp1252_enc:
            byte_val = cp1252_enc[ch]
    
    if byte_val is not None:
        print(f"  U+{cp:04X} ({ch}) -> byte 0x{byte_val:02X}", end='')
        # Is this byte a valid utf-8 start or continuation?
        if 0x80 <= byte_val <= 0xBF:
            print(" [UTF-8 continuation]", end='')
        elif 0xC2 <= byte_val <= 0xF4:
            print(" [UTF-8 start]", end='')
        elif byte_val < 0x80:
            print(" [ASCII]", end='')
        print()

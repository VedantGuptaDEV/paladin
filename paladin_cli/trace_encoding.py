#!/usr/bin/env python3
"""
Trace the exact bytes and figure out the correct box chars.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# The file has chars like: Γ (U+0393), û (U+00FB), ê (U+00EA)
# These appear in sequence: ce 93, c3 bb, c3 aa in UTF-8

# Let's figure out: what encoding would make a "block" logo char?
# The logo looks like the PALADIN block text art.
# These are likely from CP437 (DOS codepage) block chars.

# CP437 full block = 0xDB = █
# CP437 chars used in block text art:
cp437_logo_chars = {
    0xDB: '█',  # full block - SOLID
    0xDC: '▄',  # lower half
    0xDD: '▌',  # left half  
    0xDE: '▐',  # right half
    0xDF: '▀',  # upper half
    0xC9: '╔',  # various box chars
    0xBB: '╗',
    0xC8: '╚',
    0xBC: '╝',
    0xBA: '║',
    0xCD: '═',
}

# The file bytes for "Γûê" are: CE 93 C3 BB C3 AA
# Decoded as UTF-8: U+0393 U+00FB U+00EA (3 chars)
# 
# How could 3 chars become from what should be 1 block char?
# 
# Option 1: Each char was 3 bytes in UTF-8:
#   U+0393 = CE 93 (2 bytes)
#   U+00FB = C3 BB (2 bytes)
#   U+00EA = C3 AA (2 bytes)
# Total: 6 bytes for 3 chars -> but a single CP437 char is 1 byte
# So it's NOT a 1-to-1 mapping.
#
# HOWEVER: looking at CE 93, C3 BB, C3 AA as a 6-byte sequence,
# maybe the original had PAIRS of bytes:
# CE 93 -> original byte: ?
# C3 BB -> original byte: ?  
# C3 AA -> original byte: ?
#
# In UTF-8: C3 BB = 0xFB in latin-1 = û
# In UTF-8: C3 AA = 0xEA in latin-1 = ê
# In UTF-8: CE 93 = 0x0393 = Γ (Greek)
#
# Γ (U+0393) in UTF-8 is CE 93 - but latin-1 only goes to FF,
# so this can't come from a single latin-1 byte.
#
# WAIT. Let me reconsider. What if the chars are Windows-1252 where:
# byte 0x93 in Windows-1252 = U+201C (left double quotation mark ")?
# BUT the file has U+0393 not U+201C.
# 
# There's only one way to get U+0393 from a byte: if someone decoded
# byte 0x93 using "ISO-8859-7" (Greek) where 0x93 is undefined,
# OR they decoded it with a codec that maps 0x93 -> U+0393.
# 
# Actually: in ISO-8859-7 (Greek), 0xC0=À,...0xF0=ð, but 0x93 is undefined.
# 
# In MacRoman: byte 0x93 = U+0201C? No...
#
# Let me just check: what codec maps byte 0x93 to U+0393 (Greek Gamma)?
print("Searching for codec that maps 0x93 -> U+0393 (Γ):")
import codecs
for enc in ['cp437', 'cp850', 'cp852', 'cp866', 'cp1251', 'cp1252', 'cp1253',
            'iso-8859-1', 'iso-8859-2', 'iso-8859-5', 'iso-8859-7', 'koi8-r',
            'mac-roman', 'mac-greek', 'ascii']:
    try:
        ch = bytes([0x93]).decode(enc)
        if ch == 'Γ' or ord(ch) == 0x0393:
            print(f"  {enc}: 0x93 -> U+{ord(ch):04X} ({ch}) MATCH!")
        # also check if it could produce the full sequence
    except:
        pass

# Also check for 0xFB -> û (U+00FB)
print("\nChecking which codecs map 0xFB -> U+00FB (û):")
for enc in ['cp437', 'cp850', 'cp1252', 'latin-1', 'cp866']:
    try:
        ch = bytes([0xFB]).decode(enc)
        print(f"  {enc}: 0xFB -> U+{ord(ch):04X} ({ch!r})")
    except:
        pass

# The key insight: Γ (U+0393) is Greek Gamma. In UTF-8 it's encoded CE 93.
# If someone accidentally ran utf-8 bytes through an encoder again:
# Original char: █ (U+2588, UTF-8: E2 96 88)
# E2 = â in latin-1, 96 = control char in latin-1, 88 = ˆ in cp1252
# Saved as UTF-8: C3 A2, C2 96, CB 86 -> decoded: â, –, ˆ (not what we have)
#
# Different approach: look at what the LOGO actually renders as.
# The user's error shows the LOGO with Γûê etc - which IS the cp1252 mojibake
# of Unicode block characters! Specifically:
# █ (U+2588) in UTF-8 = E2 96 88
# Read as cp1252: â (E2), – (96=en dash), ˆ (88=circumflex)... nope
#
# Let's try: the chars in the file (Γ U+0393, û U+00FB) - decode their 
# UNICODE CODEPOINTS as if they were cp1252 BYTE VALUES:
# U+0393 = 0x0393 - too large for a byte
# 
# I think the actual issue is: when Python reads this file for the TERMINAL,
# the terminal is Windows and NOT configured for UTF-8, so it shows garbled chars.
# The file content might actually be CORRECT Unicode box chars when printed
# on a UTF-8 terminal, but the Windows console is showing garbled output
# because its codepage is not UTF-8.

print("\n\n=== TESTING: What does the file ACTUALLY contain? ===")
print("Checking if these chars ARE actual Unicode block/box chars:")

# Re-read and check
with open(r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py', 'r', encoding='utf-8') as f:
    content = f.read()

logo_idx = content.find('LOGO = [')
logo_end = content.find(']', logo_idx)
logo_section = content[logo_idx:logo_end]

# What codepoints are actually present?
print("\nAll unique non-ASCII codepoints in LOGO, in order of first appearance:")
seen = []
seen_set = set()
for ch in logo_section:
    cp = ord(ch)
    if cp > 127 and cp not in seen_set:
        seen.append(cp)
        seen_set.add(cp)

for cp in seen:
    import unicodedata
    try:
        name = unicodedata.name(chr(cp))
    except:
        name = "(unnamed)"
    print(f"  U+{cp:04X}: {name}")
    
# If these are Latin letters like É, æ, ê etc. then the file is WRONG.
# The correct chars should be block/box chars like:
# U+2588 (█ FULL BLOCK), U+2554 (╔), U+2557 (╗), etc.
print()
print("Expected box/block chars for a block-art logo:")
expected = [
    (0x2588, "FULL BLOCK"),
    (0x2554, "BOX DRAWINGS DOUBLE DOWN AND RIGHT"),
    (0x2557, "BOX DRAWINGS DOUBLE DOWN AND LEFT"),
    (0x2551, "BOX DRAWINGS DOUBLE VERTICAL"),
    (0x2550, "BOX DRAWINGS DOUBLE HORIZONTAL"),
    (0x255A, "BOX DRAWINGS DOUBLE UP AND RIGHT"),
    (0x255D, "BOX DRAWINGS DOUBLE UP AND LEFT"),
    (0x2560, "BOX DRAWINGS DOUBLE VERTICAL AND RIGHT"),
    (0x2563, "BOX DRAWINGS DOUBLE VERTICAL AND LEFT"),
    (0x2566, "BOX DRAWINGS DOUBLE DOWN AND HORIZONTAL"),
    (0x2569, "BOX DRAWINGS DOUBLE UP AND HORIZONTAL"),
    (0x256C, "BOX DRAWINGS DOUBLE VERTICAL AND HORIZONTAL"),
]
for cp, name in expected:
    print(f"  U+{cp:04X} ({chr(cp)}): {name}")

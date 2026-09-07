#!/usr/bin/env python3
"""
Fix the double-encoded UTF-8 box/block characters in paladin.py.

Pattern:
  The file bytes are valid UTF-8 but the *characters* are wrong.
  e.g. LOGO first byte sequence:  ce 93 c3 bb c3 aa
  As UTF-8: U+0393 U+00FB U+00EA = "Γûê"
  
  U+0393 (Γ) is NOT in latin-1 range. In cp1252 byte 0x93 = right curly quote (")
  but encoded as UTF-8 cp1252 gives ce 93.
  
  What actually happened: the source had raw byte 0x93 (from cp1252 / Windows-1252)
  which is NOT latin-1. When the file was edited/saved in UTF-8, that byte was
  misinterpreted as the single-byte "character" 0x93, saved as UTF-8 two-byte
  sequence CE 93 (= U+0393, Greek Gamma).

  Similarly: 0xFB (latin-1 û) -> C3 BB in UTF-8; 0xEA (ê) -> C3 AA.
  So the original bytes were: 93 FB EA ...

  93 FB EA in cp1252 decoding: 
    0x93 = " (right double curly quote, U+201C)
    0xFB = û (U+00FB)
    0xEA = ê (U+00EA)
  But 93 FB EA as UTF-8 bytes: 0x93 is not valid UTF-8 start byte.
  
  HOWEVER: if we treat those bytes as a straight single-byte stream,
  they might be OEM (CP437 / CP850) encoded box chars!
  
  CP437 box chars:
    0xDB = █ (full block)
    0xDC = ▄ (lower half block)  
    0xDD = ▌ (left half block)
    0xC9 = ╔ (box top-left double)
    0xBB = ╗ (box top-right double)
    0xC8 = ╚ (box bottom-left double)
    0xBC = ╝ (box bottom-right double)
    0xBA = ║ (vertical double)
    0xCD = ═ (horizontal double)
    ...
  
  Let's actually just look at what chars would be correct for a "PALADIN" block logo.
  The logo uses block chars like: █ ╗ ╔ ╚ ╝ ╠ ╣ ╦ ╩ ╬ ═ ║
  
  The simplest fix: replace every multi-byte sequence that decodes to a 
  non-ASCII char with its "intended" box char by decoding the bytes as cp437.
"""

import sys, re
sys.stdout.reconfigure(encoding='utf-8')

INFILE  = r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py'
BACKUP  = r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py.bak'

# ── 1. Read raw bytes ──────────────────────────────────────────────────────────
with open(INFILE, 'rb') as f:
    raw = f.read()

# Save backup
with open(BACKUP, 'wb') as f:
    f.write(raw)
print(f"Backup saved to {BACKUP}")

# Strip BOM
had_bom = raw[:3] == b'\xef\xbb\xbf'
if had_bom:
    raw = raw[3:]
    print("Stripped UTF-8 BOM")

# Normalise CRLF
if b'\r\n' in raw:
    raw = raw.replace(b'\r\n', b'\n')
    print("Normalised CRLF -> LF")

# ── 2. The core fix ────────────────────────────────────────────────────────────
# Each non-ASCII char was originally a single byte in cp437/cp850 that got
# saved incorrectly as UTF-8. The sequence:
#   U+0393 U+00FB U+00EA -> bytes CE93 C3BB C3AA
#   -> original bytes: 93 FB EA
#   -> as cp437: box char depends on byte value
#
# The pattern for every non-ASCII char in the file:
#   if char in range U+0080..U+00FF: its byte value = char - 0 (latin-1)
#   if char == U+0393 (Γ): the original byte was 0x93 (cp1252)
#   if char == U+0192 (ƒ): byte was 0x83 (cp1252)
#   etc.
#
# Then decode those collected bytes as cp437.

# Build cp1252 decode table (byte -> unicode char)
cp1252_decode = {}
for b in range(0x00, 0x100):
    try:
        cp1252_decode[b] = bytes([b]).decode('cp1252')
    except:
        pass
# Invert: char -> byte
cp1252_encode = {v: k for k, v in cp1252_decode.items()}

def char_to_original_byte(ch: str):
    """Return the original single byte that became this char via UTF-8 mis-encoding."""
    cp = ord(ch)
    if cp < 0x80:
        return cp  # ASCII, no change
    if cp <= 0xFF:
        return cp  # latin-1 range, byte == codepoint
    # For cp1252 special chars (0x80-0x9F range, maps to Unicode)
    if ch in cp1252_encode:
        return cp1252_encode[ch]
    return None

# Now scan the utf-8 decoded string, collect runs of non-ASCII chars,
# try to decode those collected original bytes as cp437.
content = raw.decode('utf-8')

# Build a mapping: for each sequence of "mojibake" chars, what is the cp437 char?
# We do this by:
#   1. Convert non-ASCII chars back to their "original bytes"
#   2. Decode those bytes as cp437

def fix_char_sequence(chars: str) -> str:
    """Convert a sequence of mojibake chars to their cp437 equivalent."""
    orig_bytes = []
    for ch in chars:
        b = char_to_original_byte(ch)
        if b is None:
            return None  # can't convert
        orig_bytes.append(b)
    try:
        return bytes(orig_bytes).decode('cp437')
    except:
        return None

# Replace runs of non-ASCII chars
result = []
i = 0
fixes = 0
while i < len(content):
    ch = content[i]
    if ord(ch) > 127:
        # Collect consecutive non-ASCII chars
        j = i
        while j < len(content) and ord(content[j]) > 127:
            j += 1
        run = content[i:j]
        fixed = fix_char_sequence(run)
        if fixed is not None:
            result.append(fixed)
            fixes += 1
        else:
            result.append(run)  # leave unchanged
        i = j
    else:
        result.append(ch)
        i += 1

fixed_content = ''.join(result)
print(f"Fixed {fixes} non-ASCII runs")

# ── 3. Write back as UTF-8 without BOM ────────────────────────────────────────
out_bytes = fixed_content.encode('utf-8')
with open(INFILE, 'wb') as f:
    f.write(out_bytes)
print(f"Written {len(out_bytes)} bytes")

# ── 4. Quick verification ──────────────────────────────────────────────────────
with open(INFILE, 'r', encoding='utf-8') as f:
    check = f.read()

# Show LOGO
logo_idx = check.find('LOGO = [')
logo_end = check.find(']', logo_idx) + 1
print("\nLOGO after fix:")
print(check[logo_idx:logo_end])

# Show box chars used
print("\nBox char sample (_box_top):")
bt_idx = check.find('def _box_top', check.find('# Pure black'))
print(check[bt_idx:bt_idx+300])

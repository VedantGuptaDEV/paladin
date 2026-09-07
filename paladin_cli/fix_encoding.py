#!/usr/bin/env python3
"""
Diagnose and fix the double-encoded UTF-8 box characters in paladin.py
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

INFILE  = r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py'
OUTFILE = r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py'

# ── Step 1: read raw bytes ────────────────────────────────────────────────────
with open(INFILE, 'rb') as f:
    raw = f.read()

# Strip UTF-8 BOM if present
if raw[:3] == b'\xef\xbb\xbf':
    print("Found UTF-8 BOM — stripping it")
    raw = raw[3:]

# Normalise CRLF → LF
if b'\r\n' in raw:
    print("Found CRLF line endings — converting to LF")
    raw = raw.replace(b'\r\n', b'\n')

# ── Step 2: decode as UTF-8 to get the mojibake string ───────────────────────
content = raw.decode('utf-8')
print(f"File decoded as UTF-8 OK  ({len(content)} chars)")

# ── Step 3: figure out what characters need to be fixed ──────────────────────
# Approach: scan for sequences of chars where each char is <= U+00FF (latin-1 range)
# AND the sequence of their latin-1 byte values forms valid UTF-8 for a box/block char.

def fix_mojibake(text: str) -> str:
    """
    Walk the string and fix double-encoded sequences.
    A double-encoded run is a maximal consecutive sequence of code points
    all in the Latin-1 Supplement range (U+0080..U+00FF) or
    in cp1252 private-use range — together their byte values (in latin-1)
    form a valid UTF-8 sequence.
    
    We also handle the case where Γ (U+0393, Greek capital Gamma) appears:
    it maps to byte 0x93 in cp1252 which CAN start a sequence.
    """
    # Build a mapping from cp1252 code point back to byte value
    # (for the range U+0080..U+00FF / cp1252)
    cp1252_to_byte = {}
    for byte_val in range(0x80, 0x100):
        try:
            ch = bytes([byte_val]).decode('cp1252')
            cp1252_to_byte[ch] = byte_val
        except Exception:
            pass
    # Also add latin-1 U+00A0..U+00FF (same as cp1252 for those)
    for byte_val in range(0x00, 0x80):
        cp1252_to_byte[chr(byte_val)] = byte_val

    result = []
    i = 0
    fixes = 0
    while i < len(text):
        ch = text[i]
        # Check if this char is in cp1252-encodeable range (could be a mojibake byte)
        if ch in cp1252_to_byte:
            byte_val = cp1252_to_byte[ch]
            # Check if it could be start of a multi-byte UTF-8 sequence
            if 0xC2 <= byte_val <= 0xF4:
                # Attempt to consume bytes for a UTF-8 sequence
                seq_len = (
                    2 if byte_val < 0xE0 else
                    3 if byte_val < 0xF0 else
                    4
                )
                # Try to collect seq_len consecutive cp1252-encodeable chars
                seq_bytes = bytes([byte_val])
                j = i + 1
                ok = True
                while len(seq_bytes) < seq_len and j < len(text):
                    next_ch = text[j]
                    if next_ch in cp1252_to_byte:
                        nb = cp1252_to_byte[next_ch]
                        if 0x80 <= nb <= 0xBF:  # continuation byte
                            seq_bytes += bytes([nb])
                            j += 1
                        else:
                            ok = False
                            break
                    else:
                        ok = False
                        break
                if ok and len(seq_bytes) == seq_len:
                    try:
                        fixed_char = seq_bytes.decode('utf-8')
                        # Only apply if it's actually a non-ASCII unicode char
                        if ord(fixed_char) > 0x7E:
                            result.append(fixed_char)
                            fixes += 1
                            i = j
                            continue
                    except Exception:
                        pass
        result.append(ch)
        i += 1

    print(f"Fixed {fixes} double-encoded sequences")
    return ''.join(result)

fixed = fix_mojibake(content)

# ── Step 4: write back as UTF-8 without BOM ──────────────────────────────────
out_bytes = fixed.encode('utf-8')
with open(OUTFILE, 'wb') as f:
    f.write(out_bytes)

print(f"Written {len(out_bytes)} bytes to {OUTFILE}")
print()

# ── Step 5: quick verification ────────────────────────────────────────────────
# Re-read and show a snippet of the LOGO section
with open(OUTFILE, 'r', encoding='utf-8') as f:
    check = f.read()

logo_idx = check.find('LOGO = [')
logo_snippet = check[logo_idx:logo_idx+300]
print("LOGO section after fix:")
print(logo_snippet[:300])

#!/usr/bin/env python3
"""
final_fix.py — Replace all mojibake chars in paladin.py with correct Unicode.

Each 3-char mojibake sequence (Γ + 2 Latin chars) maps to one Unicode char.
Mapping deduced from context and codepoint analysis.
"""
import sys, re, subprocess
sys.stdout.reconfigure(encoding='utf-8')

INFILE = r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py'

with open(INFILE, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Read {len(content)} chars")

# ── Complete char map ─────────────────────────────────────────────────────────
# Format: garbled_sequence -> correct_char
# The garbled sequences are identified by their exact Unicode codepoints.
# Each entry maps a specific multi-char mojibake to the correct box/symbol char.

CHAR_MAP = [
    # Box drawing chars (single-line)
    ('Γò¡',  '╔'),   # U+0393 U+00F2 U+00A1  → top-left double corner
    ('Γò«',  '╗'),   # U+0393 U+00F2 U+00AB  → top-right double corner
    ('Γòö',  '╠'),   # U+0393 U+00F2 U+00F6  → left double T-junction
    ('Γòæ',  '║'),   # U+0393 U+00F2 U+00E6  → vertical double line
    ('ΓòÉ',  '═'),   # U+0393 U+00F2 U+00C9  → horizontal double line
    ('Γò¥',  '╝'),   # U+0393 U+00F2 U+00A5  → bottom-right double corner
    ('ΓòÜ',  '╚'),   # U+0393 U+00F2 U+00DC  → bottom-left double corner
    ('Γò░',  '╚'),   # U+0393 U+00F2 U+2591  → bottom-left (alt)
    ('Γò»',  '╝'),   # U+0393 U+00F2 U+00BB  → bottom-right (alt)
    # These are for single-line box (used in banner outline)
    ('Γöé',  '│'),   # U+0393 U+00F6 U+00E9  → vertical single
    ('Γö£',  '├'),   # U+0393 U+00F6 U+00A3  → left T single
    ('Γöñ',  '┤'),   # U+0393 U+00F6 U+00F1  → right T single
    ('ΓöÇ',  '─'),   # U+0393 U+00F6 U+00C7  → horizontal single
    # Code block corners
    ('Γöî',  '┌'),   # code block top-left
    ('Γöö',  '└'),   # code block bottom-left
    ('Γöÿ',  '┘'),   # code block bottom-right
    # Block chars
    ('Γûê',  '█'),   # U+0393 U+00FB U+00EA  → full block
    ('Γûæ',  '░'),   # U+0393 U+00FB U+00E6  → light shade (for risk bar empty)
    # Section dividers (the ━━━ lines in comments are already correct U+2501)
    ('Γöü',  '─'),   # U+0393 U+00F6 U+00FC  → comment section divider (use ─)
    # Symbols / icons
    ('Γ¼í',  '🛡'),  # U+0393 U+00BC U+00ED  → shield icon (paladin icon)
    ('Γ¼ñ',  '🔑'),  # U+0393 U+00BC U+00F1  → key/connected icon
    ('Γùå',  '⚠'),   # U+0393 U+00F9 U+00E5  → warning triangle
    ('Γùï',  '✗'),   # U+0393 U+00F9 U+00EF  → not found / X
    ('ΓùÅ',  '●'),   # U+0393 U+00F9 U+00C5  → bullet/status dot
    ('Γ£ô',  '✔'),   # U+0393 U+00A3 U+00F4  → check mark
    ('Γ£ò',  '✘'),   # U+0393 U+00A3 U+00F2  → X mark
    ('Γ£ù',  '✗'),   # U+0393 U+00A3 U+00F9  → error X
    ('ΓÅ▒',  '⏱'),   # U+0393 U+00C5 U+2592  → timer/elapsed
    ('ΓåÆ',  '→'),   # U+0393 U+00E5 U+00C6  → arrow right
    ('Γ¢¿',  '🛡'),  # U+0393 U+00A2 U+00BF  → shield (alternate)
    ('Γ¥»',  '❯'),   # U+0393 U+00A5 U+00BB  → prompt arrow / chevron
    ('ΓǪ',   '…'),   # U+0393 U+01EA         → ellipsis
    ('┬╖',   '·'),   # U+252C U+2556         → middle dot (already unicode, just wrong chars)
    # Arrow for comments/docstrings
    ('ΓÇö',  '—'),   # U+0393 U+00C7 U+00F6  → em dash (used in comments)
    ('ΓÇó',  '•'),   # bullet in some lists
    ('ΓÇì',  '"'),   # opening quote
    ('ΓÇ»',  '»'),   # right angle quote
    ('ΓÇ╗',  '»'),
    ('ΓÇ║',  '║'),
    ('ΓÇ¬',  '¬'),
    # Ellipsis variant
    ('ΓǪ',   '…'),
]

fixes_total = 0
for garbled, proper in CHAR_MAP:
    count = content.count(garbled)
    if count > 0:
        content = content.replace(garbled, proper)
        fixes_total += count
        print(f"  {count:3d}x  {garbled!r:12s} → {proper}")

print(f"\nTotal replacements: {fixes_total}")

# ── Add UTF-8 stdout setup at the very top of main() ─────────────────────────
# Find 'def main():' and add reconfigure right after the first line
UTF8_CODE = '''\
    # ── Windows UTF-8 console ──────────────────────────────────────────────────
    import io as _io
    if sys.platform == 'win32':
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
    # ─────────────────────────────────────────────────────────────────────────
'''

main_idx = content.find('\ndef main():\n')
if main_idx >= 0:
    # Find the first line of main() body
    body_start = content.find('\n', main_idx + 1) + 1  # skip 'def main():\n'
    content = content[:body_start] + UTF8_CODE + content[body_start:]
    print("\nAdded UTF-8 stdout setup in main()")
else:
    print("\nWARNING: Could not find main() function!")

# ── Write back ────────────────────────────────────────────────────────────────
with open(INFILE, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Wrote {len(content)} chars to {INFILE}")

# ── Verify syntax ─────────────────────────────────────────────────────────────
result = subprocess.run(
    [sys.executable, '-m', 'py_compile', INFILE],
    capture_output=True, text=True
)
if result.returncode == 0:
    print('✓ Syntax OK')
else:
    print(f'✗ Syntax error:\n{result.stderr}')

# ── Show remaining non-ASCII chars ────────────────────────────────────────────
with open(INFILE, 'r', encoding='utf-8') as f:
    final = f.read()

remaining = {}
for ch in final:
    if ord(ch) > 127 and ord(ch) < 0x2000:  # Latin supplement range still present
        cp = ord(ch)
        if cp not in remaining:
            remaining[cp] = 0
        remaining[cp] += 1

if remaining:
    print("\nRemaining Latin-supplement chars (may still be garbled):")
    for cp, count in sorted(remaining.items()):
        import unicodedata
        try: name = unicodedata.name(chr(cp))
        except: name = "?"
        print(f"  U+{cp:04X} ({chr(cp)}) x{count}: {name}")
else:
    print("\nNo remaining Latin-supplement chars — all clean!")

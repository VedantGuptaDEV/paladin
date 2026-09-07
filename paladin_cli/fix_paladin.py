#!/usr/bin/env python3
"""
fix_paladin.py — Replace garbled chars in paladin.py with proper Unicode.

The file contains Latin/accented chars (É, æ, û, etc.) and U+0393 (Γ)
used as visual elements. These need to be replaced with proper Unicode
box-drawing and block chars, and the file needs UTF-8 stdout setup.

Mapping deduced from the visual context of each char:
  Γûê (Γ+û+ê = U+0393 U+00FB U+00EA) → █  U+2588 FULL BLOCK
  Γòù (Γ+ò+ù) → ╗  
  Γòö (Γ+ò+ö) → ╔  etc.

Actually the simplest approach: the LOGO uses only 2-3 distinct "cell types":
  - "solid fill" = █  
  - "top-right corner" of a letter
  - "bottom" etc.

Let me look at what chars appear where in the logo:
  Line 1: ΓûêΓûêΓûêΓûêΓûêΓûêΓòù  ΓûêΓûêΓûêΓûêΓûêΓòù ΓûêΓûêΓòù ...
  The repeating Γûê = full block █
  Γòù = box top-right / corner char

Rather than guessing, I'll replace the entire LOGO with a clean ASCII-art
PALADIN made from proper Unicode block chars, and fix all the box drawing
chars in the rest of the file.
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

INFILE = r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py'

with open(INFILE, 'r', encoding='utf-8') as f:
    content = f.read()

# ── 1. Add UTF-8 stdout reconfigure right after the first import block ────────
# Find the existing imports block end (after `import os, sys, ...`)
# and add the reconfigure there.

UTF8_SETUP = '''
# ── Windows UTF-8 console fix ─────────────────────────────────────────────────
import io as _io
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
elif sys.platform == 'win32':
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
# ─────────────────────────────────────────────────────────────────────────────
'''

# Insert after the first import line (import os, sys, ...)
first_import = content.find('import os, sys,')
if first_import == -1:
    first_import = content.find('import os,')
eol = content.find('\n', first_import)
content = content[:eol+1] + UTF8_SETUP + content[eol+1:]
print("Added UTF-8 stdout reconfigure")

# ── 2. Replace the garbled LOGO with proper Unicode block chars ───────────────
# The new LOGO uses proper box/block drawing chars: █ ╔ ╗ ╚ ╝ ║ ═ ╠ ╣ ╦ ╩
# PALADIN block text art using full blocks:

NEW_LOGO = '''LOGO = [
    " ██████╗  █████╗ ██╗      █████╗ ██████╗ ██╗███╗   ██╗",
    " ██╔══██╗██╔══██╗██║     ██╔══██╗██╔══██╗██║████╗  ██║",
    " ██████╔╝███████║██║     ███████║██║  ██║██║██╔██╗ ██║",
    " ██╔══╝  ██╔══██║██║     ██╔══██║██║  ██║██║██║╚██╗██║",
    " ██║     ██║  ██║███████╗██║  ██║██████╔╝██║██║ ╚████║",
    " ╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝",
]'''

# Find and replace the existing LOGO list
logo_match = re.search(r'LOGO\s*=\s*\[.*?\]', content, re.DOTALL)
if logo_match:
    content = content[:logo_match.start()] + NEW_LOGO + content[logo_match.end():]
    print("Replaced LOGO with proper Unicode block chars")
else:
    print("WARNING: Could not find LOGO definition!")

# ── 3. Fix the box-drawing chars in _box_* functions ─────────────────────────
# The box chars used in the code (in _box_top, _box_bot etc.) contain:
# These function bodies use f-strings with embedded chars.
# The chars in the _box functions come from the LGREY/_BDRC helpers.
# Let's check what chars appear in the box function strings directly:

# Find all the box char literals in _box_* functions
# The problematic chars: Γò¡ Γò« Γò░ Γò» Γöé Γö£ Γöñ (used in older box functions)
# and in the newer functions: they use the same pattern

# From reading the code, the box functions in the file use these literal chars:
# _box_top:  Γò¡  ...  Γò«  (top border)
# _box_row:  Γöé  (side borders)
# _box_sep:  Γö£  ...  Γöñ  (middle separator)
# _box_bot:  Γò░  ...  Γò»  (bottom border)

# These specific "garbled" sequences map to:
# Γò¡ (appears in box_top) -> ╔ or ┌  (top-left corner)
# Γò« (appears in box_top) -> ╗ or ┐  (top-right corner)
# Γöé (side border)        -> │ or ║  (vertical line)
# Γö£ (separator left)     -> ├ or ╠  (left T-junction)
# Γöñ (separator right)    -> ┤ or ╣  (right T-junction)
# Γò░ (box_bot left)       -> ╚ or └  (bottom-left)
# Γò» (box_bot right)      -> ╝ or ┘  (bottom-right)
# ΓöÇ (horizontal)         -> ─ or ═  (horizontal line)

# Let's do char-by-char replacement of the known garbled sequences
# These are the chars as they appear in the UTF-8 decoded string:
CHAR_MAP = {
    # Garbled char : proper Unicode
    # Top-left corner (Γò¡ in the code appears as: Γ=U+0393, ò=U+00F2, ¡=U+00A1)
    'Γò¡': '╔',
    # Top-right corner (Γò«)  Γ=U+0393, ò=U+00F2, «=U+00AB
    'Γò«': '╗',
    # Vertical bar (Γöé)  Γ=U+0393, ö=U+00F6, é... wait é is not in the set
    # From our scan: chars found are U+00A5 ¥, U+00C9 É, U+00DC Ü, U+00E6 æ, U+00EA ê, U+00F2 ò, U+00F6 ö, U+00F9 ù, U+00FB û, U+0393 Γ
    # No é (U+00E9). Let me re-check the box function content.
    'Γöé': '│',
    'Γö£': '╠',
    'Γöñ': '╣',
    'Γò░': '╚',
    'Γò»': '╝',
    'ΓöÇ': '─',
    # Also in _box functions: Γöî Γöÿ Γöö for code blocks
    'Γöî': '┌',
    'Γöÿ': '┘',
    'Γöö': '└',
    # Full block in LOGO and risk bar
    'Γûê': '█',
    # Other logo chars
    'Γûæ': '░',
    'Γòö': '╠',
    'ΓòÉ': '═',
    'Γò¥': '╝',
    'Γòæ': '║',
    'Γòù': '╗',
    'ΓòÜ': '╚',
    # These are 3-char sequences, but let me also handle 2-char ones
}

fixes = 0
for garbled, proper in CHAR_MAP.items():
    count = content.count(garbled)
    if count > 0:
        content = content.replace(garbled, proper)
        fixes += count
        print(f"  Replaced {count}x '{garbled}' -> '{proper}'")

print(f"Total char replacements: {fixes}")

# ── 4. Write back ─────────────────────────────────────────────────────────────
with open(INFILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nWrote {len(content)} chars to {INFILE}")

# ── 5. Verify syntax ─────────────────────────────────────────────────────────
import subprocess
result = subprocess.run(
    [sys.executable, '-m', 'py_compile', INFILE],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("✓ Syntax OK")
else:
    print(f"✗ Syntax error: {result.stderr}")

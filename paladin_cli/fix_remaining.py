#!/usr/bin/env python3
"""Fix remaining garbled chars in paladin.py"""
import sys, re, subprocess
sys.stdout.reconfigure(encoding='utf-8')

INFILE = r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py'

with open(INFILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Remaining fixes
CHAR_MAP = [
    # In LOGO: Γòù appears after █ chars — it's ╗ (top-right corner)
    # The LOGO has mixed replaced and remaining: ██████Γòù = ██████╗
    ('Γòù',  '╗'),   # U+0393 U+00F2 U+00F9  → top-right double corner
    # Code block: ΓöÉ = ┐ (top-right single corner for code blocks)
    ('ΓöÉ',  '┐'),   
    # Sub-bullet icon
    ('Γùç',  '◦'),   
    # Blockquote bar / vertical bar
    ('ΓûÄ',  '▌'),   
    # User bubble icon (a person icon)
    ('Γû╕',  '◈'),   # or use any icon
    # En dash (0–100)
    ('ΓÇô',  '–'),   
    # Lightning / attack icon
    ('ΓÜí',  '⚡'),  
    # Also fix remaining ù that appears alone (the lone U+00F9)
    # Need to check context first
]

fixes = 0
for garbled, proper in CHAR_MAP:
    count = content.count(garbled)
    if count > 0:
        content = content.replace(garbled, proper)
        fixes += count
        print(f"  {count}x  {garbled!r} → {proper}")

print(f"\nTotal: {fixes}")

# Also fix the remaining lone ù chars that are really part of unmatched sequences
# The ù at U+00F9 alone - check context
lone_u_grave = '\u00F9'
count = content.count(lone_u_grave)
if count > 0:
    print(f"\nLone ù (U+00F9) appears {count} times - checking context...")
    for i, ch in enumerate(content):
        if ch == lone_u_grave:
            ctx_start = max(0, i-30)
            ctx_end = min(len(content), i+30)
            print(f"  pos {i}: {content[ctx_start:ctx_end]!r}")

# Write
with open(INFILE, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"\nWrote {len(content)} chars")

# Syntax check
result = subprocess.run([sys.executable, '-m', 'py_compile', INFILE],
                        capture_output=True, text=True)
if result.returncode == 0:
    print('✓ Syntax OK')
else:
    print(f'✗ Syntax error:\n{result.stderr}')

# Check remaining Γ
remaining_gamma = content.count('\u0393')
print(f"Remaining Γ (U+0393): {remaining_gamma}")

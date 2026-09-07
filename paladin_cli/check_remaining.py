#!/usr/bin/env python3
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all remaining sequences containing Γ (U+0393)
gamma = '\u0393'
positions = [i for i, c in enumerate(content) if c == gamma]

print(f"Remaining Γ (U+0393) occurrences: {len(positions)}")
print()

seen = set()
for pos in positions:
    # Get context: up to 5 chars before and 5 after
    start = max(0, pos-2)
    end = min(len(content), pos+6)
    ctx = content[start:end]
    # Extract the non-ASCII run containing this position
    run_start = pos
    while run_start > 0 and ord(content[run_start-1]) > 127:
        run_start -= 1
    run_end = pos + 1
    while run_end < len(content) and ord(content[run_end]) > 127:
        run_end += 1
    run = content[run_start:run_end]
    
    if run not in seen:
        seen.add(run)
        cps = ' '.join(f'U+{ord(c):04X}({c})' for c in run)
        # Find all occurrences
        count = content.count(run)
        print(f"  {count}x {run!r}: {cps}")
        # Show line context
        line_start = content.rfind('\n', 0, pos) + 1
        line_end = content.find('\n', pos)
        line = content[line_start:line_end][:100]
        print(f"     context: {line!r}")
        print()

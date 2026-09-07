#!/usr/bin/env python3
"""Find all unique non-ASCII char sequences used as box/block chars in paladin.py"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\Vedant Gupta\paladin\paladin_cli\paladin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all runs of non-ASCII chars (these are our garbled sequences)
runs = re.findall(r'[^\x00-\x7E]+', content)
counts = {}
for r in runs:
    counts[r] = counts.get(r, 0) + 1

# Show by frequency
print("Unique non-ASCII runs (sorted by frequency):")
for run, count in sorted(counts.items(), key=lambda x: -x[1])[:40]:
    cps = ' '.join(f'U+{ord(c):04X}' for c in run)
    print(f"  {count:4d}x  {run!r:20s}  codepoints: {cps}")

# Also check box function literals specifically
print()
print("Box function content:")
for func_name in ['_box_top', '_box_row', '_box_sep', '_box_bot', '_box']:
    idx = content.find(f'def {func_name}')
    if idx >= 0:
        snippet = content[idx:idx+400]
        non_ascii = set(c for c in snippet if ord(c) > 127)
        if non_ascii:
            print(f"  {func_name}: {[f'U+{ord(c):04X}({c})' for c in sorted(non_ascii, key=ord)]}")

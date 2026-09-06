#!/usr/bin/env python3
"""
Test script to verify color output on different terminal backgrounds.
"""

import sys
import os

# Add the current directory to path so we can import display
sys.path.insert(0, os.path.dirname(__file__))

from display import test_colors, console

if __name__ == "__main__":
    console.print("=== Paladin CLI Color Test ===")
    console.print()
    test_colors()
    console.print()
    console.print("If the text above is clearly readable, the background fix is working!")
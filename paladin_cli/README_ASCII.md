# Paladin CLI - ASCII Version

This is a Windows PowerShell-compatible version of Paladin CLI that uses only ASCII characters for display, avoiding the Unicode encoding issues that cause garbled display in older terminal environments.

## The Problem

The original `paladin.py` uses Unicode box-drawing characters and special symbols that don't display correctly in Windows PowerShell with certain code page settings, appearing as garbled characters like `Γò¡ΓöÇΓöÇ`.

## The Solution

`paladin_ascii.py` provides the same functionality but with:
- Standard ASCII box-drawing characters (`+`, `-`, `|`)
- ASCII-only logo and symbols
- Better compatibility with Windows PowerShell
- Simplified display that works across different terminal environments

## Usage

### Option 1: Direct Python execution
```powershell
python paladin_ascii.py
```

### Option 2: Batch file (easier)
```powershell
.\paladin_ascii.bat
```

### Option 3: One-shot commands
```powershell
python paladin_ascii.py help
python paladin_ascii.py "analyze this security issue"
```

## Features

✅ **ASCII-safe display** - Works in any Windows terminal
✅ **Same functionality** - All commands from original paladin
✅ **Interactive REPL** - Type commands and prompts directly  
✅ **Color support** - Uses ANSI colors that work in PowerShell
✅ **Proper layout** - Commands display correctly without truncation

## Comparison

| Feature | Original paladin.py | paladin_ascii.py |
|---------|-------------------|------------------|
| Unicode box drawing | ✅ | ❌ (uses ASCII) |
| Windows PowerShell | ❌ (garbled) | ✅ |
| Windows Terminal | ✅ | ✅ |
| Linux/macOS | ✅ | ✅ |
| Functionality | ✅ | ✅ |

## Installation

1. Make sure you have Python installed
2. Install kiro-cli: `kiro login`  
3. Install requirements: `pip install -r requirements.txt`
4. Run: `python paladin_ascii.py`

## Future Improvements

- Detect terminal capabilities and auto-switch between Unicode and ASCII modes
- Add Windows Terminal detection for enhanced display
- Improve ASCII art logo design
- Add more color compatibility options

This ASCII version ensures Paladin CLI works reliably in your Windows PowerShell environment while maintaining all the core functionality.
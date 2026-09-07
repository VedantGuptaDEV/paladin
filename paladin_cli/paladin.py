#!/usr/bin/env python3
"""
paladin — AI security agent for your terminal.
<<<<<<< HEAD
Full-screen TUI: scrollable output + sticky status bar + sticky input.
=======
Interactive REPL that delegates all work to kiro-cli with full tool trust.
>>>>>>> main
"""

import os, sys, shutil, subprocess, json, platform, re, threading
from pathlib import Path
from datetime import datetime

<<<<<<< HEAD
# ── prompt_toolkit (minimal for simple CLI) ──────────────────────────────────
HAS_PT = True  # We don't actually need prompt_toolkit for simple CLI

# ── Rich (for input prompts only) ─────────────────────────────────────────────
try:
    from rich.prompt import Prompt as RPrompt, Confirm as RConfirm
=======
# ── Rich (optional, for richer input prompts) ────────────────────────────────
try:
    from rich.prompt import Prompt as RPrompt
>>>>>>> main
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# ─────────────────────────────────────────────────────────────────────────────
VERSION      = "0.1.0"
CONFIG_DIR   = Path.home() / ".paladin"
CONFIG_FILE  = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history"
SESSION_FILE = CONFIG_DIR / "session.json"
DEFAULTS     = {"model": None, "agent": "paladin"}

<<<<<<< HEAD
=======
# Locate kiro binary — try all known names
>>>>>>> main
KIRO_BIN = (
    shutil.which("kiro-cli-chat")
    or shutil.which("kiro")
    or shutil.which("kiro-cli")
)

<<<<<<< HEAD
=======
# Absolute path to this script's directory — used for --working-dir and agent config
SCRIPT_DIR = Path(__file__).resolve().parent

>>>>>>> main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANSI palette
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<<<<<<< HEAD
R       = "\033[0m"
B       = "\033[1m"
DIM     = "\033[2m"
IT      = "\033[3m"
UL      = "\033[4m"

# foreground
CY      = "\033[38;5;39m"    # bright sky-blue  (like kiro)
CY2     = "\033[38;5;80m"    # lighter cyan accent
GR      = "\033[38;5;78m"    # soft green
YL      = "\033[38;5;221m"   # warm yellow
RD      = "\033[38;5;203m"   # soft red
MA      = "\033[38;5;171m"   # purple/magenta
OR      = "\033[38;5;215m"   # orange
WH      = "\033[38;5;253m"   # off-white
GREY    = "\033[38;5;243m"   # mid grey
LGREY   = "\033[38;5;238m"   # dark grey (for borders)

# background
BG_MAIN = "\033[48;5;234m"   # #1c1c1c — main bg
BG_CARD = "\033[48;5;236m"   # #303030 — card / user bubble bg
BG_CODE = "\033[48;5;235m"   # #262626 — code block bg
BG_STAT = "\033[48;5;232m"   # #080808 — status bar bg

CYB     = f"{B}{CY}"         # bold cyan  (logo / headers)

def _W() -> int:
    """Usable terminal width."""
    try:    return max(60, os.get_terminal_size().columns - 10)  # Leave more margin, minimum 60
    except: return 80

def _box(w: int) -> tuple:
    """Return (top, mid, bot) border strings for a given inner width."""
    return (
        f"{LGREY}╭{'─'*w}╮{R}",
        f"{LGREY}│{R}",
        f"{LGREY}╰{'─'*w}╯{R}",
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Config / session
=======
R     = "\033[0m"
B     = "\033[1m"
DIM   = "\033[2m"
IT    = "\033[3m"
UL    = "\033[4m"

CY    = "\033[38;5;39m"    # bright sky-blue
CY2   = "\033[38;5;80m"    # lighter cyan
GR    = "\033[38;5;78m"    # soft green
YL    = "\033[38;5;221m"   # warm yellow
RD    = "\033[38;5;203m"   # soft red
MA    = "\033[38;5;171m"   # purple/magenta
OR    = "\033[38;5;215m"   # orange
WH    = "\033[38;5;253m"   # off-white
GREY  = "\033[38;5;243m"   # mid grey
LGREY = "\033[38;5;238m"   # dark grey (borders)

BG_CODE = "\033[48;5;235m"  # code block bg

CYB   = f"{B}{CY}"

def _W() -> int:
    try:    return max(60, os.get_terminal_size().columns - 4)
    except: return 80

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Config / session helpers
>>>>>>> main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _mkdirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_config() -> dict:
    if not CONFIG_FILE.exists(): return dict(DEFAULTS)
    try:
        with open(CONFIG_FILE) as f: return {**DEFAULTS, **json.load(f)}
    except Exception: return dict(DEFAULTS)

def save_config(cfg: dict):
    _mkdirs()
    with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=2)

def load_session() -> dict:
    if not SESSION_FILE.exists(): return {}
    try:
        with open(SESSION_FILE) as f: return json.load(f)
    except Exception: return {}

def save_session(data: dict):
    _mkdirs()
    with open(SESSION_FILE, "w") as f: json.dump(data, f, indent=2)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<<<<<<< HEAD
# Output buffer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_lines: list[str] = []
_app = None
_scroll_pos = 0        # current top-of-viewport line index
_user_scrolled = False # True when user has manually scrolled up

def _total_lines() -> int:
    return len(_lines)

def _push(*ls: str):
    global _scroll_pos, _user_scrolled
    for l in ls:
        _lines.append(l)
    if not _user_scrolled:
        # auto-follow: keep scroll at the very bottom
        _scroll_pos = max(0, len(_lines) - 1) if _lines else 0
    # Ensure scroll position is always valid
    if _lines:
        _scroll_pos = min(_scroll_pos, len(_lines) - 1)
    else:
        _scroll_pos = 0
    if _app and _app.is_running:
        _app.invalidate()

def _nl(): _push("")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Markdown-lite streaming renderer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_in_code  = False
_code_buf: list[str] = []

def _inline(t: str) -> str:
    t = re.sub(r"`([^`]+)`",     lambda m: f"{BG_CODE}{YL} {m.group(1)} {R}", t)
    t = re.sub(r"\*\*(.+?)\*\*", lambda m: f"{B}{WH}{m.group(1)}{R}",         t)
    t = re.sub(r"\*(.+?)\*",     lambda m: f"{IT}{GREY}{m.group(1)}{R}",       t)
    t = re.sub(r"__(.*?)__",     lambda m: f"{UL}{m.group(1)}{R}",             t)
    return t

def _render_line(raw: str) -> list[str]:
    """Return 0-N styled lines for one raw output line."""
    global _in_code, _code_buf
    line = raw.rstrip("\n")

    # ── fenced code block ─────────────────────────────────────────────────────
    if line.startswith("```"):
        if not _in_code:
            _in_code = True
            lang = line[3:].strip() or "text"
            w = min(_W() - 10, 50)  # Reduced width for safety
            return [f"   {BG_CODE}{LGREY}┌── {CY2}{lang}{LGREY} {'─'*(w - len(lang) - 4)}┐{R}"]
        else:
            _in_code = False
            w = min(_W() - 10, 50)  # Reduced width for safety
            return [f"   {BG_CODE}{LGREY}└{'─'*w}┘{R}", ""]
    if _in_code:
        w = min(_W() - 10, 50)  # Reduced width for safety
        padded = line.ljust(w)
        return [f"   {BG_CODE}{GR}{padded}{R}"]

    if not line.strip():
        return [""]

    # ── headings ──────────────────────────────────────────────────────────────
    m = re.match(r"^(#{1,3}) (.*)", line)
    if m:
        lvl, txt = len(m.group(1)), m.group(2)
        if lvl == 1:
            w = min(_W() - 8, 50)  # Reduced width for safety
            return ["", f"  {CYB}{txt}{R}", f"  {CY}{'═'*min(len(txt)+2,w)}{R}", ""]
        elif lvl == 2:
            return ["", f"  {B}{WH}{txt}{R}", f"  {LGREY}{'─'*min(len(txt)+2,40)}{R}", ""]  # Reduced from 60 to 40
        else:
            return [f"  {B}{GREY}{txt}{R}"]

    # ── horizontal rule ───────────────────────────────────────────────────────
    if re.match(r"^[-*_]{3,}$", line.strip()):
        return [f"  {LGREY}{'─'*min(_W()-4,70)}{R}"]

    # ── bullet list ───────────────────────────────────────────────────────────
    m = re.match(r"^(\s*)([-*•]) (.*)", line)
    if m:
        depth  = len(m.group(1)) // 2
        indent = "    " * depth
        icons  = [f"{CY}◆{R}", f"{CY2}◇{R}", f"{GREY}·{R}"]
        icon   = icons[min(depth, 2)]
        return [f"  {indent}{icon} {_inline(m.group(3))}"]

    # ── numbered list ─────────────────────────────────────────────────────────
    m = re.match(r"^(\s*)(\d+)\. (.*)", line)
    if m:
        depth  = len(m.group(1)) // 2
        indent = "    " * depth
        return [f"  {indent}{CY}{m.group(2)}.{R} {_inline(m.group(3))}"]

    # ── blockquote ────────────────────────────────────────────────────────────
    if line.startswith(">"):
        return [f"  {CY}▎{R}{IT}{GREY} {line[1:].strip()}{R}"]

    # ── table row (simple) ───────────────────────────────────────────────────
    if line.startswith("|") and line.endswith("|"):
        cells = [c.strip() for c in line.strip("|").split("|")]
        parts = [f"  {LGREY}│{R}"]
        for c in cells:
            if re.match(r"^[-: ]+$", c):
                parts.append(f" {LGREY}{'─'*max(len(c),3)}{R} {LGREY}│{R}")
            else:
                parts.append(f" {_inline(c)} {LGREY}│{R}")
        return ["".join(parts)]

    return [f"  {_inline(line)}"]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bubbles & chrome
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# consistent bg for the whole content area
BG  = "\033[48;5;234m"    # #1c1c1c  — main dark bg
BGC = "\033[48;5;236m"    # #303030  — slightly lighter for user bubble

=======
# Box / rendering helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

>>>>>>> main
def _ansi_len(s: str) -> int:
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))

def _center(text: str, width: int) -> str:
    vlen = _ansi_len(text)
    pad  = max(0, width - vlen)
    return " " * (pad // 2) + text + " " * (pad - pad // 2)

<<<<<<< HEAD
def _box_top(inner_w: int, title: str = "") -> str:
    if title:
        tlen  = _ansi_len(title)
        left  = (inner_w - tlen) // 2
        right = inner_w - tlen - left
        return f"{BG}{LGREY}╭{'─'*left}{title}{'─'*right}╮{R}"
    return f"{BG}{LGREY}╭{'─'*inner_w}╮{R}"

def _box_row(content: str, inner_w: int, bg: str = "") -> str:
    used_bg = bg or BG
    vlen = _ansi_len(content)
    pad  = max(0, inner_w - vlen - 2)   # -2 for the 1-space padding each side
    return f"{used_bg}{LGREY}│{R}{used_bg} {content}{' '*pad} {LGREY}│{R}"

def _box_sep(inner_w: int) -> str:
    return f"{BG}{LGREY}├{'─'*inner_w}┤{R}"

def _box_bot(inner_w: int) -> str:
    return f"{BG}{LGREY}╰{'─'*inner_w}╯{R}"

def _wrap_text(text: str, width: int) -> list[str]:
=======
def _wrap_text(text: str, width: int) -> list:
>>>>>>> main
    import textwrap
    raw = re.sub(r"\x1b\[[0-9;]*m", "", text)
    if len(raw) <= width: return [text]
    return textwrap.wrap(raw, width) or [raw]

<<<<<<< HEAD

def _push_user_bubble(text: str):
    tw    = _W()
    inner = tw - 2          # box inner width  (tw = │ + inner + │)
    ts    = datetime.now().strftime("%H:%M")

    _nl()
    _push(_box_top(inner, title=f"{BG}{GR} ▸ you {R}{BG}{LGREY}"))
    for part in text.splitlines():
        for chunk in _wrap_text(part, inner - 4):
            _push(_box_row(f"{WH}{chunk}{R}", inner, bg=BGC))
    # timestamp right-aligned on its own row
    ts_str  = f"{LGREY}{ts}{R}"
    ts_rpad = inner - _ansi_len(ts_str) - 2
    _push(_box_row(f"{' '*ts_rpad}{ts_str}", inner, bg=BGC))
    _push(_box_bot(inner))
    _nl()


def _push_agent_header(label: str):
    tw    = _W()
    inner = tw - 2
    ts    = datetime.now().strftime("%H:%M:%S")
    sid   = load_session().get("id", "")
    tag   = f"  {LGREY}#{sid[-5:]}{R}" if sid else ""
    title = f"{BG}{CYB} ⬡ paladin {R}{BG}{LGREY}"
    _nl()
    _push(_box_top(inner, title=title))
    sub   = f"{DIM}{label}{R}{tag}  {LGREY}{ts}{R}"
    _push(_box_row(_center(sub, inner - 2), inner))


def _push_agent_footer(elapsed: float):
    tw    = _W()
    inner = tw - 2
    foot  = f"{DIM}⏱  {elapsed:.1f}s{R}"
    _push(_box_row(foot, inner))
    _push(_box_bot(inner))
    _nl()


def push_ok(m):
    tw = _W(); inner = tw - 2
    _push(_box_row(f"{GR}✓{R}  {WH}{m}{R}", inner))

def push_err(m):
    tw = _W(); inner = tw - 2
    _push(_box_row(f"{RD}✗{R}  {WH}{m}{R}", inner))
    _push(_box_bot(inner)); _nl()

def push_warn(m):
    tw = _W(); inner = tw - 2
    _push(_box_row(f"{YL}◆{R}  {WH}{m}{R}", inner))

def push_info(m):
    tw = _W(); inner = tw - 2
    _push(_box_row(f"{CY2}›{R}  {GREY}{m}{R}", inner))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Kiro bridge
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ask_and_render(prompt: str, label: str = "response", model: str = None):
    global _in_code
    _in_code = False

    if not KIRO_BIN:
        push_err("kiro CLI not found. Install from https://kiro.ai"); return

    _push_agent_header(label)
    cmd = [KIRO_BIN, "chat", "--no-interactive", prompt]
    if model: cmd += ["--model", model]
=======
def _box_top(inner: int, title: str = "") -> str:
    if title:
        tlen  = _ansi_len(title)
        left  = max(1, (inner - tlen) // 2)
        right = max(1, inner - tlen - left)
        return f"{LGREY}╭{'─'*left}{title}{LGREY}{'─'*right}╮{R}"
    return f"{LGREY}╭{'─'*inner}╮{R}"

def _box_row(content: str, inner: int) -> str:
    pad = max(0, inner - _ansi_len(content) - 2)
    return f"{LGREY}│{R} {content}{' '*pad} {LGREY}│{R}"

def _box_sep(inner: int) -> str:
    return f"{LGREY}├{'─'*inner}┤{R}"

def _box_bot(inner: int) -> str:
    return f"{LGREY}╰{'─'*inner}╯{R}"

def _print_box(title: str, lines: list, title_color: str = None):
    """Print a titled info box to stdout."""
    inner = _W() - 2
    tc    = title_color or CYB
    print(_box_top(inner, title=f" {tc}{title}{R} "))
    for line in lines:
        print(_box_row(line, inner))
    print(_box_bot(inner))

def _ok(msg: str):   print(f"  {GR}✓{R}  {WH}{msg}{R}")
def _err(msg: str):  print(f"  {RD}✗{R}  {WH}{msg}{R}")
def _warn(msg: str): print(f"  {YL}◆{R}  {WH}{msg}{R}")
def _info(msg: str): print(f"  {CY2}›{R}  {GREY}{msg}{R}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Markdown-lite renderer (for streaming kiro output)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_in_code = False

def _inline(t: str) -> str:
    t = re.sub(r"`([^`]+)`",      lambda m: f"{BG_CODE}{YL} {m.group(1)} {R}", t)
    t = re.sub(r"\*\*(.+?)\*\*",  lambda m: f"{B}{WH}{m.group(1)}{R}",         t)
    t = re.sub(r"\*(.+?)\*",      lambda m: f"{IT}{GREY}{m.group(1)}{R}",       t)
    t = re.sub(r"__(.*?)__",      lambda m: f"{UL}{m.group(1)}{R}",             t)
    return t

def _render_and_print(raw: str, inner: int = 0):
    """
    Render one line of kiro output with light markdown styling.
    If inner > 0, wrap the line inside box borders.
    """
    global _in_code
    line = raw.rstrip("\n")
    w    = inner or (_W() - 2)

    def emit(text: str):
        if inner:
            print(_box_row(text, inner))
        else:
            print(text)

    # fenced code block
    if line.startswith("```"):
        if not _in_code:
            _in_code = True
            lang = line[3:].strip() or "text"
            emit(f"  {BG_CODE}{LGREY}┌── {CY2}{lang}{LGREY}{'─'*max(1,36-len(lang))}┐{R}")
        else:
            _in_code = False
            emit(f"  {BG_CODE}{LGREY}└{'─'*38}┘{R}")
        return
    if _in_code:
        emit(f"  {BG_CODE}{GR}{line}{R}")
        return
    if not line.strip():
        emit("")
        return

    # headings
    m = re.match(r"^(#{1,3}) (.*)", line)
    if m:
        lvl, txt = len(m.group(1)), m.group(2)
        if lvl == 1:
            emit(f"")
            emit(f"  {CYB}{txt}{R}")
            emit(f"  {CY}{'═'*min(len(txt)+2,50)}{R}")
            emit(f"")
        elif lvl == 2:
            emit(f"")
            emit(f"  {B}{WH}{txt}{R}")
            emit(f"  {LGREY}{'─'*min(len(txt)+2,40)}{R}")
        else:
            emit(f"  {B}{GREY}{txt}{R}")
        return

    # horizontal rule
    if re.match(r"^[-*_]{3,}$", line.strip()):
        emit(f"  {LGREY}{'─'*min(w-4,60)}{R}")
        return

    # bullet
    m = re.match(r"^(\s*)([-*•]) (.*)", line)
    if m:
        depth  = len(m.group(1)) // 2
        indent = "    " * depth
        icons  = [f"{CY}◆{R}", f"{CY2}◇{R}", f"{GREY}·{R}"]
        emit(f"  {indent}{icons[min(depth,2)]} {_inline(m.group(3))}")
        return

    # numbered list
    m = re.match(r"^(\s*)(\d+)\. (.*)", line)
    if m:
        depth  = len(m.group(1)) // 2
        indent = "    " * depth
        emit(f"  {indent}{CY}{m.group(2)}.{R} {_inline(m.group(3))}")
        return

    # blockquote
    if line.startswith(">"):
        emit(f"  {CY}▎{R}{IT}{GREY} {line[1:].strip()}{R}")
        return

    # table
    if line.startswith("|") and line.endswith("|"):
        cells = [c.strip() for c in line.strip("|").split("|")]
        row   = f"  {LGREY}│{R}"
        for c in cells:
            if re.match(r"^[-: ]+$", c):
                row += f" {LGREY}{'─'*max(len(c),3)}{R} {LGREY}│{R}"
            else:
                row += f" {_inline(c)} {LGREY}│{R}"
        emit(row)
        return

    emit(f"  {_inline(line)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Kiro bridge — the core
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ask_kiro(prompt: str, label: str = "kiro", model: str = None,
             cwd: str = None, trust: bool = True):
    """
    Print a 'you' bubble, send prompt to kiro-cli, stream response inside a
    matching '⬡ paladin' box so everything looks consistent.
    """
    global _in_code
    _in_code = False

    inner = _W() - 2
    ts    = datetime.now().strftime("%H:%M")

    # ── user bubble ──────────────────────────────────────────────────────────
    print()
    print(_box_top(inner, title=f" {GR}▸ you{R} "))
    import textwrap as _tw
    for part in prompt.splitlines():
        for chunk in (_tw.wrap(part, inner - 4) or [part]):
            print(_box_row(f"{WH}{chunk}{R}", inner))
    ts_pad = inner - len(ts) - 2
    print(_box_row(f"{' '*ts_pad}{LGREY}{ts}{R}", inner))
    print(_box_bot(inner))

    if not KIRO_BIN:
        print()
        print(_box_top(inner, title=f" {CYB}⬡ paladin{R} "))
        print(_box_row(f"{RD}✗{R}  kiro-cli not found — install from https://kiro.ai", inner))
        print(_box_bot(inner))
        print()
        return

    # ── paladin response box: open it, stream inside, close it ───────────────
    work_dir = cwd or str(Path.cwd())
    ts2      = datetime.now().strftime("%H:%M:%S")
    sess_id  = load_session().get("id", "")
    tag      = f"  {LGREY}#{sess_id[-5:]}{R}" if sess_id else ""
    sub      = f"{DIM}{label}{R}{tag}  {LGREY}{ts2}{R}"

    print()
    print(_box_top(inner, title=f" {CYB}⬡ paladin{R} "))
    print(_box_row(_center(sub, inner - 2), inner))
    print(_box_sep(inner))

    cmd = [KIRO_BIN, "chat", "--no-interactive", "--agent", "paladin", prompt]
    if trust:
        cmd.append("--trust-all-tools")
    if model:
        cmd += ["--model", model]
>>>>>>> main

    start = datetime.now().timestamp()
    got   = False

    try:
<<<<<<< HEAD
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        for raw in proc.stdout:
            got = True
            for styled in _render_line(raw):
                _push(styled)
        proc.wait()
    except KeyboardInterrupt:
        _push(f"  {DIM}interrupted{R}"); return
    except Exception as e:
        push_err(str(e)); return

    if not got:
        push_warn("No response."); return

    _push_agent_footer(datetime.now().timestamp() - start)
=======
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=work_dir,
        )
        for raw in proc.stdout:
            got = True
            _render_and_print(raw, inner)
        proc.wait()
        if proc.returncode not in (0, None) and not got:
            print(_box_row(f"{YL}◆{R}  kiro exited with code {proc.returncode}", inner))
    except KeyboardInterrupt:
        print(_box_row(f"{DIM}interrupted{R}", inner))
        print(_box_bot(inner))
        print()
        return
    except Exception as e:
        print(_box_row(f"{RD}✗{R}  {e}", inner))
        print(_box_bot(inner))
        print()
        return

    if not got:
        print(_box_row(f"{YL}◆{R}  No response received from kiro.", inner))

    elapsed = datetime.now().timestamp() - start
    print()
    print(_box_row(f"{DIM}⏱  {elapsed:.1f}s{R}", inner))
    print(_box_bot(inner))
    print()
>>>>>>> main

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Banner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOGO = [
    " ██████╗  █████╗ ██╗      █████╗ ██████╗ ██╗███╗   ██╗",
    " ██╔══██╗██╔══██╗██║     ██╔══██╗██╔══██╗██║████╗  ██║",
    " ██████╔╝███████║██║     ███████║██║  ██║██║██╔██╗ ██║",
    " ██╔═══╝ ██╔══██║██║     ██╔══██║██║  ██║██║██║╚██╗██║",
    " ██║     ██║  ██║███████╗██║  ██║██████╔╝██║██║ ╚████║",
    " ╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝",
]

<<<<<<< HEAD
# ── box / centering helpers ────────────────────────────────────────────────────
# Pure black bg (#0a0a0a) fills every line edge-to-edge so nothing bleeds.

BG  = "\033[48;2;10;10;10m"     # #0a0a0a  true black for all content
BGU = "\033[48;2;24;24;32m"     # #181820  slightly blue-tinted for user bubble
BDR = "\033[38;2;64;72;88m"     # #404858  border/dim colour (higher contrast)
# Override the earlier LGREY for borders so they're visible on black
_BDRC = "\033[38;2;64;72;88m"

def _ansi_len(s: str) -> int:
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))

def _center(text: str, width: int) -> str:
    vlen = _ansi_len(text)
    pad  = max(0, width - vlen)
    return " " * (pad // 2) + text + " " * (pad - pad // 2)

def _fill(bg: str, width: int) -> str:
    """A fully bg-painted blank line of exactly `width` visible chars."""
    return f"{bg}{' ' * width}\033[0m"

def _box_top(inner_w: int, title: str = "", bg: str = "") -> str:
    """Full-width top border. inner_w = terminal_width - 2 (for the two │)."""
    _bg = bg or BG
    if title:
        tlen  = _ansi_len(title)
        left  = (inner_w - tlen) // 2
        right = inner_w - tlen - left
        return f"{_bg}{_BDRC}╭{'─'*left}{title}{_bg}{_BDRC}{'─'*right}╮\033[0m"
    return f"{_bg}{_BDRC}╭{'─'*inner_w}╮\033[0m"

def _box_row(content: str, inner_w: int, bg: str = "") -> str:
    """
    One content row — full terminal line painted with bg, no bleed.
    Layout:  bg │ bg <space> content <padding> <space> bg │ reset
    """
    _bg  = bg or BG
    used = _ansi_len(content) + 2          # 1 space each side
    pad  = max(0, inner_w - used)
    # re-apply _bg before the trailing padding and before the right border
    return (f"{_bg}{_BDRC}│{_bg} {content}"
            f"{_bg}{' '*pad} {_BDRC}│\033[0m")

def _box_sep(inner_w: int, bg: str = "") -> str:
    _bg = bg or BG
    return f"{_bg}{_BDRC}├{'─'*inner_w}┤\033[0m"

def _box_bot(inner_w: int, bg: str = "") -> str:
    _bg = bg or BG
    return f"{_bg}{_BDRC}╰{'─'*inner_w}╯\033[0m"

def _wrap_text(text: str, width: int) -> list:
    import textwrap as _tw
    raw = re.sub(r"\x1b\[[0-9;]*m", "", text)
    if len(raw) <= width: return [text]
    return _tw.wrap(raw, width) or [raw]


def _push_banner_lines():
    tw    = _W()
    inner = tw - 2        # box interior  (╭─ INNER ─╮, │ costs 1 each side)

    session = load_session()
    sid  = session.get("id", "")
    proj = session.get("project", "")
    stat = session.get("status", "idle")

    kiro_text = (f"{GR}⬤  kiro connected{R}" if KIRO_BIN
                 else f"{RD}○  kiro not found{R}  {LGREY}→ https://kiro.ai{R}")
    sc = {"running": GR, "paused": YL, "failed": RD, "idle": LGREY}.get(stat, LGREY)
    sess_text = (f"{LGREY}session  {R}{CYB}{sid}{R}  {LGREY}{proj}  {R}{sc}● {stat}{R}"
                 if sid else f"{LGREY}no session  ·  type {R}{CY}start{R}{LGREY} to begin{R}")

    cmds = [
        (f"{CY}init{R}",       "Init project"),
        (f"{CY}start{R}",      "New session"),
        (f"{CY}status{R}",     "Session status"),
        (f"{CY}run{R}",        "Run a task"),
        (f"{CY}approvals{R}",  "Pending approvals"),
        (f"{CY}approve{R}",    "Approve action"),
        (f"{CY}deny{R}",       "Deny action"),
        (f"{CY}activity{R}",   "Activity log"),
        (f"{CY}policy{R}",     "Manage policies"),
        (f"{CY}config{R}",     "Configuration"),
        (f"{CY}doctor{R}",     "Health check"),
        (f"{CY}version{R}",    "Version info"),
    ]
    shortcuts = f"{DIM}/help  ·  /clear  ·  /session  ·  /model <name>  ·  Ctrl-C exits{R}"

    _nl()
    _push(_box_top(inner, title=f"{BG}{CY} ⬡ paladin {R}{BG}{LGREY}"))
    _push(_box_row("", inner))

    for ll in LOGO:
        _push(_box_row(_center(f"{CY}{ll}{R}", inner - 2), inner))
    tagline = f"{DIM}AI Security Agent  ·  v{VERSION}  ·  powered by kiro{R}"
    _push(_box_row(_center(tagline, inner - 2), inner))

    _push(_box_row("", inner))
    _push(_box_sep(inner))
    _push(_box_row("", inner))

    _push(_box_row(_center(kiro_text, inner - 2), inner))
    _push(_box_row(_center(sess_text, inner - 2), inner))

    _push(_box_row("", inner))
    _push(_box_sep(inner))
    _push(_box_row("", inner))

    col_w = (inner - 2) // 3
    for i in range(0, len(cmds), 3):
        row_cmds = cmds[i:i+3]
        parts = []
        for cmd_str, desc in row_cmds:
            cell = f"{cmd_str}  {LGREY}{desc}{R}"
            pad  = max(0, col_w - _ansi_len(cell))
            parts.append(cell + " " * pad)
        row_str = "  ".join(parts).rstrip()
        _push(_box_row(_center(row_str, inner - 2), inner))

    _push(_box_row("", inner))
    _push(_box_sep(inner))
    _push(_box_row("", inner))

    _push(_box_row(_center(shortcuts, inner - 2), inner))
    _push(_box_row("", inner))
    _push(_box_bot(inner))
    _nl()


def _push_help():
    tw    = _W()
    inner = tw - 2
    sections = [
        ("Session", [
            ("init",             "Initialise paladin in current project"),
            ("start",            "Start a new agent session"),
            ("status",           "Show session status"),
            ("run [task]",       "Run the agent on a task"),
        ]),
        ("Approvals", [
            ("approvals",        "List all pending approvals"),
            ("approve <id>",     "Approve an action by ID"),
            ("deny <id>",        "Deny an action by ID"),
        ]),
        ("Activity", [
            ("activity",         "Show activity log for current session"),
            ("activity <id>",    "Show activity log for specific session"),
        ]),
        ("Policy", [
            ("policy list",      "List all security policies"),
            ("policy add",       "Add a new policy interactively"),
            ("policy test",      "Test a prompt against policies"),
        ]),
        ("Tools", [
            ("config",           "Show / edit configuration"),
            ("doctor",           "Environment health check"),
            ("version",          "Show version info"),
        ]),
        ("REPL", [
            ("/help",            "Show this help"),
            ("/clear",           "Clear screen and redraw banner"),
            ("/session",         "Show current session details"),
            ("/model <name>",    "Switch model for this session"),
            ("Ctrl-C / Ctrl-D",  "Exit paladin"),
        ]),
    ]
    _nl()
    _push(_box_top(inner, title=f"{BG}{CYB} paladin commands {R}{BG}{LGREY}"))
    _push(_box_row("", inner))
    for group, items in sections:
        _push(_box_row(f"  {B}{GREY}{group}{R}", inner))
        for cmd, desc in items:
            pad = max(1, 24 - _ansi_len(cmd))
            _push(_box_row(f"    {CY}{cmd}{R}{' '*pad}{GREY}{desc}{R}", inner))
        _push(_box_row("", inner))
    _push(_box_bot(inner))
    _nl()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Slash commands
=======
def print_banner():
    inner = _W() - 2
    sess  = load_session()
    sid   = sess.get("id", "")
    stat  = sess.get("status", "idle")
    proj  = sess.get("project", "")

    kiro_str = (f"{GR}⬤  kiro connected{R}" if KIRO_BIN
                else f"{RD}○  kiro not found{R}  {LGREY}→ https://kiro.ai{R}")
    sc       = {"running": GR, "paused": YL, "failed": RD, "idle": LGREY}.get(stat, LGREY)
    sess_str = (f"{LGREY}session  {R}{CYB}{sid}{R}  {LGREY}{proj}  {R}{sc}● {stat}{R}"
                if sid else f"{LGREY}no session  ·  type {R}{CY}start{R}{LGREY} to begin{R}")
    shortcuts = f"{DIM}/help · /clear · /session · /model <name> · exit{R}"

    print()
    print(_box_top(inner, title=f" {CYB}⬡ paladin{R} "))
    for ll in LOGO:
        print(_box_row(_center(f"{CY}{ll}{R}", inner - 2), inner))
    print(_box_row(_center(f"{DIM}AI Security Agent · v{VERSION} · powered by kiro{R}", inner - 2), inner))
    print(_box_sep(inner))
    print(_box_row(_center(kiro_str,  inner - 2), inner))
    print(_box_row(_center(sess_str,  inner - 2), inner))
    print(_box_sep(inner))
    print(_box_row(_center(shortcuts, inner - 2), inner))
    print(_box_bot(inner))
    print()


def print_help():
    sections = [
        ("Session", [
            ("init",           "Initialise paladin in current project"),
            ("start",          "Start a new agent session"),
            ("status",         "Show session status"),
            ("run [task]",     "Run any task via kiro (with full tool access)"),
        ]),
        ("Approvals", [
            ("approvals",      "List pending approvals"),
            ("approve <id>",   "Approve an action"),
            ("deny <id>",      "Deny an action"),
        ]),
        ("Activity & Policy", [
            ("activity [id]",  "Show activity log"),
            ("policy list",    "List security policies"),
            ("policy add",     "Add a policy interactively"),
            ("policy test",    "Test a prompt against policies"),
        ]),
        ("Utilities", [
            ("config",         "Show / edit config"),
            ("doctor",         "Health check"),
            ("version",        "Version info"),
        ]),
        ("REPL shortcuts", [
            ("/help",          "Show this help"),
            ("/clear",         "Clear screen"),
            ("/session",       "Show session details"),
            ("/model <name>",  "Switch model"),
            ("exit / Ctrl-C",  "Quit"),
        ]),
    ]
    print()
    for group, items in sections:
        print(f"  {B}{GREY}{group}{R}")
        for cmd, desc in items:
            pad = max(1, 22 - len(cmd))
            print(f"    {CY}{cmd}{R}{' '*pad}{GREY}{desc}{R}")
        print()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _ask_input(label: str, choices: list = None, default: str = "") -> str:
    sfx = f" [{'/'.join(choices)}]" if choices else (f" [{default}]" if default else "")
    try:
        raw = input(f"\n  {label}{sfx}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return raw or default


def cmd_init(model: str = None):
    cwd    = Path.cwd()
    marker = cwd / ".paladin"
    if marker.exists():
        _warn(".paladin already exists — re-initializing.")
    marker.write_text(json.dumps({
        "initialized_at": datetime.now().isoformat(),
        "project": cwd.name,
    }, indent=2))
    _ok(f"Initialized paladin in {cwd}")
    ask_kiro(
        f"I have initialized the Paladin AI security agent in the project at: {cwd}. "
        "The project is called '{cwd.name}'. Briefly acknowledge and list what you can "
        "monitor and protect in this project.",
        label="init", model=model, cwd=str(cwd),
    )


def cmd_start(model: str = None):
    sid = f"SES-{int(datetime.now().timestamp())}"
    save_session({
        "id": sid,
        "started_at": datetime.now().isoformat(),
        "status": "running",
        "project": Path.cwd().name,
    })
    _ok(f"Session {CYB}{sid}{R} started")
    ask_kiro(
        f"A new Paladin security session has started. Session ID: {sid}. "
        "Project: {Path.cwd().name}. Greet the user and ask what they want to work on.",
        label="start", model=model,
    )


def cmd_status(model: str = None):
    sess = load_session()
    if not sess:
        _warn("No active session. Run: start")
        return
    print()
    _print_box("Session Status", [
        f"{GREY}{'id':<16}{R}{CY2}{sess.get('id','')}{R}",
        f"{GREY}{'project':<16}{R}{CY2}{sess.get('project','')}{R}",
        f"{GREY}{'started':<16}{R}{CY2}{sess.get('started_at','')}{R}",
        f"{GREY}{'status':<16}{R}{GR}{sess.get('status','')}{R}",
    ])
    ask_kiro(
        f"Summarize this Paladin session: {json.dumps(sess)}. "
        "What is happening, are there any pending actions or risks?",
        label="status", model=model,
    )


def cmd_run(task: str = None, model: str = None):
    if not task:
        task = _ask_input("Task to run")
    if not task:
        _err("No task provided.")
        return
    sess = load_session()
    ctx  = f"\n\nCurrent session: {json.dumps(sess)}" if sess else ""
    # Pass the task directly — no wrapper verbiage so kiro treats it as a real task
    ask_kiro(task + ctx, label="run", model=model, trust=True)


def cmd_approvals(model: str = None):
    ask_kiro(
        "List all pending Paladin approval requests. "
        "For each: ID, tool name, risk level (low/medium/high/critical), and a brief description.",
        label="approvals", model=model,
    )


def cmd_approve(aid: str, msg: str = None, model: str = None):
    note = f" Additional note: {msg}" if msg else ""
    ask_kiro(
        f"Approve Paladin action ID: {aid}.{note} Confirm the approval and proceed with execution.",
        label=f"approve {aid}", model=model,
    )


def cmd_deny(aid: str, msg: str = None, model: str = None):
    note = f" Reason: {msg}" if msg else ""
    ask_kiro(
        f"Deny Paladin action ID: {aid}.{note} Confirm the denial and explain why.",
        label=f"deny {aid}", model=model,
    )


def cmd_activity(sid: str = None, model: str = None):
    if sid:
        ask_kiro(
            f"Show the full activity log for Paladin session {sid}. "
            "Include all tool calls, agent messages, shield decisions, and user approvals in order.",
            label=f"activity {sid}", model=model,
        )
    else:
        ask_kiro(
            "Show the activity log for the current Paladin session. "
            "Include tool calls, agent messages, shield decisions, and user approvals.",
            label="activity", model=model,
        )


def cmd_policy_list(model: str = None):
    ask_kiro(
        "List all Paladin security policies. For each: name, action (allow/ask/block), "
        "risk threshold, enabled status, and description.",
        label="policy list", model=model,
    )


def cmd_policy_add(model: str = None):
    name    = _ask_input("Policy name")
    desc    = _ask_input("Description")
    action  = _ask_input("Action", choices=["allow", "ask", "block"], default="ask")
    thresh  = _ask_input("Risk threshold (0–100)", default="50")
    pattern = _ask_input("Match pattern (optional, press Enter to skip)")
    pol: dict = {
        "name": name,
        "description": desc,
        "action": action,
        "threshold": int(thresh or 50),
        "enabled": True,
    }
    if pattern:
        pol["match_patterns"] = [pattern]
    ask_kiro(
        f"Add this Paladin security policy: {json.dumps(pol)}. "
        "Confirm it has been added and explain when it will trigger.",
        label="policy add", model=model,
    )


def cmd_policy_test(model: str = None):
    ti = _ask_input("Prompt or tool call to test")
    if not ti:
        _err("Nothing to test.")
        return
    ask_kiro(
        f'Test the following against all Paladin security policies: "{ti}". '
        "Show which policies match, the final decision, risk score, and reasoning.",
        label="policy test", model=model,
    )


def cmd_config():
    cfg = load_config()
    print()
    _print_box("Config", [
        f"{GREY}{'file':<16}{R}{DIM}{CONFIG_FILE}{R}",
        *[
            f"{GREY}{k:<16}{R}{CY2}{v}{R}" if v is not None
            else f"{GREY}{k:<16}{R}{LGREY}not set{R}"
            for k, v in cfg.items()
        ],
    ])
    try:
        edit = input("  Edit a value? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if edit == "y":
        key = _ask_input("Key")
        val = _ask_input(f"Value for {key}")
        cfg[key] = val
        save_config(cfg)
        _ok(f"{key} = {val}")


def cmd_doctor():
    checks = [
        ("kiro-cli",       bool(KIRO_BIN),              KIRO_BIN or "not found — https://kiro.ai"),
        ("python",         sys.version_info >= (3, 9),  platform.python_version()),
        ("rich",           HAS_RICH,                    "ok" if HAS_RICH else "pip install rich"),
        ("config dir",     CONFIG_DIR.exists(),          str(CONFIG_DIR)),
        (".paladin marker",(Path.cwd() / ".paladin").exists(),
                           "found" if (Path.cwd() / ".paladin").exists() else "run: init"),
        ("agent config",   (SCRIPT_DIR / ".kiro" / "agents" / "paladin.json").exists(),
                           "found" if (SCRIPT_DIR / ".kiro" / "agents" / "paladin.json").exists()
                           else "missing — hooks not active"),
    ]
    print()
    _print_box("paladin doctor", [
        f"{'  ' if good else '  '}{GR if good else YL}{'✓' if good else '◆'}{R}  "
        f"{B}{name:<20}{R}{GREY}{detail}{R}"
        for name, good, detail in checks
    ])


def cmd_version():
    print()
    _print_box("paladin version", [
        f"{GREY}{'version':<16}{R}{CYB}v{VERSION}{R}",
        f"{GREY}{'python':<16}{R}{CY2}{platform.python_version()}{R}",
        f"{GREY}{'platform':<16}{R}{CY2}{platform.system()} {platform.release()}{R}",
        f"{GREY}{'kiro':<16}{R}{(GR + KIRO_BIN + R) if KIRO_BIN else (RD + 'not found' + R)}",
    ])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REPL slash commands
>>>>>>> main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _handle_slash(line: str, model_ref: list):
    parts = line.strip().split()
    cmd   = parts[0].lower()

    if cmd in ("/exit", "/quit", "/q"):
<<<<<<< HEAD
        if _app and _app.is_running: _app.exit()

    elif cmd == "/help":
        _push_help()

    elif cmd == "/clear":
        _lines.clear(); _push_banner_lines()

    elif cmd == "/session":
        s = load_session()
        if not s: push_warn("No active session."); return
        _nl()
        _push(f"  {CYB}Session{R}")
        for k, v in s.items():
            _push(f"  {GREY}{k:<18}{R}{CY2}{v}{R}")
        _nl()
=======
        raise SystemExit(0)

    elif cmd == "/help":
        print_help()

    elif cmd == "/clear":
        os.system("clear")
        print_banner()

    elif cmd == "/session":
        s = load_session()
        if not s:
            _warn("No active session.")
            return
        print()
        for k, v in s.items():
            print(f"  {GREY}{k:<18}{R}{CY2}{v}{R}")
        print()
>>>>>>> main

    elif cmd == "/model":
        if len(parts) > 1:
            model_ref[0] = parts[1]
<<<<<<< HEAD
            push_ok(f"Model → {B}{parts[1]}{R}")
            cfg = load_config(); cfg["model"] = parts[1]; save_config(cfg)
        else:
            push_info(f"Model: {B}{model_ref[0] or 'default'}{R}")

    else:
        push_err(f"Unknown: {cmd}  ·  type /help for commands")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _ask(label: str, choices: list = None, default: str = "") -> str:
    sfx = f" [{'/'.join(choices)}]" if choices else (f" [{default}]" if default else "")
    raw = input(f"\n  {re.sub(chr(27)+r'[[0-9;]*m','',label)}{sfx}: ").strip()
    return raw or default

def cmd_init():
    cwd = Path.cwd(); marker = cwd / ".paladin"
    if marker.exists(): push_warn(".paladin already exists.")
    else:
        marker.write_text(json.dumps({"initialized_at": datetime.now().isoformat(),
                                      "project": cwd.name}, indent=2))
        push_ok(f"Created .paladin in {cwd}")
    cfg = load_config()
    ask_and_render(f"I am initializing Paladin AI security agent in: {cwd}. "
                   "Briefly acknowledge and summarize what Paladin will monitor.",
                   label="init", model=cfg.get("model"))

def cmd_start():
    sid = f"SES-{int(datetime.now().timestamp())}"
    save_session({"id": sid, "started_at": datetime.now().isoformat(),
                  "status": "running", "project": Path.cwd().name})
    push_ok(f"Session {CYB}{sid}{R} started.")
    cfg = load_config()
    ask_and_render(f"Starting Paladin session {sid} in {Path.cwd().name}. "
                   "Acknowledge and ask what the user wants to work on.",
                   label="start", model=cfg.get("model"))

def cmd_status():
    sess = load_session()
    if not sess: push_warn("No active session.  Run: start"); return
    _nl(); _push(f"  {CYB}Session Status{R}")
    stat = sess.get("status",""); sc = {"running":GR,"paused":YL,"failed":RD}.get(stat,GREY)
    for k, v in sess.items():
        val = f"{sc}{v}{R}" if k=="status" else f"{CY2}{v}{R}"
        _push(f"  {GREY}{k:<18}{R}{val}")
    _nl()
    cfg = load_config()
    ask_and_render(f"Summarize this Paladin session: {json.dumps(sess)}. "
                   "What's happening, any pending actions?",
                   label="status", model=cfg.get("model"))

def cmd_run(task: str = None):
    if not task: task = _ask("Task to run")
    if not task: push_err("No task provided."); return
    sess = load_session()
    ctx  = f" Session: {json.dumps(sess)}." if sess else ""
    cfg  = load_config()
    ask_and_render(f"Run this Paladin task:{ctx} Task: {task}. "
                   "Execute step by step, use tools, report actions.",
                   label="run", model=cfg.get("model"))

def cmd_approvals():
    cfg = load_config()
    ask_and_render("List all pending Paladin approval requests. "
                   "For each: ID, tool name, risk level, brief description.",
                   label="approvals", model=cfg.get("model"))

def cmd_approve(aid: str, msg: str = None):
    note = f" Note: {msg}" if msg else ""
    cfg  = load_config()
    ask_and_render(f"Approve Paladin action ID: {aid}.{note} Confirm and proceed.",
                   label=f"approve {aid}", model=cfg.get("model"))

def cmd_deny(aid: str, msg: str = None):
    note = f" Reason: {msg}" if msg else ""
    cfg  = load_config()
    ask_and_render(f"Deny Paladin action ID: {aid}.{note} Confirm and explain.",
                   label=f"deny {aid}", model=cfg.get("model"))

def cmd_activity(sid: str = None):
    cfg = load_config()
    if sid:
        ask_and_render(f"Full activity log for Paladin session {sid}. "
                       "All tool calls, decisions, approvals, messages in order.",
                       label=f"activity {sid}", model=cfg.get("model"))
    else:
        ask_and_render("Activity log for current Paladin session. "
                       "Tool calls, agent messages, shield decisions, user approvals.",
                       label="activity", model=cfg.get("model"))

def cmd_policy_list():
    cfg = load_config()
    ask_and_render("List all Paladin security policies: name, action (allow/ask/block), "
                   "threshold, enabled, description.",
                   label="policy list", model=cfg.get("model"))

def cmd_policy_add():
    name    = _ask("Policy name")
    desc    = _ask("Description")
    action  = _ask("Action", choices=["allow","ask","block"], default="ask")
    thresh  = _ask("Risk threshold (0–100)", default="50")
    pattern = _ask("Match pattern (optional)")
    pol     = {"name": name, "description": desc, "action": action,
               "threshold": int(thresh or 50), "enabled": True}
    if pattern: pol["match_patterns"] = [pattern]
    cfg = load_config()
    ask_and_render(f"Add this Paladin policy: {json.dumps(pol)}. "
                   "Confirm and explain when it triggers.",
                   label="policy add", model=cfg.get("model"))

def cmd_policy_test():
    ti = _ask("Prompt or tool to test")
    if not ti: push_err("Nothing to test."); return
    cfg = load_config()
    ask_and_render(f'Test against all Paladin policies: "{ti}". '
                   "Show matching policies, decision, risk score, reason.",
                   label="policy test", model=cfg.get("model"))

def cmd_config():
    cfg = load_config()
    _nl(); _push(f"  {CYB}Config{R}  {LGREY}{CONFIG_FILE}{R}")
    _push(f"  {LGREY}{'─'*40}{R}")
    for k, v in cfg.items():
        val = f"{CY2}{v}{R}" if v is not None else f"{LGREY}not set{R}"
        _push(f"  {GREY}{k:<18}{R}{val}")
    _nl()
    edit = input("  Edit a value? (y/N): ").strip().lower()
    if edit == "y":
        key = _ask("Key"); val = _ask(f"Value for {key}")
        cfg[key] = val; save_config(cfg)
        push_ok(f"{key} = {val}")

def cmd_doctor():
    checks = [
        ("kiro-cli",      bool(KIRO_BIN), KIRO_BIN or "not found — https://kiro.ai"),
        ("python",        sys.version_info>=(3,9), platform.python_version()),
        ("prompt_toolkit",HAS_PT,         "ok" if HAS_PT else "pip install prompt_toolkit"),
        ("config dir",    CONFIG_DIR.exists(), str(CONFIG_DIR)),
        (".paladin",      (Path.cwd()/".paladin").exists(),
                          "found" if (Path.cwd()/".paladin").exists() else "run: init"),
    ]
    _nl(); _push(f"  {CYB}paladin doctor{R}")
    _push(f"  {LGREY}{'─'*40}{R}")
    for name, good, detail in checks:
        icon = f"{GR}✓{R}" if good else f"{YL}◆{R}"
        _push(f"  {icon}  {B}{name:<18}{R}{GREY}{detail}{R}")
    _nl()

def cmd_version():
    _nl()
    _push(f"  {CYB}paladin{R}  {LGREY}v{VERSION}{R}")
    _push(f"  {GREY}python {platform.python_version()} · {platform.system()}{R}")
    _push(f"  {GREY}kiro: {KIRO_BIN or 'not found'}{R}")
    _nl()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dispatcher
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _dispatch(args: list) -> bool:
    if not args: return False
    cmd, rest = args[0].lower(), args[1:]

    if   cmd == "init":      cmd_init()
    elif cmd == "start":     cmd_start()
    elif cmd == "status":    cmd_status()
    elif cmd == "run":       cmd_run(" ".join(rest) if rest else None)
    elif cmd == "approvals": cmd_approvals()
    elif cmd == "approve":
        (push_err("approve <id>") if not rest else cmd_approve(rest[0], " ".join(rest[1:]) or None))
    elif cmd == "deny":
        (push_err("deny <id>") if not rest else cmd_deny(rest[0], " ".join(rest[1:]) or None))
    elif cmd == "activity":  cmd_activity(rest[0] if rest else None)
    elif cmd == "policy":
        sub = rest[0].lower() if rest else ""
        if   sub=="list": cmd_policy_list()
        elif sub=="add":  cmd_policy_add()
        elif sub=="test": cmd_policy_test()
        else: push_err("policy [list|add|test]")
    elif cmd == "config":    cmd_config()
    elif cmd == "doctor":    cmd_doctor()
    elif cmd == "version":   cmd_version()
    elif cmd in ("help","--help","-h"): _push_help()
    else: return False
    return True

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TUI layout
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _make_app(model_ref: list):
    """Simple CLI - no complex TUI needed"""
    return None

    # ── output pane ───────────────────────────────────────────────────────────
    # FormattedTextControl + ANSI() renders escape codes correctly.
    def _output_text():
        if not _lines:
            return ANSI("")
        
        # Show only visible lines based on scroll position and terminal height
        try:
            terminal_height = max(10, os.get_terminal_size().lines - 8)  # Leave space for UI
        except:
            terminal_height = 20  # Fallback
        
        total_lines = len(_lines)
        if total_lines <= terminal_height:
            # All lines fit, show everything
            visible_lines = _lines
        else:
            # Calculate visible window based on scroll position
            if not _user_scrolled:
                # Auto-scroll: show last N lines
                start_idx = max(0, total_lines - terminal_height)
                visible_lines = _lines[start_idx:]
            else:
                # Manual scroll: show lines around scroll position
                start_idx = max(0, min(_scroll_pos, total_lines - terminal_height))
                end_idx = start_idx + terminal_height
                visible_lines = _lines[start_idx:end_idx]
        
        return ANSI("\n".join(visible_lines) + "\n")

    output_window = Window(
        content=FormattedTextControl(
            _output_text,
            focusable=False,
            show_cursor=False,
        ),
        wrap_lines=False,
        scroll_offsets=ScrollOffsets(top=0, bottom=0),
        style="bg:#0a0a0a",  # Explicit black background
    )

    # ── status bar ────────────────────────────────────────────────────────────
    def _sb_text():
        s   = load_session()
        sid = s.get("id",""); proj = s.get("project",""); stat = s.get("status","")
        sc  = {"running":"ansigreen","paused":"ansiyellow","failed":"ansired"}.get(stat,"#6e7681")
        mid = f"  {proj}  #{sid[-5:]}" if sid else "  no session"
        kc  = "ansigreen" if KIRO_BIN else "ansired"
        ki  = "⬤ kiro" if KIRO_BIN else "○ kiro"
        return HTML(
            f"<style bg='#0a0a0a' fg='#58c8ff'><b>  ⬡ paladin</b></style>"
            f"<style bg='#0a0a0a' fg='#484f58'>  v{VERSION}</style>"
            f"<style bg='#0a0a0a' fg='#6e7681'>{mid}</style>"
            f"<style bg='#0a0a0a' fg='{sc}'>  ● {stat}</style>"
            f"<style bg='#0a0a0a' fg='#484f58'>   {model_ref[0] or 'default'}  </style>"
            f"<style bg='#0a0a0a' fg='{kc}'>  {ki}  </style>"
        )

    statusbar = Window(
        content=FormattedTextControl(_sb_text),
        height=1, style="bg:#0a0a0a",
    )

    # ── thin separator ────────────────────────────────────────────────────────
    sep = Window(height=1, char="─", style="fg:#404858 bg:#0a0a0a")

    # ── input buffer ──────────────────────────────────────────────────────────
    hist = FileHistory(str(HISTORY_FILE)) if HISTORY_FILE.parent.exists() else InMemoryHistory()
    buf  = Buffer(name="main", history=hist,
                  auto_suggest=AutoSuggestFromHistory(), multiline=False)

    def _prompt_text():
        s   = load_session()
        sid = s.get("id","")
        tag = f"#{sid[-5:]} " if sid else ""
        return HTML(f"<ansicyan><b>  ⬡ {tag}❯ </b></ansicyan>")

    input_win = Window(
        content=BufferControl(buf, input_processors=[BeforeInput(_prompt_text)],
                              focusable=True),
        height=1, style="bg:#0a0a0a fg:#d0d8e8",
    )

    # ── scroll helper ─────────────────────────────────────────────────────────
    def _scroll(delta: int):
        global _scroll_pos, _user_scrolled
        if not _lines:
            return
        
        # Mark that user has manually scrolled
        _user_scrolled = True
        
        # Update scroll position
        total_lines = len(_lines)
        try:
            terminal_height = max(10, os.get_terminal_size().lines - 8)
        except:
            terminal_height = 20
        
        # Calculate new scroll position
        max_scroll = max(0, total_lines - terminal_height)
        _scroll_pos = max(0, min(_scroll_pos + delta, max_scroll))
        
        # If we scrolled to the bottom, resume auto-follow
        if _scroll_pos >= max_scroll:
            _user_scrolled = False
        
        _app.invalidate()

    def _scroll_to_bottom():
        global _user_scrolled, _scroll_pos
        _user_scrolled = False
        _scroll_pos = len(_lines)  # Will be clamped in _scroll logic
        _app.invalidate()

    # ── key bindings ──────────────────────────────────────────────────────────
    kb = KeyBindings()

    @kb.add("enter")
    def _enter(event):
        text = buf.text.strip(); buf.reset()
        if not text: return
        _scroll_to_bottom()
        def _run():
            _push_user_bubble(text)
            if text.startswith("/"):
                _handle_slash(text, model_ref)
            elif not _dispatch(text.split()):
                ask_and_render(text, model=model_ref[0])
        threading.Thread(target=_run, daemon=True).start()

    @kb.add("c-c")
    def _exit_ctrl_c(event): event.app.exit()
    
    @kb.add("c-q")  # Use Ctrl+Q for quit
    def _exit_ctrl_q(event): event.app.exit()

    @kb.add("c-l")
    def _clear(event):
        _lines.clear()
        _push_banner_lines()
        _app.invalidate()

    # Scroll key bindings
    @kb.add("pageup")
    def _page_up(event): _scroll(-10)

    @kb.add("pagedown") 
    def _page_down(event): _scroll(10)

    @kb.add("c-u")
    def _scroll_up(event): _scroll(-5)

    @kb.add("c-d") 
    def _scroll_down(event): _scroll(5)

    @kb.add("up")
    def _up(event): _scroll(-1)

    @kb.add("down")
    def _down(event): _scroll(1)

    @kb.add("home")
    def _scroll_home(event): 
        global _scroll_pos, _user_scrolled
        _scroll_pos = 0
        _user_scrolled = True
        _app.invalidate()

    @kb.add("end")
    def _scroll_end(event): _scroll_to_bottom()

    # ── layout and app ─────────────────────────────────────────────────────────

    # ── layout and app ─────────────────────────────────────────────────────────
    sep = Window(height=1, char="─", style="fg:#404858 bg:#0a0a0a")

    layout = Layout(HSplit([output_window, statusbar, sep, input_win]),
                    focused_element=input_win)

    style = Style.from_dict({
        "":                                    "bg:#0a0a0a fg:#d0d8e8",
        "scrollbar.background":                "bg:#0a0a0a",
        "scrollbar.button":                    "bg:#404858",
        "completion-menu.completion":          "bg:#141420 fg:#8090a8",
        "completion-menu.completion.current":  "bg:#0a0a0a fg:#58c8ff bold",
        "auto-suggestion":                     "fg:#383848",
    })

    app = Application(layout=layout, key_bindings=kb, style=style,
                       full_screen=True, mouse_support=True, refresh_interval=0.08)
    
    return app

    # ── key bindings ──────────────────────────────────────────────────────────
    kb = KeyBindings()

    @kb.add("enter")
    def _enter(event):
        text = buf.text.strip(); buf.reset()
        if not text: return
        _scroll_to_bottom()
        def _run():
            _push_user_bubble(text)
            if text.startswith("/"):
                _handle_slash(text, model_ref)
            elif not _dispatch(text.split()):
                ask_and_render(text, model=model_ref[0])
        threading.Thread(target=_run, daemon=True).start()

    @kb.add("c-c")
    @kb.add("c-d")
    def _exit(event): event.app.exit()

    @kb.add("c-l")
    def _clear(event):
        _lines.clear()
        _push_banner_lines()
        _scroll_to_bottom()

    @kb.add("pageup")
    def _pgup(event):
        global _user_scrolled
        _user_scrolled = True
        _scroll(-20)

    @kb.add("pagedown")
    def _pgdn(event): _scroll(20)

    @kb.add("up")
    def _up(event):
        if buf.text:
            buf.history_backward()
        else:
            global _user_scrolled
            _user_scrolled = True
            _scroll(-3)

    @kb.add("down")
    def _down(event):
        if buf.text:
            buf.history_forward()
        else:
            _scroll(3)

    # ── layout & style ────────────────────────────────────────────────────────
    layout = Layout(HSplit([output_window, statusbar, sep, input_win]),
                    focused_element=input_win)

    style = Style.from_dict({
        "":                                    "bg:#0a0a0a fg:#d0d8e8",
        "scrollbar.background":                "bg:#0a0a0a",
        "scrollbar.button":                    "bg:#404858",
        "completion-menu.completion":          "bg:#141420 fg:#8090a8",
        "completion-menu.completion.current":  "bg:#0a0a0a fg:#58c8ff bold",
        "auto-suggestion":                     "fg:#383848",
    })

    return Application(layout=layout, key_bindings=kb, style=style,
                       full_screen=True, mouse_support=True, refresh_interval=0.08)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    global _app
    _mkdirs()
    args = sys.argv[1:]

    cfg = load_config()
    model_ref = [cfg.get("model")]

    if args:
        # Handle command directly
        _lines.clear()  # Clear any previous content
        
        if not _dispatch(args):
            # If not a built-in command, treat as a prompt
            ask_and_render(" ".join(args), model=model_ref[0])
        
        # Print the output
        for line in _lines:
            print(line)
    else:
        # Simple interactive mode
        _push_banner_lines()
        # Print the banner
        for line in _lines:
            print(line)
        
        print("\nSimple CLI mode - type commands or prompts directly")
        print("Commands: init, start, status, run, config, version, help")
        print("Type 'exit' or press Ctrl+C to quit")
        print()
        
        try:
            while True:
                try:
                    user_input = input("⬡ ❯ ").strip()
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['exit', 'quit']:
                        break
                    
                    # Clear previous output
                    _lines.clear()
                    
                    # Handle the input
                    if not _dispatch(user_input.split()):
                        ask_and_render(user_input, model=model_ref[0])
                    
                    # Print any output
                    for line in _lines:
                        print(line)
                    print()
                        
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
        except Exception as e:
            print(f"Error: {e}")
=======
            cfg = load_config()
            cfg["model"] = parts[1]
            save_config(cfg)
            _ok(f"Model → {B}{parts[1]}{R}")
        else:
            _info(f"Model: {B}{model_ref[0] or 'default (set by kiro)'}{R}")

    else:
        _err(f"Unknown slash command: {cmd}  (try /help)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dispatcher — maps text tokens to commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _dispatch(args: list, model: str = None) -> bool:
    """Return True if args matched a built-in command, False if it should go to kiro."""
    if not args:
        return False
    cmd, rest = args[0].lower(), args[1:]

    if   cmd == "init":      cmd_init(model)
    elif cmd == "start":     cmd_start(model)
    elif cmd == "status":    cmd_status(model)
    elif cmd == "run":       cmd_run(" ".join(rest) if rest else None, model)
    elif cmd == "approvals": cmd_approvals(model)
    elif cmd == "approve":
        if not rest: _err("Usage: approve <id> [message]")
        else:        cmd_approve(rest[0], " ".join(rest[1:]) or None, model)
    elif cmd == "deny":
        if not rest: _err("Usage: deny <id> [reason]")
        else:        cmd_deny(rest[0], " ".join(rest[1:]) or None, model)
    elif cmd == "activity":  cmd_activity(rest[0] if rest else None, model)
    elif cmd == "policy":
        sub = rest[0].lower() if rest else ""
        if   sub == "list": cmd_policy_list(model)
        elif sub == "add":  cmd_policy_add(model)
        elif sub == "test": cmd_policy_test(model)
        else: _err("Usage: policy [list|add|test]")
    elif cmd == "config":    cmd_config()
    elif cmd == "doctor":    cmd_doctor()
    elif cmd == "version":   cmd_version()
    elif cmd in ("help", "--help", "-h"): print_help()
    else:
        return False
    return True

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entry point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    _mkdirs()
    args = sys.argv[1:]
    cfg  = load_config()
    model_ref = [cfg.get("model")]

    # ── one-shot mode: python paladin.py "do something" ──────────────────────
    if args:
        if not _dispatch(args, model_ref[0]):
            # Not a built-in command — pass the whole thing to kiro as a task
            ask_kiro(" ".join(args), label="task", model=model_ref[0], trust=True)
        return

    # ── interactive REPL ─────────────────────────────────────────────────────
    print_banner()

    # Warn if kiro is missing before we start
    if not KIRO_BIN:
        _err("kiro-cli not found. Install from https://kiro.ai and run `kiro login`.")
        print()

    try:
        while True:
            try:
                sess  = load_session()
                sid   = sess.get("id", "")
                tag   = f"#{sid[-5:]} " if sid else ""
                line  = input(f"  {CY}⬡ {tag}❯ {R}").strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                break

            if not line:
                continue

            if line.lower() in ("exit", "quit", "q"):
                break

            if line.startswith("/"):
                _handle_slash(line, model_ref)
                continue

            tokens = line.split()
            if not _dispatch(tokens, model_ref[0]):
                # Free-form prompt — send directly to kiro with full tool trust
                ask_kiro(line, label="chat", model=model_ref[0], trust=True)

    except SystemExit:
        pass

    print(f"\n  {DIM}bye.{R}\n")

>>>>>>> main

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
paladin - AI security agent for your terminal.
ASCII-only version for better Windows PowerShell compatibility.
"""

import os, sys, shutil, subprocess, json, platform, re, threading, csv
from pathlib import Path
from datetime import datetime

# Simple prompt/confirm helpers for when rich is not available
def simple_prompt(message: str, default: str = "") -> str:
    try:
        result = input(f"{message} [{default}]: ").strip()
        return result if result else default
    except (EOFError, KeyboardInterrupt):
        return default

def simple_confirm(message: str, default: bool = True) -> bool:
    try:
        default_str = "Y/n" if default else "y/N"
        result = input(f"{message} [{default_str}]: ").strip().lower()
        if not result:
            return default
        return result.startswith('y')
    except (EOFError, KeyboardInterrupt):
        return default

# Rich (for input prompts only)
try:
    from rich.prompt import Prompt as RPrompt, Confirm as RConfirm
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    RPrompt = type('RPrompt', (), {'ask': staticmethod(simple_prompt)})()
    RConfirm = type('RConfirm', (), {'ask': staticmethod(simple_confirm)})()

# paladin-engine (context screening)
try:
    import sys as _sys, os as _os
    _engine_root = str(Path(__file__).resolve().parent.parent / "paladin-engine")
    if _engine_root not in _sys.path:
        _sys.path.insert(0, _engine_root)

    from paladin.context.engine import ContextEngine
    from paladin.context.history import ActionHistory
    from paladin.schemas.action import AgentAction

    _engine         = ContextEngine(action_history=ActionHistory())
    _shield_enabled = True
    _last_screen    = None
    HAS_ENGINE = True
except Exception as _engine_err:
    HAS_ENGINE      = False
    _shield_enabled = False
    _last_screen    = None
    _engine_err_msg = str(_engine_err)

VERSION      = "0.1.0-ascii"
CONFIG_DIR   = Path.home() / ".paladin"
CONFIG_FILE  = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history"
SESSION_FILE = CONFIG_DIR / "session.json"
DEFAULTS     = {"model": None, "agent": "paladin"}

# ASCII-only color codes (no background colors for better compatibility)
R    = "\033[0m"     # reset
RD   = "\033[31m"    # red
GR   = "\033[32m"    # green  
YL   = "\033[33m"    # yellow
BL   = "\033[34m"    # blue
MG   = "\033[35m"    # magenta
CY   = "\033[36m"    # cyan
WH   = "\033[37m"    # white
GREY = "\033[90m"    # dark grey
LGREY = "\033[37m"   # light grey (same as white for compatibility)
CY2  = "\033[96m"    # bright cyan
CYB  = "\033[96m"    # bright cyan bold
DIM  = "\033[2m"     # dim

# Simple ASCII art logo (using only standard ASCII characters)
LOGO = [
    "PPPPP    AAA   L       AAA   DDDD   I  N   N",
    "P   P   A   A  L      A   A  D   D  I  NN  N", 
    "PPPPP   AAAAA  L      AAAAA  D   D  I  N N N",
    "P       A   A  L      A   A  D   D  I  N  NN",
    "P       A   A  LLLLL  A   A  DDDD   I  N   N",
]

_output_buffer = []
_W = lambda: shutil.get_terminal_size().columns

def _nl(): 
    _output_buffer.append("")

def _push(line: str): 
    _output_buffer.append(line)

def _ansi_len(s: str) -> int:
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))

def _center(text: str, width: int) -> str:
    raw_len = _ansi_len(text)
    if raw_len >= width: 
        return text
    pad = width - raw_len
    return " " * (pad // 2) + text + " " * (pad - pad // 2)

# ASCII box drawing functions
def _box_top(inner_w: int, title: str = "") -> str:
    if title:
        tlen = _ansi_len(title)
        left = max(0, (inner_w - tlen) // 2)
        right = max(0, inner_w - tlen - left)
        return f"+{'-'*left}{title}{'-'*right}+"
    return f"+{'-'*inner_w}+"

def _box_row(content: str, inner_w: int) -> str:
    vlen = _ansi_len(content)
    pad = max(0, inner_w - vlen - 2)  # -2 for the 1-space padding each side
    return f"| {content}{' '*pad} |"

def _box_sep(inner_w: int) -> str:
    return f"|{'-'*inner_w}|"

def _box_bot(inner_w: int) -> str:
    return f"+{'-'*inner_w}+"

def _wrap_text(text: str, width: int) -> list[str]:
    import textwrap
    raw = re.sub(r"\x1b\[[0-9;]*m", "", text)
    if len(raw) <= width: 
        return [text]
    return textwrap.wrap(raw, width) or [raw]

def _push_user_bubble(text: str):
    tw = _W()
    inner = tw - 2
    ts = datetime.now().strftime("%H:%M")

    _nl()
    _push(_box_top(inner, title=f" {GR}YOU{R} "))
    for part in text.splitlines():
        for chunk in _wrap_text(part, inner - 4):
            _push(_box_row(f"{WH}{chunk}{R}", inner))
    # timestamp right-aligned on its own row
    ts_str = f"{GREY}{ts}{R}"
    ts_rpad = inner - _ansi_len(ts_str) - 2
    _push(_box_row(f"{' '*ts_rpad}{ts_str}", inner))
    _push(_box_bot(inner))
    _nl()

def _push_agent_header(label: str):
    tw = _W()
    inner = tw - 2
    ts = datetime.now().strftime("%H:%M:%S")
    sid = load_session().get("id", "")
    tag = f"  {GREY}#{sid[-5:]}{R}" if sid else ""
    title = f" {CYB}PALADIN{R} "
    _nl()
    _push(_box_top(inner, title=title))
    sub = f"{DIM}{label}{R}{tag}  {GREY}{ts}{R}"
    _push(_box_row(_center(sub, inner - 2), inner))

def _push_agent_footer(elapsed: float):
    tw = _W()
    inner = tw - 2
    foot = f"{DIM}-> {elapsed:.1f}s{R}"
    _push(_box_row(foot, inner))
    _push(_box_bot(inner))
    _nl()

def push_ok(m):
    tw = _W()
    inner = tw - 2
    _push(_box_row(f"{GR}[OK]{R}  {WH}{m}{R}", inner))

def push_err(m):
    tw = _W()
    inner = tw - 2
    _push(_box_row(f"{RD}[ERROR]{R}  {WH}{m}{R}", inner))
    _push(_box_bot(inner))
    _nl()

def push_warn(m):
    tw = _W()
    inner = tw - 2
    _push(_box_row(f"{YL}[WARN]{R}  {WH}{m}{R}", inner))

def push_info(m):
    tw = _W()
    inner = tw - 2
    _push(_box_row(f"{CY2}[INFO]{R}  {GREY}{m}{R}", inner))

def _push_banner_lines():
    tw = _W()
    inner = tw - 2

    session = load_session()
    sid = session.get("id", "")
    proj = session.get("project", "")
    stat = session.get("status", "idle")

    kiro_text = (f"{GR}* kiro connected{R}" if find_kiro_bin()
                 else f"{RD}* kiro not found{R}  {GREY}-> https://kiro.ai{R}")
    sc = {"running": GR, "paused": YL, "failed": RD, "idle": GREY}.get(stat, GREY)
    sess_text = (f"{GREY}session  {R}{CYB}{sid}{R}  {GREY}{proj}  {R}{sc}> {stat}{R}"
                 if sid else f"{GREY}no session  *  type {R}{CY}start{R}{GREY} to begin{R}")

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
        (f"{CY}check{R}",      "Context check"),
        (f"{CY}demo{R}",       "Attack replay demo"),
    ]
    shortcuts = f"{DIM}/help  *  /clear  *  /session  *  /model <name>  *  /shield  *  Ctrl-C exits{R}"

    _nl()
    _push(_box_top(inner, title=f" {CY}PALADIN{R} "))
    _push(_box_row("", inner))

    for ll in LOGO:
        _push(_box_row(_center(f"{CY}{ll}{R}", inner - 2), inner))
    tagline = f"{DIM}AI Security Agent  *  v{VERSION}  *  powered by kiro{R}"
    _push(_box_row(_center(tagline, inner - 2), inner))

    _push(_box_row("", inner))
    _push(_box_sep(inner))
    _push(_box_row("", inner))
    _push(_box_row(_center(kiro_text, inner - 2), inner))
    _push(_box_row(_center(sess_text, inner - 2), inner))
    _push(_box_row("", inner))
    _push(_box_sep(inner))
    _push(_box_row("", inner))

    # Commands in a simpler 2-column layout that fits better
    cmd_pairs = [
        (("init", "Init project"), ("start", "New session")),
        (("status", "Session status"), ("run", "Run a task")),
        (("approvals", "Pending approvals"), ("approve", "Approve action")),
        (("deny", "Deny action"), ("activity", "Activity log")),
        (("policy", "Manage policies"), ("config", "Configuration")),
        (("doctor", "Health check"), ("check", "Context check")),
        (("demo", "Attack replay demo"), ("", "")),
    ]
    
    for (c1, d1), (c2, d2) in cmd_pairs:
        if c1 and c2:
            line = f"   {CY}{c1:<10}{R} {d1:<18} {CY}{c2:<10}{R} {d2}"
        elif c1:
            line = f"   {CY}{c1:<10}{R} {d1}"
        else:
            continue
        _push(_box_row(line[:inner-2], inner))

    _push(_box_row("", inner))
    _push(_box_sep(inner))
    _push(_box_row("", inner))
    _push(_box_row(_center(shortcuts, inner - 2), inner))
    _push(_box_row("", inner))
    _push(_box_bot(inner))

def find_kiro_bin():
    """Find kiro binary"""
    return shutil.which("kiro") is not None

def load_config():
    """Load configuration from file"""
    if not CONFIG_FILE.exists():
        return DEFAULTS.copy()
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Merge with defaults for any missing keys
        result = DEFAULTS.copy()
        result.update(config)
        return result
    except (json.JSONDecodeError, IOError):
        return DEFAULTS.copy()

def save_config(config):
    """Save configuration to file"""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_session():
    """Load current session info"""
    if not SESSION_FILE.exists():
        return {}
    try:
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_session(session_data):
    """Save session info"""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(SESSION_FILE, 'w') as f:
        json.dump(session_data, f, indent=2)

def flush_output():
    """Flush the output buffer to stdout"""
    for line in _output_buffer:
        print(line)
    _output_buffer.clear()

def main():
    """Main CLI entry point"""
    if len(sys.argv) > 1:
        # Handle subcommands
        cmd = sys.argv[1].lower()
        if cmd in ["help", "--help", "-h"]:
            show_help()
        elif cmd == "version":
            print(f"paladin v{VERSION}")
        elif cmd in ["init", "start", "status", "run", "config", "doctor"]:
            print(f"Command '{cmd}' would be implemented here")
            print("This is a simplified ASCII version for demo purposes")
        else:
            # Treat as a one-shot prompt
            prompt = " ".join(sys.argv[1:])
            print(f"One-shot mode: {prompt}")
            print("This would send the prompt to kiro-cli")
        return

    # Interactive REPL mode
    print(f"{CY}Starting Paladin CLI (ASCII mode)...{R}")
    
    # Show banner
    _push_banner_lines()
    flush_output()
    
    print("\nSimple CLI mode - type commands or prompts directly")
    print("Commands: init, start, status, run, config, version, help")
    print("Type 'exit' or press Ctrl+C to quit")
    
    while True:
        try:
            user_input = input(f"\n{CY}>{R} ").strip()
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', '/exit', '/quit']:
                break
            elif user_input.lower() in ['help', '/help']:
                show_help()
            elif user_input.lower() in ['clear', '/clear']:
                os.system('cls' if os.name == 'nt' else 'clear')
            elif user_input.startswith('/'):
                print(f"Command: {user_input}")
            else:
                print(f"Would send to kiro: {user_input}")
                
        except (EOFError, KeyboardInterrupt):
            print(f"\n{GREY}Goodbye!{R}")
            break

def show_help():
    """Show help information"""
    help_text = f"""
{CY}Paladin CLI - AI Security Agent{R}

{WH}Usage:{R}
  python paladin_ascii.py                    # Interactive mode
  python paladin_ascii.py "your prompt"     # One-shot mode
  python paladin_ascii.py <command>         # Run command

{WH}Commands:{R}
  {CY}init{R}       Initialize paladin in current project
  {CY}start{R}      Start a new agent session
  {CY}status{R}     Show current session status
  {CY}run{R}        Run the agent on a task
  {CY}config{R}     Show/edit configuration
  {CY}doctor{R}     Check environment health
  {CY}version{R}    Show version info
  {CY}help{R}       Show this help

{WH}Interactive shortcuts:{R}
  {CY}/help{R}      Show help
  {CY}/clear{R}     Clear screen
  {CY}/exit{R}      Exit (or Ctrl+C)
"""
    print(help_text)

if __name__ == "__main__":
    main()
"""
flagger.py  —  paladin interrupt & permission gate

When the risk engine scores a prompt above the high-risk threshold,
flag(prompt) is called.  It:
  1. Renders a paladin-styled warning card to the terminal
  2. Asks the user for explicit permission (y / n)
  3. If approved  → forwards the prompt to kiro-cli via paladin's renderer
  4. If denied    → renders a paladin-styled "blocked" card and exits cleanly
"""

import os
import sys
import re


# ── ANSI palette (mirrors paladin_cli/paladin.py exactly) ────────────────────
R     = "\033[0m"
B     = "\033[1m"
DIM   = "\033[2m"

CY    = "\033[38;5;39m"
CY2   = "\033[38;5;80m"
GR    = "\033[38;5;78m"
YL    = "\033[38;5;221m"
RD    = "\033[38;5;203m"
OR    = "\033[38;5;215m"
WH    = "\033[38;5;253m"
GREY  = "\033[38;5;243m"
LGREY = "\033[38;5;238m"

BG    = "\033[48;2;10;10;10m"   # #0a0a0a — same as paladin's BG
BDR   = "\033[38;2;64;72;88m"   # #404858 — same as paladin's _BDRC
CYB   = f"{B}{CY}"


# ── Box helpers (identical logic to paladin.py) ───────────────────────────────

def _W() -> int:
    try:
        return max(60, os.get_terminal_size().columns - 10)
    except Exception:
        return 80


def _ansi_len(s: str) -> int:
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))


def _box_top(inner_w: int, title: str = "") -> str:
    if title:
        tlen  = _ansi_len(title)
        left  = (inner_w - tlen) // 2
        right = inner_w - tlen - left
        return f"{BG}{BDR}╔{'═'*left}{title}{BG}{BDR}{'═'*right}╗{R}"
    return f"{BG}{BDR}╔{'═'*inner_w}╗{R}"


def _box_row(content: str, inner_w: int) -> str:
    used = _ansi_len(content) + 2
    pad  = max(0, inner_w - used)
    return f"{BG}{BDR}║{BG} {content}{BG}{' '*pad} {BDR}║{R}"


def _box_sep(inner_w: int) -> str:
    return f"{BG}{BDR}╠{'═'*inner_w}╣{R}"


def _box_bot(inner_w: int) -> str:
    return f"{BG}{BDR}╚{'═'*inner_w}╝{R}"


def _center(text: str, width: int) -> str:
    vlen = _ansi_len(text)
    pad  = max(0, width - vlen)
    return " " * (pad // 2) + text + " " * (pad - pad // 2)


def _print_lines(*lines: str) -> None:
    for line in lines:
        print(line)


# ── Main flag() function ──────────────────────────────────────────────────────

def flag(prompt: str = "") -> None:
    """
    Interrupt the CLI with a permission gate.

    Parameters
    ----------
    prompt : str
        The raw user prompt that triggered the high-risk flag.
        Required to forward to kiro-cli if the user approves.
    """
    tw    = _W()
    inner = tw - 2

    # ── Warning card ─────────────────────────────────────────────────────────
    print()
    _print_lines(
        _box_top(inner, title=f"{BG}{B}{RD} ⚠  HIGH-RISK PROMPT DETECTED  {R}{BG}{BDR}"),
        _box_row("", inner),
        _box_row(
            f"  {RD}{B}paladin{R}{RD} flagged this prompt as potentially dangerous.{R}",
            inner,
        ),
        _box_row("", inner),
        _box_sep(inner),
        _box_row("", inner),
        _box_row(f"  {GREY}prompt  {R}{WH}{prompt[:120]}{'…' if len(prompt) > 120 else ''}{R}", inner),
        _box_row("", inner),
        _box_sep(inner),
        _box_row("", inner),
        _box_row(
            f"  {YL}Running this prompt may access sensitive resources or perform{R}",
            inner,
        ),
        _box_row(
            f"  {YL}destructive actions.  Review carefully before proceeding.{R}",
            inner,
        ),
        _box_row("", inner),
        _box_bot(inner),
    )
    print()

    # ── Permission prompt ─────────────────────────────────────────────────────
    try:
        answer = input(
            f"{BG}{BDR}║{R}{BG} {YL}{B} Allow this prompt to proceed?{R}"
            f"  {DIM}[y / n]{R}  "
            f"{BG}{BDR}║{R}  "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"
        print()

    print()

    if answer == "y":
        # ── Approved card ─────────────────────────────────────────────────────
        _print_lines(
            _box_top(inner, title=f"{BG}{B}{GR} ✔  APPROVED — forwarding to kiro  {R}{BG}{BDR}"),
            _box_row("", inner),
            _box_row(
                f"  {GR}Permission granted.{R}{GREY}  Sending prompt to kiro-cli…{R}",
                inner,
            ),
            _box_row("", inner),
            _box_bot(inner),
        )
        print()

        # Forward to kiro via paladin's renderer
        _pass_to_kiro(prompt)

    else:
        # ── Blocked card ──────────────────────────────────────────────────────
        _print_lines(
            _box_top(inner, title=f"{BG}{B}{RD} ✖  BLOCKED — prompt denied  {R}{BG}{BDR}"),
            _box_row("", inner),
            _box_row(
                f"  {RD}Permission denied.{R}{GREY}  The prompt was not forwarded to kiro-cli.{R}",
                inner,
            ),
            _box_row("", inner),
            _box_row(
                f"  {DIM}Paladin has blocked this action and returned to idle.{R}",
                inner,
            ),
            _box_row("", inner),
            _box_bot(inner),
        )
        print()


# ── Kiro forwarding (identical to Backend.pass_to_kiro) ──────────────────────

def _pass_to_kiro(prompt: str) -> None:
    """Load paladin as a module and use its renderer to call kiro-cli."""
    import importlib.util as _ilu

    _here     = os.path.dirname(os.path.abspath(__file__))
    _cli_dir  = os.path.join(_here, "..", "paladin_cli")
    _pal_path = os.path.join(_cli_dir, "paladin.py")

    if _cli_dir not in sys.path:
        sys.path.insert(0, _cli_dir)

    try:
        spec    = _ilu.spec_from_file_location("paladin_flagger", _pal_path)
        paladin = _ilu.module_from_spec(spec)
        spec.loader.exec_module(paladin)

        paladin._lines.clear()
        paladin._push_user_bubble(prompt)
        paladin.ask_and_render(prompt, label="response")

        for line in paladin._lines:
            print(line)

    except Exception as exc:
        tw    = _W()
        inner = tw - 2
        _print_lines(
            _box_top(inner, title=f"{BG}{B}{RD} ✖  kiro error  {R}{BG}{BDR}"),
            _box_row(f"  {RD}{exc}{R}", inner),
            _box_bot(inner),
        )
        print()

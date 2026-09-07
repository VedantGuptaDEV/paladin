"""
kiro_guard.py — paladin command-level security gate

Wraps kiro-cli so that EVERY tool-use command (shell, fs_write, fs_read,
etc.) is evaluated by the same Risk Engine vector-similarity method used in
watcher.py / Backend.py BEFORE kiro executes it.

How it works
─────────────
1. Spawns kiro with --output-format stream-json --agent-engine v2 -a
   (trust-all-tools so kiro doesn't auto-deny; we become the gate instead).
2. Reads stdout line-by-line in a background thread, parsing JSON events.
3. On every "tool_call" event (before execution):
     • Extracts the command string from rawInput.command
     • Calls risk_score() — same SentenceTransformer + cosine similarity
       against embedded_mal_prompts.npy
     • SAFE  (< 0.5)  : prints a green pass badge, lets kiro continue
     • WARN  (0.5–0.7): prints an orange warning badge, lets kiro continue
     • HIGH  (≥ 0.7)  : kills kiro immediately (command never executed),
                         shows the flagger-style permission gate to the user.
                         If the user approves → restarts kiro with the same
                         prompt so the command can run.
                         If the user denies  → blocked card, paladin idle.
4. "agent_message_chunk" events are assembled and re-rendered through
   paladin's _render_line() pipeline so the output looks native.

Usage (called from paladin.py ask_and_render):
    from Engine.kiro_guard import run_guarded
    run_guarded(prompt, push_fn=_push, render_line_fn=_render_line)

Direct CLI use (for testing):
    python Engine/kiro_guard.py "list the files in this directory"
"""

import os
import sys
import json
import shutil
import subprocess
import threading
import re
from datetime import datetime

# ── Force UTF-8 stdout/stderr on Windows (avoids cp1252 UnicodeEncodeError) ──
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Python < 3.7 — best-effort only

# ── Resolve paths regardless of where the script is launched from ─────────────
_HERE        = os.path.dirname(os.path.abspath(__file__))       # .../Engine/
_ROOT        = os.path.dirname(_HERE)                           # .../paladin/
_CLI_DIR     = os.path.join(_ROOT, "paladin_cli")
_RISK_DIR    = os.path.join(_HERE, "Risk_Engine")

for _p in (_HERE, _CLI_DIR, _RISK_DIR, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Risk Engine ───────────────────────────────────────────────────────────────
try:
    import Risk_Engine.RiskEngine as _risk
    _RISK_OK = True
except ImportError:
    try:
        import Risk_Engine.RiskEngine as _risk           # fallback when already in Risk_Engine dir
        _RISK_OK = True
    except ImportError:
        _RISK_OK = False

# Thresholds (mirrors RiskEngine.py)
_NULL2GREEN   = 0.5
_GREEN2ORANGE = 0.7

# ── Kiro binary ───────────────────────────────────────────────────────────────
KIRO_BIN = (
    shutil.which("kiro-cli")
    or shutil.which("kiro-cli-chat")
    or shutil.which("kiro")
    or r"C:\Users\Vedant Gupta\AppData\Local\Kiro-Cli\kiro-cli.exe"
)

# ── ANSI palette (mirrors paladin.py and flagger.py exactly) ─────────────────
R     = "\033[0m"
B     = "\033[1m"
DIM   = "\033[2m"
IT    = "\033[3m"

CY    = "\033[38;5;39m"
CY2   = "\033[38;5;80m"
GR    = "\033[38;5;78m"
YL    = "\033[38;5;221m"
RD    = "\033[38;5;203m"
OR    = "\033[38;5;215m"
WH    = "\033[38;5;253m"
GREY  = "\033[38;5;243m"
LGREY = "\033[38;5;238m"

BG    = "\033[48;2;10;10;10m"
BDR   = "\033[38;2;64;72;88m"
CYB   = f"{B}{CY}"


# ── Box helpers (identical to flagger.py) ────────────────────────────────────

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


# ── Command log (mirrors trialHack_output.csv schema exactly) ─────────────────
_GUARD_CSV = os.path.join(
    _HERE, "Context_Engine", "kiro_guard_output.csv"
)

_GUARD_FIELDNAMES = [
    "timestamp", "raw_prompt", "action_type",
    "target", "agent", "sensitivity", "target_category", "cwd",
    "risk_score",
]

def _log_command(
    raw_prompt: str,
    action_type: str,        # tool name  e.g. "shell", "fs_write"
    target: str,             # the command / path string
    sensitivity: str,        # "safe" | "warn" | "block" | "block-approved" | "block-denied"
    target_category: str,    # risk score string  e.g. "55.30"
) -> None:
    """Append one row to kiro_guard_output.csv (same schema as trialHack_output.csv)."""
    import csv as _csv
    row = {
        "timestamp":       datetime.now().isoformat(timespec="seconds"),
        "raw_prompt":      raw_prompt,
        "action_type":     action_type,
        "target":          target,
        "agent":           "kiro",
        "sensitivity":     sensitivity,
        "target_category": target_category,
        "cwd":             os.getcwd(),
        "risk_score":      target_category,   # target_category already holds the score string
    }
    file_exists = os.path.isfile(_GUARD_CSV)
    try:
        with open(_GUARD_CSV, "a", newline="", encoding="utf-8") as fh:
            writer = _csv.DictWriter(fh, fieldnames=_GUARD_FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception:
        pass  # never crash the guard over a log write




def _print_tool_info(tool_name: str, command: str) -> None:
    """Dim info line for non-command tools (no risk evaluation needed)."""
    tw    = _W()
    inner = tw - 2
    print(_box_top(inner, title=f"{BG}{DIM} ·  {tool_name}  {R}{BG}{BDR}"))
    print(_box_row(f"  {GREY}{command[:120]}{'…' if len(command) > 120 else ''}{R}", inner))
    print(_box_bot(inner))
    print()


def _print_tool_result(tool_name: str, title: str, status: str, update: dict) -> None:
    """Show tool execution result — output snippet and exit status."""
    tw    = _W()
    inner = tw - 2

    ok      = status == "completed"
    icon    = f"{GR}✔{R}" if ok else f"{RD}✖{R}"
    clr     = GR if ok else RD
    label   = f"{BG}{clr}{B} {icon}  {title}  {R}{BG}{BDR}"

    # Pull stdout snippet from rawOutput if present
    raw_out   = update.get("rawOutput", {})
    out_items = raw_out.get("items", []) if isinstance(raw_out, dict) else []
    stdout_snip = ""
    for item in out_items:
        j = item.get("Json", {}) if isinstance(item, dict) else {}
        if isinstance(j, dict) and "stdout" in j:
            stdout_snip = j["stdout"].strip()[:200]
            break
        # content array fallback
        content_list = update.get("content", [])
        for c in content_list:
            if isinstance(c, dict):
                inner_c = c.get("content", {})
                if isinstance(inner_c, dict) and inner_c.get("type") == "text":
                    stdout_snip = inner_c.get("text", "").strip()[:200]
                    break

    print(_box_top(inner, title=label))
    if stdout_snip:
        for line in stdout_snip.splitlines()[:6]:   # max 6 lines of output
            print(_box_row(f"  {DIM}{line}{R}", inner))
        if stdout_snip.count("\n") > 5:
            print(_box_row(f"  {GREY}… (truncated){R}", inner))
    else:
        print(_box_row(f"  {GREY}(no stdout){R}", inner))
    print(_box_bot(inner))
    print()


# ── Risk badge printers ───────────────────────────────────────────────────────

def _print_safe_badge(tool_name: str, command: str, score: str) -> None:
    """Green pass badge for safe commands."""
    tw    = _W()
    inner = tw - 2
    print()
    print(_box_top(inner, title=f"{BG}{B}{GR} ✔  GUARD PASS  {R}{BG}{BDR}"))
    print(_box_row(f"  {GREY}tool     {R}{CY2}{tool_name}{R}", inner))
    print(_box_row(f"  {GREY}command  {R}{WH}{command[:120]}{'…' if len(command) > 120 else ''}{R}", inner))
    print(_box_row(f"  {GREY}score    {R}{GR}{score}{R}  {DIM}(safe — below {_NULL2GREEN}){R}", inner))
    print(_box_bot(inner))
    print()


def _print_warn_badge(tool_name: str, command: str, score: str) -> None:
    """Orange warning badge for medium-risk commands."""
    tw    = _W()
    inner = tw - 2
    print()
    print(_box_top(inner, title=f"{BG}{B}{OR} ⚠  GUARD WARN  {R}{BG}{BDR}"))
    print(_box_row(f"  {GREY}tool     {R}{CY2}{tool_name}{R}", inner))
    print(_box_row(f"  {GREY}command  {R}{WH}{command[:120]}{'…' if len(command) > 120 else ''}{R}", inner))
    print(_box_row(f"  {GREY}score    {R}{OR}{score}{R}  {DIM}(elevated — {_NULL2GREEN}–{_GREEN2ORANGE}){R}", inner))
    print(_box_row("", inner))
    print(_box_row(f"  {OR}Elevated risk detected — proceeding but logging this command.{R}", inner))
    print(_box_bot(inner))
    print()


def _print_blocked_card(tool_name: str, command: str, score: str) -> None:
    """Red block card when a command is denied."""
    tw    = _W()
    inner = tw - 2
    print()
    print(_box_top(inner, title=f"{BG}{B}{RD} ✖  GUARD BLOCKED  {R}{BG}{BDR}"))
    print(_box_row("", inner))
    print(_box_row(f"  {RD}Permission denied.{R}{GREY}  The command was not executed.{R}", inner))
    print(_box_row("", inner))
    print(_box_row(f"  {GREY}tool     {R}{CY2}{tool_name}{R}", inner))
    print(_box_row(f"  {GREY}command  {R}{WH}{command[:120]}{'…' if len(command) > 120 else ''}{R}", inner))
    print(_box_row(f"  {GREY}score    {R}{RD}{score}{R}  {DIM}(high-risk — above {_GREEN2ORANGE}){R}", inner))
    print(_box_row("", inner))
    print(_box_row(f"  {DIM}Paladin has blocked this action and returned to idle.{R}", inner))
    print(_box_row("", inner))
    print(_box_bot(inner))
    print()


def _print_high_risk_gate(tool_name: str, command: str, score: str) -> bool:
    """
    Show the high-risk permission gate (mirrors flagger.flag()).
    Returns True if the user approves, False if denied.
    """
    tw    = _W()
    inner = tw - 2

    print()
    print(_box_top(inner, title=f"{BG}{B}{RD} ⚠  HIGH-RISK COMMAND DETECTED  {R}{BG}{BDR}"))
    print(_box_row("", inner))
    print(_box_row(
        f"  {RD}{B}paladin{R}{RD} flagged this kiro tool-use as potentially dangerous.{R}",
        inner,
    ))
    print(_box_row("", inner))
    print(_box_sep(inner))
    print(_box_row("", inner))
    print(_box_row(f"  {GREY}tool     {R}{CY2}{tool_name}{R}", inner))
    print(_box_row(
        f"  {GREY}command  {R}{WH}{command[:120]}{'…' if len(command) > 120 else ''}{R}",
        inner,
    ))
    print(_box_row(
        f"  {GREY}score    {R}{RD}{score}{R}  {DIM}(high-risk threshold: {_GREEN2ORANGE}){R}",
        inner,
    ))
    print(_box_row("", inner))
    print(_box_sep(inner))
    print(_box_row("", inner))
    print(_box_row(
        f"  {YL}Executing this command may access sensitive resources or perform{R}",
        inner,
    ))
    print(_box_row(
        f"  {YL}destructive actions.  Review carefully before proceeding.{R}",
        inner,
    ))
    print(_box_row("", inner))
    print(_box_bot(inner))
    print()

    try:
        answer = input(
            f"{BG}{BDR}║{R}{BG} {YL}{B} Allow this command to execute?{R}"
            f"  {DIM}[y / n]{R}  "
            f"{BG}{BDR}║{R}  "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"
        print()

    print()
    return answer == "y"


# ── Risk evaluation ───────────────────────────────────────────────────────────

def _evaluate_command(tool_name: str, command: str) -> tuple[str, float, str]:
    """
    Evaluate a command string through the Risk Engine.

    Returns (verdict, risk_factor, score_str) where verdict is one of:
        "safe"    risk_factor < _NULL2GREEN
        "warn"    _NULL2GREEN <= risk_factor < _GREEN2ORANGE
        "block"   risk_factor >= _GREEN2ORANGE
    """
    if not _RISK_OK:
        # Risk engine unavailable — let everything through with a warning
        print(f"{YL}[guard] Risk Engine not loaded — cannot evaluate '{tool_name}': {command[:60]}{R}")
        return ("safe", 0.0, "N/A")

    # Evaluate the *command* string, not the original user prompt
    risk_factor, score_str = _risk.risk_score(command)

    if risk_factor >= _GREEN2ORANGE:
        verdict = "block"
    elif risk_factor >= _NULL2GREEN:
        verdict = "warn"
    else:
        verdict = "safe"

    return (verdict, risk_factor, score_str)


# ── Tool-use tools to intercept ───────────────────────────────────────────────
# Only these kiro tool names carry commands worth evaluating.
# fs_read / fs_list are read-only but still worth scoring.
_TOOL_HAS_COMMAND = {
    "shell",
    "fs_write",
    "fs_read",
    "fs_list",
    "fs_delete",
    "computer",
}


def _extract_command(update: dict) -> str:
    """
    Pull a human-readable command string from a tool_call update dict.
    Falls back to the title field if rawInput.command isn't present.
    """
    raw_input = update.get("rawInput", {})
    tool_name = update.get("_meta", {}).get("kiro", {}).get("toolName", "")

    # shell tool
    if "command" in raw_input:
        return raw_input["command"]

    # fs_write / fs_read / fs_delete — use path as the command string
    if "path" in raw_input:
        path = raw_input["path"]
        content_preview = ""
        if "content" in raw_input:
            c = str(raw_input["content"])
            content_preview = f" [writing {len(c)} chars]"
        return f"{tool_name} {path}{content_preview}"

    # fs_list
    if "paths" in raw_input:
        return f"{tool_name} {raw_input['paths']}"

    # fallback: use the event title
    return update.get("title", f"{tool_name} (unknown input)")


# ── Main guard function ───────────────────────────────────────────────────────

def run_guarded(
    prompt: str,
    push_fn=None,
    render_line_fn=None,
    model: str = None,
    extra_kiro_args: list = None,
) -> None:
    """
    Run kiro with the given prompt, intercepting every tool-use command
    through the Risk Engine before it executes.

    Parameters
    ----------
    prompt         : user prompt string
    push_fn        : callable(str) — paladin's _push(), used to buffer output lines.
                     Falls back to print() when called standalone.
    render_line_fn : callable(str) -> list[str] — paladin's _render_line().
                     Falls back to a simple passthrough.
    model          : optional model override for kiro
    extra_kiro_args: additional args forwarded to kiro-cli
    """
    _out  = push_fn      if push_fn      else print
    _rend = render_line_fn if render_line_fn else lambda l: [l]

    def _emit(text: str) -> None:
        for styled in _rend(text):
            _out(styled)

    if not KIRO_BIN or not os.path.isfile(KIRO_BIN):
        _out(f"  {RD}kiro-cli not found.  Install from https://kiro.ai{R}")
        return

    # ── Build the kiro command ────────────────────────────────────────────────
    cmd = [
        KIRO_BIN, "chat",
        "--agent-engine", "v2",
        "--output-format", "stream-json",
        "--trust-all-tools",   # we are the gate; kiro must not block itself
    ]
    if model:
        cmd += ["--model", model]
    if extra_kiro_args:
        cmd += extra_kiro_args
    cmd.append(prompt)

    # ── State shared between the reader thread and this function ─────────────
    _text_buf  = []          # accumulates agent_message_chunk text fragments
    _kill_evt  = threading.Event()   # signals reader to stop after kill
    _blocked   = [False]     # mutable flag: True when kiro was killed by guard
    _proc_ref  = [None]      # mutable reference to the subprocess

    def _flush_text() -> None:
        """Emit accumulated text chunks through the renderer."""
        if not _text_buf:
            return
        full = "".join(_text_buf)
        _text_buf.clear()
        for line in full.splitlines():
            _emit(line)

    def _reader(proc: subprocess.Popen) -> None:
        """Background thread: read stdout, evaluate tool calls."""
        try:
            for raw_line in proc.stdout:
                if _kill_evt.is_set():
                    break
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                _process_event(proc, raw_line)
        except Exception as _reader_exc:
            # Surface the error through the push channel rather than silently dropping
            _out(f"  {RD}[guard] reader error: {_reader_exc}{R}")

    def _process_event(proc: subprocess.Popen, raw_line: str) -> None:
        """Parse one JSON event line and act on it."""
        try:
            evt = json.loads(raw_line)
        except json.JSONDecodeError:
            # Non-JSON line (e.g. a raw error message) — emit as-is
            _out(f"  {GREY}{raw_line[:200]}{R}")
            return

        evt_type = evt.get("type", "")
        update   = evt.get("data", {}).get("update", {}) if evt_type == "sessionUpdate" else {}
        su       = update.get("sessionUpdate", "")

        # ── Agent text ───────────────────────────────────────────────────────
        if su == "agent_message_chunk":
            content = update.get("content", {})
            if content.get("type") == "text":
                _text_buf.append(content.get("text", ""))
            return

        # ── Tool call (pre-execution) ─────────────────────────────────────────
        if su == "tool_call":
            _flush_text()   # emit any buffered agent text before the badge

            tool_name = update.get("_meta", {}).get("kiro", {}).get("toolName", "unknown")
            command   = _extract_command(update)
            tool_call_id = update.get("toolCallId", "")

            if tool_name in _TOOL_HAS_COMMAND:
                _guard_tool_call(proc, tool_name, command)
            else:
                # Non-command tool (e.g. knowledge lookup) — still show it
                _print_tool_info(tool_name, command)
                _log_command(prompt, tool_name, command, "safe", "N/A")
            return

        # ── Tool result (post-execution) ──────────────────────────────────────
        if su == "tool_call_update":
            status    = update.get("status", "")
            tool_name = update.get("_meta", {}).get("kiro", {}).get("toolName", "")
            title     = update.get("title", tool_name)

            # Only print when the call finishes (not intermediate streaming updates)
            if status in ("completed", "failed"):
                _print_tool_result(tool_name, title, status, update)
            return

        # ── Run finished ──────────────────────────────────────────────────────
        if evt_type == "runFinished":
            _flush_text()
            return

        # ── Errors ────────────────────────────────────────────────────────────
        if evt_type == "runError":
            msg = evt.get("data", {}).get("message", "unknown error")
            _out(f"  {RD}kiro error: {msg}{R}")
            return

        # all other event types (metadata, runStarted) — silently ignore

    def _guard_tool_call(proc: subprocess.Popen, tool_name: str, command: str) -> None:
        """Evaluate the command and kill kiro if it's too dangerous."""
        verdict, risk_factor, score_str = _evaluate_command(tool_name, command)

        if verdict == "safe":
            _print_safe_badge(tool_name, command, score_str)
            _log_command(prompt, tool_name, command, "safe", score_str)

        elif verdict == "warn":
            _print_warn_badge(tool_name, command, score_str)
            _log_command(prompt, tool_name, command, "warn", score_str)

        else:  # block
            # Kill kiro immediately — command has NOT yet executed
            _kill_evt.set()
            _blocked[0] = True
            proc.kill()

            approved = _print_high_risk_gate(tool_name, command, score_str)

            if approved:
                _log_command(prompt, tool_name, command, "block-approved", score_str)
                # User approved — show approved card then restart kiro
                tw    = _W()
                inner = tw - 2
                print(_box_top(inner, title=f"{BG}{B}{GR} ✔  APPROVED — restarting kiro  {R}{BG}{BDR}"))
                print(_box_row("", inner))
                print(_box_row(
                    f"  {GR}Permission granted.{R}{GREY}  Restarting kiro with the same prompt…{R}",
                    inner,
                ))
                print(_box_row("", inner))
                print(_box_bot(inner))
                print()

                # Restart in a new call — recursive guard keeps protection
                _blocked[0] = False   # allow the new run
                run_guarded(prompt, push_fn=push_fn, render_line_fn=render_line_fn, model=model)
            else:
                _log_command(prompt, tool_name, command, "block-denied", score_str)
                _print_blocked_card(tool_name, command, score_str)

    # ── Start kiro ────────────────────────────────────────────────────────────
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    except Exception as exc:
        _out(f"  {RD}Failed to start kiro: {exc}{R}")
        return

    _proc_ref[0] = proc

    reader_thread = threading.Thread(target=_reader, args=(proc,), daemon=True)
    reader_thread.start()

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.kill()
        _out(f"  {DIM}interrupted{R}")
        return
    finally:
        _kill_evt.set()
        reader_thread.join(timeout=3)

    # Flush any remaining buffered text
    _flush_text()


# ── Standalone CLI entry-point ────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python kiro_guard.py <prompt>")
        sys.exit(1)

    user_prompt = " ".join(sys.argv[1:])

    print(f"\n{CYB}[kiro_guard]{R}  Evaluating commands for: {WH}{user_prompt[:80]}{R}\n")

    if not _RISK_OK:
        print(f"{RD}[kiro_guard] WARNING: Risk Engine failed to load.{R}")
        print(f"  Make sure Engine/Risk_Engine/RiskEngine.py is importable.")
        print(f"  Running without protection.\n")

    run_guarded(user_prompt)

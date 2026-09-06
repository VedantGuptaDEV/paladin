"""
display.py — Rich terminal rendering helpers for the paladin CLI.
"""

import os
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.align import Align
from rich.rule import Rule
from rich.padding import Padding

# Simple black background console
console = Console()

# ─── Design tokens ─────────────────────────────────────────────────────────────
# Black background with bright colors for good contrast
ACCENT   = "bright_cyan"
DIM      = "grey70"
MUTED    = "grey50"
HEADER   = "bold bright_white"

def get_width():
    """Get dynamic terminal width with safe margins"""
    import os
    try:    return max(60, os.get_terminal_size().columns - 10)  # Leave 10 chars margin, min 60
    except: return 80

WIDTH = get_width()  # Dynamic width based on terminal size

RISK_COLOUR = {
    "low":      "green",
    "medium":   "yellow",
    "high":     "red",
    "critical": "bold red",
}

STATUS_COLOUR = {
    "running":          ACCENT,
    "completed":        "green",
    "failed":           "red",
    "idle":             DIM,
    "paused":           "yellow",
    "pending":          "yellow",
    "approved":         "green",
    "denied":           "red",
    "allowed":          "green",
    "blocked":          "red",
    "approval_required":"yellow",
    "analyzing":        ACCENT,
}

DECISION_ICON = {
    "allowed":          "✓",
    "blocked":          "✗",
    "approval_required":"?",
    "pending":          "·",
    "analyzing":        "⟳",
}

ACTOR_STYLE = {
    "USER":        "bright_green",
    "KIRO":        ACCENT,
    "AGENTSHIELD": "bright_magenta",
}

EVENT_ICON = {
    "user_message":  "╸",
    "agent_message": "╸",
    "tool_request":  "╸",
    "shield_decision":"╸",
    "user_approval": "╸",
    "agent_feedback":"╸",
}

ACTION_COLOUR = {"allow": "green", "ask": "yellow", "block": "red"}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _ts(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d  %H:%M")
    except Exception:
        return iso


def _c(renderable) -> Align:
    """Centre any renderable within WIDTH columns."""
    return Align.center(renderable, width=WIDTH)


def _table(**kw) -> Table:
    """Shared table style: borderless, clean header underline."""
    defaults = dict(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style=HEADER,
        border_style=DIM,
        show_edge=False,
        pad_edge=True,
        min_width=WIDTH,
    )
    defaults.update(kw)
    return Table(**defaults)


def _panel(content, *, title: str = "", border: str = DIM) -> Panel:
    return Panel(
        content,
        title=title,
        title_align="left",
        border_style=border,
        padding=(1, 3),
        width=WIDTH,
    )


# ─── Inline feedback ───────────────────────────────────────────────────────────

def rule(title: str = "") -> None:
    console.print(_c(Rule(title, style=DIM)))

def error(msg: str)   -> None: console.print(f"  [red]✗[/red]  {msg}")
def success(msg: str) -> None: console.print(f"  [green]✓[/green]  {msg}")
def warn(msg: str)    -> None: console.print(f"  [yellow]![/yellow]  {msg}")
def info(msg: str)    -> None: console.print(f"  [{DIM}]·[/{DIM}]  [{MUTED}]{msg}[/{MUTED}]")
def spinner_msg(msg: str) -> None: console.print(f"  [{ACCENT}]⟳[/{ACCENT}]  {msg}")


# ─── Sessions ──────────────────────────────────────────────────────────────────

def print_sessions(sessions: list) -> None:
    if not sessions:
        info("No sessions found.")
        return

    t = _table()
    t.add_column("ID",      style=DIM,    no_wrap=True, max_width=22)
    t.add_column("Status",                no_wrap=True)
    t.add_column("Risk",                  no_wrap=True)
    t.add_column("Agent")
    t.add_column("Actions", justify="right", no_wrap=True)
    t.add_column("Created",               no_wrap=True)
    t.add_column("Prompt")

    for s in sessions:
        status = s.get("status", "")
        risk   = s.get("risk_level", "")
        t.add_row(
            s.get("id", ""),
            f"[{STATUS_COLOUR.get(status, 'white')}]{status}[/]",
            f"[{RISK_COLOUR.get(risk, 'white')}]{risk}[/]",
            s.get("agent", ""),
            str(s.get("action_count", 0)),
            _ts(s.get("created_at", "")),
            (s.get("user_prompt") or "")[:50],
        )
    console.print(_c(t))


def print_session_detail(s: dict) -> None:
    status = s.get("status", "")
    risk   = s.get("risk_level", "")

    body = Text()
    def row(label, value): body.append(f"  {label:<12}", style=MUTED); body.append(f"{value}\n")

    row("id",      s.get("id", ""))
    row("status",  f"[{STATUS_COLOUR.get(status,'white')}]{status}[/]")
    row("risk",    f"[{RISK_COLOUR.get(risk,'white')}]{risk}[/]")
    row("agent",   s.get("agent", ""))
    row("actions", str(s.get("action_count", 0)))
    row("created", _ts(s.get("created_at", "")))
    row("prompt",  s.get("user_prompt", ""))

    console.print(_c(_panel(body, title=f"[{ACCENT}]session[/{ACCENT}]", border=ACCENT)))


def print_messages(messages: list) -> None:
    if not messages:
        info("No messages in this session yet.")
        return

    for m in messages:
        role    = m.get("role", "")
        content = m.get("content", "")
        ts      = _ts(m.get("timestamp", ""))

        if role == "user":
            title  = f"[bold green]you[/bold green]  [{DIM}]{ts}[/{DIM}]"
            border = "green"
        elif role == "agent":
            title  = f"[bold {ACCENT}]agent[/bold {ACCENT}]  [{DIM}]{ts}[/{DIM}]"
            border = ACCENT
        else:
            title  = f"[{DIM}]system  {ts}[/{DIM}]"
            border = DIM

        console.print(_c(_panel(content, title=title, border=border)))
        console.print()   # breathe


# ─── Approvals ─────────────────────────────────────────────────────────────────

def print_approvals(approvals: list) -> None:
    if not approvals:
        info("No approvals found.")
        return

    t = _table()
    t.add_column("ID",       style=DIM, no_wrap=True, max_width=22)
    t.add_column("Status",              no_wrap=True)
    t.add_column("Tool")
    t.add_column("Risk",     justify="right", no_wrap=True)
    t.add_column("Severity",            no_wrap=True)
    t.add_column("Decision",            no_wrap=True)
    t.add_column("Created",             no_wrap=True)

    for a in approvals:
        status   = a.get("status", "")
        action   = a.get("action") or {}
        decision = action.get("decision", "")
        severity = action.get("severity", "")
        t.add_row(
            a.get("id", ""),
            f"[{STATUS_COLOUR.get(status, 'white')}]{status}[/]",
            action.get("tool_name", ""),
            str(action.get("risk_score", "")),
            f"[{RISK_COLOUR.get(severity, 'white')}]{severity}[/]",
            f"[{STATUS_COLOUR.get(decision, 'white')}]{DECISION_ICON.get(decision,'')} {decision}[/]",
            _ts(a.get("created_at", "")),
        )
    console.print(_c(t))


def print_approval_detail(a: dict) -> None:
    action   = a.get("action") or {}
    status   = a.get("status", "")
    severity = action.get("severity", "")
    decision = action.get("decision", "")

    body = Text()
    def row(label, value): body.append(f"  {label:<14}", style=MUTED); body.append(f"{value}\n")

    row("approval id",  a.get("id", ""))
    row("status",       f"[{STATUS_COLOUR.get(status,'white')}]{status}[/]")
    row("tool",         action.get("tool_name", ""))
    row("risk score",   str(action.get("risk_score", "")))
    row("severity",     f"[{RISK_COLOUR.get(severity,'white')}]{severity}[/]")
    row("decision",     f"[{STATUS_COLOUR.get(decision,'white')}]{DECISION_ICON.get(decision,'')} {decision}[/]")
    row("reason",       action.get("reason", ""))
    row("created",      _ts(a.get("created_at", "")))

    if a.get("resolved_at"):
        row("resolved", _ts(a["resolved_at"]))
    if a.get("user_message"):
        row("note",     a["user_message"])

    risk_factors = action.get("risk_factors") or []
    if risk_factors:
        body.append(f"\n  {'risk factors':<14}", style=MUTED)
        body.append("\n")
        for rf in risk_factors:
            body.append(f"    [red]·[/red]  {rf}\n")

    tool_input = action.get("tool_input") or {}
    if tool_input:
        body.append(f"\n  {'tool input':<14}", style=MUTED)
        body.append("\n")
        for k, v in tool_input.items():
            body.append(f"    [{DIM}]{k}[/{DIM}]  {v}\n")

    console.print(_c(_panel(body, title=f"[yellow]approval[/yellow]", border="yellow")))


# ─── Activity ──────────────────────────────────────────────────────────────────

def print_activity(events: list) -> None:
    if not events:
        info("No activity found.")
        return

    t = _table()
    t.add_column("Time",   no_wrap=True)
    t.add_column("Actor",  no_wrap=True)
    t.add_column("Type")
    t.add_column("Summary")

    for e in events:
        actor = e.get("actor", "")
        etype = e.get("event_type", "")
        t.add_row(
            f"[{DIM}]{_ts(e.get('timestamp',''))}[/{DIM}]",
            f"[{ACTOR_STYLE.get(actor, 'white')}]{actor}[/]",
            f"[{MUTED}]{etype}[/{MUTED}]",
            e.get("summary", ""),
        )
    console.print(_c(t))


# ─── Policies ──────────────────────────────────────────────────────────────────

def print_policies(policies: list) -> None:
    if not policies:
        info("No policies found.")
        return

    t = _table()
    t.add_column("ID",          style=DIM, no_wrap=True, max_width=22)
    t.add_column("Name")
    t.add_column("Action",      no_wrap=True)
    t.add_column("Threshold",   justify="right", no_wrap=True)
    t.add_column("Enabled",     no_wrap=True)
    t.add_column("Description")

    for p in policies:
        action  = p.get("action", "")
        enabled = p.get("enabled", False)
        t.add_row(
            p.get("id", ""),
            p.get("name", ""),
            f"[{ACTION_COLOUR.get(action, 'white')}]{action}[/]",
            str(p.get("threshold", "")),
            "[green]yes[/]" if enabled else f"[{DIM}]no[/{DIM}]",
            p.get("description", ""),
        )
    console.print(_c(t))


def print_policy_test_result(result: dict) -> None:
    decision = result.get("decision", "")
    colour   = STATUS_COLOUR.get(decision, "white")
    icon     = DECISION_ICON.get(decision, "·")

    body = Text()
    def row(label, value): body.append(f"  {label:<12}", style=MUTED); body.append(f"{value}\n")

    row("decision",   f"[{colour}]{icon}  {decision}[/]")
    row("risk score", str(result.get("risk_score", "")))
    row("severity",   f"[{RISK_COLOUR.get(result.get('severity',''),'white')}]{result.get('severity','')}[/]")
    row("reason",     result.get("reason", ""))

    risk_factors = result.get("risk_factors") or []
    if risk_factors:
        body.append(f"\n  {'risk factors':<12}", style=MUTED)
        body.append("\n")
        for rf in risk_factors:
            body.append(f"    [red]·[/red]  {rf}\n")

    console.print(_c(_panel(body, title=f"[{colour}]policy test[/{colour}]", border=colour)))


# ─── Dashboard ─────────────────────────────────────────────────────────────────

def print_dashboard(stats: dict) -> None:
    if not stats:
        info("No stats available.")
        return

    cards = []
    for k, v in stats.items():
        label = k.replace("_", " ")
        cards.append(Panel(
            Align.center(f"[bold white]{v}[/bold white]\n[{MUTED}]{label}[/{MUTED}]"),
            border_style=DIM,
            padding=(1, 2),
            width=20,
        ))
    console.print(_c(Columns(cards, equal=True, expand=False)))


# ─── Config ────────────────────────────────────────────────────────────────────

def print_config(cfg_data: dict) -> None:
    body = Text()
    for k, v in cfg_data.items():
        body.append(f"  {k:<20}", style=MUTED)
        if v is not None:
            body.append(f"{v}\n")
        else:
            body.append(f"[{DIM}]—[/{DIM}]\n")

    console.print(_c(_panel(body, title=f"[{ACCENT}]paladin config[/{ACCENT}]", border=ACCENT)))


def test_colors() -> None:
    """Test function to verify color output on black background."""
    console.print("Black background theme active")
    console.print()
    
    # Test basic colors
    console.print(f"[{ACCENT}]Accent color test[/{ACCENT}]")
    console.print(f"[{DIM}]Dim text test[/{DIM}]")
    console.print(f"[{MUTED}]Muted text test[/{MUTED}]")
    console.print(f"[{HEADER}]Header text test[/{HEADER}]")
    console.print()
    
    # Test status colors
    for status, color in STATUS_COLOUR.items():
        console.print(f"[{color}]{status}[/{color}]")
    console.print()
    
    # Test a simple panel
    console.print(_c(_panel(
        "Black background with bright colors for maximum contrast.",
        title=f"[{ACCENT}]Black Background Test[/{ACCENT}]",
        border=ACCENT
    )))

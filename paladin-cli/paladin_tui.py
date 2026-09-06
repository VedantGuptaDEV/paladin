# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
paladin_tui.py  --  Paladin AgentShield  /  Terminal UI
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Footer,
    Input,
    ListItem,
    ListView,
    RichLog,
    Static,
)
from rich.text import Text
from rich.table import Table
from rich import box

# ── constants ──────────────────────────────────────────────────────────────────

VERSION  = "0.1.0"
API_BASE = os.environ.get("PALADIN_API_URL", "http://localhost:8000")
KIRO_BIN = (
    shutil.which("kiro-cli-chat")
    or shutil.which("kiro")
    or shutil.which("kiro-cli")
)

# ── palette (dark) ─────────────────────────────────────────────────────────────
#  BG       #0d1117   deepest background
#  PANEL    #161b22   sidebar, input bar, modals
#  BOOST    #21262d   dividers, hover, borders
#  ACCENT   #58a6ff   primary highlight
#  TEXT     #c9d1d9   body text
#  MUTED    #8b949e   dim text

# ── api helpers ────────────────────────────────────────────────────────────────

def _get(path: str):
    req = urllib.request.Request(
        f"{API_BASE}{path}", headers={"Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())


def _post(path: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{API_BASE}{path}", data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())


def _fmt_ts(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%H:%M:%S")
    except Exception:
        return iso[:8]


def _risk_style(score) -> str:
    try:
        v = int(score)
    except Exception:
        return "dim"
    return "bold red" if v >= 70 else ("yellow" if v >= 40 else "green")


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGETS
# ══════════════════════════════════════════════════════════════════════════════

class Clock(Widget):
    """Live HH:MM:SS clock in the status bar."""

    _t: reactive[str] = reactive("")

    DEFAULT_CSS = """
    Clock {
        width: auto;
        content-align: right middle;
        color: #58a6ff;
        padding: 0 1;
    }
    """

    def on_mount(self) -> None:
        self._tick()
        self.set_interval(1, self._tick)

    def _tick(self) -> None:
        self._t = datetime.now().strftime("%H:%M:%S")

    def watch__t(self, _: str) -> None:
        self.refresh()

    def render(self) -> Text:
        return Text(f" {self._t} ", style="bold #58a6ff")


class Spinner(Widget):
    """Braille spinner shown while Kiro is processing."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    _f: reactive[int] = reactive(0)

    DEFAULT_CSS = """
    Spinner {
        width: auto;
        height: 1;
        color: #58a6ff;
        display: none;
        padding: 0 4;
    }
    Spinner.active {
        display: block;
    }
    """

    def on_mount(self) -> None:
        self.set_interval(0.08, self._step)

    def _step(self) -> None:
        self._f = (self._f + 1) % len(self.FRAMES)

    def watch__f(self, _: int) -> None:
        self.refresh()

    def render(self) -> Text:
        return Text(f"{self.FRAMES[self._f]}  thinking…", style="italic #58a6ff")

    def show(self) -> None:
        self.add_class("active")

    def hide(self) -> None:
        self.remove_class("active")


# ── nav item ───────────────────────────────────────────────────────────────────

class NavItem(ListItem):
    def __init__(self, icon: str, label: str, view_id: str) -> None:
        super().__init__()
        self.icon    = icon
        self._label  = label
        self.view_id = view_id

    def compose(self) -> ComposeResult:
        yield Static(f"  {self.icon}  {self._label}", classes="nav-text")


# ── sidebar ────────────────────────────────────────────────────────────────────

class Sidebar(Widget):

    DEFAULT_CSS = """
    Sidebar {
        width: 22;
        height: 100%;
        background: #161b22;
        border-right: tall #21262d;
    }
    Sidebar .brand {
        height: 5;
        border-bottom: tall #21262d;
        content-align: center middle;
        align: center middle;
        padding: 0 1;
    }
    Sidebar .brand-name {
        text-style: bold;
        color: #c9d1d9;
        text-align: center;
    }
    Sidebar .brand-ver {
        color: #8b949e;
        text-align: center;
    }
    Sidebar ListView {
        background: #161b22;
        border: none;
        height: 1fr;
        padding: 1 0;
    }
    Sidebar ListItem {
        background: #161b22;
        height: 3;
        padding: 0;
        border-bottom: tall #21262d;
    }
    Sidebar ListItem:hover {
        background: #21262d;
    }
    Sidebar ListItem.--highlight {
        border-left: thick #58a6ff;
        background: #21262d;
    }
    Sidebar .nav-text {
        height: 3;
        content-align: left middle;
        color: #8b949e;
        padding: 0 1;
    }
    Sidebar ListItem.--highlight .nav-text {
        color: #58a6ff;
        text-style: bold;
    }
    Sidebar .sidebar-footer {
        dock: bottom;
        height: 8;
        border-top: tall #21262d;
        padding: 1 2;
        background: #161b22;
    }
    Sidebar .health-line {
        height: 1;
        color: #8b949e;
    }
    Sidebar .theme-btn {
        margin-top: 1;
        height: 3;
        background: #21262d;
        border: tall #58a6ff;
        color: #8b949e;
        width: 100%;
        content-align: center middle;
    }
    Sidebar .theme-btn:hover {
        color: #58a6ff;
        background: #161b22;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(classes="brand"):
            yield Static("PALADIN", classes="brand-name")
            yield Static(f"AgentShield  v{VERSION}", classes="brand-ver")

        yield ListView(
            NavItem("◉", "Session",   "session"),
            NavItem("▦", "Dashboard", "dashboard"),
            NavItem("✓", "Approvals", "approvals"),
            NavItem("≋", "Activity",  "activity"),
            NavItem("⛊", "Policies",  "policies"),
            NavItem("⚙", "Settings",  "settings"),
            id="nav-list",
        )

        with Container(classes="sidebar-footer"):
            kiro_icon = "[green]●[/]" if KIRO_BIN else "[red]●[/]"
            yield Static(f"{kiro_icon} Kiro CLI",     classes="health-line", markup=True)
            yield Static("[green]●[/] AgentShield",   classes="health-line", markup=True)
            yield Static("[green]●[/] Protection",    classes="health-line", markup=True)
            yield Button("  Toggle Theme", id="theme-btn", classes="theme-btn")

    @on(Button.Pressed, "#theme-btn")
    def _toggle(self) -> None:
        self.app.action_toggle_theme()


# ══════════════════════════════════════════════════════════════════════════════
#  CONTENT VIEWS
# ══════════════════════════════════════════════════════════════════════════════

class SessionView(Widget):

    DEFAULT_CSS = """
    SessionView {
        width: 100%;
        height: 100%;
        background: #0d1117;
        layout: vertical;
    }
    SessionView #welcome {
        height: auto;
        padding: 1 4;
        border-bottom: tall #21262d;
    }
    SessionView .wt {
        color: #58a6ff;
        text-style: bold;
    }
    SessionView .ws {
        color: #8b949e;
    }
    SessionView #log {
        width: 100%;
        height: 1fr;
        padding: 0 4;
        background: #0d1117;
    }
    SessionView #spinner {
        height: 1;
        padding: 0 4;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="welcome"):
            yield Static("Paladin  /  AgentShield", classes="wt")
            yield Static(
                "Runtime security for autonomous AI agents. "
                "Type a query or /help for commands.",
                classes="ws",
            )
        yield RichLog(id="log", highlight=True, markup=True, wrap=True)
        yield Spinner(id="spinner")

    def post(self, role: str, content: str) -> None:
        log = self.query_one("#log", RichLog)
        ts  = datetime.now().strftime("%H:%M:%S")
        BADGE = {
            "user":    "[bold #58a6ff] you  [/]",
            "kiro":    "[bold #3fb950] kiro [/]",
            "system":  "[dim #8b949e] sys  [/]",
            "error":   "[bold #f85149] err  [/]",
            "info":    "[bold #58a6ff] info [/]",
            "success": "[bold #3fb950] ok   [/]",
        }
        COLOR = {
            "user":    "#c9d1d9",
            "kiro":    "#c9d1d9",
            "system":  "#8b949e",
            "error":   "#f85149",
            "info":    "#c9d1d9",
            "success": "#3fb950",
        }
        badge = BADGE.get(role, "[dim] ??? [/]")
        color = COLOR.get(role, "#c9d1d9")
        log.write(Text.from_markup(
            f"[dim #8b949e]{ts}[/]  {badge}  [{color}]{content}[/]"
        ))

    def thinking(self, active: bool) -> None:
        try:
            s = self.query_one("#spinner", Spinner)
            s.show() if active else s.hide()
        except NoMatches:
            pass


class DashboardView(Widget):

    DEFAULT_CSS = """
    DashboardView {
        width: 100%;
        height: 100%;
        background: #0d1117;
        padding: 2 4;
        overflow-y: scroll;
    }
    DashboardView .vt { color: #58a6ff; text-style: bold; margin-bottom: 1; }
    DashboardView .vd { color: #21262d; margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Static("▦  Dashboard", classes="vt")
        yield Static("─" * 56, classes="vd")
        yield Static(id="body")

    def on_mount(self) -> None:
        self._load()

    @work(thread=True)
    def _load(self) -> None:
        try:
            data = _get("/stats")
        except Exception:
            data = {"actions_analyzed": 47, "allowed": 38,
                    "approval_required": 5, "blocked": 4, "avg_risk": 23}
        self.app.call_from_thread(self._render, data)

    def _render(self, s: dict) -> None:
        from io import StringIO
        from rich.console import Console as RC

        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        t.add_column("k", style="dim")
        t.add_column("v", justify="right", style="bold")
        t.add_row("Actions Analyzed", str(s.get("actions_analyzed", "-")))
        t.add_row("[green]Allowed[/]",       f"[green]{s.get('allowed','-')}[/]")
        t.add_row("[yellow]Needs Review[/]", f"[yellow]{s.get('approval_required','-')}[/]")
        t.add_row("[red]Blocked[/]",         f"[red]{s.get('blocked','-')}[/]")
        t.add_row("Avg Risk",          str(s.get("avg_risk", "-")))

        h = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        h.add_column("k", style="dim")
        h.add_column("v")
        h.add_row("AgentShield", "[green]active[/]")
        h.add_row("Kiro CLI",
                  f"[green]{KIRO_BIN}[/]" if KIRO_BIN else "[red]not found[/]")
        h.add_row("Auto Block",  "[green]enabled[/]")
        h.add_row("Auto Allow",  "[green]enabled[/]")

        buf = StringIO()
        c = RC(file=buf, force_terminal=False, width=80)
        c.print("[bold]  Action Summary[/]"); c.print(t)
        c.print("[bold]  System Health[/]");  c.print(h)
        self.query_one("#body", Static).update(buf.getvalue())


class ApprovalsView(Widget):

    DEFAULT_CSS = """
    ApprovalsView {
        width: 100%;
        height: 100%;
        background: #0d1117;
        padding: 2 4;
        overflow-y: scroll;
    }
    ApprovalsView .vt { color: #58a6ff; text-style: bold; margin-bottom: 1; }
    ApprovalsView .vd { color: #21262d; margin-bottom: 1; }
    """

    MOCK = [
        {"id": "APR001", "action": {"tool_name": "bash",       "risk_score": 72}},
        {"id": "APR002", "action": {"tool_name": "write_file", "risk_score": 45}},
    ]

    def compose(self) -> ComposeResult:
        yield Static("✓  Approvals", classes="vt")
        yield Static("─" * 56, classes="vd")
        yield Static(id="body")

    def on_mount(self) -> None:
        self.load()

    @work(thread=True)
    def load(self) -> None:
        try:
            data = _get("/approvals?status=pending")
        except Exception:
            data = self.MOCK
        self.app.call_from_thread(self._render, data)

    def _render(self, items: list) -> None:
        if not items:
            self.query_one("#body", Static).update(
                "\n  [dim]No pending approvals.[/dim]"
            )
            return
        t = Table("ID", "Tool", "Risk", "Actions",
                  box=box.SIMPLE_HEAD, header_style="bold",
                  style="dim", expand=True)
        for a in items:
            aid  = a.get("id", "?")
            act  = a.get("action", {})
            tool = act.get("tool_name", "?") if isinstance(act, dict) else "?"
            risk = act.get("risk_score",  "?") if isinstance(act, dict) else "?"
            t.add_row(
                f"[bold]{aid}[/]",
                f"[cyan]{tool}[/]",
                f"[{_risk_style(risk)}]{risk}[/]",
                f"[dim]approve {aid}   deny {aid}[/]",
            )
        from io import StringIO
        from rich.console import Console as RC
        buf = StringIO()
        RC(file=buf, force_terminal=False, width=90).print(t)
        self.query_one("#body", Static).update(
            f"\n  [yellow]Pending:[/] {len(items)}\n\n" + buf.getvalue()
        )


class ActivityView(Widget):

    DEFAULT_CSS = """
    ActivityView {
        width: 100%;
        height: 100%;
        background: #0d1117;
        padding: 2 4;
        overflow-y: scroll;
    }
    ActivityView .vt { color: #58a6ff; text-style: bold; margin-bottom: 1; }
    ActivityView .vd { color: #21262d; margin-bottom: 1; }
    """

    MOCK = [
        {"timestamp": "2024-01-01T10:00:00Z", "tool_name": "bash",       "decision": "allowed",           "risk_score": 12},
        {"timestamp": "2024-01-01T10:01:00Z", "tool_name": "read_file",  "decision": "allowed",           "risk_score": 8},
        {"timestamp": "2024-01-01T10:02:00Z", "tool_name": "write_file", "decision": "approval_required", "risk_score": 65},
        {"timestamp": "2024-01-01T10:03:00Z", "tool_name": "bash",       "decision": "blocked",           "risk_score": 88},
        {"timestamp": "2024-01-01T10:04:00Z", "tool_name": "http_call",  "decision": "allowed",           "risk_score": 30},
    ]

    def compose(self) -> ComposeResult:
        yield Static("≋  Activity Log", classes="vt")
        yield Static("─" * 56, classes="vd")
        yield Static(id="body")

    def on_mount(self) -> None:
        self._load()

    @work(thread=True)
    def _load(self) -> None:
        try:
            data = _get("/activity")
        except Exception:
            data = self.MOCK
        self.app.call_from_thread(self._render, data)

    def _render(self, items: list) -> None:
        if not items:
            self.query_one("#body", Static).update("\n  [dim]No activity.[/dim]")
            return
        t = Table("Time", "Tool", "Decision", "Risk",
                  box=box.SIMPLE_HEAD, header_style="bold",
                  style="dim", expand=True)
        for e in items[:50]:
            ts   = _fmt_ts(e.get("timestamp", ""))
            tool = e.get("tool_name", "?")
            dec  = e.get("decision",  "?")
            risk = e.get("risk_score", "?")
            df = (f"[green]{dec}[/]"  if dec == "allowed"
                  else f"[red]{dec}[/]" if dec == "blocked"
                  else "[yellow]review[/]")
            t.add_row(
                f"[dim]{ts}[/]",
                f"[cyan]{tool}[/]",
                df,
                f"[{_risk_style(risk)}]{risk}[/]",
            )
        from io import StringIO
        from rich.console import Console as RC
        buf = StringIO()
        RC(file=buf, force_terminal=False, width=90).print(t)
        self.query_one("#body", Static).update(buf.getvalue())


class PoliciesView(Widget):

    DEFAULT_CSS = """
    PoliciesView {
        width: 100%;
        height: 100%;
        background: #0d1117;
        padding: 2 4;
        overflow-y: scroll;
    }
    PoliciesView .vt { color: #58a6ff; text-style: bold; margin-bottom: 1; }
    PoliciesView .vd { color: #21262d; margin-bottom: 1; }
    """

    MOCK = [
        {"id": "POL001", "name": "No shell access",                  "action": "block",    "enabled": True},
        {"id": "POL002", "name": "Require approval for file writes", "action": "approval", "enabled": True},
        {"id": "POL003", "name": "Allow read-only operations",       "action": "allow",    "enabled": True},
    ]

    def compose(self) -> ComposeResult:
        yield Static("⛊  Policies", classes="vt")
        yield Static("─" * 56, classes="vd")
        yield Static(id="body")

    def on_mount(self) -> None:
        self._load()

    @work(thread=True)
    def _load(self) -> None:
        try:
            data = _get("/policies")
        except Exception:
            data = self.MOCK
        self.app.call_from_thread(self._render, data)

    def _render(self, items: list) -> None:
        if not items:
            self.query_one("#body", Static).update(
                "\n  [dim]No policies. Run [bold]paladin policy add[/bold].[/dim]"
            )
            return
        t = Table("", "ID", "Name", "Action",
                  box=box.SIMPLE_HEAD, header_style="bold",
                  style="dim", expand=True)
        for p in items:
            en  = "[green]●[/]" if p.get("enabled", True) else "[red]●[/]"
            act = p.get("action", "?")
            af  = (f"[red]{act}[/]"    if act == "block"
                   else f"[green]{act}[/]" if act == "allow"
                   else f"[yellow]{act}[/]")
            t.add_row(en, f"[bold]{p.get('id','?')}[/]", p.get("name", "?"), af)
        from io import StringIO
        from rich.console import Console as RC
        buf = StringIO()
        RC(file=buf, force_terminal=False, width=90).print(t)
        self.query_one("#body", Static).update(
            f"\n  [bold]Active:[/] {len(items)}\n\n" + buf.getvalue()
        )


class SettingsView(Widget):

    DEFAULT_CSS = """
    SettingsView {
        width: 100%;
        height: 100%;
        background: #0d1117;
        padding: 2 4;
        overflow-y: scroll;
    }
    SettingsView .vt { color: #58a6ff; text-style: bold; margin-bottom: 1; }
    SettingsView .vd { color: #21262d; margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Static("⚙  Settings", classes="vt")
        yield Static("─" * 56, classes="vd")
        yield Static(id="body")

    def on_mount(self) -> None:
        from io import StringIO
        from rich.console import Console as RC

        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        t.add_column("k", style="dim")
        t.add_column("v", style="bold")
        kiro = f"[green]{KIRO_BIN}[/]" if KIRO_BIN else "[red]not found[/]"
        t.add_row("Version",   f"v{VERSION}")
        t.add_row("API",       API_BASE)
        t.add_row("Kiro CLI",  kiro)
        t.add_row("Theme",     "press  t  to toggle")
        t.add_row("Sidebar",   "press  s  to toggle")

        kb = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        kb.add_column("key",  style="bold cyan", width=10)
        kb.add_column("desc", style="dim")
        for key, desc in [
            ("s",      "Toggle sidebar"),
            ("t",      "Toggle theme"),
            ("q",      "Quit"),
            ("?",      "Help"),
            ("Escape", "Close modal"),
        ]:
            kb.add_row(key, desc)

        buf = StringIO()
        c = RC(file=buf, force_terminal=False, width=80)
        c.print("[bold]  Configuration[/]");     c.print(t)
        c.print("[bold]  Keyboard Shortcuts[/]"); c.print(kb)
        self.query_one("#body", Static).update(buf.getvalue())


# ══════════════════════════════════════════════════════════════════════════════
#  HELP MODAL
# ══════════════════════════════════════════════════════════════════════════════

class HelpModal(ModalScreen):

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
    }
    HelpModal #box {
        width: 68;
        height: 42;
        background: #161b22;
        border: double #58a6ff;
        padding: 1 2;
        overflow-y: scroll;
    }
    HelpModal .ht {
        text-style: bold;
        color: #58a6ff;
        text-align: center;
    }
    HelpModal .hd {
        color: #21262d;
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="box"):
            yield Static("PALADIN  --  Help", classes="ht")
            yield Static("=" * 60, classes="hd")
            yield Static(
                "\n[bold]Commands[/]\n\n"
                "  [cyan]paladin init[/]              Initialize config\n"
                "  [cyan]paladin start[/]             Connect to backend\n"
                "  [cyan]paladin status[/]            Session status\n"
                "  [cyan]paladin run <query>[/]       Send query to Kiro\n\n"
                "  [cyan]paladin approvals[/]         Pending approvals\n"
                "  [cyan]paladin approve <id>[/]      Approve action\n"
                "  [cyan]paladin deny <id>[/]         Deny action\n\n"
                "  [cyan]paladin activity[/]          Activity log\n"
                "  [cyan]paladin activity <id>[/]     Detail for ID\n\n"
                "  [cyan]paladin policy list[/]       List policies\n"
                "  [cyan]paladin policy add[/]        Add policy\n"
                "  [cyan]paladin policy test[/]       Test policy\n\n"
                "  [cyan]paladin config[/]            Configuration\n"
                "  [cyan]paladin doctor[/]            Health check\n"
                "  [cyan]paladin version[/]           Version info\n\n"
                "[bold]Slash commands[/]\n\n"
                "  [cyan]/help[/]   Show this screen\n"
                "  [cyan]/clear[/]  Clear the log\n"
                "  [cyan]/theme[/]  Toggle theme\n\n"
                "[bold]Keys[/]\n\n"
                "  [cyan]s[/]  sidebar   [cyan]t[/]  theme   "
                "[cyan]q[/]  quit   [cyan]?[/]  help   [cyan]Esc[/]  close\n",
                markup=True,
            )
            yield Static("\n  Escape to close", style="dim", markup=False)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

VIEWS = ["session", "dashboard", "approvals", "activity", "policies", "settings"]


class PaladinApp(App):

    TITLE     = "Paladin"
    SUB_TITLE = "AgentShield"

    CSS = """
    Screen {
        background: #0d1117;
        layers: base overlay;
    }
    #root {
        width: 100%;
        height: 100%;
        layout: vertical;
    }
    #body-row {
        width: 100%;
        height: 1fr;
        layout: horizontal;
    }
    #right {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }
    #stack {
        width: 100%;
        height: 1fr;
        overflow: hidden;
    }

    /* input bar */
    #input-bar {
        height: 3;
        background: #161b22;
        border-top: tall #21262d;
        layout: horizontal;
        padding: 0 2;
    }
    #prompt {
        width: auto;
        height: 3;
        content-align: left middle;
        color: #58a6ff;
        text-style: bold;
        padding: 0 1;
    }
    #query {
        width: 1fr;
        height: 3;
        background: #161b22;
        border: none;
        color: #c9d1d9;
        padding: 0 1;
    }
    #query:focus {
        background: #21262d;
        border: none;
    }
    #send {
        width: 9;
        height: 3;
        background: #58a6ff;
        color: #0d1117;
        border: none;
        text-style: bold;
        margin-left: 1;
        content-align: center middle;
    }
    #send:hover {
        background: #c9d1d9;
        color: #0d1117;
    }

    /* status bar */
    #status-bar {
        dock: bottom;
        height: 1;
        background: #161b22;
        layout: horizontal;
        padding: 0 2;
        border-top: tall #21262d;
    }
    #sb-left {
        width: 1fr;
        content-align: left middle;
        color: #8b949e;
    }
    #sb-mid {
        width: auto;
        content-align: center middle;
        color: #8b949e;
    }
    #sb-right {
        width: auto;
        content-align: right middle;
        color: #58a6ff;
    }

    /* sidebar */
    Sidebar.hidden { display: none; }

    /* view toggling */
    .hidden-view { display: none; }

    /* footer */
    Footer {
        background: #161b22;
        color: #8b949e;
        height: 1;
    }
    """

    BINDINGS = [
        Binding("s",      "toggle_sidebar", "Sidebar", show=True),
        Binding("t",      "toggle_theme",   "Theme",   show=True),
        Binding("q",      "quit",           "Quit",    show=True),
        Binding("?",      "help",           "Help",    show=True),
        Binding("ctrl+c", "quit",           "",        show=False),
    ]

    _dark: reactive[bool] = reactive(True)

    # ── compose ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Vertical(id="root"):
            with Horizontal(id="body-row"):
                yield Sidebar(id="sidebar")
                with Vertical(id="right"):
                    with Container(id="stack"):
                        yield SessionView(id="v-session")
                        yield DashboardView(id="v-dashboard")
                        yield ApprovalsView(id="v-approvals")
                        yield ActivityView(id="v-activity")
                        yield PoliciesView(id="v-policies")
                        yield SettingsView(id="v-settings")
                    with Horizontal(id="input-bar"):
                        yield Static("❯", id="prompt")
                        yield Input(placeholder="command or query…", id="query")
                        yield Button("Send", id="send")
            with Horizontal(id="status-bar"):
                yield Static(
                    "◉ Session #A82F  ·  [green]active[/]  ·  AgentShield",
                    id="sb-left", markup=True,
                )
                yield Static(
                    "  s sidebar   t theme   ? help   q quit  ",
                    id="sb-mid",
                )
                yield Clock(id="sb-right")
        yield Footer()

    def on_mount(self) -> None:
        self._switch("session")
        self.query_one("#query", Input).focus()

    # ── view switch ────────────────────────────────────────────────────────────

    def _switch(self, view_id: str) -> None:
        for v in VIEWS:
            try:
                w = self.query_one(f"#v-{v}")
                if v == view_id:
                    w.remove_class("hidden-view")
                else:
                    w.add_class("hidden-view")
            except NoMatches:
                pass

    @on(ListView.Selected, "#nav-list")
    def _nav(self, event: ListView.Selected) -> None:
        item = event.item
        if hasattr(item, "view_id"):
            self._switch(item.view_id)

    # ── input ──────────────────────────────────────────────────────────────────

    @on(Input.Submitted, "#query")
    def _submitted(self, event: Input.Submitted) -> None:
        self._handle(event.value)
        event.input.clear()

    @on(Button.Pressed, "#send")
    def _send_pressed(self) -> None:
        inp = self.query_one("#query", Input)
        self._handle(inp.value)
        inp.clear()
        inp.focus()

    def _handle(self, raw: str) -> None:
        text = raw.strip()
        if not text:
            return
        self._switch("session")
        sv = self._sv()
        if not sv:
            return
        sv.post("user", text)

        if text in ("?", "help"):
            self.action_help()
        elif text.startswith("/"):
            self._slash(text[1:], sv)
        elif text.lower().startswith("paladin"):
            self._paladin_cmd(text[7:].strip(), sv)
        else:
            self._kiro(text, sv)

    def _sv(self) -> Optional[SessionView]:
        try:
            return self.query_one("#v-session", SessionView)
        except NoMatches:
            return None

    # ── slash commands ─────────────────────────────────────────────────────────

    def _slash(self, cmd: str, sv: SessionView) -> None:
        c = cmd.strip().lower()
        if c in ("help", "h", "?"):
            self.action_help()
        elif c == "clear":
            try:
                sv.query_one("#log", RichLog).clear()
            except NoMatches:
                pass
            sv.post("system", "Log cleared.")
        elif c == "theme":
            self.action_toggle_theme()
            sv.post("system", f"Theme: {'light' if not self._dark else 'dark'}.")
        elif c.startswith("run "):
            self._kiro(c[4:].strip(), sv)
        else:
            sv.post("error", f"Unknown: /{cmd}  --  try /help")

    # ── paladin commands ───────────────────────────────────────────────────────

    def _paladin_cmd(self, cmd: str, sv: SessionView) -> None:
        parts = cmd.strip().split()
        if not parts:
            sv.post("info", f"Paladin v{VERSION} -- AgentShield.  /help for commands.")
            return

        base, args = parts[0].lower(), parts[1:]

        def goto(view: str, msg: str) -> None:
            self._switch(view); sv.post("system", msg)

        dispatch = {
            "init":      lambda: self._w_init(sv),
            "start":     lambda: self._w_start(sv),
            "status":    lambda: self._w_status(sv),
            "config":    lambda: goto("settings",  "Settings."),
            "approvals": lambda: goto("approvals", "Approvals."),
            "doctor":    lambda: self._w_doctor(sv),
            "version":   lambda: sv.post("info",
                f"Paladin v{VERSION}  "
                f"Python {sys.version.split()[0]}  "
                f"Kiro: {KIRO_BIN or 'not found'}  "
                f"API: {API_BASE}"),
            "approve":   lambda: (
                self._w_approve(args[0], sv) if args
                else sv.post("error", "Usage: paladin approve <id>")),
            "deny":      lambda: (
                self._w_deny(args[0], sv) if args
                else sv.post("error", "Usage: paladin deny <id>")),
            "run":       lambda: (
                self._kiro(" ".join(args), sv) if args
                else sv.post("error", "Usage: paladin run <query>")),
            "activity":  lambda: (
                self._w_activity_detail(args[0], sv) if args
                else goto("activity", "Activity.")),
            "policy":    lambda: self._policy_cmd(args, sv),
        }

        fn = dispatch.get(base)
        if fn:
            fn()
        else:
            sv.post("error", f"Unknown: {base}  --  try /help")

    def _policy_cmd(self, args: list, sv: SessionView) -> None:
        sub = args[0].lower() if args else "list"
        if sub == "list":
            self._switch("policies"); sv.post("system", "Policies.")
        elif sub == "add":
            sv.post("info", "Use the web dashboard at http://localhost:8000")
        elif sub == "test":
            sv.post("info", "Policy test -- coming soon.")
        else:
            sv.post("error", f"Unknown: policy {sub}")

    # ── workers ────────────────────────────────────────────────────────────────

    @work(thread=True)
    def _kiro(self, query: str, sv: SessionView) -> None:
        if not query:
            return
        if not KIRO_BIN:
            self.app.call_from_thread(
                sv.post, "error",
                "Kiro CLI not found. Install from https://kiro.ai"
            )
            return
        self.app.call_from_thread(sv.thinking, True)
        try:
            r = subprocess.run(
                [KIRO_BIN, "chat", "--no-interactive", query],
                capture_output=True, text=True, timeout=60,
            )
            out = r.stdout.strip() or r.stderr.strip() or "(no output)"
            self.app.call_from_thread(sv.post, "kiro", out)
        except subprocess.TimeoutExpired:
            self.app.call_from_thread(sv.post, "error", "Timed out after 60 s.")
        except Exception as e:
            self.app.call_from_thread(sv.post, "error", str(e))
        finally:
            self.app.call_from_thread(sv.thinking, False)

    @work(thread=True)
    def _w_init(self, sv: SessionView) -> None:
        cfg = {
            "version": VERSION, "api_base": API_BASE,
            "created_at": datetime.now().isoformat(),
            "policies": [],
            "auto_block_risk_threshold": 80,
            "auto_allow_risk_threshold": 20,
        }
        try:
            path = os.path.join(os.getcwd(), ".paladin.json")
            with open(path, "w") as f:
                json.dump(cfg, f, indent=2)
            self.app.call_from_thread(sv.post, "success", f"Initialized  ->  {path}")
        except Exception as e:
            self.app.call_from_thread(sv.post, "error", str(e))

    @work(thread=True)
    def _w_start(self, sv: SessionView) -> None:
        self.app.call_from_thread(sv.post, "system", "Connecting...")
        try:
            s = _get("/sessions")
            count = len(s) if isinstance(s, list) else "?"
            self.app.call_from_thread(
                sv.post, "success", f"Connected to {API_BASE}.  Sessions: {count}"
            )
        except Exception:
            self.app.call_from_thread(
                sv.post, "success", "Running in offline mode (backend unreachable)."
            )

    @work(thread=True)
    def _w_status(self, sv: SessionView) -> None:
        try:
            s = _get("/sessions/A82F")
            self.app.call_from_thread(sv.post, "info",
                f"Session #{s.get('id','A82F')}  "
                f"agent: {s.get('agent','Kiro')}  "
                f"status: {s.get('status','running')}  "
                f"actions: {s.get('action_count',0)}")
        except Exception:
            kiro = "found" if KIRO_BIN else "not found"
            self.app.call_from_thread(sv.post, "info",
                f"TUI running  Kiro: {kiro}  Backend: unreachable  offline")

    @work(thread=True)
    def _w_approve(self, aid: str, sv: SessionView) -> None:
        try:
            _post(f"/approvals/{aid}/decision",
                  {"approval_id": aid, "status": "approved"})
            self.app.call_from_thread(sv.post, "success", f"Approved {aid}.")
        except Exception as e:
            self.app.call_from_thread(sv.post, "error", str(e))

    @work(thread=True)
    def _w_deny(self, aid: str, sv: SessionView) -> None:
        try:
            _post(f"/approvals/{aid}/decision",
                  {"approval_id": aid, "status": "denied"})
            self.app.call_from_thread(sv.post, "success", f"Denied {aid}.")
        except Exception as e:
            self.app.call_from_thread(sv.post, "error", str(e))

    @work(thread=True)
    def _w_activity_detail(self, did: str, sv: SessionView) -> None:
        try:
            d = _get(f"/activity/{did}")
            body = "\n".join(f"  {k}: {v}" for k, v in d.items())
            self.app.call_from_thread(sv.post, "info", f"Activity {did}\n{body}")
        except Exception as e:
            self.app.call_from_thread(sv.post, "error", str(e))

    @work(thread=True)
    def _w_doctor(self, sv: SessionView) -> None:
        checks = []

        if KIRO_BIN:
            checks.append(("[green]✓[/]", "Kiro CLI", str(KIRO_BIN)))
        else:
            checks.append(("[red]✗[/]", "Kiro CLI",
                           "not found -- install from https://kiro.ai"))

        maj, minor_ = sys.version_info[:2]
        checks.append((
            "[green]✓[/]" if (maj, minor_) >= (3, 8) else "[red]✗[/]",
            "Python", f"{maj}.{minor_}",
        ))

        for pkg in ("textual", "rich"):
            try:
                m = __import__(pkg)
                checks.append(
                    ("[green]✓[/]", pkg.capitalize(),
                     getattr(m, "__version__", "installed"))
                )
            except ImportError:
                checks.append(("[red]✗[/]", pkg.capitalize(), "not installed"))

        try:
            _get("/")
            checks.append(("[green]✓[/]", "Backend", f"reachable  {API_BASE}"))
        except Exception:
            checks.append(("[yellow]![/]", "Backend", f"unreachable  {API_BASE}"))

        cfg_ok = os.path.exists(".paladin.json")
        checks.append((
            "[green]✓[/]" if cfg_ok else "[yellow]![/]",
            "Config",
            ".paladin.json found" if cfg_ok else "missing -- run paladin init",
        ))

        lines = ["[bold]Doctor[/]\n"]
        for icon, name, detail in checks:
            lines.append(f"  {icon}  [bold]{name:<14}[/]  {detail}")
        ok = all(c[0] == "[green]✓[/]" for c in checks)
        lines.append(
            "\n  " + ("[green]All checks passed.[/]" if ok else "[yellow]Some issues.[/]")
        )
        self.app.call_from_thread(sv.post, "info", "\n".join(lines))

    # ── actions ────────────────────────────────────────────────────────────────

    def action_toggle_sidebar(self) -> None:
        sb = self.query_one("#sidebar", Sidebar)
        if "hidden" in sb.classes:
            sb.remove_class("hidden")
        else:
            sb.add_class("hidden")

    def action_toggle_theme(self) -> None:
        self._dark = not self._dark
        if self._dark:
            self.screen.styles.background = "#0d1117"
            try:
                self.query_one("#sidebar").styles.background    = "#161b22"
                self.query_one("#input-bar").styles.background  = "#161b22"
                self.query_one("#query").styles.background      = "#161b22"
                self.query_one("#status-bar").styles.background = "#161b22"
                self.query_one("#query", Input).styles.color    = "#c9d1d9"
            except NoMatches:
                pass
        else:
            self.screen.styles.background = "#ffffff"
            try:
                self.query_one("#sidebar").styles.background    = "#f6f8fa"
                self.query_one("#input-bar").styles.background  = "#f6f8fa"
                self.query_one("#query").styles.background      = "#f6f8fa"
                self.query_one("#status-bar").styles.background = "#f6f8fa"
                self.query_one("#query", Input).styles.color    = "#24292f"
            except NoMatches:
                pass

    def action_help(self) -> None:
        self.push_screen(HelpModal())

    def action_quit(self) -> None:
        self.exit()


# ── entry point ────────────────────────────────────────────────────────────────

def run_tui() -> None:
    PaladinApp().run()


if __name__ == "__main__":
    run_tui()

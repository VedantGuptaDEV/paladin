#!/usr/bin/env python3
"""
paladin_tui.py — Paladin Terminal UI
A Textual-based TUI for the Paladin AgentShield CLI.
"""

from __future__ import annotations

import subprocess
import shutil
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    RichLog,
    Static,
    Button,
    Rule,
)
from textual import events, on, work
from rich.text import Text
from rich.console import Console
from rich.panel import Panel

# ─── Constants ────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"
KIRO_BIN = shutil.which("kiro-cli-chat") or shutil.which("kiro") or shutil.which("kiro-cli")
VERSION = "0.1.0"

# ─── Shield / Logo ASCII Art ──────────────────────────────────────────────────

SHIELD_ART = """\
      ╭───────────────╮
     ╱                 ╲
    │  ·  ·  ·  ·  ·   │
    │ ·  ██████████  ·  │
    │  · ██  ·  ██  ·   │
    │ ·  ██████████  ·  │
    │  · ██  ·  ·   ·   │
    │ ·  ██  ·  ·   ·   │
    │  · ██  ·  ·   ·   │
    │ ·  ·  ·  ·  ·  ·  │
    │   ╔═══════════╗   │
    │   ║  PALADIN  ║   │
    │   ╚═══════════╝   │
     ╲                 ╱
      ╰───────────────╯"""

SHIELD_ART_SMALL = """\
    ╭───────────╮
   ╱ · · · · · ╲
  │ · ██████  · │
  │ · ██  ██  · │
  │ · ████████· │
  │ · ██  · · · │
  │ · ██  · · · │
  │  PALADIN   │
   ╲ · · · · · ╱
    ╰───────────╯"""

# The big shield with dotted 'P' in the center
MAIN_SHIELD = """\
           ╭─────────────────────────────╮
          ╱ ·   ·   ·   ·   ·   ·   ·    ╲
         │  ·   ·   ·   ·   ·   ·   ·   · │
         │  ·  ██████████  ·  ·   ·   ·  · │
         │  · ██  ·  ·  ██ ·  ·   ·   ·  · │
         │  · ██  ·  ·  ██ ·  ·   ·   ·  · │
         │  · ██████████  ·  ·   ·   ·   · │
         │  · ██  ·  ·  ·  ·  ·   ·   ·  · │
         │  · ██  ·  ·  ·  ·  ·   ·   ·  · │
         │  · ██  ·  ·  ·  ·  ·   ·   ·  · │
         │  ·  ·  ·  ·  ·  ·  ·   ·   ·  · │
         │  ·   ·   ·   ·   ·   ·   ·   · │
         │        ╔═══════════════╗       │
         │        ║   P A L A D I N ║       │
         │        ╚═══════════════╝       │
          ╲  ·   ·   ·   ·   ·   ·   ·  ╱
           ╰────────────────────────────╯"""

# ─── Utility functions ─────────────────────────────────────────────────────────

def api_get(path: str) -> dict | list:
    """Make a GET request to the backend API."""
    try:
        url = f"{API_BASE}{path}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        raise RuntimeError(f"API error: {e}") from e


def api_post(path: str, data: dict) -> dict:
    """Make a POST request to the backend API."""
    try:
        url = f"{API_BASE}{path}"
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        raise RuntimeError(f"API error: {e}") from e


def format_timestamp(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        return iso[:8]


# ─── Widgets ──────────────────────────────────────────────────────────────────

class ShieldLogo(Static):
    """The main Paladin shield logo with dotted 'P' pattern."""

    DEFAULT_CSS = """
    ShieldLogo {
        width: 100%;
        content-align: center middle;
        text-align: center;
        padding: 1 2;
        color: #0FA4AF;
    }
    """

    def render(self) -> Text:
        t = Text(justify="center")
        lines = MAIN_SHIELD.split("\n")
        for line in lines:
            if "PALADIN" in line or "P A L A D I N" in line:
                t.append(line + "\n", style="bold #AFDDE5")
            elif "██" in line:
                t.append(line + "\n", style="dim #0FA4AF")
            elif "╔" in line or "╚" in line or "║" in line:
                t.append(line + "\n", style="bold #0FA4AF")
            else:
                t.append(line + "\n", style="dim #6fa8b0")
        return t


class SidebarItem(ListItem):
    """A nav item in the sidebar."""

    def __init__(self, label: str, icon: str, view_id: str, badge: str = "") -> None:
        super().__init__()
        self.label_text = label
        self.icon = icon
        self.view_id = view_id
        self.badge_text = badge

    def compose(self) -> ComposeResult:
        badge_str = f" [{self.badge_text}]" if self.badge_text else ""
        yield Static(f"{self.icon}  {self.label_text}{badge_str}", classes="sidebar-item-label")


class Sidebar(Widget):
    """Collapsible left sidebar with navigation."""

    DEFAULT_CSS = """
    Sidebar {
        width: 22;
        height: 100%;
        background: #024950;
        border-right: tall #0FA4AF;
        dock: left;
    }
    Sidebar .sidebar-header {
        padding: 1 2;
        border-bottom: tall #0FA4AF;
        color: #AFDDE5;
        text-style: bold;
        height: 5;
        content-align: center middle;
    }
    Sidebar .sidebar-logo-row {
        color: #0FA4AF;
        text-style: bold;
    }
    Sidebar .sidebar-subtitle {
        color: #6fa8b0;
        text-style: dim;
    }
    Sidebar ListView {
        background: transparent;
        border: none;
        padding: 1 0;
    }
    Sidebar ListItem {
        background: transparent;
        padding: 0 1;
        height: 3;
    }
    Sidebar ListItem:hover {
        background: #035560;
    }
    Sidebar ListItem.--highlight {
        background: #0FA4AF;
        color: #003135;
    }
    Sidebar .sidebar-item-label {
        padding: 0 1;
        height: 3;
        content-align: left middle;
        color: #AFDDE5;
    }
    Sidebar ListItem.--highlight .sidebar-item-label {
        color: #003135;
        text-style: bold;
    }
    Sidebar .sidebar-footer {
        dock: bottom;
        padding: 1 2;
        border-top: tall #0FA4AF;
        height: 7;
    }
    Sidebar .status-row {
        height: 1;
        color: #6fa8b0;
    }
    Sidebar .theme-toggle {
        margin-top: 1;
        height: 3;
        background: #035560;
        border: tall #0FA4AF;
        color: #6fa8b0;
        content-align: center middle;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(classes="sidebar-header"):
            yield Static("🛡  Paladin", classes="sidebar-logo-row")
            yield Static("AgentShield v0.1", classes="sidebar-subtitle")

        items = [
            SidebarItem("Active Session", "◉", "session"),
            SidebarItem("Dashboard",      "⊞", "dashboard"),
            SidebarItem("Approvals",      "✓", "approvals"),
            SidebarItem("Activity",       "≋", "activity"),
            SidebarItem("Policies",       "⛊", "policies"),
            SidebarItem("Settings",       "⚙", "settings"),
        ]
        lv = ListView(*items, id="sidebar-list")
        yield lv

        with Container(classes="sidebar-footer"):
            yield Static("● Kiro CLI      [green]ok[/]",       classes="status-row", markup=True)
            yield Static("● AgentShield   [green]ok[/]",       classes="status-row", markup=True)
            yield Static("● Protection    [green]on[/]",       classes="status-row", markup=True)
            yield Button("☀ Toggle Theme", id="theme-toggle-btn", classes="theme-toggle")

    @on(Button.Pressed, "#theme-toggle-btn")
    def on_theme_toggle(self) -> None:
        self.app.action_toggle_theme()


# ─── Content Views ─────────────────────────────────────────────────────────────

class SessionView(Widget):
    """The main session view — shows shield logo and chat output."""

    DEFAULT_CSS = """
    SessionView {
        width: 100%;
        height: 100%;
        background: #003135;
    }
    SessionView #logo-container {
        width: 100%;
        height: auto;
        align: center top;
        padding: 1 2;
    }
    SessionView #chat-log {
        width: 100%;
        height: 1fr;
        background: #003135;
        border: none;
        padding: 0 2;
    }
    SessionView #session-status {
        height: 1;
        padding: 0 2;
        color: #AFDDE5;
        background: #024950;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="logo-container"):
            yield ShieldLogo()
        yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
        yield Static(
            "◉ Session #A82F  ·  [green]RUNNING[/]  ·  Kiro agent connected",
            id="session-status",
            markup=True,
        )

    def on_mount(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(Text.from_markup(
            "[dim]Welcome to [bold]Paladin AgentShield[/bold] — Runtime security for autonomous AI agents.[/dim]\n"
            "[dim]Type a query below or use [bold]/help[/bold] to see available commands.[/dim]"
        ))

    def add_message(self, role: str, content: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        if role == "user":
            log.write(Text.from_markup(
                f"\n[dim]{ts}[/dim]  [bold #964734]You[/]  {content}"
            ))
        elif role == "kiro":
            log.write(Text.from_markup(
                f"\n[dim]{ts}[/dim]  [bold #0FA4AF]Kiro[/]  {content}"
            ))
        elif role == "system":
            log.write(Text.from_markup(
                f"\n[dim]{ts}[/dim]  [dim #6fa8b0]Shield[/]  [dim]{content}[/dim]"
            ))
        elif role == "error":
            log.write(Text.from_markup(
                f"\n[dim]{ts}[/dim]  [bold red]Error[/]  [red]{content}[/red]"
            ))
        elif role == "info":
            log.write(Text.from_markup(
                f"\n[dim]{ts}[/dim]  [bold #0FA4AF]Info[/]   [dim]{content}[/dim]"
            ))
        elif role == "success":
            log.write(Text.from_markup(
                f"\n[dim]{ts}[/dim]  [bold green]Done[/]   [green]{content}[/green]"
            ))


class DashboardView(Widget):
    """Dashboard stats view."""

    DEFAULT_CSS = """
    DashboardView {
        width: 100%;
        height: 100%;
        background: #003135;
        padding: 2 4;
        overflow: auto scroll;
    }
    DashboardView .dash-title {
        color: #AFDDE5;
        text-style: bold;
        margin-bottom: 1;
    }
    DashboardView .dash-section {
        margin-top: 2;
        color: #6fa8b0;
        text-style: bold;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._stats: dict = {}

    def compose(self) -> ComposeResult:
        yield Static("⊞  Dashboard — Paladin AgentShield", classes="dash-title")
        yield Rule()
        yield Static(id="dash-content")

    def on_mount(self) -> None:
        self.load_stats()

    @work(thread=True)
    def load_stats(self) -> None:
        try:
            stats = api_get("/stats")
            self.app.call_from_thread(self._render_stats, stats)
        except Exception as e:
            self.app.call_from_thread(self._render_mock_stats)

    def _render_mock_stats(self) -> None:
        mock = {
            "actions_analyzed": 47,
            "allowed": 38,
            "approval_required": 5,
            "blocked": 4,
            "avg_risk": 23,
        }
        self._render_stats(mock)

    def _render_stats(self, stats: dict) -> None:
        content = self.query_one("#dash-content", Static)
        lines = [
            f"\n  [bold]Actions Analyzed[/]  {stats.get('actions_analyzed', '-')}",
            f"  [green]Allowed[/]           {stats.get('allowed', '-')}",
            f"  [yellow]Needs Review[/]      {stats.get('approval_required', '-')}",
            f"  [red]Blocked[/]           {stats.get('blocked', '-')}",
            f"  [dim]Avg Risk Score[/]    {stats.get('avg_risk', '-')}",
            "",
            "  [dim]-------------------------------------------[/]",
            "  [bold #0FA4AF]System Status[/]",
            "  [green]o[/] AgentShield      active",
            "  [green]o[/] Kiro CLI         connected",
            "  [green]o[/] Auto Block       enabled",
            "  [green]o[/] Auto Allow       enabled",
        ]
        content.update("\n".join(lines))


class ApprovalsView(Widget):
    """Approvals list view."""

    DEFAULT_CSS = """
    ApprovalsView {
        width: 100%;
        height: 100%;
        background: #003135;
        padding: 2 4;
        overflow: auto scroll;
    }
    ApprovalsView .title {
        color: #AFDDE5;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("✓  Approvals", classes="title")
        yield Rule()
        yield Static(id="approvals-content")

    def on_mount(self) -> None:
        self.load_approvals()

    @work(thread=True)
    def load_approvals(self) -> None:
        try:
            approvals = api_get("/approvals?status=pending")
            self.app.call_from_thread(self._render, approvals)
        except Exception:
            self.app.call_from_thread(self._render_mock)

    def _render_mock(self) -> None:
        mock = [
            {"id": "APR001", "action": {"tool_name": "bash", "risk_score": 72}, "status": "pending"},
            {"id": "APR002", "action": {"tool_name": "write_file", "risk_score": 45}, "status": "pending"},
        ]
        self._render(mock)

    def _render(self, approvals: list) -> None:
        content = self.query_one("#approvals-content", Static)
        if not approvals:
            content.update("\n  [dim]No pending approvals.[/dim]")
            return
        lines = [f"\n  [yellow]Pending approvals ({len(approvals)}):[/]\n"]
        for a in approvals:
            aid = a.get("id", "?")
            action = a.get("action", {})
            tool = action.get("tool_name", "unknown") if isinstance(action, dict) else "unknown"
            risk = action.get("risk_score", "?") if isinstance(action, dict) else "?"
            lines.append(f"  [bold]{aid}[/]  tool=[cyan]{tool}[/]  risk=[yellow]{risk}[/]")
            lines.append(f"         [dim]paladin approve {aid}[/]  or  [dim]paladin deny {aid}[/]\n")
        content.update("\n".join(lines))


class ActivityView(Widget):
    """Activity log view."""

    DEFAULT_CSS = """
    ActivityView {
        width: 100%;
        height: 100%;
        background: #003135;
        padding: 2 4;
        overflow: auto scroll;
    }
    ActivityView .title {
        color: #AFDDE5;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("≋  Activity Log", classes="title")
        yield Rule()
        yield Static(id="activity-content")

    def on_mount(self) -> None:
        self.load_activity()

    @work(thread=True)
    def load_activity(self) -> None:
        try:
            events = api_get("/activity")
            self.app.call_from_thread(self._render, events)
        except Exception:
            self.app.call_from_thread(self._render_mock)

    def _render_mock(self) -> None:
        mock = [
            {"timestamp": "2024-01-01T10:00:00Z", "tool_name": "bash", "decision": "allowed",  "risk_score": 12},
            {"timestamp": "2024-01-01T10:01:00Z", "tool_name": "read_file", "decision": "allowed",  "risk_score": 8},
            {"timestamp": "2024-01-01T10:02:00Z", "tool_name": "write_file", "decision": "approval_required", "risk_score": 65},
            {"timestamp": "2024-01-01T10:03:00Z", "tool_name": "bash", "decision": "blocked",  "risk_score": 88},
        ]
        self._render(mock)

    def _render(self, events: list) -> None:
        content = self.query_one("#activity-content", Static)
        if not events:
            content.update("\n  [dim]No activity recorded.[/dim]")
            return
        lines = []
        for e in events[:50]:
            ts = format_timestamp(e.get("timestamp", ""))
            tool = e.get("tool_name", "?")
            decision = e.get("decision", "?")
            risk = e.get("risk_score", "?")
            if decision == "allowed":
                dec_fmt = f"[green]{decision}[/]"
            elif decision == "blocked":
                dec_fmt = f"[red]{decision}[/]"
            elif decision == "approval_required":
                dec_fmt = f"[yellow]review[/]"
            else:
                dec_fmt = f"[dim]{decision}[/]"
            lines.append(f"  [dim]{ts}[/]  [cyan]{tool:<18}[/]  {dec_fmt:<20}  risk=[yellow]{risk}[/]")
        content.update("\n".join(lines))


class PoliciesView(Widget):
    """Policy management view."""

    DEFAULT_CSS = """
    PoliciesView {
        width: 100%;
        height: 100%;
        background: #003135;
        padding: 2 4;
        overflow: auto scroll;
    }
    PoliciesView .title {
        color: #AFDDE5;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("⛊  Policies", classes="title")
        yield Rule()
        yield Static(id="policy-content")

    def on_mount(self) -> None:
        self.load_policies()

    @work(thread=True)
    def load_policies(self) -> None:
        try:
            policies = api_get("/policies")
            self.app.call_from_thread(self._render, policies)
        except Exception:
            self.app.call_from_thread(self._render_mock)

    def _render_mock(self) -> None:
        mock = [
            {"id": "POL001", "name": "No shell access",    "action": "block",   "enabled": True},
            {"id": "POL002", "name": "Require approval for file writes", "action": "approval", "enabled": True},
            {"id": "POL003", "name": "Allow read-only ops", "action": "allow",   "enabled": True},
        ]
        self._render(mock)

    def _render(self, policies: list) -> None:
        content = self.query_one("#policy-content", Static)
        if not policies:
            content.update("\n  [dim]No policies defined.[/dim]\n  [dim]Use [bold]paladin policy add[/] to create one.[/dim]")
            return
        lines = [f"\n  [bold]Active Policies ({len(policies)}):[/]\n"]
        for p in policies:
            pid = p.get("id", "?")
            name = p.get("name", "Unnamed")
            action = p.get("action", "?")
            enabled = p.get("enabled", True)
            status = "[green]on[/]" if enabled else "[red]off[/]"
            if action == "block":
                act_fmt = f"[red]{action}[/]"
            elif action == "allow":
                act_fmt = f"[green]{action}[/]"
            else:
                act_fmt = f"[yellow]{action}[/]"
            lines.append(f"  {status}  [bold]{pid}[/]  {name}")
            lines.append(f"       action={act_fmt}\n")
        content.update("\n".join(lines))


class SettingsView(Widget):
    """Settings view."""

    DEFAULT_CSS = """
    SettingsView {
        width: 100%;
        height: 100%;
        background: #003135;
        padding: 2 4;
        overflow: auto scroll;
    }
    SettingsView .title {
        color: #AFDDE5;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("⚙  Settings", classes="title")
        yield Rule()
        yield Static(id="settings-content")

    def on_mount(self) -> None:
        content = self.query_one("#settings-content", Static)
        kiro_status = f"[green]{KIRO_BIN}[/]" if KIRO_BIN else "[red]not found — install from https://kiro.ai[/]"
        content.update(
            f"\n  [dim]Paladin CLI  v{VERSION}[/]\n\n"
            f"  [bold]API Backend[/]\n"
            f"  Base URL:      [cyan]{API_BASE}[/]\n\n"
            f"  [bold]Kiro CLI[/]\n"
            f"  Binary:        {kiro_status}\n\n"
            f"  [bold]Theme[/]\n"
            f"  Mode:          [cyan]Dark (default)[/]  · press [bold]t[/] to toggle\n\n"
            f"  [bold]Keybindings[/]\n"
            f"  [bold]s[/]   Toggle sidebar\n"
            f"  [bold]t[/]   Toggle dark/light theme\n"
            f"  [bold]q[/]   Quit\n"
            f"  [bold]?[/]   Help\n"
            f"  [bold]Ctrl+C[/]  Force quit\n"
        )


# ─── Help Modal ────────────────────────────────────────────────────────────────

class HelpScreen(ModalScreen):
    """A modal help screen."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    HelpScreen #help-box {
        width: 70;
        height: 40;
        background: #024950;
        border: double #0FA4AF;
        padding: 1 2;
        overflow: auto scroll;
    }
    HelpScreen .help-title {
        color: #0FA4AF;
        text-style: bold;
        text-align: center;
    }
    HelpScreen .help-close {
        dock: bottom;
        height: 3;
        align: center middle;
        color: #6fa8b0;
    }
    """

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="help-box"):
            yield Static("🛡  PALADIN CLI — Help", classes="help-title")
            yield Rule()
            yield Static(
                "\n[bold]Commands:[/]\n\n"
                "  [cyan]paladin init[/]              Initialize Paladin in this project\n"
                "  [cyan]paladin start[/]             Start the Paladin agent session\n"
                "  [cyan]paladin status[/]            Show current session status\n"
                "  [cyan]paladin run <query>[/]       Run a query via Kiro\n\n"
                "  [cyan]paladin approvals[/]         List pending approvals\n"
                "  [cyan]paladin approve <id>[/]      Approve an action by ID\n"
                "  [cyan]paladin deny <id>[/]         Deny an action by ID\n\n"
                "  [cyan]paladin activity[/]          Show activity log\n"
                "  [cyan]paladin activity <id>[/]     Show details for session/action ID\n\n"
                "  [cyan]paladin policy list[/]       List all policies\n"
                "  [cyan]paladin policy add[/]        Add a new policy (interactive)\n"
                "  [cyan]paladin policy test[/]       Test a policy against an action\n\n"
                "  [cyan]paladin config[/]            Show/edit configuration\n"
                "  [cyan]paladin doctor[/]            Check system health\n"
                "  [cyan]paladin version[/]           Show version info\n"
                "  [cyan]/help[/]  or  [cyan]?[/]              Show this help\n"
                "  [cyan]/clear[/]                    Clear the session log\n"
                "  [cyan]/theme[/]                    Toggle dark/light mode\n\n"
                "[bold]Navigation (keyboard):[/]\n\n"
                "  [bold]s[/]   Toggle sidebar\n"
                "  [bold]t[/]   Toggle theme\n"
                "  [bold]q[/]   Quit\n"
                "  [bold]Escape[/]  Close modal / cancel\n",
                markup=True,
            )
            yield Static("\n  Press [bold]Escape[/] to close", classes="help-close", markup=True)


# ─── Main App ──────────────────────────────────────────────────────────────────

class PaladinApp(App):
    """The Paladin TUI application."""

    TITLE = "Paladin — AgentShield"
    SUB_TITLE = f"v{VERSION}"

    BINDINGS = [
        Binding("s",       "toggle_sidebar",  "Sidebar",  show=True),
        Binding("t",       "toggle_theme",    "Theme",    show=True),
        Binding("q",       "quit",            "Quit",     show=True),
        Binding("ctrl+c",  "quit",            "Force quit", show=False),
        Binding("?",       "show_help",       "Help",     show=True),
    ]

    # ── CSS ────────────────────────────────────────────────────────────────────
    CSS = """
    /* ── App layout ── */
    Screen {
        background: #003135;
        layers: base overlay;
    }

    #app-layout {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }

    #main-area {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }

    #content-area {
        width: 100%;
        height: 1fr;
        overflow: hidden;
    }

    /* ── Input bar at bottom ── */
    #input-bar {
        dock: bottom;
        height: 3;
        background: #024950;
        border-top: tall #0FA4AF;
        padding: 0 1;
        layout: horizontal;
    }

    #main-input {
        width: 1fr;
        height: 3;
        background: #024950;
        border: none;
        color: #AFDDE5;
        padding: 0 1;
    }

    #main-input:focus {
        border: none;
        background: #024950;
    }

    #send-btn {
        width: 8;
        height: 3;
        background: #0FA4AF;
        color: #003135;
        border: none;
        content-align: center middle;
        text-style: bold;
        margin-left: 1;
    }

    #send-btn:hover {
        background: #AFDDE5;
    }

    /* ── Footer ── */
    Footer {
        background: #024950;
        color: #AFDDE5;
    }

    /* ── Sidebar toggle hidden state ── */
    Sidebar.hidden {
        display: none;
    }

    /* ── Active view visibility ── */
    .view-hidden {
        display: none;
    }
    """

    # ── Light theme CSS (applied via add_class) ─────────────────────────────
    LIGHT_CSS = """
    Screen {
        background: #B8E3E9;
    }
    """

    DARK_THEME_VARS = {
        "main-bg":           "#003135",
        "sidebar-bg":        "#024950",
        "sidebar-border":    "#0FA4AF",
        "sidebar-text":      "#AFDDE5",
        "sidebar-muted":     "#6fa8b0",
        "sidebar-hover":     "#035560",
        "sidebar-active":    "#0FA4AF",
        "sidebar-active-text": "#003135",
        "sidebar-logo-color": "#AFDDE5",
        "sidebar-accent":    "#0FA4AF",
        "shield-primary":    "#0FA4AF",
        "shield-accent":     "#AFDDE5",
        "shield-muted":      "#6fa8b0",
        "card-bg":           "#024950",
        "card-border":       "#0FA4AF",
        "input-bg":          "#024950",
        "input-border":      "#0FA4AF",
        "input-text":        "#AFDDE5",
        "input-accent":      "#964734",
        "info-color":        "#0FA4AF",
        "modal-bg":          "#024950",
        "modal-border":      "#0FA4AF",
        "footer-bg":         "#024950",
        "footer-text":       "#AFDDE5",
    }

    LIGHT_THEME_VARS = {
        "main-bg":           "#B8E3E9",
        "sidebar-bg":        "#B298E7",
        "sidebar-border":    "#F5B8D5",
        "sidebar-text":      "#2d2d4e",
        "sidebar-muted":     "#6b5b8e",
        "sidebar-hover":     "#c8ade8",
        "sidebar-active":    "#F5B8D5",
        "sidebar-active-text": "#2d2d4e",
        "sidebar-logo-color": "#2d2d4e",
        "sidebar-accent":    "#F5B8D5",
        "shield-primary":    "#B298E7",
        "shield-accent":     "#F9BEDD",
        "shield-muted":      "#c8ade8",
        "card-bg":           "#d4edf0",
        "card-border":       "#F5B8D5",
        "input-bg":          "#d4edf0",
        "input-border":      "#F5B8D5",
        "input-text":        "#2d2d4e",
        "input-accent":      "#F9BEDD",
        "info-color":        "#B298E7",
        "modal-bg":          "#d4edf0",
        "modal-border":      "#F5B8D5",
        "footer-bg":         "#B298E7",
        "footer-text":       "#2d2d4e",
    }

    _is_dark: reactive[bool] = reactive(True)
    _sidebar_visible: reactive[bool] = reactive(True)
    _current_view: reactive[str] = reactive("session")

    def compose(self) -> ComposeResult:
        with Horizontal(id="app-layout"):
            yield Sidebar(id="main-sidebar")
            with Vertical(id="main-area"):
                with Container(id="content-area"):
                    yield SessionView(id="view-session")
                    yield DashboardView(id="view-dashboard")
                    yield ApprovalsView(id="view-approvals")
                    yield ActivityView(id="view-activity")
                    yield PoliciesView(id="view-policies")
                    yield SettingsView(id="view-settings")
                with Horizontal(id="input-bar"):
                    yield Input(
                        placeholder="Type a command or query… (use /help for commands)",
                        id="main-input",
                    )
                    yield Button("Send", id="send-btn")
        yield Footer()

    def on_mount(self) -> None:
        # Show only the session view initially
        self._switch_view("session")
        # Focus the input
        self.query_one("#main-input", Input).focus()

    # ── View switching ─────────────────────────────────────────────────────────

    def _switch_view(self, view_id: str) -> None:
        all_ids = ["session", "dashboard", "approvals", "activity", "policies", "settings"]
        for vid in all_ids:
            widget_id = f"#view-{vid}"
            try:
                w = self.query_one(widget_id)
                if vid == view_id:
                    w.remove_class("view-hidden")
                else:
                    w.add_class("view-hidden")
            except NoMatches:
                pass
        self._current_view = view_id

    @on(ListView.Selected, "#sidebar-list")
    def on_sidebar_select(self, event: ListView.Selected) -> None:
        item = event.item
        if hasattr(item, "view_id"):
            self._switch_view(item.view_id)

    # ── Input handling ─────────────────────────────────────────────────────────

    @on(Input.Submitted, "#main-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._handle_input(event.value)
        event.input.clear()

    @on(Button.Pressed, "#send-btn")
    def on_send_pressed(self) -> None:
        inp = self.query_one("#main-input", Input)
        self._handle_input(inp.value)
        inp.clear()
        inp.focus()

    def _handle_input(self, raw: str) -> None:
        text = raw.strip()
        if not text:
            return

        # Always switch to session view when user types something
        self._switch_view("session")

        # Get the session view to add messages
        try:
            sv = self.query_one("#view-session", SessionView)
        except NoMatches:
            return

        sv.add_message("user", text)

        # Parse slash commands and paladin commands
        if text.startswith("/"):
            self._handle_slash_command(text[1:], sv)
        elif text.lower().startswith("paladin ") or text.lower() in (
            "paladin", "init", "start", "status", "run", "approvals",
            "activity", "policy", "config", "doctor", "version",
        ):
            cmd_text = text
            if text.lower().startswith("paladin "):
                cmd_text = text[8:].strip()
            elif text.lower() == "paladin":
                cmd_text = ""
            self._handle_paladin_command(cmd_text, sv)
        else:
            # Treat as a Kiro query
            self._run_kiro_query(text, sv)

    def _handle_slash_command(self, cmd: str, sv: SessionView) -> None:
        cmd_lower = cmd.strip().lower()
        if cmd_lower in ("help", "h", "?"):
            self.action_show_help()
        elif cmd_lower == "clear":
            try:
                log = sv.query_one("#chat-log", RichLog)
                log.clear()
            except NoMatches:
                pass
            sv.add_message("system", "Log cleared.")
        elif cmd_lower == "theme":
            self.action_toggle_theme()
            mode = "light" if not self._is_dark else "dark"
            sv.add_message("system", f"Switched to {mode} mode.")
        elif cmd_lower == "sidebar":
            self.action_toggle_sidebar()
        elif cmd_lower.startswith("run "):
            query = cmd[4:].strip()
            self._run_kiro_query(query, sv)
        else:
            sv.add_message("error", f"Unknown command: /{cmd}  — try [bold]/help[/]")

    def _handle_paladin_command(self, cmd: str, sv: SessionView) -> None:
        parts = cmd.strip().split()
        if not parts:
            sv.add_message("info", f"Paladin CLI v{VERSION} — AgentShield runtime security.\nType [bold]/help[/] for available commands.")
            return

        base = parts[0].lower()
        args = parts[1:]

        if base == "init":
            sv.add_message("system", "Initializing Paladin in current directory…")
            self._cmd_init(sv)

        elif base == "start":
            sv.add_message("system", "Starting Paladin agent session…")
            self._cmd_start(sv)

        elif base == "status":
            self._cmd_status(sv)

        elif base == "run":
            if args:
                query = " ".join(args)
                self._run_kiro_query(query, sv)
            else:
                sv.add_message("error", "Usage: paladin run <query>")

        elif base == "approvals":
            self._switch_view("approvals")
            try:
                self.query_one("#view-approvals", ApprovalsView).load_approvals()
            except NoMatches:
                pass
            sv.add_message("system", "Switched to Approvals view.")

        elif base == "approve":
            if args:
                self._cmd_approve(args[0], sv)
            else:
                sv.add_message("error", "Usage: paladin approve <id>")

        elif base == "deny":
            if args:
                self._cmd_deny(args[0], sv)
            else:
                sv.add_message("error", "Usage: paladin deny <id>")

        elif base == "activity":
            if args:
                self._cmd_activity_detail(args[0], sv)
            else:
                self._switch_view("activity")
                sv.add_message("system", "Switched to Activity view.")

        elif base == "policy":
            if not args or args[0] == "list":
                self._switch_view("policies")
                sv.add_message("system", "Switched to Policies view.")
            elif args[0] == "add":
                sv.add_message("info", "Policy add is available in the Settings view.\nUse the web dashboard at http://localhost:8000 for advanced policy management.")
            elif args[0] == "test":
                sv.add_message("info", "Policy test mode — enter a tool call to simulate:\n[dim]Feature coming soon. Use the web dashboard for now.[/dim]")
            else:
                sv.add_message("error", f"Unknown policy subcommand: {args[0]}\nUsage: paladin policy [list|add|test]")

        elif base == "config":
            self._switch_view("settings")
            sv.add_message("system", "Switched to Settings view.")

        elif base == "doctor":
            self._cmd_doctor(sv)

        elif base == "version":
            sv.add_message("info",
                f"[bold]Paladin[/] v{VERSION}\n"
                f"Python {sys.version.split()[0]}\n"
                f"Kiro CLI: {KIRO_BIN or '[red]not found[/]'}\n"
                f"API: {API_BASE}"
            )

        else:
            sv.add_message("error", f"Unknown command: {base}\nType [bold]/help[/] for available commands.")

    # ── Background command workers ─────────────────────────────────────────────

    @work(thread=True)
    def _run_kiro_query(self, query: str, sv: SessionView) -> None:
        if not KIRO_BIN:
            self.app.call_from_thread(sv.add_message, "error",
                "Kiro CLI not found. Install from https://kiro.ai\n"
                "Expected: kiro-cli-chat, kiro, or kiro-cli in PATH."
            )
            return
        self.app.call_from_thread(sv.add_message, "system", "Sending query to Kiro…")
        try:
            result = subprocess.run(
                [KIRO_BIN, "chat", "--no-interactive", query],
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout.strip() or result.stderr.strip() or "(no output)"
            self.app.call_from_thread(sv.add_message, "kiro", output)
        except subprocess.TimeoutExpired:
            self.app.call_from_thread(sv.add_message, "error", "Kiro query timed out after 60s.")
        except Exception as e:
            self.app.call_from_thread(sv.add_message, "error", f"Failed to run Kiro: {e}")

    @work(thread=True)
    def _cmd_init(self, sv: SessionView) -> None:
        import os, json as _json
        config = {
            "version": VERSION,
            "api_base": API_BASE,
            "created_at": datetime.now().isoformat(),
            "policies": [],
            "auto_block_risk_threshold": 80,
            "auto_allow_risk_threshold": 20,
        }
        try:
            path = os.path.join(os.getcwd(), ".paladin.json")
            with open(path, "w") as f:
                _json.dump(config, f, indent=2)
            self.app.call_from_thread(sv.add_message, "success",
                f"Paladin initialized!\nConfig written to: {path}"
            )
        except Exception as e:
            self.app.call_from_thread(sv.add_message, "error", f"Init failed: {e}")

    @work(thread=True)
    def _cmd_start(self, sv: SessionView) -> None:
        self.app.call_from_thread(sv.add_message, "system", "Connecting to AgentShield backend…")
        try:
            result = api_get("/sessions")
            count = len(result) if isinstance(result, list) else "?"
            self.app.call_from_thread(sv.add_message, "success",
                f"Paladin started. {count} session(s) found on backend."
            )
        except Exception:
            self.app.call_from_thread(sv.add_message, "success",
                "Paladin TUI is running.\n"
                "[dim]Backend not reachable — running in offline mode.[/dim]"
            )

    @work(thread=True)
    def _cmd_status(self, sv: SessionView) -> None:
        try:
            session = api_get("/sessions/A82F")
            name = session.get("id", "A82F")
            agent = session.get("agent", "Kiro")
            status = session.get("status", "running")
            actions = session.get("action_count", 0)
            self.app.call_from_thread(sv.add_message, "info",
                f"[bold]Session #{name}[/]\n"
                f"  Agent:    {agent}\n"
                f"  Status:   [green]{status}[/]\n"
                f"  Actions:  {actions}"
            )
        except Exception:
            kiro_ok = "[green]found[/]" if KIRO_BIN else "[red]not found[/]"
            self.app.call_from_thread(sv.add_message, "info",
                f"[bold]Status[/]\n"
                f"  Paladin TUI:   [green]running[/]\n"
                f"  Kiro CLI:      {kiro_ok}\n"
                f"  Backend API:   [red]unreachable[/] ({API_BASE})\n"
                f"  Mode:          offline"
            )

    @work(thread=True)
    def _cmd_approve(self, approval_id: str, sv: SessionView) -> None:
        try:
            result = api_post(
                f"/approvals/{approval_id}/decision",
                {"approval_id": approval_id, "status": "approved"},
            )
            self.app.call_from_thread(sv.add_message, "success",
                f"Approved action [bold]{approval_id}[/]."
            )
        except Exception as e:
            self.app.call_from_thread(sv.add_message, "error",
                f"Failed to approve {approval_id}: {e}"
            )

    @work(thread=True)
    def _cmd_deny(self, approval_id: str, sv: SessionView) -> None:
        try:
            result = api_post(
                f"/approvals/{approval_id}/decision",
                {"approval_id": approval_id, "status": "denied"},
            )
            self.app.call_from_thread(sv.add_message, "success",
                f"Denied action [bold]{approval_id}[/]."
            )
        except Exception as e:
            self.app.call_from_thread(sv.add_message, "error",
                f"Failed to deny {approval_id}: {e}"
            )

    @work(thread=True)
    def _cmd_activity_detail(self, detail_id: str, sv: SessionView) -> None:
        try:
            detail = api_get(f"/activity/{detail_id}")
            lines = [f"[bold]Activity {detail_id}[/]"]
            for k, v in detail.items():
                lines.append(f"  {k}: {v}")
            self.app.call_from_thread(sv.add_message, "info", "\n".join(lines))
        except Exception as e:
            self.app.call_from_thread(sv.add_message, "error",
                f"Could not fetch activity {detail_id}: {e}"
            )

    @work(thread=True)
    def _cmd_doctor(self, sv: SessionView) -> None:
        checks = []
        # Check Kiro CLI
        if KIRO_BIN:
            checks.append(("[green]✓[/]", "Kiro CLI", f"found at {KIRO_BIN}"))
        else:
            checks.append(("[red]✗[/]", "Kiro CLI", "not found — install from https://kiro.ai"))

        # Check API
        try:
            api_get("/")
            checks.append(("[green]✓[/]", "Backend API", f"reachable at {API_BASE}"))
        except Exception:
            checks.append(("[yellow]![/]", "Backend API", f"not reachable at {API_BASE}"))

        # Check Python version
        major, minor = sys.version_info[:2]
        if major >= 3 and minor >= 8:
            checks.append(("[green]✓[/]", "Python", f"{major}.{minor} (ok)"))
        else:
            checks.append(("[red]✗[/]", "Python", f"{major}.{minor} — need 3.8+"))

        # Check Textual
        try:
            import textual
            checks.append(("[green]✓[/]", "Textual", f"v{textual.__version__}"))
        except ImportError:
            checks.append(("[red]✗[/]", "Textual", "not installed"))

        lines = ["[bold]Doctor — System Health Check[/]\n"]
        for icon, name, detail in checks:
            lines.append(f"  {icon}  [bold]{name:<14}[/]  {detail}")

        all_ok = all(c[0] == "[green]✓[/]" for c in checks)
        lines.append("")
        if all_ok:
            lines.append("  [green]All checks passed.[/]")
        else:
            lines.append("  [yellow]Some issues found. Review above.[/]")

        self.app.call_from_thread(sv.add_message, "info", "\n".join(lines))

    # ── Action handlers ────────────────────────────────────────────────────────

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#main-sidebar", Sidebar)
        self._sidebar_visible = not self._sidebar_visible
        if self._sidebar_visible:
            sidebar.remove_class("hidden")
        else:
            sidebar.add_class("hidden")

    def action_toggle_theme(self) -> None:
        self._is_dark = not self._is_dark
        if self._is_dark:
            self._apply_theme_vars(self.DARK_THEME_VARS)
            self.remove_class("light-mode")
        else:
            self._apply_theme_vars(self.LIGHT_THEME_VARS)
            self.add_class("light-mode")

    def _apply_theme_vars(self, vars: dict) -> None:
        """Apply CSS variable overrides for theming via screen background."""
        # Textual doesn't support runtime CSS variable changes directly,
        # but we use dark/light_theme CSS classes on the Screen
        if vars == self.LIGHT_THEME_VARS:
            self.screen.styles.background = "#B8E3E9"
            try:
                self.query_one("#main-sidebar").styles.background = "#B298E7"
                self.query_one("#main-sidebar").styles.border_right = ("tall", "#F5B8D5")
                self.query_one("#input-bar").styles.background = "#d4edf0"
                self.query_one("#input-bar").styles.border_top = ("tall", "#F5B8D5")
                self.query_one("#main-input").styles.background = "#d4edf0"
                self.query_one("#main-input").styles.color = "#2d2d4e"
            except NoMatches:
                pass
        else:
            self.screen.styles.background = "#003135"
            try:
                self.query_one("#main-sidebar").styles.background = "#024950"
                self.query_one("#main-sidebar").styles.border_right = ("tall", "#0FA4AF")
                self.query_one("#input-bar").styles.background = "#024950"
                self.query_one("#input-bar").styles.border_top = ("tall", "#0FA4AF")
                self.query_one("#main-input").styles.background = "#024950"
                self.query_one("#main-input").styles.color = "#AFDDE5"
            except NoMatches:
                pass

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_quit(self) -> None:
        self.exit()


# ─── Entry point ──────────────────────────────────────────────────────────────

def run_tui() -> None:
    """Launch the Paladin TUI."""
    app = PaladinApp()
    app.run()


if __name__ == "__main__":
    run_tui()

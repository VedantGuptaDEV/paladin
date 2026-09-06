#!/usr/bin/env python3
"""
paladin — AgentShield CLI entry point.

Usage:
  paladin                     Launch the interactive TUI
  paladin <command> [args]    Run a specific command directly

Commands:
  init                Initialize Paladin in this project
  start               Start the Paladin agent session
  status              Show session/system status
  run <query>         Send a query to Kiro

  approvals           List pending approvals
  approve <id>        Approve an action
  deny <id>           Deny an action

  activity            Show activity log
  activity <id>       Show details for an ID

  policy list         List all policies
  policy add          Add a new policy
  policy test         Test a policy

  config              Show configuration
  doctor              Check system health
  version             Show version
"""

from __future__ import annotations

from typing import Optional, Union, List, Dict, Any
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime

# Force UTF-8 output on Windows to avoid charmap errors with Unicode characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

VERSION = "0.1.0"
API_BASE = os.environ.get("PALADIN_API_URL", "http://localhost:8000")
KIRO_BIN = shutil.which("kiro-cli-chat") or shutil.which("kiro") or shutil.which("kiro-cli")


# ─── API helpers ──────────────────────────────────────────────────────────────

def _api_get(path: str) -> Any:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


def _api_post(path: str, data: dict) -> dict:
    url = f"{API_BASE}{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


# ─── Print helpers ─────────────────────────────────────────────────────────────

def _ok(msg: str) -> None:
    print(f"\033[32m✓\033[0m  {msg}")

def _err(msg: str) -> None:
    print(f"\033[31m✗\033[0m  {msg}", file=sys.stderr)

def _info(msg: str) -> None:
    print(f"\033[36m·\033[0m  {msg}")

def _warn(msg: str) -> None:
    print(f"\033[33m!\033[0m  {msg}")

def _header(msg: str) -> None:
    print(f"\n\033[1m{msg}\033[0m")
    print("─" * len(msg))


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_init() -> int:
    _header("Paladin Init")
    config = {
        "version": VERSION,
        "api_base": API_BASE,
        "created_at": datetime.now().isoformat(),
        "policies": [],
        "auto_block_risk_threshold": 80,
        "auto_allow_risk_threshold": 20,
    }
    path = os.path.join(os.getcwd(), ".paladin.json")
    try:
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
        _ok(f"Created {path}")
        _info(f"API base: {API_BASE}")
        _info("Edit .paladin.json to customize thresholds and policies.")
        return 0
    except Exception as e:
        _err(f"Failed to write config: {e}")
        return 1


def cmd_start() -> int:
    _header("Paladin Start")
    _info("Connecting to AgentShield backend…")
    try:
        sessions = _api_get("/sessions")
        count = len(sessions) if isinstance(sessions, list) else "?"
        _ok(f"Connected to {API_BASE}")
        _info(f"Active sessions: {count}")
    except Exception:
        _warn(f"Backend not reachable at {API_BASE} — starting in offline mode.")
    if KIRO_BIN:
        _ok(f"Kiro CLI found: {KIRO_BIN}")
    else:
        _warn("Kiro CLI not found. Install from https://kiro.ai")
    _ok("Paladin is running.")
    return 0


def cmd_status() -> int:
    _header("Paladin Status")
    try:
        session = _api_get("/sessions/A82F")
        _ok("Backend reachable")
        _info(f"Session: #{session.get('id', 'A82F')}")
        _info(f"Agent:   {session.get('agent', 'Kiro')}")
        _info(f"Status:  {session.get('status', 'running')}")
        _info(f"Actions: {session.get('action_count', 0)}")
    except Exception:
        _warn(f"Backend unreachable at {API_BASE}")
        kiro_status = f"found ({KIRO_BIN})" if KIRO_BIN else "not found"
        _info(f"Kiro CLI: {kiro_status}")
        _info("Mode: offline")
    return 0


def cmd_run(query: str, model: Optional[str] = None) -> int:
    if not KIRO_BIN:
        _err("Kiro CLI not found. Install from https://kiro.ai")
        return 1
    cmd = [KIRO_BIN, "chat", "--no-interactive", query]
    if model:
        cmd += ["--model", model]
    result = subprocess.run(cmd, text=True)
    return result.returncode


def cmd_approvals() -> int:
    _header("Pending Approvals")
    try:
        approvals = _api_get("/approvals?status=pending")
        if not approvals:
            _info("No pending approvals.")
            return 0
        for a in approvals:
            aid = a.get("id", "?")
            action = a.get("action", {})
            tool = action.get("tool_name", "unknown") if isinstance(action, dict) else "unknown"
            risk = action.get("risk_score", "?") if isinstance(action, dict) else "?"
            print(f"  {aid}  tool={tool}  risk={risk}")
            print(f"         paladin approve {aid}  |  paladin deny {aid}")
    except Exception as e:
        _err(f"Could not fetch approvals: {e}")
    return 0


def cmd_approve(approval_id: str) -> int:
    _info(f"Approving {approval_id}…")
    try:
        _api_post(f"/approvals/{approval_id}/decision", {"approval_id": approval_id, "status": "approved"})
        _ok(f"Approved: {approval_id}")
    except Exception as e:
        _err(f"Failed: {e}")
        return 1
    return 0


def cmd_deny(approval_id: str) -> int:
    _info(f"Denying {approval_id}…")
    try:
        _api_post(f"/approvals/{approval_id}/decision", {"approval_id": approval_id, "status": "denied"})
        _ok(f"Denied: {approval_id}")
    except Exception as e:
        _err(f"Failed: {e}")
        return 1
    return 0


def cmd_activity(detail_id: Optional[str] = None) -> int:
    if detail_id:
        _header(f"Activity: {detail_id}")
        try:
            detail = _api_get(f"/activity/{detail_id}")
            for k, v in detail.items():
                _info(f"{k}: {v}")
        except Exception as e:
            _err(f"Could not fetch: {e}")
            return 1
    else:
        _header("Activity Log")
        try:
            events = _api_get("/activity")
            if not events:
                _info("No activity recorded.")
                return 0
            for e in (events[:20] if isinstance(events, list) else []):
                ts = e.get("timestamp", "")[:19].replace("T", " ")
                tool = e.get("tool_name", "?")
                decision = e.get("decision", "?")
                risk = e.get("risk_score", "?")
                # Color code decision
                if decision == "allowed":
                    d = f"\033[32m{decision}\033[0m"
                elif decision == "blocked":
                    d = f"\033[31m{decision}\033[0m"
                else:
                    d = f"\033[33m{decision}\033[0m"
                print(f"  {ts}  {tool:<18} {d:<25} risk={risk}")
        except Exception as e:
            _err(f"Could not fetch activity: {e}")
            return 1
    return 0


def cmd_policy(subcommand: str = "list", extra: Optional[List[str]] = None) -> int:
    if subcommand == "list":
        _header("Policies")
        try:
            policies = _api_get("/policies")
            if not policies:
                _info("No policies defined.")
                return 0
            for p in policies:
                pid = p.get("id", "?")
                name = p.get("name", "Unnamed")
                action = p.get("action", "?")
                enabled = "on" if p.get("enabled", True) else "off"
                print(f"  {pid}  {name:<40}  action={action}  [{enabled}]")
        except Exception as e:
            _err(f"Could not fetch policies: {e}")
            return 1

    elif subcommand == "add":
        _header("Add Policy")
        _info("Interactive policy creation (requires backend connection).")
        try:
            name = input("Policy name: ").strip()
            action = input("Action [allow/block/approval]: ").strip() or "block"
            risk_min = input("Min risk threshold (0-100) [0]: ").strip() or "0"
            risk_max = input("Max risk threshold (0-100) [100]: ").strip() or "100"
            payload = {
                "name": name,
                "action": action,
                "risk_range": [int(risk_min), int(risk_max)],
                "enabled": True,
            }
            result = _api_post("/policies", payload)
            _ok(f"Policy created: {result.get('id', '?')}")
        except KeyboardInterrupt:
            print("\nCancelled.")
        except Exception as e:
            _err(f"Failed to create policy: {e}")
            return 1

    elif subcommand == "test":
        _header("Policy Test")
        _info("Simulate a tool call against all active policies.")
        try:
            tool = input("Tool name: ").strip()
            risk = int(input("Risk score (0-100): ").strip() or "50")
            payload = {"tool_name": tool, "risk_score": risk}
            result = _api_post("/policies/test", payload)
            decision = result.get("decision", "?")
            policy = result.get("matched_policy", "none")
            if decision == "allowed":
                _ok(f"Decision: allowed  (policy: {policy})")
            elif decision == "blocked":
                _err(f"Decision: blocked  (policy: {policy})")
            else:
                _warn(f"Decision: {decision}  (policy: {policy})")
        except KeyboardInterrupt:
            print("\nCancelled.")
        except Exception as e:
            _err(f"Test failed: {e}")
            return 1
    else:
        _err(f"Unknown policy subcommand: {subcommand}")
        _info("Usage: paladin policy [list|add|test]")
        return 1

    return 0


def cmd_config() -> int:
    _header("Configuration")
    _info(f"API Base URL:   {API_BASE}")
    _info(f"Kiro CLI:       {KIRO_BIN or 'not found'}")
    _info(f"Paladin TUI:    paladin_tui.py")
    _info(f"Version:        {VERSION}")

    config_path = os.path.join(os.getcwd(), ".paladin.json")
    if os.path.exists(config_path):
        _info(f"Project config: {config_path}")
        try:
            with open(config_path) as f:
                data = json.load(f)
            for k, v in data.items():
                print(f"    {k}: {v}")
        except Exception:
            pass
    else:
        _warn("No .paladin.json found in current directory. Run 'paladin init'.")
    return 0


def cmd_doctor() -> int:
    _header("Doctor — System Health Check")
    issues = 0

    # Kiro CLI
    if KIRO_BIN:
        _ok(f"Kiro CLI found: {KIRO_BIN}")
    else:
        _err("Kiro CLI not found — install from https://kiro.ai")
        issues += 1

    # Python version
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 8:
        _ok(f"Python {major}.{minor}")
    else:
        _err(f"Python {major}.{minor} — need 3.8+")
        issues += 1

    # Textual
    try:
        import textual
        _ok(f"Textual {textual.__version__}")
    except ImportError:
        _err("Textual not installed — run: pip install textual")
        issues += 1

    # Rich
    try:
        import rich
        rich_ver = getattr(rich, "__version__", None) or getattr(rich, "version", "installed")
        _ok(f"Rich {rich_ver}")
    except ImportError:
        _err("Rich not installed — run: pip install rich")
        issues += 1

    # Backend API
    try:
        _api_get("/")
        _ok(f"Backend API reachable at {API_BASE}")
    except Exception:
        _warn(f"Backend API not reachable at {API_BASE}")
        # Not a hard failure — offline mode works

    # Config file
    if os.path.exists(".paladin.json"):
        _ok("Project config found (.paladin.json)")
    else:
        _warn("No .paladin.json in current directory — run: paladin init")

    print()
    if issues == 0:
        _ok("All critical checks passed.")
    else:
        _warn(f"{issues} critical issue(s) found.")
    return issues


def cmd_version() -> int:
    print(f"paladin v{VERSION}")
    print(f"Python {sys.version.split()[0]}")
    if KIRO_BIN:
        print(f"Kiro CLI: {KIRO_BIN}")
    else:
        print("Kiro CLI: not found")
    print(f"API: {API_BASE}")
    return 0


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # If no arguments, launch the TUI
    if len(sys.argv) == 1:
        try:
            from paladin_tui import run_tui
            run_tui()
            return
        except ImportError:
            _err("paladin_tui.py not found. Make sure it's in the same directory.")
            sys.exit(1)

    parser = argparse.ArgumentParser(
        prog="paladin",
        description="Paladin AgentShield — Runtime security for autonomous AI agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init",    help="Initialize Paladin in this project")
    subparsers.add_parser("start",   help="Start the Paladin agent session")
    subparsers.add_parser("status",  help="Show current status")

    run_p = subparsers.add_parser("run", help="Run a Kiro query")
    run_p.add_argument("query", nargs="+", help="Query to send to Kiro")
    run_p.add_argument("--model", default=None, help="Model override")

    subparsers.add_parser("approvals", help="List pending approvals")

    approve_p = subparsers.add_parser("approve", help="Approve an action by ID")
    approve_p.add_argument("id", help="Approval ID")

    deny_p = subparsers.add_parser("deny", help="Deny an action by ID")
    deny_p.add_argument("id", help="Approval ID")

    activity_p = subparsers.add_parser("activity", help="Show activity log")
    activity_p.add_argument("id", nargs="?", default=None, help="Optional session/action ID")

    policy_p = subparsers.add_parser("policy", help="Manage policies")
    policy_p.add_argument("subcommand", nargs="?", default="list",
                          choices=["list", "add", "test"],
                          help="Policy subcommand")

    subparsers.add_parser("config",  help="Show configuration")
    subparsers.add_parser("doctor",  help="Check system health")
    subparsers.add_parser("version", help="Show version")

    # Special: launch TUI
    subparsers.add_parser("tui", help="Launch the interactive TUI (default with no args)")

    args = parser.parse_args()

    if args.version or args.command == "version":
        sys.exit(cmd_version())

    dispatch = {
        "init":      lambda: cmd_init(),
        "start":     lambda: cmd_start(),
        "status":    lambda: cmd_status(),
        "run":       lambda: cmd_run(" ".join(args.query), getattr(args, "model", None)),
        "approvals": lambda: cmd_approvals(),
        "approve":   lambda: cmd_approve(args.id),
        "deny":      lambda: cmd_deny(args.id),
        "activity":  lambda: cmd_activity(getattr(args, "id", None)),
        "policy":    lambda: cmd_policy(getattr(args, "subcommand", "list")),
        "config":    lambda: cmd_config(),
        "doctor":    lambda: cmd_doctor(),
        "tui":       lambda: _launch_tui(),
    }

    if args.command in dispatch:
        sys.exit(dispatch[args.command]() or 0)
    else:
        parser.print_help()
        sys.exit(0)


def _launch_tui() -> int:
    try:
        from paladin_tui import run_tui
        run_tui()
        return 0
    except ImportError as e:
        _err(f"Cannot launch TUI: {e}")
        return 1


if __name__ == "__main__":
    main()

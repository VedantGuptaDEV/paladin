"""
trialhack.py — paladin_cli integration for the trialHack Context Engine.

Exposes `run_check(prompt_str)` which:
  1. Parses the prompt string into a structured dict
  2. Feeds it through the ContextEngine
  3. Returns a CheckResult dataclass with all relevant fields
  4. Appends a row to Engine/Context_Engine/trialHack_output.csv

Import contract:
  The Engine/Context_Engine directory is added to sys.path so that
  `paladin.context.engine` (the paladin package inside Context_Engine)
  can be imported without any pip install step.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ── Locate the Context Engine package ────────────────────────────────────────
# paladin_cli/ lives one level above paladin/ (the project root).
# Engine/Context_Engine/ is a sibling of paladin_cli/.
_HERE = Path(__file__).resolve().parent          # …/paladin/paladin_cli
_PROJ = _HERE.parent                             # …/paladin
_CTX_ENGINE_DIR = _PROJ / "Engine" / "Context_Engine"
_CSV_PATH = _CTX_ENGINE_DIR / "trialHack_output.csv"

# Inject path so `from paladin.context.engine import ContextEngine` works
if str(_CTX_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_CTX_ENGINE_DIR))

# ── Lazy import — only fail at call time, not at import time ─────────────────
def _import_engine():
    try:
        from paladin.context.engine import ContextEngine
        from paladin.context.history import ActionHistory
        from paladin.schemas.action import AgentAction
        return ContextEngine, ActionHistory, AgentAction
    except ImportError as exc:
        raise ImportError(
            f"Could not import the Context Engine from {_CTX_ENGINE_DIR}.\n"
            f"Make sure pydantic is installed: pip install pydantic==2.10.6\n"
            f"Original error: {exc}"
        ) from exc

# ── Key mapping (same as trialHack.py) ───────────────────────────────────────
_KEY_MAP = {
    "prompt":  "prompt",
    "agent":   "agent",
    "action":  "action_type",
    "target":  "target",
    "cwd":     "cwd",
    "os":      "os",
    "shell":   "shell",
    "parent":  "parent_process",
    "user":    "user",
    "project": "project_root",
    "task":    "task_context",
    "command": "command",
}

_FLAGGED_SENSITIVITIES = {"sensitive", "critical"}

_CSV_FIELDNAMES = [
    "timestamp",
    "raw_prompt",
    "action_type",
    "target",
    "agent",
    "sensitivity",
    "target_category",
    "cwd",
    "risk_score",
]


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    raw_prompt:      str
    prompt_id:       str
    action_type:     str
    target:          str
    agent:           str
    sensitivity:     str
    target_category: str
    cwd:             str
    is_outside_project: bool
    flags:           list[str]
    ctx_dict:        dict = field(default_factory=dict)
    error:           str | None = None

    @property
    def is_flagged(self) -> bool:
        return bool(self.flags)

    @property
    def passed(self) -> bool:
        return not self.flags and self.error is None


# ── Core helpers ──────────────────────────────────────────────────────────────

def parse_prompt(prompt_str: str) -> dict:
    """Parse a key=value prompt string into a structured dict."""
    pattern = r'(\w+)=(?:"([^"]*)"|([\S]+))'
    matches = re.findall(pattern, prompt_str)

    raw = {}
    for key, quoted_val, plain_val in matches:
        raw[key.lower()] = quoted_val if quoted_val else plain_val

    structured: dict = {}
    for short_key, value in raw.items():
        field_name = _KEY_MAP.get(short_key, short_key)
        structured[field_name] = value

    structured.setdefault("prompt", "unknown")
    structured.setdefault("action_type", "file_read")
    structured.setdefault("metadata", {})

    return structured


def _build_agent_action(data: dict, AgentAction):  # noqa: N803
    return AgentAction(
        action_id      = data.get("prompt", "unknown"),
        action_type    = data["action_type"],
        target         = data.get("target"),
        command        = data.get("command"),
        task_context   = data.get("task_context"),
        agent          = data.get("agent", "unknown"),
        parent_process = data.get("parent_process"),
        cwd            = data.get("cwd"),
        os             = data.get("os"),
        shell          = data.get("shell"),
        project_root   = data.get("project_root"),
        user           = data.get("user"),
        metadata       = data.get("metadata", {}),
    )


def _check_flags(ctx, prompt_id: str, target: str) -> list[str]:
    reasons = []
    sensitivity = str(ctx.sensitivity).lower()
    if sensitivity in _FLAGGED_SENSITIVITIES:
        reasons.append(
            f"sensitivity is '{ctx.sensitivity}' — prompt '{prompt_id}' "
            f"tried to access a {ctx.target_category} resource: {target!r}"
        )
    if ctx.is_outside_project:
        reasons.append(
            f"target is outside the project root — prompt '{prompt_id}' "
            f"accessed {target!r} which is not under the project directory"
        )
    return reasons


def _append_csv(data: dict, ctx) -> None:
    """Append one result row to trialHack_output.csv."""
    raw_prompt = data.get("_raw_prompt", "")
    risk_score = ""
    try:
        import sys as _sys, os as _os
        _here = _os.path.dirname(_os.path.abspath(__file__))
        _engine_dir = _os.path.join(_here, "..", "Engine")
        _risk_dir   = _os.path.join(_here, "..", "Engine", "Risk_Engine")
        for _p in (_engine_dir, _risk_dir):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        import Risk_Engine.RiskEngine as _re
        _, risk_score = _re.risk_score(raw_prompt)
    except Exception:
        pass
    row = {
        "timestamp":       datetime.now().isoformat(timespec="seconds"),
        "raw_prompt":      raw_prompt,
        "action_type":     data.get("action_type", "unknown"),
        "target":          data.get("target", "N/A"),
        "agent":           data.get("agent", "unknown"),
        "sensitivity":     str(ctx.sensitivity),
        "target_category": str(ctx.target_category),
        "cwd":             data.get("cwd", ""),
        "risk_score":      risk_score,
    }

    file_exists = _CSV_PATH.is_file()
    with open(_CSV_PATH, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ── Public API ────────────────────────────────────────────────────────────────

def run_check(prompt_str: str) -> CheckResult:
    """
    Run the Context Engine on `prompt_str` and return a CheckResult.

    The result is also appended to trialHack_output.csv automatically.
    Raises nothing — errors are captured in CheckResult.error.
    """
    try:
        ContextEngine, ActionHistory, AgentAction = _import_engine()
    except ImportError as exc:
        return CheckResult(
            raw_prompt=prompt_str,
            prompt_id="unknown",
            action_type="unknown",
            target="N/A",
            agent="unknown",
            sensitivity="unknown",
            target_category="unknown",
            cwd="",
            is_outside_project=False,
            flags=[],
            error=str(exc),
        )

    try:
        data = parse_prompt(prompt_str)
        data["_raw_prompt"] = prompt_str  # stash for CSV writer

        engine = ContextEngine(action_history=ActionHistory())
        action = _build_agent_action(data, AgentAction)
        ctx    = engine.build_context(action)

        prompt_id = data.get("prompt", "unknown")
        target    = data.get("target", "N/A")
        flags     = _check_flags(ctx, prompt_id, target)

        # Write to CSV
        _append_csv(data, ctx)

        return CheckResult(
            raw_prompt      = prompt_str,
            prompt_id       = prompt_id,
            action_type     = data.get("action_type", "unknown"),
            target          = target,
            agent           = data.get("agent", "unknown"),
            sensitivity     = str(ctx.sensitivity),
            target_category = str(ctx.target_category),
            cwd             = data.get("cwd", ""),
            is_outside_project = bool(ctx.is_outside_project),
            flags           = flags,
            ctx_dict        = ctx.to_dict(),
        )

    except Exception as exc:
        return CheckResult(
            raw_prompt=prompt_str,
            prompt_id="unknown",
            action_type="unknown",
            target="N/A",
            agent="unknown",
            sensitivity="error",
            target_category="unknown",
            cwd="",
            is_outside_project=False,
            flags=[],
            error=str(exc),
        )

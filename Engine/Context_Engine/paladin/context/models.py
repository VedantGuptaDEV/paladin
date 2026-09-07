"""
context/models.py

ActionContext — the single normalized object produced by the Context Engine
and consumed by every downstream engine (Policy, Risk, Decision).

Architecture rule:
  Raw AgentAction → ContextEngine.build_context() → ActionContext
  → Policy Engine
  → Risk Engine
  → Decision Engine

No downstream engine ever inspects the raw AgentAction.
No downstream engine makes security decisions based on raw strings.
They all operate on the structured, enriched ActionContext.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionContext:
    """
    A fully-enriched, normalized context object.

    Answers the six questions every security decision needs:

    WHO?    agent, agent_pid, parent_process, user
    WHAT?   action_type, target, command, task_context
    WHERE?  cwd, os, shell, project_root
    TARGET? target_type, target_sensitivity, target_category
    HOW SENSITIVE? sensitivity
    WHAT HAPPENED BEFORE? recent_actions
    WHAT PROJECT? project_root, is_outside_project
    """

    # ── WHO ──────────────────────────────────────────────────────────────────
    agent: str = "unknown"
    agent_pid: int | None = None
    parent_process: str | None = None
    user: str | None = None

    # ── WHAT ─────────────────────────────────────────────────────────────────
    action_type: str = ""
    target: str | None = None
    command: str | None = None
    task_context: str | None = None

    # ── WHERE ────────────────────────────────────────────────────────────────
    cwd: str | None = None
    os: str | None = None
    shell: str | None = None
    project_root: str | None = None

    # ── TARGET classification (set by ContextEngine) ─────────────────────────
    target_type: str = "unknown"        # "file", "url", "command", "process"
    target_category: str = "unknown"    # "source_code", "credential", "config", etc.
    sensitivity: str = "normal"         # "normal", "sensitive", "critical"

    # ── PROJECT scope (set by ContextEngine) ─────────────────────────────────
    is_outside_project: bool = False    # True if target is outside project_root

    # ── HISTORY (set by ContextEngine using history manager) ─────────────────
    recent_actions: list[dict[str, Any]] = field(default_factory=list)

    # ── TIMESTAMP ────────────────────────────────────────────────────────────
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict for JSON output / downstream engines."""
        import dataclasses
        return dataclasses.asdict(self)

    def summary(self) -> str:
        """One-line human-readable summary for logging."""
        return (
            f"[{self.agent}] {self.action_type} "
            f"target={self.target or self.command or 'none'} "
            f"sensitivity={self.sensitivity} "
            f"outside_project={self.is_outside_project}"
        )

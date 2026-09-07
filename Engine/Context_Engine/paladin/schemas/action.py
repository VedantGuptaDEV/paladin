"""
schemas/action.py

Input model for a raw agent action received by Paladin.

This is the payload that Kiro (or any other agent) sends to the Paladin CLI.
It includes the action itself plus all available environment context at the
time the action was attempted.
"""

from typing import Any
from pydantic import BaseModel, Field


class AgentAction(BaseModel):
    """
    A single action attempted by an AI coding agent.

    This is the raw input. The Context Engine will enrich this into a
    fully-normalized ActionContext that all downstream engines consume.
    """

    # ── Action fields ────────────────────────────────────────────────────────
    action_id: str = Field(..., description="Unique identifier for this action")
    action_type: str = Field(
        ...,
        description=(
            "Type of action being attempted. "
            "Values: file_read, file_write, file_delete, command_execute, "
            "network_request, credential_access, process_start"
        ),
    )
    target: str | None = Field(
        default=None,
        description="File path, URL, or resource being acted upon",
    )
    command: str | None = Field(
        default=None,
        description="Shell command string (for command_execute actions)",
    )
    task_context: str | None = Field(
        default=None,
        description="What the agent says it is trying to accomplish",
    )

    # ── Agent fields ─────────────────────────────────────────────────────────
    agent: str = Field(
        default="unknown",
        description="Name of the agent (e.g. 'kiro')",
    )
    agent_pid: int | None = Field(
        default=None,
        description="PID of the agent process",
    )
    parent_process: str | None = Field(
        default=None,
        description="Name of the parent process (e.g. 'kiro-cli')",
    )

    # ── Environment fields ───────────────────────────────────────────────────
    cwd: str | None = Field(
        default=None,
        description="Current working directory at time of action",
    )
    os: str | None = Field(
        default=None,
        description="Operating system (e.g. 'linux', 'darwin', 'windows')",
    )
    shell: str | None = Field(
        default=None,
        description="Shell being used (e.g. 'bash', 'zsh', 'powershell')",
    )

    # ── Project fields ───────────────────────────────────────────────────────
    project_root: str | None = Field(
        default=None,
        description="Absolute path to the project root directory",
    )
    user: str | None = Field(
        default=None,
        description="OS username performing the action",
    )

    # ── Extra metadata ───────────────────────────────────────────────────────
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional action-specific metadata",
    )

    model_config = {"extra": "allow"}

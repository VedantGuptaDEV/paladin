"""
intent/rules.py

Deterministic intent rules.

Each rule is a (condition, intent_category, confidence, reason_template) tuple.
Rules are evaluated in order — first match wins.

Adding a new rule: append a Rule to INTENT_RULES. No other file needs to change.
"""

from dataclasses import dataclass
from typing import Callable

from paladin.schemas.action import AgentAction
from paladin.schemas.context import ContextResult, ResourceCategory, Sensitivity
from paladin.schemas.intent import IntentCategory
from paladin.context import patterns as P


@dataclass(frozen=True)
class Rule:
    """A single deterministic intent rule."""
    condition: Callable[[AgentAction, ContextResult], bool]
    intent: IntentCategory
    confidence: float
    reason_template: str   # may reference {action_type}, {target}, {command}

    def matches(self, action: AgentAction, context: ContextResult) -> bool:
        return self.condition(action, context)

    def reason(self, action: AgentAction) -> str:
        return self.reason_template.format(
            action_type=action.action_type,
            target=action.target or "",
            command=action.command or "",
        )


# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------

def _action_type_in(action_types: frozenset[str]):
    def check(action: AgentAction, ctx: ContextResult) -> bool:
        return action.action_type.lower().strip() in action_types
    return check


def _is_file_read(action: AgentAction, ctx: ContextResult) -> bool:
    return action.action_type.lower() in P.READ_ACTION_TYPES


def _is_file_write(action: AgentAction, ctx: ContextResult) -> bool:
    return action.action_type.lower() in P.WRITE_ACTION_TYPES


def _is_file_delete(action: AgentAction, ctx: ContextResult) -> bool:
    return action.action_type.lower() in P.DELETE_ACTION_TYPES


def _is_execute(action: AgentAction, ctx: ContextResult) -> bool:
    return action.action_type.lower() in P.EXECUTE_ACTION_TYPES


# ---------------------------------------------------------------------------
# Rule definitions — evaluated top-to-bottom, first match wins
# ---------------------------------------------------------------------------

INTENT_RULES: list[Rule] = [

    # ── DELETE actions ──────────────────────────────────────────────────────
    Rule(
        condition=_is_file_delete,
        intent=IntentCategory.DELETE_RESOURCE,
        confidence=0.95,
        reason_template=(
            "The agent is performing a delete action on '{target}'. "
            "This is classified as a resource deletion intent."
        ),
    ),

    # ── SENSITIVE read: credentials / SSH keys / cloud creds ─────────────────
    Rule(
        condition=lambda a, c: (
            _is_file_read(a, c)
            and (
                c.resource_category == ResourceCategory.CREDENTIAL_OR_SECRET
                or (
                    c.resource_category == ResourceCategory.SSH_RESOURCE
                    and c.contains_credentials  # keys, not config
                )
            )
        ),
        intent=IntentCategory.ACCESS_CREDENTIALS,
        confidence=0.92,
        reason_template=(
            "The agent is reading '{target}', which is a credential or secret resource. "
            "Intent is classified as credential access."
        ),
    ),

    # ── SENSITIVE read: SSH config / known_hosts (no direct credentials) ─────
    Rule(
        condition=lambda a, c: (
            _is_file_read(a, c)
            and c.resource_category == ResourceCategory.SSH_RESOURCE
            and not c.contains_credentials
        ),
        intent=IntentCategory.ACCESS_SENSITIVE_CONFIGURATION,
        confidence=0.90,
        reason_template=(
            "The agent is attempting to access an SSH resource '{target}'. "
            "SSH configuration and keys are sensitive resources."
        ),
    ),

    # ── SENSITIVE write: credentials / SSH ──────────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_file_write(a, c)
            and c.resource_category in (
                ResourceCategory.CREDENTIAL_OR_SECRET,
                ResourceCategory.SSH_RESOURCE,
            )
        ),
        intent=IntentCategory.ACCESS_CREDENTIALS,
        confidence=0.95,
        reason_template=(
            "The agent is writing to a credential or SSH resource '{target}'. "
            "This is a high-risk modification of sensitive configuration."
        ),
    ),

    # ── SYSTEM RESOURCE write/modify ─────────────────────────────────────────
    Rule(
        condition=lambda a, c: (
            (_is_file_write(a, c) or _is_file_delete(a, c))
            and c.is_system_resource
        ),
        intent=IntentCategory.MODIFY_SYSTEM,
        confidence=0.88,
        reason_template=(
            "The agent is modifying a system resource '{target}'. "
            "Changes to system files can affect the entire environment."
        ),
    ),

    # ── NETWORK actions (action type) ────────────────────────────────────────
    Rule(
        condition=_action_type_in(P.NETWORK_ACTION_TYPES),
        intent=IntentCategory.NETWORK_ACCESS,
        confidence=0.93,
        reason_template=(
            "The agent is performing a network request to '{target}'. "
            "Intent is classified as network access."
        ),
    ),

    # ── PACKAGE installation (command) — checked BEFORE generic network ──────
    Rule(
        condition=lambda a, c: (
            action_type_is_package(a) or (
                _is_execute(a, c)
                and bool(a.command)
                and P.matches_any(a.command, P.PACKAGE_INSTALL_PATTERNS)
            )
        ),
        intent=IntentCategory.INSTALL_DEPENDENCY,
        confidence=0.92,
        reason_template=(
            "The agent is installing a package or dependency via '{command}'. "
            "Intent is classified as dependency installation."
        ),
    ),

    # ── DESTRUCTIVE command ──────────────────────────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_execute(a, c)
            and c.is_destructive
        ),
        intent=IntentCategory.DELETE_RESOURCE,
        confidence=0.90,
        reason_template=(
            "The command '{command}' matches a destructive pattern. "
            "This could permanently remove or corrupt data."
        ),
    ),

    # ── NETWORK command (curl, wget, ssh, etc.) ──────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_execute(a, c)
            and c.is_network_operation
            and not c.is_destructive
        ),
        intent=IntentCategory.NETWORK_ACCESS,
        confidence=0.85,
        reason_template=(
            "The command '{command}' performs a network operation. "
            "Intent is classified as network access."
        ),
    ),

    # ── PROCESS / SYSTEM command ─────────────────────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_execute(a, c)
            and c.is_system_resource
            and not c.is_destructive
            and not c.is_network_operation
        ),
        intent=IntentCategory.EXECUTE_COMMAND,
        confidence=0.80,
        reason_template=(
            "The command '{command}' manages processes or system services. "
            "Intent is classified as system command execution."
        ),
    ),

    # ── GENERAL command execution ────────────────────────────────────────────
    Rule(
        condition=_is_execute,
        intent=IntentCategory.EXECUTE_COMMAND,
        confidence=0.75,
        reason_template=(
            "The agent is executing a shell command: '{command}'. "
            "Intent is classified as general command execution."
        ),
    ),

    # ── CONFIGURATION read ───────────────────────────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_file_read(a, c)
            and c.resource_category == ResourceCategory.CONFIGURATION_FILE
            and not c.contains_credentials
        ),
        intent=IntentCategory.ACCESS_CONFIGURATION,
        confidence=0.85,
        reason_template=(
            "The agent is reading a configuration file '{target}'. "
            "Intent is classified as configuration access."
        ),
    ),

    # ── SENSITIVE CONFIGURATION read ─────────────────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_file_read(a, c)
            and c.resource_category == ResourceCategory.CONFIGURATION_FILE
            and c.contains_credentials
        ),
        intent=IntentCategory.ACCESS_SENSITIVE_CONFIGURATION,
        confidence=0.88,
        reason_template=(
            "The agent is reading a configuration file '{target}' that may contain secrets. "
            "Intent is classified as sensitive configuration access."
        ),
    ),

    # ── ENVIRONMENT FILE read ────────────────────────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_file_read(a, c)
            and c.resource_category == ResourceCategory.ENVIRONMENT_FILE
        ),
        intent=IntentCategory.ACCESS_SENSITIVE_CONFIGURATION,
        confidence=0.90,
        reason_template=(
            "The agent is reading an environment file '{target}' which typically contains secrets. "
            "Intent is classified as sensitive configuration access."
        ),
    ),

    # ── WRITE to configuration ───────────────────────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_file_write(a, c)
            and c.resource_category in (
                ResourceCategory.CONFIGURATION_FILE,
                ResourceCategory.ENVIRONMENT_FILE,
            )
        ),
        intent=IntentCategory.ACCESS_CONFIGURATION,
        confidence=0.82,
        reason_template=(
            "The agent is modifying a configuration file '{target}'. "
            "Intent is classified as configuration modification."
        ),
    ),

    # ── WRITE to project file ────────────────────────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_file_write(a, c)
            and c.resource_category == ResourceCategory.PROJECT_FILE
        ),
        intent=IntentCategory.MODIFY_PROJECT_FILE,
        confidence=0.88,
        reason_template=(
            "The agent is writing to a project file '{target}'. "
            "Intent is classified as project file modification."
        ),
    ),

    # ── READ project file ────────────────────────────────────────────────────
    Rule(
        condition=lambda a, c: (
            _is_file_read(a, c)
            and c.resource_category == ResourceCategory.PROJECT_FILE
        ),
        intent=IntentCategory.READ_PROJECT_FILE,
        confidence=0.90,
        reason_template=(
            "The agent is reading a project file '{target}'. "
            "Intent is classified as normal project file read."
        ),
    ),

    # ── PACKAGE action type (without a command) ──────────────────────────────
    Rule(
        condition=lambda a, c: action_type_is_package(a),
        intent=IntentCategory.INSTALL_DEPENDENCY,
        confidence=0.90,
        reason_template=(
            "The action type '{action_type}' indicates a package installation. "
            "Intent is classified as dependency installation."
        ),
    ),

    # ── PROCESS SPAWN ────────────────────────────────────────────────────────
    Rule(
        condition=_action_type_in(P.PROCESS_ACTION_TYPES),
        intent=IntentCategory.SPAWN_PROCESS,
        confidence=0.88,
        reason_template=(
            "The action type '{action_type}' indicates a process is being spawned. "
            "Intent is classified as process spawn."
        ),
    ),
]


def action_type_is_package(action: AgentAction) -> bool:
    return action.action_type.lower().strip() in P.PACKAGE_ACTION_TYPES

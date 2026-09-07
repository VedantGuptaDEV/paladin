"""
context/analyzer.py

ContextEngine — the main entry point for context analysis.

Usage:
    from paladin.context import ContextEngine
    from paladin.schemas import AgentAction

    engine = ContextEngine()
    result = engine.analyze(action)
    print(result.sensitivity)   # "HIGH"
    print(result.resource_type) # "ssh_configuration"
"""

from paladin.schemas.action import AgentAction
from paladin.schemas.context import (
    ContextResult,
    ResourceCategory,
    ResourceType,
    Sensitivity,
)
from paladin.context import patterns as P
from paladin.context.classifiers import (
    classify_file_target,
    classify_command,
    extract_security_attributes,
    resolve_sensitivity,
    FileClassification,
    CommandClassification,
)


class ContextEngine:
    """
    Deterministic context analysis engine.

    Accepts an AgentAction and returns a ContextResult that describes:
    - What kind of resource is being targeted
    - How sensitive it is
    - Security attributes (credentials, destructive, network, etc.)

    This class is stateless — safe to instantiate once and reuse across
    multiple actions. Thread-safe.
    """

    def analyze(self, action: AgentAction) -> ContextResult:
        """
        Analyse an agent action and return structured context.

        Strategy:
        1. If action has a file target → classify the file path
        2. If action has a command    → classify the command
        3. If action is network type  → classify as network resource
        4. Merge results, resolve final sensitivity
        5. Build and return ContextResult
        """
        action_type = action.action_type.lower().strip()

        file_cls: FileClassification | None = None
        cmd_cls: CommandClassification | None = None

        # ── Step 1: classify the file target ───────────────────────────────
        if action.target and action_type not in P.NETWORK_ACTION_TYPES:
            file_cls = classify_file_target(action.target)

        # ── Step 2: classify the command ────────────────────────────────────
        if action.command:
            cmd_cls = classify_command(action.command)

        # ── Step 3: handle network action types directly ────────────────────
        if action_type in P.NETWORK_ACTION_TYPES:
            return self._build_network_result(action)

        # ── Step 4: handle package install action types ─────────────────────
        if action_type in P.PACKAGE_ACTION_TYPES:
            return self._build_package_result(action, cmd_cls)

        # ── Step 5: handle process spawn ────────────────────────────────────
        if action_type in P.PROCESS_ACTION_TYPES:
            return self._build_process_result(action, cmd_cls)

        # ── Step 6: handle pure command execution ───────────────────────────
        if action_type in P.EXECUTE_ACTION_TYPES and cmd_cls is not None:
            return self._build_command_result(action, cmd_cls)

        # ── Step 7: handle file-based actions ───────────────────────────────
        if file_cls is not None:
            return self._build_file_result(action, file_cls, cmd_cls)

        # ── Step 8: no target, no command — use action type alone ────────────
        return self._build_unknown_result(action)

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    def _build_file_result(
        self,
        action: AgentAction,
        file_cls: FileClassification,
        cmd_cls: CommandClassification | None,
    ) -> ContextResult:
        """Build a ContextResult when a file target was classified."""
        security = extract_security_attributes(
            action_type=action.action_type,
            target=action.target,
            command=action.command,
            file_cls=file_cls,
            cmd_cls=cmd_cls,
        )
        sensitivity = resolve_sensitivity(file_cls, cmd_cls, action.action_type)

        # Compose reason
        parts = [file_cls.reason]
        if cmd_cls:
            parts.append(cmd_cls.reason)
        reason = " ".join(parts)

        return ContextResult(
            resource_type=file_cls.resource_type,
            resource_category=file_cls.resource_category,
            sensitivity=sensitivity,
            reason=reason,
            **security,
        )

    def _build_command_result(
        self,
        action: AgentAction,
        cmd_cls: CommandClassification,
    ) -> ContextResult:
        """Build a ContextResult when a command is being executed."""
        security = extract_security_attributes(
            action_type=action.action_type,
            target=action.target,
            command=action.command,
            file_cls=None,
            cmd_cls=cmd_cls,
        )
        return ContextResult(
            resource_type=cmd_cls.resource_type,
            resource_category=cmd_cls.resource_category,
            sensitivity=cmd_cls.sensitivity,
            reason=cmd_cls.reason,
            **security,
        )

    def _build_network_result(self, action: AgentAction) -> ContextResult:
        """Build a ContextResult for a network request action."""
        target = action.target or ""
        # Internal vs external URL
        is_internal = any(
            kw in target.lower()
            for kw in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "internal", "local")
        )
        resource_type = ResourceType.INTERNAL_URL if is_internal else ResourceType.EXTERNAL_URL
        sensitivity = Sensitivity.LOW if is_internal else Sensitivity.MEDIUM

        return ContextResult(
            resource_type=resource_type,
            resource_category=ResourceCategory.NETWORK_RESOURCE,
            sensitivity=sensitivity,
            is_network_operation=True,
            is_destructive=False,
            is_system_resource=False,
            contains_credentials=False,
            requires_special_attention=False,
            reason=(
                f"Action is a network request to {'an internal' if is_internal else 'an external'} URL."
            ),
        )

    def _build_package_result(
        self,
        action: AgentAction,
        cmd_cls: CommandClassification | None,
    ) -> ContextResult:
        """Build a ContextResult for a package installation."""
        reason = "Action installs a package or dependency."
        if cmd_cls:
            reason = cmd_cls.reason

        return ContextResult(
            resource_type=ResourceType.PACKAGE_INSTALL,
            resource_category=ResourceCategory.PACKAGE_OR_DEPENDENCY,
            sensitivity=Sensitivity.MEDIUM,
            is_network_operation=True,
            is_destructive=False,
            is_system_resource=False,
            contains_credentials=False,
            requires_special_attention=False,
            reason=reason,
        )

    def _build_process_result(
        self,
        action: AgentAction,
        cmd_cls: CommandClassification | None,
    ) -> ContextResult:
        """Build a ContextResult for a process spawn or system operation."""
        reason = "Action spawns a process or manages system services."
        sensitivity = Sensitivity.MEDIUM

        if cmd_cls:
            reason = cmd_cls.reason
            sensitivity = cmd_cls.sensitivity

        return ContextResult(
            resource_type=ResourceType.PROCESS_COMMAND,
            resource_category=ResourceCategory.PROCESS,
            sensitivity=sensitivity,
            is_network_operation=False,
            is_destructive=False,
            is_system_resource=True,
            contains_credentials=False,
            requires_special_attention=sensitivity in (Sensitivity.HIGH, Sensitivity.CRITICAL),
            reason=reason,
        )

    def _build_unknown_result(self, action: AgentAction) -> ContextResult:
        """Fallback when no target, command, or recognised action type."""
        return ContextResult(
            resource_type=ResourceType.UNKNOWN,
            resource_category=ResourceCategory.UNKNOWN,
            sensitivity=Sensitivity.LOW,
            is_network_operation=False,
            is_destructive=False,
            is_system_resource=False,
            contains_credentials=False,
            requires_special_attention=False,
            reason=(
                f"Action type '{action.action_type}' with no target or command. "
                "Context cannot be determined deterministically."
            ),
        )

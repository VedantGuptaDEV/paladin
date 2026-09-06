"""
context/classifiers.py

Pure deterministic classification functions.
No side effects. No external calls. Input in, classification out.

Each function accepts a normalised string (path or command) and returns
an enum value from the schemas package.
"""

import os
from typing import NamedTuple

from paladin.schemas.context import (
    ResourceCategory,
    ResourceType,
    Sensitivity,
)
from paladin.context import patterns as P


# ---------------------------------------------------------------------------
# Internal data class for classifier output before final assembly
# ---------------------------------------------------------------------------

class FileClassification(NamedTuple):
    resource_type: ResourceType
    resource_category: ResourceCategory
    sensitivity: Sensitivity
    contains_credentials: bool
    is_system_resource: bool
    reason: str


class CommandClassification(NamedTuple):
    resource_type: ResourceType
    resource_category: ResourceCategory
    sensitivity: Sensitivity
    is_destructive: bool
    is_network_operation: bool
    is_system_resource: bool
    contains_credentials: bool
    reason: str


# ---------------------------------------------------------------------------
# File / path classifier
# ---------------------------------------------------------------------------

def classify_file_target(path: str) -> FileClassification:
    """
    Classify a file path into resource type, category, and sensitivity.

    Decision priority (highest to lowest):
    1. SSH keys / private keys           → CRITICAL
    2. Cloud credentials                 → CRITICAL
    3. .env / credential / secret files  → HIGH
    4. SSH config / known_hosts          → HIGH
    5. System paths (/etc/, /proc/, …)   → HIGH
    6. Shell history / profile           → MEDIUM
    7. Git / Docker config               → MEDIUM
    8. Database files                    → MEDIUM
    9. General config files              → MEDIUM
    10. Source code / everything else    → LOW
    """
    norm = path.replace("\\", "/")

    # ── CRITICAL: private keys ──────────────────────────────────────────────
    if P.matches_any(norm, P.SSH_KEY_PATTERNS):
        return FileClassification(
            resource_type=ResourceType.SSH_KEY,
            resource_category=ResourceCategory.SSH_RESOURCE,
            sensitivity=Sensitivity.CRITICAL,
            contains_credentials=True,
            is_system_resource=False,
            reason="Path matches an SSH private key file.",
        )

    if P.matches_any(norm, P.PRIVATE_KEY_PATTERNS):
        return FileClassification(
            resource_type=ResourceType.PRIVATE_KEY,
            resource_category=ResourceCategory.CREDENTIAL_OR_SECRET,
            sensitivity=Sensitivity.CRITICAL,
            contains_credentials=True,
            is_system_resource=False,
            reason="Path matches a private key or certificate file.",
        )

    # ── CRITICAL: cloud credentials ─────────────────────────────────────────
    if P.matches_any(norm, P.CLOUD_CREDENTIAL_PATTERNS):
        return FileClassification(
            resource_type=ResourceType.CLOUD_CREDENTIALS,
            resource_category=ResourceCategory.CREDENTIAL_OR_SECRET,
            sensitivity=Sensitivity.CRITICAL,
            contains_credentials=True,
            is_system_resource=False,
            reason="Path matches a cloud provider credentials file or directory.",
        )

    # ── HIGH: system paths (checked BEFORE credential patterns to avoid
    #         /etc/passwd matching the 'passwords?' credential pattern) ────────
    if P.matches_any(norm, P.SYSTEM_PATH_PATTERNS):
        return FileClassification(
            resource_type=ResourceType.SYSTEM_CONFIGURATION,
            resource_category=ResourceCategory.SYSTEM_RESOURCE,
            sensitivity=Sensitivity.HIGH,
            contains_credentials=False,
            is_system_resource=True,
            reason="Path is a system-level resource (/etc/, /proc/, Windows system directory).",
        )

    # ── HIGH: .env / general credential files ───────────────────────────────
    if P.matches_any(norm, P.CREDENTIAL_PATH_PATTERNS):
        # Distinguish .env from generic credential files
        if re.search(r"\.env($|\.)", norm, re.IGNORECASE):
            return FileClassification(
                resource_type=ResourceType.ENVIRONMENT_FILE,
                resource_category=ResourceCategory.ENVIRONMENT_FILE,
                sensitivity=Sensitivity.HIGH,
                contains_credentials=True,
                is_system_resource=False,
                reason="Path matches an environment (.env) file likely containing secrets.",
            )
        return FileClassification(
            resource_type=ResourceType.CREDENTIAL_FILE,
            resource_category=ResourceCategory.CREDENTIAL_OR_SECRET,
            sensitivity=Sensitivity.HIGH,
            contains_credentials=True,
            is_system_resource=False,
            reason="Path matches a credential or secret file.",
        )

    # ── HIGH: SSH directory / config / known_hosts ───────────────────────────
    if P.matches_any(norm, P.SSH_PATH_PATTERNS):
        if P.matches_any(norm, P.SSH_CONFIG_PATTERNS):
            return FileClassification(
                resource_type=ResourceType.SSH_CONFIGURATION,
                resource_category=ResourceCategory.SSH_RESOURCE,
                sensitivity=Sensitivity.HIGH,
                contains_credentials=False,
                is_system_resource=False,
                reason="Path matches an SSH configuration file.",
            )
        if "known_hosts" in norm.lower():
            return FileClassification(
                resource_type=ResourceType.SSH_KNOWN_HOSTS,
                resource_category=ResourceCategory.SSH_RESOURCE,
                sensitivity=Sensitivity.HIGH,
                contains_credentials=False,
                is_system_resource=False,
                reason="Path matches the SSH known_hosts file.",
            )
        # General .ssh directory access
        return FileClassification(
            resource_type=ResourceType.SSH_CONFIGURATION,
            resource_category=ResourceCategory.SSH_RESOURCE,
            sensitivity=Sensitivity.HIGH,
            contains_credentials=True,
            is_system_resource=False,
            reason="Path is inside the .ssh directory, which contains sensitive keys and config.",
        )

    # ── MEDIUM: shell history ────────────────────────────────────────────────
    if P.matches_any(norm, P.SHELL_HISTORY_PATTERNS):
        return FileClassification(
            resource_type=ResourceType.SHELL_HISTORY,
            resource_category=ResourceCategory.SYSTEM_RESOURCE,
            sensitivity=Sensitivity.MEDIUM,
            contains_credentials=True,  # history may contain passwords typed in CLI
            is_system_resource=False,
            reason="Path matches a shell history file, which may contain sensitive commands.",
        )

    # ── MEDIUM: shell profiles ───────────────────────────────────────────────
    if P.matches_any(norm, P.SHELL_PROFILE_PATTERNS):
        return FileClassification(
            resource_type=ResourceType.SHELL_PROFILE,
            resource_category=ResourceCategory.CONFIGURATION_FILE,
            sensitivity=Sensitivity.MEDIUM,
            contains_credentials=False,
            is_system_resource=False,
            reason="Path matches a shell profile file that may contain environment variables or aliases.",
        )

    # ── MEDIUM: git config ───────────────────────────────────────────────────
    if P.matches_any(norm, P.GIT_CONFIG_PATTERNS):
        contains_creds = "gitcredentials" in norm.lower()
        return FileClassification(
            resource_type=ResourceType.GIT_CONFIGURATION,
            resource_category=ResourceCategory.CONFIGURATION_FILE,
            sensitivity=Sensitivity.MEDIUM,
            contains_credentials=contains_creds,
            is_system_resource=False,
            reason="Path matches a Git configuration file.",
        )

    # ── MEDIUM: Docker config ────────────────────────────────────────────────
    if P.matches_any(norm, P.DOCKER_CONFIG_PATTERNS):
        return FileClassification(
            resource_type=ResourceType.DOCKER_CONFIGURATION,
            resource_category=ResourceCategory.CONFIGURATION_FILE,
            sensitivity=Sensitivity.MEDIUM,
            contains_credentials="config.json" in norm.lower(),
            is_system_resource=False,
            reason="Path matches a Docker configuration file.",
        )

    # ── MEDIUM: database files ───────────────────────────────────────────────
    if P.matches_any(norm, P.DATABASE_PATTERNS):
        return FileClassification(
            resource_type=ResourceType.DATABASE_FILE,
            resource_category=ResourceCategory.CONFIGURATION_FILE,
            sensitivity=Sensitivity.MEDIUM,
            contains_credentials=True,
            is_system_resource=False,
            reason="Path matches a database file or database configuration.",
        )

    # ── MEDIUM: general config files ─────────────────────────────────────────
    if P.matches_any(norm, P.CONFIG_FILE_PATTERNS):
        return FileClassification(
            resource_type=ResourceType.CONFIGURATION,
            resource_category=ResourceCategory.CONFIGURATION_FILE,
            sensitivity=Sensitivity.MEDIUM,
            contains_credentials=False,
            is_system_resource=False,
            reason="Path matches a configuration file.",
        )

    # ── LOW: package manifests ───────────────────────────────────────────────
    basename = os.path.basename(norm).lower()
    if basename in (
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
        "cargo.toml", "cargo.lock", "go.mod", "go.sum",
        "gemfile", "gemfile.lock", "pom.xml", "build.gradle",
        "composer.json", "composer.lock",
    ):
        return FileClassification(
            resource_type=ResourceType.PACKAGE_MANIFEST,
            resource_category=ResourceCategory.PACKAGE_OR_DEPENDENCY,
            sensitivity=Sensitivity.LOW,
            contains_credentials=False,
            is_system_resource=False,
            reason="Path matches a package manifest or dependency lockfile.",
        )

    # ── LOW: default — project source file ───────────────────────────────────
    return FileClassification(
        resource_type=ResourceType.SOURCE_CODE,
        resource_category=ResourceCategory.PROJECT_FILE,
        sensitivity=Sensitivity.LOW,
        contains_credentials=False,
        is_system_resource=False,
        reason="Path does not match any sensitive pattern; treated as a normal project file.",
    )


# ---------------------------------------------------------------------------
# Command classifier
# ---------------------------------------------------------------------------

def classify_command(command: str) -> CommandClassification:
    """
    Classify a shell command by what it does.

    Checks in order: destructive → network → package install → process/privilege → default.
    """
    if not command or not command.strip():
        return CommandClassification(
            resource_type=ResourceType.SHELL_COMMAND,
            resource_category=ResourceCategory.UNKNOWN,
            sensitivity=Sensitivity.LOW,
            is_destructive=False,
            is_network_operation=False,
            is_system_resource=False,
            contains_credentials=False,
            reason="Empty or blank command.",
        )

    cmd = command.strip()

    is_destructive = P.matches_any(cmd, P.DESTRUCTIVE_COMMAND_PATTERNS)
    is_network = P.matches_any(cmd, P.NETWORK_COMMAND_PATTERNS)
    is_package = P.matches_any(cmd, P.PACKAGE_INSTALL_PATTERNS)
    is_process = P.matches_any(cmd, P.PROCESS_COMMAND_PATTERNS)

    # Destructive takes highest priority
    if is_destructive:
        return CommandClassification(
            resource_type=ResourceType.DESTRUCTIVE_COMMAND,
            resource_category=ResourceCategory.SYSTEM_RESOURCE,
            sensitivity=Sensitivity.CRITICAL,
            is_destructive=True,
            is_network_operation=is_network,
            is_system_resource=True,
            contains_credentials=False,
            reason="Command matches a destructive pattern (data deletion, format, drop, etc.).",
        )

    if is_network:
        # Privilege escalation + network = higher risk
        sensitivity = Sensitivity.HIGH if is_process else Sensitivity.MEDIUM
        return CommandClassification(
            resource_type=ResourceType.NETWORK_COMMAND,
            resource_category=ResourceCategory.NETWORK_RESOURCE,
            sensitivity=sensitivity,
            is_destructive=False,
            is_network_operation=True,
            is_system_resource=False,
            contains_credentials=False,
            reason="Command performs a network operation (HTTP, SSH, DNS, cloud CLI, etc.).",
        )

    if is_package:
        return CommandClassification(
            resource_type=ResourceType.PACKAGE_INSTALL,
            resource_category=ResourceCategory.PACKAGE_OR_DEPENDENCY,
            sensitivity=Sensitivity.MEDIUM,
            is_destructive=False,
            is_network_operation=True,  # package installs always hit the network
            is_system_resource=False,
            contains_credentials=False,
            reason="Command installs a package or dependency.",
        )

    if is_process:
        return CommandClassification(
            resource_type=ResourceType.PROCESS_COMMAND,
            resource_category=ResourceCategory.PROCESS,
            sensitivity=Sensitivity.MEDIUM,
            is_destructive=False,
            is_network_operation=False,
            is_system_resource=True,
            contains_credentials=False,
            reason="Command manages processes, services, or privileges (sudo, systemctl, chmod, etc.).",
        )

    # Default: normal shell command
    return CommandClassification(
        resource_type=ResourceType.SHELL_COMMAND,
        resource_category=ResourceCategory.UNKNOWN,
        sensitivity=Sensitivity.LOW,
        is_destructive=False,
        is_network_operation=False,
        is_system_resource=False,
        contains_credentials=False,
        reason="Command does not match any high-risk pattern.",
    )


# ---------------------------------------------------------------------------
# Security attribute extractor
# ---------------------------------------------------------------------------

def extract_security_attributes(
    action_type: str,
    target: str | None,
    command: str | None,
    file_cls: FileClassification | None,
    cmd_cls: CommandClassification | None,
) -> dict:
    """
    Combine file and command classifications with action type to produce
    a final set of security attributes.

    Returns a dict with keys matching ContextResult fields.
    """
    at = action_type.lower().strip()

    # Action-type level is_destructive override
    action_is_destructive = at in P.DELETE_ACTION_TYPES
    action_is_network = at in P.NETWORK_ACTION_TYPES
    action_is_package = at in P.PACKAGE_ACTION_TYPES

    # Merge from file classification
    is_destructive = action_is_destructive
    is_network = action_is_network or action_is_package
    is_system = False
    contains_creds = False
    requires_attention = False

    if file_cls:
        is_system = file_cls.is_system_resource
        contains_creds = file_cls.contains_credentials
        # Writing/deleting to a HIGH/CRITICAL resource always needs attention
        if file_cls.sensitivity in (Sensitivity.HIGH, Sensitivity.CRITICAL):
            if at in P.WRITE_ACTION_TYPES | P.DELETE_ACTION_TYPES:
                requires_attention = True
                is_destructive = is_destructive or at in P.DELETE_ACTION_TYPES

    if cmd_cls:
        is_destructive = is_destructive or cmd_cls.is_destructive
        is_network = is_network or cmd_cls.is_network_operation
        is_system = is_system or cmd_cls.is_system_resource
        if cmd_cls.sensitivity == Sensitivity.CRITICAL:
            requires_attention = True

    # Any access to credentials requires attention
    if contains_creds:
        requires_attention = True

    return {
        "is_destructive": is_destructive,
        "is_network_operation": is_network,
        "is_system_resource": is_system,
        "contains_credentials": contains_creds,
        "requires_special_attention": requires_attention,
    }


# ---------------------------------------------------------------------------
# Merged sensitivity resolver
# ---------------------------------------------------------------------------

def resolve_sensitivity(
    file_cls: FileClassification | None,
    cmd_cls: CommandClassification | None,
    action_type: str,
) -> Sensitivity:
    """
    Return the highest sensitivity from file and command classifications,
    boosted by action type where appropriate.
    """
    RANK = {
        Sensitivity.LOW: 0,
        Sensitivity.MEDIUM: 1,
        Sensitivity.HIGH: 2,
        Sensitivity.CRITICAL: 3,
    }

    base = Sensitivity.LOW

    if file_cls and RANK[file_cls.sensitivity] > RANK[base]:
        base = file_cls.sensitivity
    if cmd_cls and RANK[cmd_cls.sensitivity] > RANK[base]:
        base = cmd_cls.sensitivity

    at = action_type.lower()

    # Writing or deleting to a sensitive resource bumps one level
    if at in P.WRITE_ACTION_TYPES | P.DELETE_ACTION_TYPES:
        if base == Sensitivity.MEDIUM:
            base = Sensitivity.HIGH
        elif base == Sensitivity.HIGH:
            base = Sensitivity.CRITICAL

    return base


# ---------------------------------------------------------------------------
# Re-export re for use in classifiers (imported in classify_file_target)
# ---------------------------------------------------------------------------
import re  # noqa: E402  (placed here to keep top of file clean)

"""
context/classifier.py

Simple, fast, deterministic target classifier.

This is intentionally kept separate from the heavier classifiers.py.
Its job is narrow and specific:

    classify_target(path) → {"type": "file", "sensitivity": "critical", "category": "credential"}

It answers:
    - What TYPE is the target?     (file, url, command, process)
    - How SENSITIVE is it?         (normal, sensitive, critical)
    - What CATEGORY is it?         (source_code, credential, config, system, etc.)

No AI. No external calls. Fast enough to run on every action.

Adding new patterns: just add an entry to CRITICAL_PATTERNS, SENSITIVE_PATTERNS,
or the category blocks below. Nothing else needs to change.
"""

import os
import re
from typing import TypedDict


class TargetInfo(TypedDict):
    type: str           # "file" | "url" | "command" | "process" | "unknown"
    sensitivity: str    # "normal" | "sensitive" | "critical"
    category: str       # see CATEGORIES below


# ---------------------------------------------------------------------------
# Sensitivity patterns
# ---------------------------------------------------------------------------

# Any path matching these → critical
CRITICAL_PATTERNS: list[str] = [
    # SSH keys
    r"id_rsa$", r"id_ed25519$", r"id_ecdsa$", r"id_dsa$",
    r"\.pem$", r"\.key$",
    r"ssh_host_",
    r"authorized_keys",
    # Credential files
    r"\.env$", r"\.env\.",
    r"credentials?\.json$", r"secrets?\.json$",
    r"\.netrc$", r"\.pgpass$",
    r"api[_-]?key", r"private[_-]?key",
    r"secret[s]?\.ya?ml",
    # Cloud credentials
    r"[/\\]\.aws[/\\]",
    r"[/\\]\.gcloud[/\\]",
    r"application_default_credentials",
    r"service[_-]?account.*\.json$",
    r"[/\\]\.kube[/\\]config$",
    # Certificates & keystores
    r"\.p12$", r"\.pfx$", r"\.jks$",
    r"keystore", r"truststore",
    # Token / password files
    r"token", r"password[s]?", r"passwd",
]

# Any path matching these → sensitive (but not critical)
SENSITIVE_PATTERNS: list[str] = [
    # SSH config (not keys)
    r"[/\\]\.ssh[/\\]", r"ssh_config$", r"sshd_config$", r"known_hosts",
    # Shell history
    r"\.bash_history$", r"\.zsh_history$", r"\.sh_history$",
    # Shell profiles
    r"\.bashrc$", r"\.zshrc$", r"\.bash_profile$", r"\.profile$",
    # System paths
    r"^/etc/", r"^/proc/", r"^/sys/",
    r"^C:[/\\]Windows[/\\]",
    # Git credentials
    r"\.gitcredentials$",
    # Docker config
    r"[/\\]\.docker[/\\]config\.json$",
    # Database config
    r"database\.ya?ml$", r"database\.conf$", r"db\.conf$",
    # General config
    r"\.ya?ml$", r"\.toml$", r"\.ini$", r"\.cfg$", r"\.conf$",
]

# Compiled once at import time
_CRITICAL = [re.compile(p, re.IGNORECASE) for p in CRITICAL_PATTERNS]
_SENSITIVE = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_PATTERNS]

# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

_CATEGORY_RULES: list[tuple[re.Pattern, str]] = [
    # Credentials first (highest priority)
    (re.compile(r"id_rsa|id_ed25519|id_ecdsa|\.pem$|\.key$|private[_-]?key", re.I), "private_key"),
    (re.compile(r"[/\\]\.aws[/\\]|[/\\]\.gcloud[/\\]|[/\\]\.kube[/\\]|service[_-]?account", re.I), "cloud_credential"),
    (re.compile(r"\.env$|\.env\.|credentials?\.json|secrets?\.json|\.netrc|api[_-]?key|token|password", re.I), "credential"),
    # SSH
    (re.compile(r"[/\\]\.ssh[/\\]|ssh_config|sshd_config|known_hosts|authorized_keys", re.I), "ssh"),
    # System
    (re.compile(r"^/etc/|^/proc/|^/sys/|^C:[/\\]Windows[/\\]", re.I), "system"),
    # Shell
    (re.compile(r"\.bash_history|\.zsh_history|\.bashrc|\.zshrc|\.profile", re.I), "shell_config"),
    # Database
    (re.compile(r"\.sqlite3?$|\.db$|database\.ya?ml|database\.conf", re.I), "database"),
    # Config
    (re.compile(r"\.ya?ml$|\.toml$|\.ini$|\.cfg$|\.conf$|\.config$|settings\.py", re.I), "config"),
    # Package manifests
    (re.compile(r"package\.json$|requirements\.txt$|pyproject\.toml$|cargo\.toml$|go\.mod$", re.I), "package_manifest"),
]


def _detect_category(path: str) -> str:
    for pattern, category in _CATEGORY_RULES:
        if pattern.search(path):
            return category
    return "source_code"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_target(path: str | None) -> TargetInfo:
    """
    Classify a file path or URL into type, sensitivity, and category.

    Returns a TargetInfo dict. Always returns a valid result — never raises.

    Examples:
        classify_target("~/.ssh/id_rsa")
        → {"type": "file", "sensitivity": "critical", "category": "private_key"}

        classify_target("/project/src/main.py")
        → {"type": "file", "sensitivity": "normal", "category": "source_code"}

        classify_target("https://api.example.com")
        → {"type": "url", "sensitivity": "sensitive", "category": "network"}
    """
    if not path:
        return TargetInfo(type="unknown", sensitivity="normal", category="unknown")

    norm = path.replace("\\", "/")

    # URL check first
    if norm.startswith(("http://", "https://", "ftp://", "ws://", "wss://")):
        is_internal = any(
            kw in norm.lower()
            for kw in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "internal")
        )
        return TargetInfo(
            type="url",
            sensitivity="normal" if is_internal else "sensitive",
            category="network",
        )

    # Critical check
    if any(p.search(norm) for p in _CRITICAL):
        return TargetInfo(
            type="file",
            sensitivity="critical",
            category=_detect_category(norm),
        )

    # Sensitive check
    if any(p.search(norm) for p in _SENSITIVE):
        return TargetInfo(
            type="file",
            sensitivity="sensitive",
            category=_detect_category(norm),
        )

    # Normal file
    return TargetInfo(
        type="file",
        sensitivity="normal",
        category=_detect_category(norm),
    )


def is_outside_project(target: str | None, project_root: str | None) -> bool:
    """
    Return True if target path is outside the project root.

    This enables the policy rule:
        "Agent can freely access files inside project root.
         Agent cannot access files outside project root without approval."

    Returns False (safe default) if either argument is None.
    """
    if not target or not project_root:
        return False

    # Normalise separators
    t = os.path.normpath(target.replace("~", os.path.expanduser("~")))
    r = os.path.normpath(project_root)

    try:
        # If target is relative to project_root, it's inside
        t_resolved = os.path.realpath(t)
        r_resolved = os.path.realpath(r)
        return not t_resolved.startswith(r_resolved)
    except (OSError, ValueError):
        # Path can't be resolved (e.g. hypothetical paths in tests) —
        # fall back to simple string prefix check
        return not t.startswith(r)

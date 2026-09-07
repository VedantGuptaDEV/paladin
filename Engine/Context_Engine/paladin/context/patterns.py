"""
context/patterns.py

All regex and path-matching patterns used by the Context Engine.

Design principles:
- No AI, no external calls. Pure pattern matching.
- Patterns are compiled once at module load for performance.
- Organised by category so new patterns are easy to add.
"""

import re
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compile(patterns: list[str], flags: int = re.IGNORECASE) -> list[re.Pattern]:
    """Compile a list of regex strings into Pattern objects."""
    return [re.compile(p, flags) for p in patterns]


def matches_any(value: str, patterns: list[re.Pattern]) -> bool:
    """Return True if *value* matches at least one compiled pattern."""
    return any(p.search(value) for p in patterns)


# ---------------------------------------------------------------------------
# SSH patterns
# ---------------------------------------------------------------------------

SSH_PATH_PATTERNS: list[re.Pattern] = _compile([
    r"[/\\]\.ssh[/\\]",           # .ssh directory
    r"[/\\]\.ssh$",               # .ssh directory itself
    r"id_rsa",                    # RSA private key
    r"id_ed25519",                # Ed25519 private key
    r"id_ecdsa",                  # ECDSA private key
    r"id_dsa",                    # DSA private key (legacy)
    r"ssh_host_",                 # host keys
    r"authorized_keys",           # authorised keys file
    r"known_hosts",               # known hosts file
    r"ssh_config",                # SSH client config
    r"sshd_config",               # SSH daemon config
])

SSH_CONFIG_PATTERNS: list[re.Pattern] = _compile([
    r"ssh_config$",
    r"sshd_config$",
    r"[/\\]\.ssh[/\\]config$",   # bare 'config' file inside .ssh/
])

SSH_KEY_PATTERNS: list[re.Pattern] = _compile([
    r"id_rsa$",
    r"id_ed25519$",
    r"id_ecdsa$",
    r"id_dsa$",
    r"\.pem$",
    r"ssh_host_\w+_key$",
])

# ---------------------------------------------------------------------------
# Credential / secret patterns
# ---------------------------------------------------------------------------

CREDENTIAL_PATH_PATTERNS: list[re.Pattern] = _compile([
    r"\.env$",
    r"\.env\.",                   # .env.local, .env.production, etc.
    r"\.secret",
    r"\.secrets",
    r"secret[s]?\.ya?ml",
    r"credentials?",
    r"password[s]?",
    r"passwd",
    r"\.netrc$",
    r"\.pgpass$",
    r"token",
    r"api[_-]?key",
    r"private[_-]?key",
    r"\.p12$",
    r"\.pfx$",
    r"\.jks$",
    r"keystore",
    r"truststore",
    r"wallet",
    r"vault",
])

PRIVATE_KEY_PATTERNS: list[re.Pattern] = _compile([
    r"-----BEGIN .*(PRIVATE|ENCRYPTED).*KEY-----",
    r"\.key$",
    r"_rsa$",
    r"_ed25519$",
    r"_ecdsa$",
])

CERTIFICATE_PATTERNS: list[re.Pattern] = _compile([
    r"\.crt$",
    r"\.cert$",
    r"\.pem$",
    r"\.cer$",
    r"\.der$",
])

# ---------------------------------------------------------------------------
# Cloud credential patterns
# ---------------------------------------------------------------------------

CLOUD_CREDENTIAL_PATTERNS: list[re.Pattern] = _compile([
    r"[/\\]\.aws[/\\]",
    r"[/\\]\.aws$",
    r"aws_access_key",
    r"aws_secret",
    r"[/\\]\.gcloud[/\\]",
    r"[/\\]\.config[/\\]gcloud",
    r"application_default_credentials",
    r"[/\\]\.azure[/\\]",
    r"azure[_-]?(credentials?|config)",
    r"[/\\]\.kube[/\\]config",
    r"kubeconfig",
    r"[/\\]\.digitalocean",
    r"[/\\]\.heroku",
    r"service[_-]?account.*\.json",
])

# ---------------------------------------------------------------------------
# System resource patterns
# ---------------------------------------------------------------------------

SYSTEM_PATH_PATTERNS: list[re.Pattern] = _compile([
    r"^/etc/",
    r"^/proc/",
    r"^/sys/",
    r"^/boot/",
    r"^/dev/",
    r"^/var/log/",
    r"^/var/run/",
    r"^/usr/lib/",
    r"^/usr/bin/",
    r"^/usr/sbin/",
    r"^/sbin/",
    r"^/bin/",
    r"^C:\\Windows\\",
    r"^C:[/\\]Windows[/\\]",
    r"^C:\\Program Files",
    r"^C:[/\\]Program Files",
    r"^C:\\ProgramData",
    r"^C:[/\\]ProgramData",
    r"/etc/passwd",
    r"/etc/shadow",
    r"/etc/sudoers",
    r"/etc/hosts",
    r"/etc/hostname",
    r"/etc/fstab",
    r"/etc/crontab",
    r"/etc/cron\.",
])

SHELL_HISTORY_PATTERNS: list[re.Pattern] = _compile([
    r"\.bash_history$",
    r"\.zsh_history$",
    r"\.sh_history$",
    r"\.history$",
    r"\.fish_history$",
    r"\.python_history$",
])

SHELL_PROFILE_PATTERNS: list[re.Pattern] = _compile([
    r"\.bashrc$",
    r"\.bash_profile$",
    r"\.profile$",
    r"\.zshrc$",
    r"\.zprofile$",
    r"\.zshenv$",
    r"\.fish$",
    r"\.tcshrc$",
    r"\.cshrc$",
])

# ---------------------------------------------------------------------------
# Configuration file patterns
# ---------------------------------------------------------------------------

CONFIG_FILE_PATTERNS: list[re.Pattern] = _compile([
    r"\.ya?ml$",
    r"\.toml$",
    r"\.ini$",
    r"\.cfg$",
    r"\.conf$",
    r"\.config$",
    r"config\.js(on)?$",
    r"settings\.py$",
    r"settings\.js(on)?$",
    r"application\.properties$",
    r"application\.ya?ml$",
    r"\.properties$",
    r"web\.xml$",
])

GIT_CONFIG_PATTERNS: list[re.Pattern] = _compile([
    r"[/\\]\.git[/\\]config$",
    r"\.gitconfig$",
    r"\.gitcredentials$",
])

DOCKER_CONFIG_PATTERNS: list[re.Pattern] = _compile([
    r"[/\\]\.docker[/\\]config\.json$",
    r"docker-compose\.ya?ml$",
    r"Dockerfile$",
])

DATABASE_PATTERNS: list[re.Pattern] = _compile([
    r"\.db$",
    r"\.sqlite3?$",
    r"\.mdb$",
    r"\.accdb$",
    r"database\.ya?ml$",
    r"database\.conf$",
    r"database\.ini$",
    r"db\.conf$",
    r"db_config",
])

# ---------------------------------------------------------------------------
# Destructive command patterns
# ---------------------------------------------------------------------------

DESTRUCTIVE_COMMAND_PATTERNS: list[re.Pattern] = _compile([
    r"\brm\s+-[a-z]*r[a-z]*f|rm\s+-[a-z]*f[a-z]*r\b",  # rm -rf
    r"\brm\s+-rf\b",
    r"\brmdir\b",
    r"\bdel\s+/[sqf]",           # Windows del /s /q /f
    r"\brd\s+/[sq]",             # Windows rd /s /q
    r"\bformat\b",
    r"\bshred\b",
    r"\bwipe\b",
    r"\bdd\s+.*of=",             # dd to device
    r"\btruncate\b",
    r"\b>\s*/dev/(sd|hd|nvme)",  # redirect to block device
    r"\bdrop\s+(table|database|schema)\b",  # SQL destructive
    r"\bdelete\s+from\b",        # SQL delete
    r"\btruncate\s+table\b",
    r"\bdestroy\b",
    r"\btf\s+destroy\b",         # terraform destroy
    r"\bansible.*--become\b",    # ansible with privilege escalation
    r"\bkubectl\s+delete\b",
    r"\bheroku\s+apps:destroy\b",
])

# ---------------------------------------------------------------------------
# Network command patterns
# ---------------------------------------------------------------------------

NETWORK_COMMAND_PATTERNS: list[re.Pattern] = _compile([
    r"\bcurl\b",
    r"\bwget\b",
    r"\bnc\b",                   # netcat
    r"\bnmap\b",
    r"\bssh\s+",
    r"\bscp\s+",
    r"\bsftp\s+",
    r"\brsync\b",
    r"\btelnet\b",
    r"\bftp\b",
    r"\bdig\b",
    r"\bnslookup\b",
    r"\bping\b",
    r"\btraceroute\b",
    r"\bifconfig\b",
    r"\bip\s+(addr|route|link)\b",
    r"\bnetstat\b",
    r"\bss\s+-",                 # socket statistics
    r"\biptables\b",
    r"\bufw\b",
    r"\bfirewall-cmd\b",
    r"https?://",
    r"\baws\s+s3\b",
    r"\bgcloud\b",
    r"\baz\s+",                  # Azure CLI
    r"\bkubectl\b",
    r"\bhelm\b",
    r"\bdocker\s+pull\b",
    r"\bdocker\s+push\b",
])

# ---------------------------------------------------------------------------
# Package installation patterns
# ---------------------------------------------------------------------------

PACKAGE_INSTALL_PATTERNS: list[re.Pattern] = _compile([
    r"\bpip\s+install\b",
    r"\bpip3\s+install\b",
    r"\bnpm\s+install\b",
    r"\bnpm\s+i\b",
    r"\byarn\s+add\b",
    r"\bnpm\s+add\b",
    r"\bpnpm\s+add\b",
    r"\bpnpm\s+install\b",
    r"\bcargo\s+add\b",
    r"\bcargo\s+install\b",
    r"\bgo\s+get\b",
    r"\bgem\s+install\b",
    r"\bbundle\s+install\b",
    r"\bapt(-get)?\s+install\b",
    r"\byum\s+install\b",
    r"\bdnf\s+install\b",
    r"\bbrew\s+install\b",
    r"\bchoco\s+install\b",
    r"\bscoop\s+install\b",
    r"\bnuget\s+install\b",
    r"\bmaven\b",
    r"\bgradle\b",
    r"\bcomposer\s+require\b",
])

# ---------------------------------------------------------------------------
# Process / privilege escalation patterns
# ---------------------------------------------------------------------------

PROCESS_COMMAND_PATTERNS: list[re.Pattern] = _compile([
    r"\bsudo\b",
    r"\bsu\s+",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bkill\b",
    r"\bkillall\b",
    r"\bpkill\b",
    r"\bps\b",
    r"\btop\b",
    r"\bhtop\b",
    r"\bnohup\b",
    r"\bdaemon\b",
    r"\bsystemctl\b",
    r"\bservice\b",
    r"\bcrontab\b",
    r"\bat\b",
    r"\bbatch\b",
    r"\blaunchctl\b",
    r"\bsc\s+(start|stop|create|delete)\b",  # Windows service control
    r"\bnet\s+(start|stop|user|localgroup)\b",
    r"\breg\s+(add|delete|import|export)\b",  # Windows registry
    r"\bschtasks\b",
])

# ---------------------------------------------------------------------------
# File operation type patterns (action_type based)
# ---------------------------------------------------------------------------

READ_ACTION_TYPES: frozenset[str] = frozenset([
    "file_read", "read_file", "read", "cat", "view", "open",
])

WRITE_ACTION_TYPES: frozenset[str] = frozenset([
    "file_write", "write_file", "write", "create_file", "create",
    "append", "insert", "update_file", "edit",
])

DELETE_ACTION_TYPES: frozenset[str] = frozenset([
    "file_delete", "delete_file", "delete", "remove", "rm",
    "unlink", "destroy",
])

EXECUTE_ACTION_TYPES: frozenset[str] = frozenset([
    "command_execute", "execute_command", "exec", "run", "shell",
    "bash", "cmd", "powershell", "terminal",
])

NETWORK_ACTION_TYPES: frozenset[str] = frozenset([
    "network_request", "http_request", "https_request", "fetch",
    "request", "api_call", "webhook",
])

PACKAGE_ACTION_TYPES: frozenset[str] = frozenset([
    "package_install", "install_package", "install_dependency",
    "pip_install", "npm_install",
])

PROCESS_ACTION_TYPES: frozenset[str] = frozenset([
    "process_spawn", "spawn_process", "start_process",
])

"""
tests/test_context.py

Unit tests for the Context Engine.

Covers:
- SSH resources (keys, config, known_hosts, .ssh directory)
- Credential files (.env, .netrc, token files)
- Cloud credentials (.aws, .gcloud, .kube)
- Private keys / certificates
- System paths (/etc/, /proc/, Windows system)
- Shell history and profiles
- Config files (.yml, .toml, .ini, etc.)
- Destructive commands (rm -rf, DROP TABLE, etc.)
- Network commands (curl, wget, ssh, etc.)
- Package installs (pip, npm, cargo, etc.)
- Process/privilege commands (sudo, systemctl, etc.)
- Normal project files (LOW sensitivity baseline)
- Action type dispatch (network_request, package_install, process_spawn)
- Security attribute flags (is_destructive, contains_credentials, etc.)
"""

import pytest

from paladin.schemas.action import AgentAction
from paladin.schemas.context import ResourceCategory, ResourceType, Sensitivity
from paladin.context.analyzer import ContextEngine

engine = ContextEngine()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_action(**kwargs) -> AgentAction:
    """Build an AgentAction with sensible defaults."""
    defaults = {
        "action_id": "test-001",
        "agent": "kiro",
        "action_type": "file_read",
        "target": None,
        "command": None,
        "task_context": "test",
        "metadata": {},
    }
    defaults.update(kwargs)
    return AgentAction(**defaults)


# ===========================================================================
# SSH Resources
# ===========================================================================

class TestSSHResources:

    def test_ssh_private_key_id_rsa(self):
        action = make_action(target="/home/user/.ssh/id_rsa")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SSH_KEY
        assert result.sensitivity == Sensitivity.CRITICAL
        assert result.contains_credentials is True

    def test_ssh_private_key_ed25519(self):
        action = make_action(target="/home/user/.ssh/id_ed25519")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SSH_KEY
        assert result.sensitivity == Sensitivity.CRITICAL

    def test_ssh_config_file(self):
        action = make_action(target="/home/user/.ssh/config")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SSH_CONFIGURATION
        assert result.resource_category == ResourceCategory.SSH_RESOURCE
        assert result.sensitivity == Sensitivity.HIGH

    def test_ssh_known_hosts(self):
        action = make_action(target="/home/user/.ssh/known_hosts")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SSH_KNOWN_HOSTS
        assert result.resource_category == ResourceCategory.SSH_RESOURCE
        assert result.sensitivity == Sensitivity.HIGH

    def test_ssh_directory_access(self):
        action = make_action(target="/home/user/.ssh/authorized_keys")
        result = engine.analyze(action)
        assert result.resource_category == ResourceCategory.SSH_RESOURCE
        assert result.sensitivity in (Sensitivity.HIGH, Sensitivity.CRITICAL)

    def test_ssh_key_pem(self):
        action = make_action(target="/home/user/keys/server.pem")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.CRITICAL
        assert result.contains_credentials is True

    def test_ssh_key_write_escalates_sensitivity(self):
        action = make_action(action_type="file_write", target="/home/user/.ssh/id_rsa")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.CRITICAL
        assert result.requires_special_attention is True


# ===========================================================================
# Credential & Secret Files
# ===========================================================================

class TestCredentialFiles:

    def test_dotenv_file(self):
        action = make_action(target="/project/.env")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.ENVIRONMENT_FILE
        assert result.resource_category == ResourceCategory.ENVIRONMENT_FILE
        assert result.sensitivity == Sensitivity.HIGH
        assert result.contains_credentials is True

    def test_dotenv_local(self):
        action = make_action(target="/project/.env.local")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.HIGH
        assert result.contains_credentials is True

    def test_dotenv_production(self):
        action = make_action(target="/project/.env.production")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.HIGH

    def test_netrc_file(self):
        action = make_action(target="/home/user/.netrc")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.HIGH
        assert result.contains_credentials is True

    def test_pgpass_file(self):
        action = make_action(target="/home/user/.pgpass")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.HIGH
        assert result.contains_credentials is True

    def test_api_key_file(self):
        action = make_action(target="/project/config/api_key.txt")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.HIGH
        assert result.contains_credentials is True

    def test_token_file(self):
        action = make_action(target="/project/auth/token.json")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.HIGH
        assert result.contains_credentials is True

    def test_password_file(self):
        action = make_action(target="/project/passwords.txt")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.HIGH
        assert result.contains_credentials is True


# ===========================================================================
# Cloud Credentials
# ===========================================================================

class TestCloudCredentials:

    def test_aws_credentials(self):
        action = make_action(target="/home/user/.aws/credentials")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.CLOUD_CREDENTIALS
        assert result.sensitivity == Sensitivity.CRITICAL
        assert result.contains_credentials is True

    def test_aws_config(self):
        action = make_action(target="/home/user/.aws/config")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.CRITICAL

    def test_gcloud_credentials(self):
        action = make_action(target="/home/user/.config/gcloud/credentials.json")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.CRITICAL
        assert result.contains_credentials is True

    def test_kubeconfig(self):
        action = make_action(target="/home/user/.kube/config")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.CRITICAL
        assert result.contains_credentials is True

    def test_service_account_json(self):
        action = make_action(target="/project/service_account.json")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.CRITICAL


# ===========================================================================
# System Resources
# ===========================================================================

class TestSystemResources:

    def test_etc_passwd(self):
        action = make_action(target="/etc/passwd")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SYSTEM_CONFIGURATION
        assert result.resource_category == ResourceCategory.SYSTEM_RESOURCE
        assert result.sensitivity == Sensitivity.HIGH
        assert result.is_system_resource is True

    def test_etc_shadow(self):
        action = make_action(target="/etc/shadow")
        result = engine.analyze(action)
        assert result.is_system_resource is True
        assert result.sensitivity == Sensitivity.HIGH

    def test_etc_hosts(self):
        action = make_action(target="/etc/hosts")
        result = engine.analyze(action)
        assert result.is_system_resource is True

    def test_proc_directory(self):
        action = make_action(target="/proc/1/environ")
        result = engine.analyze(action)
        assert result.is_system_resource is True
        assert result.sensitivity == Sensitivity.HIGH

    def test_system_write_requires_attention(self):
        action = make_action(action_type="file_write", target="/etc/hosts")
        result = engine.analyze(action)
        assert result.is_system_resource is True
        assert result.requires_special_attention is True


# ===========================================================================
# Shell History & Profiles
# ===========================================================================

class TestShellFiles:

    def test_bash_history(self):
        action = make_action(target="/home/user/.bash_history")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SHELL_HISTORY
        assert result.sensitivity == Sensitivity.MEDIUM
        assert result.contains_credentials is True  # history may contain passwords

    def test_zsh_history(self):
        action = make_action(target="/home/user/.zsh_history")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SHELL_HISTORY
        assert result.sensitivity == Sensitivity.MEDIUM

    def test_bashrc(self):
        action = make_action(target="/home/user/.bashrc")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SHELL_PROFILE
        assert result.sensitivity == Sensitivity.MEDIUM

    def test_zshrc(self):
        action = make_action(target="/home/user/.zshrc")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SHELL_PROFILE


# ===========================================================================
# Configuration Files
# ===========================================================================

class TestConfigFiles:

    def test_yaml_config(self):
        action = make_action(target="/project/config/app.yaml")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.CONFIGURATION
        assert result.resource_category == ResourceCategory.CONFIGURATION_FILE
        assert result.sensitivity == Sensitivity.MEDIUM

    def test_toml_config(self):
        action = make_action(target="/project/pyproject.toml")
        result = engine.analyze(action)
        assert result.resource_category == ResourceCategory.CONFIGURATION_FILE

    def test_ini_config(self):
        action = make_action(target="/project/setup.cfg")
        result = engine.analyze(action)
        assert result.resource_category == ResourceCategory.CONFIGURATION_FILE

    def test_git_config(self):
        action = make_action(target="/home/user/.gitconfig")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.GIT_CONFIGURATION
        assert result.sensitivity == Sensitivity.MEDIUM

    def test_docker_config(self):
        action = make_action(target="/home/user/.docker/config.json")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.DOCKER_CONFIGURATION
        assert result.contains_credentials is True  # Docker config contains registry tokens

    def test_sqlite_database(self):
        action = make_action(target="/project/db.sqlite3")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.DATABASE_FILE
        assert result.sensitivity == Sensitivity.MEDIUM


# ===========================================================================
# Normal Project Files (baseline LOW sensitivity)
# ===========================================================================

class TestNormalProjectFiles:

    def test_python_source_file(self):
        action = make_action(target="/project/src/main.py")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.SOURCE_CODE
        assert result.resource_category == ResourceCategory.PROJECT_FILE
        assert result.sensitivity == Sensitivity.LOW
        assert result.contains_credentials is False
        assert result.is_system_resource is False
        assert result.is_destructive is False

    def test_javascript_file(self):
        action = make_action(target="/project/src/app.js")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.LOW

    def test_markdown_file(self):
        action = make_action(target="/project/README.md")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.LOW

    def test_package_json(self):
        action = make_action(target="/project/package.json")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.PACKAGE_MANIFEST
        assert result.resource_category == ResourceCategory.PACKAGE_OR_DEPENDENCY
        assert result.sensitivity == Sensitivity.LOW

    def test_requirements_txt(self):
        action = make_action(target="/project/requirements.txt")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.PACKAGE_MANIFEST


# ===========================================================================
# Destructive Commands
# ===========================================================================

class TestDestructiveCommands:

    def test_rm_rf(self):
        action = make_action(
            action_type="command_execute",
            command="rm -rf /var/data/old_backups"
        )
        result = engine.analyze(action)
        assert result.is_destructive is True
        assert result.sensitivity == Sensitivity.CRITICAL
        assert result.requires_special_attention is True

    def test_drop_table(self):
        action = make_action(
            action_type="command_execute",
            command="psql -c 'DROP TABLE users;'"
        )
        result = engine.analyze(action)
        assert result.is_destructive is True
        assert result.sensitivity == Sensitivity.CRITICAL

    def test_terraform_destroy(self):
        action = make_action(
            action_type="command_execute",
            command="terraform destroy -auto-approve"
        )
        result = engine.analyze(action)
        assert result.is_destructive is True

    def test_kubectl_delete(self):
        action = make_action(
            action_type="command_execute",
            command="kubectl delete deployment my-app"
        )
        result = engine.analyze(action)
        assert result.is_destructive is True

    def test_delete_action_type(self):
        action = make_action(
            action_type="file_delete",
            target="/project/src/important.py"
        )
        result = engine.analyze(action)
        assert result.is_destructive is True


# ===========================================================================
# Network Commands
# ===========================================================================

class TestNetworkCommands:

    def test_curl_command(self):
        action = make_action(
            action_type="command_execute",
            command="curl https://api.example.com/data"
        )
        result = engine.analyze(action)
        assert result.is_network_operation is True
        assert result.is_destructive is False

    def test_wget_command(self):
        action = make_action(
            action_type="command_execute",
            command="wget https://releases.ubuntu.com/22.04/ubuntu.iso"
        )
        result = engine.analyze(action)
        assert result.is_network_operation is True

    def test_network_request_action_type(self):
        action = make_action(
            action_type="network_request",
            target="https://api.github.com/repos"
        )
        result = engine.analyze(action)
        assert result.is_network_operation is True
        assert result.resource_category == ResourceCategory.NETWORK_RESOURCE

    def test_internal_network_request(self):
        action = make_action(
            action_type="network_request",
            target="http://localhost:8080/health"
        )
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.INTERNAL_URL
        assert result.sensitivity == Sensitivity.LOW

    def test_external_network_request(self):
        action = make_action(
            action_type="network_request",
            target="https://external-api.example.com/data"
        )
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.EXTERNAL_URL
        assert result.sensitivity == Sensitivity.MEDIUM


# ===========================================================================
# Package Installation
# ===========================================================================

class TestPackageInstall:

    def test_pip_install_command(self):
        action = make_action(
            action_type="command_execute",
            command="pip install requests==2.31.0"
        )
        result = engine.analyze(action)
        assert result.is_network_operation is True
        assert result.resource_category == ResourceCategory.PACKAGE_OR_DEPENDENCY

    def test_npm_install_command(self):
        action = make_action(
            action_type="command_execute",
            command="npm install express"
        )
        result = engine.analyze(action)
        assert result.resource_category == ResourceCategory.PACKAGE_OR_DEPENDENCY

    def test_package_install_action_type(self):
        action = make_action(
            action_type="package_install",
            command="pip install fastapi"
        )
        result = engine.analyze(action)
        assert result.resource_category == ResourceCategory.PACKAGE_OR_DEPENDENCY
        assert result.is_network_operation is True


# ===========================================================================
# Process / Privilege Commands
# ===========================================================================

class TestProcessCommands:

    def test_sudo_command(self):
        action = make_action(
            action_type="command_execute",
            command="sudo systemctl restart nginx"
        )
        result = engine.analyze(action)
        assert result.is_system_resource is True
        assert result.sensitivity == Sensitivity.MEDIUM

    def test_chmod_command(self):
        action = make_action(
            action_type="command_execute",
            command="chmod 600 ~/.ssh/id_rsa"
        )
        result = engine.analyze(action)
        assert result.is_system_resource is True

    def test_process_spawn_action_type(self):
        action = make_action(
            action_type="process_spawn",
            command="python worker.py"
        )
        result = engine.analyze(action)
        assert result.resource_category == ResourceCategory.PROCESS
        assert result.is_system_resource is True


# ===========================================================================
# Edge Cases
# ===========================================================================

class TestEdgeCases:

    def test_no_target_no_command(self):
        action = make_action(action_type="unknown_action_type")
        result = engine.analyze(action)
        assert result.resource_type == ResourceType.UNKNOWN
        assert result.sensitivity == Sensitivity.LOW

    def test_windows_path_ssh_key(self):
        action = make_action(target="C:\\Users\\user\\.ssh\\id_rsa")
        result = engine.analyze(action)
        assert result.sensitivity == Sensitivity.CRITICAL
        assert result.resource_type == ResourceType.SSH_KEY

    def test_windows_system_path(self):
        action = make_action(target="C:\\Windows\\System32\\config")
        result = engine.analyze(action)
        assert result.is_system_resource is True

    def test_empty_command(self):
        action = make_action(action_type="command_execute", command="")
        result = engine.analyze(action)
        # Should not crash; returns unknown or low sensitivity
        assert result is not None

    def test_engine_is_reusable(self):
        """ContextEngine is stateless — same instance should handle multiple actions."""
        a1 = make_action(target="/project/main.py")
        a2 = make_action(target="/home/user/.ssh/id_rsa")
        r1 = engine.analyze(a1)
        r2 = engine.analyze(a2)
        assert r1.sensitivity == Sensitivity.LOW
        assert r2.sensitivity == Sensitivity.CRITICAL

    def test_result_is_valid_pydantic_model(self):
        """Result can be serialised to JSON without errors."""
        action = make_action(target="/home/user/.aws/credentials")
        result = engine.analyze(action)
        data = result.model_dump()
        assert "resource_type" in data
        assert "sensitivity" in data
        assert "contains_credentials" in data

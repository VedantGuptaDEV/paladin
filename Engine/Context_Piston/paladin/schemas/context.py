"""
schemas/context.py

Output model from the Context Engine.
Consumed by: Policy Engine, Risk Engine, Decision Engine.
"""

from enum import Enum
from pydantic import BaseModel, Field


class Sensitivity(str, Enum):
    """Security sensitivity level of the resource or action."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResourceCategory(str, Enum):
    """Broad category of the resource being targeted."""
    PROJECT_FILE = "project_file"
    CONFIGURATION_FILE = "configuration_file"
    ENVIRONMENT_FILE = "environment_file"
    SSH_RESOURCE = "ssh_resource"
    CREDENTIAL_OR_SECRET = "credential_or_secret"
    SYSTEM_RESOURCE = "system_resource"
    NETWORK_RESOURCE = "network_resource"
    PACKAGE_OR_DEPENDENCY = "package_or_dependency"
    PROCESS = "process"
    UNKNOWN = "unknown"


class ResourceType(str, Enum):
    """Specific type label for the resource."""
    # File-based
    SOURCE_CODE = "source_code"
    CONFIGURATION = "configuration"
    ENVIRONMENT_FILE = "environment_file"
    SSH_CONFIGURATION = "ssh_configuration"
    SSH_KEY = "ssh_key"
    SSH_KNOWN_HOSTS = "ssh_known_hosts"
    PRIVATE_KEY = "private_key"
    CERTIFICATE = "certificate"
    CREDENTIAL_FILE = "credential_file"
    PASSWORD_FILE = "password_file"
    TOKEN_FILE = "token_file"
    DATABASE_FILE = "database_file"
    SYSTEM_CONFIGURATION = "system_configuration"
    SHELL_HISTORY = "shell_history"
    SHELL_PROFILE = "shell_profile"
    CLOUD_CREDENTIALS = "cloud_credentials"
    DOCKER_CONFIGURATION = "docker_configuration"
    GIT_CONFIGURATION = "git_configuration"
    PACKAGE_MANIFEST = "package_manifest"
    LOG_FILE = "log_file"
    BINARY = "binary"
    ARCHIVE = "archive"
    # Command-based
    SHELL_COMMAND = "shell_command"
    PACKAGE_INSTALL = "package_install"
    NETWORK_COMMAND = "network_command"
    PROCESS_COMMAND = "process_command"
    FILE_OPERATION = "file_operation"
    DESTRUCTIVE_COMMAND = "destructive_command"
    # Network
    EXTERNAL_URL = "external_url"
    INTERNAL_URL = "internal_url"
    # Unknown
    UNKNOWN = "unknown"


class ContextResult(BaseModel):
    """
    Structured context output from the Context Engine.

    Designed so that:
    - Policy Engine can inspect resource_category, sensitivity, is_destructive
    - Risk Engine can use contains_credentials, is_system_resource, sensitivity
    - Decision Engine can consume the full result
    """

    # Resource identification
    resource_type: ResourceType = Field(
        ..., description="Specific resource type label"
    )
    resource_category: ResourceCategory = Field(
        ..., description="Broad category of the resource"
    )

    # Security attributes
    sensitivity: Sensitivity = Field(
        ..., description="Overall sensitivity level"
    )
    contains_credentials: bool = Field(
        default=False,
        description="True if the resource likely contains credentials or secrets",
    )
    is_system_resource: bool = Field(
        default=False,
        description="True if the resource is an OS-level or system configuration",
    )
    is_destructive: bool = Field(
        default=False,
        description="True if the action could destroy or permanently alter data",
    )
    is_network_operation: bool = Field(
        default=False,
        description="True if the action involves network access",
    )
    requires_special_attention: bool = Field(
        default=False,
        description="True if the action warrants human review regardless of other factors",
    )

    # Human-readable context
    reason: str = Field(
        default="",
        description="Short explanation of why these classifications were assigned",
    )

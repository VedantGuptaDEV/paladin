"""
schemas/intent.py

Output model from the Intent Analyzer.
Consumed by: Policy Engine, Risk Engine, Decision Engine.
"""

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    """
    Why the agent is attempting this action.
    Maps to policy rules and risk weights in downstream engines.
    """
    READ_PROJECT_FILE = "read_project_file"
    MODIFY_PROJECT_FILE = "modify_project_file"
    ACCESS_CONFIGURATION = "access_configuration"
    ACCESS_SENSITIVE_CONFIGURATION = "access_sensitive_configuration"
    INSTALL_DEPENDENCY = "install_dependency"
    EXECUTE_COMMAND = "execute_command"
    NETWORK_ACCESS = "network_access"
    DELETE_RESOURCE = "delete_resource"
    ACCESS_CREDENTIALS = "access_credentials"
    MODIFY_SYSTEM = "modify_system"
    SPAWN_PROCESS = "spawn_process"
    UNKNOWN = "unknown"


class IntentSource(str, Enum):
    """How the intent was determined."""
    DETERMINISTIC = "deterministic"   # matched a rule with high confidence
    AI_SERVICE = "ai_service"         # AI service provided the result
    FALLBACK = "fallback"             # low-confidence deterministic fallback


class IntentResult(BaseModel):
    """
    Structured intent output from the Intent Analyzer.

    The intent answers: "Why is the agent attempting this action?"
    """

    intent: IntentCategory = Field(
        ..., description="Inferred intent category"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 (unknown) to 1.0 (certain)",
    )
    reason: str = Field(
        ..., description="Human-readable explanation of why this intent was inferred"
    )
    source: IntentSource = Field(
        default=IntentSource.DETERMINISTIC,
        description="How the intent was determined",
    )
    # Optional secondary intent when the action could have multiple purposes
    alternative_intent: IntentCategory | None = Field(
        default=None,
        description="Second most likely intent category, if applicable",
    )
    alternative_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence for the alternative intent",
    )

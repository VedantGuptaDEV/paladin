"""
tests/test_intent.py

Unit tests for the Intent Analyzer.

Covers:
- Deterministic rules: all major intent categories
- High-confidence rules bypass AI
- Unknown fallback when no rule matches
- Stub AI returns UNKNOWN (triggering deterministic fallback)
- Mock AI service: result merging when AI wins
- Mock AI service: deterministic wins when confidence is higher
- analyze_sync() works without async
- IntentAnalyzer.deterministic() class method
- Integration: ContextEngine + IntentAnalyzer end-to-end
"""

import asyncio
import pytest

from paladin.schemas.action import AgentAction
from paladin.schemas.context import ContextResult, ResourceCategory, ResourceType, Sensitivity
from paladin.schemas.intent import IntentCategory, IntentResult, IntentSource
from paladin.context.analyzer import ContextEngine
from paladin.intent.analyzer import IntentAnalyzer
from paladin.intent.service import AIIntentAnalyzer, StubAIAnalyzer, ServiceUnavailableError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_action(**kwargs) -> AgentAction:
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


context_engine = ContextEngine()


def analyze(action: AgentAction) -> tuple[ContextResult, IntentResult]:
    """Run context + deterministic intent, return both results."""
    ctx = context_engine.analyze(action)
    intent = IntentAnalyzer.deterministic(action, ctx)
    return ctx, intent


def run_async(coro):
    """Run a coroutine in the test process."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ===========================================================================
# Deterministic Rules — expected intent for each category
# ===========================================================================

class TestDeterministicRules:

    def test_read_project_file(self):
        action = make_action(target="/project/src/main.py")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.READ_PROJECT_FILE
        assert intent.confidence >= 0.85
        assert intent.source == IntentSource.DETERMINISTIC

    def test_modify_project_file(self):
        action = make_action(action_type="file_write", target="/project/src/main.py")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.MODIFY_PROJECT_FILE
        assert intent.confidence >= 0.80

    def test_access_configuration(self):
        action = make_action(target="/project/config/app.yaml")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.ACCESS_CONFIGURATION
        assert intent.confidence >= 0.80

    def test_access_sensitive_configuration_ssh(self):
        action = make_action(target="/home/user/.ssh/config")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.ACCESS_SENSITIVE_CONFIGURATION
        assert intent.confidence >= 0.85

    def test_access_sensitive_configuration_env(self):
        action = make_action(target="/project/.env")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.ACCESS_SENSITIVE_CONFIGURATION
        assert intent.confidence >= 0.85

    def test_access_credentials_aws(self):
        action = make_action(target="/home/user/.aws/credentials")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.ACCESS_CREDENTIALS
        assert intent.confidence >= 0.85

    def test_access_credentials_ssh_key(self):
        action = make_action(target="/home/user/.ssh/id_rsa")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.ACCESS_CREDENTIALS
        assert intent.confidence >= 0.85

    def test_delete_resource(self):
        action = make_action(action_type="file_delete", target="/project/old_data.db")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.DELETE_RESOURCE
        assert intent.confidence >= 0.90

    def test_delete_resource_rm_rf(self):
        action = make_action(action_type="command_execute", command="rm -rf /tmp/cache")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.DELETE_RESOURCE

    def test_install_dependency_pip(self):
        action = make_action(action_type="command_execute", command="pip install requests")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.INSTALL_DEPENDENCY
        assert intent.confidence >= 0.85

    def test_install_dependency_npm(self):
        action = make_action(action_type="command_execute", command="npm install react")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.INSTALL_DEPENDENCY

    def test_install_dependency_action_type(self):
        action = make_action(action_type="package_install", command="pip install fastapi")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.INSTALL_DEPENDENCY

    def test_network_access_action_type(self):
        action = make_action(
            action_type="network_request",
            target="https://api.github.com"
        )
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.NETWORK_ACCESS
        assert intent.confidence >= 0.85

    def test_network_access_curl(self):
        action = make_action(
            action_type="command_execute",
            command="curl https://api.example.com/data"
        )
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.NETWORK_ACCESS

    def test_execute_command_general(self):
        action = make_action(
            action_type="command_execute",
            command="echo hello world"
        )
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.EXECUTE_COMMAND

    def test_modify_system(self):
        action = make_action(action_type="file_write", target="/etc/hosts")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.MODIFY_SYSTEM
        assert intent.confidence >= 0.80

    def test_spawn_process(self):
        action = make_action(action_type="process_spawn", command="python worker.py")
        _, intent = analyze(action)
        assert intent.intent == IntentCategory.SPAWN_PROCESS

    def test_unknown_fallback(self):
        action = make_action(
            action_type="completely_unknown_action",
            target=None,
            command=None,
        )
        ctx = context_engine.analyze(action)
        intent = IntentAnalyzer.deterministic(action, ctx)
        assert intent.intent == IntentCategory.UNKNOWN
        assert intent.source == IntentSource.FALLBACK
        assert intent.confidence < 0.5


# ===========================================================================
# IntentAnalyzer.analyze_sync()
# ===========================================================================

class TestAnalyzeSync:

    def test_sync_returns_valid_result(self):
        action = make_action(target="/project/src/app.py")
        ctx = context_engine.analyze(action)
        analyzer = IntentAnalyzer()
        result = analyzer.analyze_sync(action, ctx)
        assert isinstance(result, IntentResult)
        assert result.intent is not None
        assert 0.0 <= result.confidence <= 1.0

    def test_sync_matches_deterministic(self):
        action = make_action(target="/home/user/.ssh/id_rsa")
        ctx = context_engine.analyze(action)
        analyzer = IntentAnalyzer()
        result = analyzer.analyze_sync(action, ctx)
        # sync should use deterministic path (StubAI returns nothing)
        assert result.intent == IntentCategory.ACCESS_CREDENTIALS


# ===========================================================================
# Stub AI service
# ===========================================================================

class TestStubAI:

    def test_stub_is_unavailable(self):
        stub = StubAIAnalyzer()
        assert stub.is_available() is False

    def test_stub_returns_unknown(self):
        action = make_action(target="/project/main.py")
        ctx = context_engine.analyze(action)
        result = run_async(StubAIAnalyzer().analyze(action, ctx))
        assert result.intent == IntentCategory.UNKNOWN
        assert result.confidence == 0.0

    def test_analyzer_with_stub_uses_deterministic(self):
        """When stub AI is available=False, analyzer should use deterministic."""
        action = make_action(target="/project/.env")
        ctx = context_engine.analyze(action)
        analyzer = IntentAnalyzer(ai_service=StubAIAnalyzer())
        result = run_async(analyzer.analyze(action, ctx))
        # Deterministic rule fires because stub is not available
        assert result.intent == IntentCategory.ACCESS_SENSITIVE_CONFIGURATION


# ===========================================================================
# Mock AI service — merging logic
# ===========================================================================

class MockAIAnalyzer(AIIntentAnalyzer):
    """A controllable mock for testing merge logic."""

    def __init__(self, intent: IntentCategory, confidence: float):
        self._intent = intent
        self._confidence = confidence

    async def analyze(self, action: AgentAction, ctx: ContextResult) -> IntentResult:
        return IntentResult(
            intent=self._intent,
            confidence=self._confidence,
            reason="Mock AI result.",
            source=IntentSource.AI_SERVICE,
        )

    def is_available(self) -> bool:
        return True


class MockFailingAIAnalyzer(AIIntentAnalyzer):
    """Always raises ServiceUnavailableError."""

    async def analyze(self, action: AgentAction, ctx: ContextResult) -> IntentResult:
        raise ServiceUnavailableError("Service is down")

    def is_available(self) -> bool:
        return True  # claims available but then fails


class TestMockAI:

    def test_ai_wins_when_higher_confidence(self):
        """AI result used when its confidence > deterministic."""
        action = make_action(
            action_type="command_execute",
            command="echo hello"
        )
        ctx = context_engine.analyze(action)
        # Deterministic will return EXECUTE_COMMAND ~0.75
        # Mock AI returns NETWORK_ACCESS with 0.95 → AI should win
        mock = MockAIAnalyzer(IntentCategory.NETWORK_ACCESS, 0.95)
        analyzer = IntentAnalyzer(
            ai_service=mock,
            ai_bypass_threshold=0.99,  # force AI to be tried
            ai_assist_threshold=0.0,
        )
        result = run_async(analyzer.analyze(action, ctx))
        assert result.intent == IntentCategory.NETWORK_ACCESS
        assert result.source == IntentSource.AI_SERVICE
        assert result.alternative_intent == IntentCategory.EXECUTE_COMMAND

    def test_deterministic_wins_when_higher_confidence(self):
        """Deterministic result kept when its confidence > AI."""
        action = make_action(target="/home/user/.aws/credentials")
        ctx = context_engine.analyze(action)
        # Deterministic → ACCESS_CREDENTIALS ~0.92
        # Mock AI → READ_PROJECT_FILE 0.50
        mock = MockAIAnalyzer(IntentCategory.READ_PROJECT_FILE, 0.50)
        analyzer = IntentAnalyzer(
            ai_service=mock,
            ai_bypass_threshold=0.99,  # force AI to be tried
            ai_assist_threshold=0.0,
        )
        result = run_async(analyzer.analyze(action, ctx))
        assert result.intent == IntentCategory.ACCESS_CREDENTIALS
        assert result.source == IntentSource.DETERMINISTIC

    def test_failing_ai_falls_back_to_deterministic(self):
        """When AI raises ServiceUnavailableError, deterministic result is returned."""
        action = make_action(target="/home/user/.ssh/id_rsa")
        ctx = context_engine.analyze(action)
        analyzer = IntentAnalyzer(
            ai_service=MockFailingAIAnalyzer(),
            ai_bypass_threshold=0.99,
        )
        result = run_async(analyzer.analyze(action, ctx))
        # Should NOT raise; returns deterministic
        assert result.intent == IntentCategory.ACCESS_CREDENTIALS
        assert result.source == IntentSource.DETERMINISTIC

    def test_high_confidence_deterministic_skips_ai(self):
        """When deterministic confidence >= bypass threshold, AI is never called."""
        called = []

        class TrackingAI(AIIntentAnalyzer):
            async def analyze(self, action, ctx):
                called.append(True)
                return IntentResult(
                    intent=IntentCategory.UNKNOWN,
                    confidence=0.0,
                    reason="",
                    source=IntentSource.AI_SERVICE,
                )
            def is_available(self):
                return True

        action = make_action(action_type="file_delete", target="/project/old.py")
        ctx = context_engine.analyze(action)
        analyzer = IntentAnalyzer(
            ai_service=TrackingAI(),
            ai_bypass_threshold=0.85,  # DELETE_RESOURCE confidence=0.95 → skips AI
        )
        result = run_async(analyzer.analyze(action, ctx))
        assert result.intent == IntentCategory.DELETE_RESOURCE
        assert called == []  # AI was never called


# ===========================================================================
# Integration: ContextEngine → IntentAnalyzer end-to-end
# ===========================================================================

class TestIntegration:

    def test_ssh_config_full_pipeline(self):
        """
        Replicate the exact example from the requirements:
        file_read ~/.ssh/config → access_sensitive_configuration, confidence ~0.90
        """
        action = AgentAction(
            action_id="test-001",
            agent="kiro",
            action_type="file_read",
            target="/home/user/.ssh/config",
            command=None,
            task_context="The agent is working on configuring the development environment",
            metadata={},
        )
        ctx = context_engine.analyze(action)
        intent = IntentAnalyzer.deterministic(action, ctx)

        # Context assertions
        assert ctx.resource_type == ResourceType.SSH_CONFIGURATION
        assert ctx.resource_category == ResourceCategory.SSH_RESOURCE
        assert ctx.sensitivity == Sensitivity.HIGH
        assert ctx.contains_credentials is False  # config, not a key

        # Intent assertions
        assert intent.intent == IntentCategory.ACCESS_SENSITIVE_CONFIGURATION
        assert intent.confidence >= 0.85
        assert "SSH" in intent.reason or "ssh" in intent.reason.lower()

    def test_env_file_full_pipeline(self):
        action = AgentAction(
            action_id="test-002",
            agent="kiro",
            action_type="file_read",
            target="/project/.env",
            command=None,
            task_context="Agent is reading environment configuration",
            metadata={},
        )
        ctx = context_engine.analyze(action)
        intent = IntentAnalyzer.deterministic(action, ctx)

        assert ctx.contains_credentials is True
        assert ctx.sensitivity == Sensitivity.HIGH
        assert intent.intent == IntentCategory.ACCESS_SENSITIVE_CONFIGURATION

    def test_rm_rf_full_pipeline(self):
        action = AgentAction(
            action_id="test-003",
            agent="kiro",
            action_type="command_execute",
            target=None,
            command="rm -rf /tmp/old_data",
            task_context="Cleaning up temporary files",
            metadata={},
        )
        ctx = context_engine.analyze(action)
        intent = IntentAnalyzer.deterministic(action, ctx)

        assert ctx.is_destructive is True
        assert ctx.sensitivity == Sensitivity.CRITICAL
        assert intent.intent == IntentCategory.DELETE_RESOURCE

    def test_npm_install_full_pipeline(self):
        action = AgentAction(
            action_id="test-004",
            agent="kiro",
            action_type="command_execute",
            target=None,
            command="npm install express",
            task_context="Setting up a new web server",
            metadata={},
        )
        ctx = context_engine.analyze(action)
        intent = IntentAnalyzer.deterministic(action, ctx)

        assert ctx.is_network_operation is True
        assert intent.intent == IntentCategory.INSTALL_DEPENDENCY

    def test_result_serialisable_to_json(self):
        """Both ContextResult and IntentResult must be JSON-serialisable."""
        action = make_action(target="/home/user/.aws/credentials")
        ctx = context_engine.analyze(action)
        intent = IntentAnalyzer.deterministic(action, ctx)

        ctx_dict = ctx.model_dump()
        intent_dict = intent.model_dump()

        assert isinstance(ctx_dict, dict)
        assert isinstance(intent_dict, dict)
        assert "resource_type" in ctx_dict
        assert "intent" in intent_dict
        assert "confidence" in intent_dict

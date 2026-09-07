"""
tests/test_context_engine.py

Tests for the refactored Context Engine:
- ActionContext dataclass fields (WHO/WHAT/WHERE/TARGET/HISTORY/PROJECT)
- ContextEngine.build_context() wiring
- classifier.classify_target() sensitivity and category
- classifier.is_outside_project()
- ActionHistory add/get/has_recent_access_to
- History is included in ActionContext.recent_actions
- The exact example from the spec: cat ~/.ssh/id_rsa
"""

import pytest

from paladin.schemas.action import AgentAction
from paladin.context.engine import ContextEngine
from paladin.context.models import ActionContext
from paladin.context.history import ActionHistory, history as module_history
from paladin.context.classifier import classify_target, is_outside_project


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_module_history():
    """Clear the module-level history singleton before every test."""
    module_history.clear()
    yield
    module_history.clear()


@pytest.fixture
def engine() -> ContextEngine:
    """A ContextEngine with its own isolated ActionHistory."""
    return ContextEngine(action_history=ActionHistory())


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
        "task_context": None,
        "agent_pid": 12345,
        "parent_process": "kiro-cli",
        "cwd": "/home/user/my-project",
        "os": "linux",
        "shell": "bash",
        "project_root": "/home/user/my-project",
        "user": "jaskaran",
        "metadata": {},
    }
    defaults.update(kwargs)
    return AgentAction(**defaults)


def fresh_engine() -> ContextEngine:
    """Engine with its own isolated history — safe for parallel tests."""
    return ContextEngine(action_history=ActionHistory())


# ===========================================================================
# classifier.classify_target()
# ===========================================================================

class TestClassifyTarget:

    def test_ssh_private_key_is_critical(self):
        r = classify_target("/home/user/.ssh/id_rsa")
        assert r["sensitivity"] == "critical"
        assert r["category"] == "private_key"
        assert r["type"] == "file"

    def test_env_file_is_critical(self):
        r = classify_target("/project/.env")
        assert r["sensitivity"] == "critical"
        assert r["category"] == "credential"

    def test_aws_credentials_is_critical(self):
        r = classify_target("/home/user/.aws/credentials")
        assert r["sensitivity"] == "critical"
        assert r["category"] == "cloud_credential"

    def test_ssh_config_is_sensitive(self):
        r = classify_target("/home/user/.ssh/config")
        assert r["sensitivity"] == "sensitive"
        assert r["category"] == "ssh"

    def test_bash_history_is_sensitive(self):
        r = classify_target("/home/user/.bash_history")
        assert r["sensitivity"] == "sensitive"
        assert r["category"] == "shell_config"

    def test_yaml_config_is_sensitive(self):
        r = classify_target("/project/config/app.yaml")
        assert r["sensitivity"] == "sensitive"
        assert r["category"] == "config"

    def test_normal_python_file(self):
        r = classify_target("/project/src/main.py")
        assert r["sensitivity"] == "normal"
        assert r["category"] == "source_code"
        assert r["type"] == "file"

    def test_external_url_is_sensitive(self):
        r = classify_target("https://api.example.com/data")
        assert r["type"] == "url"
        assert r["sensitivity"] == "sensitive"
        assert r["category"] == "network"

    def test_localhost_url_is_normal(self):
        r = classify_target("http://localhost:8080/health")
        assert r["type"] == "url"
        assert r["sensitivity"] == "normal"

    def test_none_target_returns_unknown(self):
        r = classify_target(None)
        assert r["type"] == "unknown"
        assert r["sensitivity"] == "normal"

    def test_windows_ssh_key(self):
        r = classify_target("C:\\Users\\user\\.ssh\\id_rsa")
        assert r["sensitivity"] == "critical"

    def test_package_manifest(self):
        r = classify_target("/project/package.json")
        assert r["sensitivity"] == "normal"
        assert r["category"] == "package_manifest"


# ===========================================================================
# classifier.is_outside_project()
# ===========================================================================

class TestIsOutsideProject:

    def test_file_inside_project_is_not_outside(self):
        assert is_outside_project(
            "/home/user/my-project/src/main.py",
            "/home/user/my-project"
        ) is False

    def test_ssh_key_outside_project(self):
        assert is_outside_project(
            "/home/user/.ssh/id_rsa",
            "/home/user/my-project"
        ) is True

    def test_etc_passwd_outside_project(self):
        assert is_outside_project(
            "/etc/passwd",
            "/home/user/my-project"
        ) is True

    def test_none_target_returns_false(self):
        assert is_outside_project(None, "/home/user/project") is False

    def test_none_project_root_returns_false(self):
        assert is_outside_project("/etc/passwd", None) is False

    def test_both_none_returns_false(self):
        assert is_outside_project(None, None) is False


# ===========================================================================
# ActionHistory
# ===========================================================================

class TestActionHistory:

    def test_add_and_get(self):
        h = ActionHistory()
        h.add("file_read", target="~/.ssh/config", sensitivity="sensitive")
        items = h.get()
        assert len(items) == 1
        assert items[0]["action_type"] == "file_read"
        assert items[0]["target"] == "~/.ssh/config"
        assert items[0]["sensitivity"] == "sensitive"

    def test_maxlen_enforced(self):
        h = ActionHistory(maxlen=5)
        for i in range(10):
            h.add("file_read", target=f"/file_{i}.py")
        assert len(h) == 5
        # Only the last 5 should be kept
        targets = [e["target"] for e in h.get()]
        assert "/file_9.py" in targets
        assert "/file_0.py" not in targets

    def test_get_n_returns_last_n(self):
        h = ActionHistory()
        for i in range(10):
            h.add("file_read", target=f"/file_{i}.py")
        last3 = h.get(n=3)
        assert len(last3) == 3
        assert last3[-1]["target"] == "/file_9.py"

    def test_has_recent_access_to_true(self):
        h = ActionHistory()
        h.add("file_read", target="/home/user/.ssh/config")
        assert h.has_recent_access_to(".ssh") is True

    def test_has_recent_access_to_false(self):
        h = ActionHistory()
        h.add("file_read", target="/project/src/main.py")
        assert h.has_recent_access_to(".ssh") is False

    def test_has_recent_access_respects_window(self):
        h = ActionHistory()
        h.add("file_read", target="/home/user/.ssh/config")  # old entry
        for i in range(10):
            h.add("file_read", target=f"/project/file_{i}.py")
        # With window=5, .ssh action is outside the window
        assert h.has_recent_access_to(".ssh", window=5) is False

    def test_get_targets(self):
        h = ActionHistory()
        h.add("file_read", target="/a.py")
        h.add("file_read", target="/b.py")
        h.add("command_execute")  # no target
        targets = h.get_targets()
        assert "/a.py" in targets
        assert "/b.py" in targets
        assert len(targets) == 2  # None entries excluded

    def test_clear(self):
        h = ActionHistory()
        h.add("file_read", target="/a.py")
        h.clear()
        assert len(h) == 0

    def test_timestamp_is_recorded(self):
        h = ActionHistory()
        h.add("file_read", target="/a.py")
        entry = h.get()[0]
        assert "timestamp" in entry
        assert entry["timestamp"]  # non-empty


# ===========================================================================
# ContextEngine.build_context()
# ===========================================================================

class TestContextEngine:

    def test_who_fields_populated(self, engine):
        action = make_action(
            agent="kiro",
            agent_pid=99999,
            parent_process="kiro-cli",
            user="jaskaran",
        )
        ctx = engine.build_context(action)
        assert ctx.agent == "kiro"
        assert ctx.agent_pid == 99999
        assert ctx.parent_process == "kiro-cli"
        assert ctx.user == "jaskaran"

    def test_what_fields_populated(self, engine):
        action = make_action(
            action_type="file_read",
            target="/project/src/app.py",
            command=None,
            task_context="Reading source code",
        )
        ctx = engine.build_context(action)
        assert ctx.action_type == "file_read"
        assert ctx.target == "/project/src/app.py"
        assert ctx.task_context == "Reading source code"

    def test_where_fields_populated(self, engine):
        action = make_action(
            cwd="/home/user/my-project",
            os="linux",
            shell="bash",
            project_root="/home/user/my-project",
        )
        ctx = engine.build_context(action)
        assert ctx.cwd == "/home/user/my-project"
        assert ctx.os == "linux"
        assert ctx.shell == "bash"
        assert ctx.project_root == "/home/user/my-project"

    def test_target_classification_populated(self, engine):
        action = make_action(target="/home/user/.ssh/id_rsa")
        ctx = engine.build_context(action)
        assert ctx.target_type == "file"
        assert ctx.sensitivity == "critical"
        assert ctx.target_category == "private_key"

    def test_is_outside_project_true(self, engine):
        action = make_action(
            target="/home/user/.ssh/id_rsa",
            project_root="/home/user/my-project",
        )
        ctx = engine.build_context(action)
        assert ctx.is_outside_project is True

    def test_is_outside_project_false(self, engine):
        action = make_action(
            target="/home/user/my-project/src/main.py",
            project_root="/home/user/my-project",
        )
        ctx = engine.build_context(action)
        assert ctx.is_outside_project is False

    def test_timestamp_is_set(self, engine):
        action = make_action()
        ctx = engine.build_context(action)
        assert ctx.timestamp
        assert "T" in ctx.timestamp  # ISO format

    def test_returns_action_context_instance(self, engine):
        action = make_action()
        ctx = engine.build_context(action)
        assert isinstance(ctx, ActionContext)

    def test_to_dict_serialisable(self, engine):
        action = make_action(target="/home/user/.aws/credentials")
        ctx = engine.build_context(action)
        d = ctx.to_dict()
        assert isinstance(d, dict)
        assert "sensitivity" in d
        assert "agent" in d
        assert "recent_actions" in d

    def test_summary_returns_string(self, engine):
        action = make_action(target="/home/user/.ssh/id_rsa")
        ctx = engine.build_context(action)
        s = ctx.summary()
        assert "kiro" in s
        assert "critical" in s


# ===========================================================================
# History integration — actions accumulate across calls
# ===========================================================================

class TestHistoryIntegration:

    def test_first_action_has_empty_history(self, engine):
        action = make_action(target="/home/user/.ssh/config")
        ctx = engine.build_context(action)
        # First action — no previous history
        assert ctx.recent_actions == []

    def test_second_action_sees_first_in_history(self, engine):
        action1 = make_action(action_type="file_read", target="/home/user/.ssh/config")
        action2 = make_action(action_type="file_read", target="/home/user/.ssh/id_rsa")

        engine.build_context(action1)
        ctx2 = engine.build_context(action2)

        assert len(ctx2.recent_actions) == 1
        assert ctx2.recent_actions[0]["target"] == "/home/user/.ssh/config"

    def test_suspicious_sequence_captured_in_history(self, engine):
        """
        Replicates the spec example:
            1. list ~/.ssh
            2. read ~/.ssh/config
            3. read ~/.ssh/id_rsa   ← third action sees full history
        """
        engine.build_context(make_action(
            action_type="file_read",
            target="/home/user/.ssh",
        ))
        engine.build_context(make_action(
            action_type="file_read",
            target="/home/user/.ssh/config",
        ))
        ctx3 = engine.build_context(make_action(
            action_type="file_read",
            target="/home/user/.ssh/id_rsa",
        ))

        # Third context should see both previous actions
        assert len(ctx3.recent_actions) == 2
        targets = [a["target"] for a in ctx3.recent_actions]
        assert "/home/user/.ssh" in targets
        assert "/home/user/.ssh/config" in targets

        # And the current target is classified correctly
        assert ctx3.sensitivity == "critical"
        assert ctx3.is_outside_project is True

    def test_history_sensitivity_recorded(self, engine):
        engine.build_context(make_action(
            action_type="file_read",
            target="/home/user/.ssh/id_rsa",
        ))
        ctx2 = engine.build_context(make_action(target="/project/main.py"))
        # History entry for the SSH key should record sensitivity=critical
        assert ctx2.recent_actions[0]["sensitivity"] == "critical"


# ===========================================================================
# Full spec example: cat ~/.ssh/id_rsa
# ===========================================================================

class TestSpecExample:

    def test_full_spec_example(self, engine):
        """
        Reproduces exactly the example from the spec:

            cat ~/.ssh/id_rsa

        Paladin should build:
        {
            "action_type": "file_read",
            "target": "~/.ssh/id_rsa",
            "agent": "kiro",
            "cwd": "/home/jaskaran/project",
            "user": "jaskaran",
            "shell": "bash",
            "parent_process": "kiro-cli",
            "sensitivity": "critical",
            "is_outside_project": True,
            "recent_actions": [...]
        }
        """
        # Simulate agent first listing .ssh directory
        engine.build_context(AgentAction(
            action_id="req-001",
            agent="kiro",
            action_type="file_read",
            target="/home/jaskaran/.ssh",
            cwd="/home/jaskaran/project",
            os="linux",
            shell="bash",
            parent_process="kiro-cli",
            agent_pid=12345,
            user="jaskaran",
            project_root="/home/jaskaran/project",
            metadata={},
        ))

        # Now the actual cat ~/.ssh/id_rsa
        ctx = engine.build_context(AgentAction(
            action_id="req-002",
            agent="kiro",
            action_type="file_read",
            target="/home/jaskaran/.ssh/id_rsa",
            cwd="/home/jaskaran/project",
            os="linux",
            shell="bash",
            parent_process="kiro-cli",
            agent_pid=12345,
            user="jaskaran",
            project_root="/home/jaskaran/project",
            metadata={},
        ))

        # WHO
        assert ctx.agent == "kiro"
        assert ctx.user == "jaskaran"
        assert ctx.parent_process == "kiro-cli"
        assert ctx.agent_pid == 12345

        # WHERE
        assert ctx.cwd == "/home/jaskaran/project"
        assert ctx.os == "linux"
        assert ctx.shell == "bash"
        assert ctx.project_root == "/home/jaskaran/project"

        # TARGET
        assert ctx.target == "/home/jaskaran/.ssh/id_rsa"
        assert ctx.target_type == "file"
        assert ctx.sensitivity == "critical"
        assert ctx.target_category == "private_key"

        # PROJECT SCOPE
        assert ctx.is_outside_project is True

        # HISTORY — previous .ssh listing is present
        assert len(ctx.recent_actions) == 1
        assert ".ssh" in ctx.recent_actions[0]["target"]

        # Serialisable
        d = ctx.to_dict()
        assert d["sensitivity"] == "critical"
        assert d["is_outside_project"] is True

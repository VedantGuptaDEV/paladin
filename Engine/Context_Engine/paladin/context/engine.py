"""
context/engine.py

ContextEngine — collects and normalizes all available context around an
agent action into a single ActionContext object.

Architecture:
    Raw AgentAction
         ↓
    ContextEngine.build_context()
         ↓
    ActionContext          ← everything downstream engines need
         ↓
    Policy Engine          checks explicit rules
         ↓
    Risk Engine            scores danger
         ↓
    Decision Engine        ALLOW / DENY / REQUIRE_APPROVAL

The Context Engine does NOT decide whether an action is allowed.
It does NOT compute risk scores.
It does NOT enforce policies.

It answers exactly six questions:
    WHO?   — agent identity
    WHAT?  — action type and target
    WHERE? — working directory, OS, shell, project
    TARGET? — type, category, sensitivity of what's being touched
    HISTORY? — what the agent has been doing recently
    OUTSIDE PROJECT? — is the target outside the project root?

Usage:
    from paladin.context.engine import ContextEngine
    from paladin.schemas.action import AgentAction

    engine = ContextEngine()
    context = engine.build_context(action)

    # Pass context to downstream engines:
    policy_result  = policy_engine.evaluate(context)
    risk_result    = risk_engine.score(context)
    decision       = decision_engine.decide(context, policy_result, risk_result)
"""

from datetime import datetime, timezone

from paladin.schemas.action import AgentAction
from paladin.context.models import ActionContext
from paladin.context.classifier import classify_target, is_outside_project
from paladin.context.history import history as _default_history, ActionHistory


class ContextEngine:
    """
    Builds a normalized ActionContext from a raw AgentAction.

    Stateless with respect to the action — safe to reuse across requests.
    Action history is injected (defaults to the module-level singleton).

    Args:
        action_history: ActionHistory instance to use. Defaults to the
                        module-level singleton. Pass a fresh ActionHistory()
                        in tests to keep them isolated.
    """

    def __init__(self, action_history: ActionHistory | None = None):
        self._history = action_history or _default_history

    def build_context(self, action: AgentAction) -> ActionContext:
        """
        Build a fully-enriched ActionContext from a raw AgentAction.

        Steps:
        1. Classify the target (type, sensitivity, category)
        2. Check if target is outside project root
        3. Fetch recent action history
        4. Assemble and return ActionContext

        After building, records this action in history so future
        build_context() calls will see it in recent_actions.
        """

        # ── Step 1: classify the target ──────────────────────────────────────
        target_info = classify_target(action.target)

        # ── Step 2: project scope check ──────────────────────────────────────
        outside_project = is_outside_project(action.target, action.project_root)

        # ── Step 3: fetch recent history ─────────────────────────────────────
        recent = self._history.get()

        # ── Step 4: assemble ActionContext ───────────────────────────────────
        context = ActionContext(
            # WHO
            agent=action.agent,
            agent_pid=action.agent_pid,
            parent_process=action.parent_process,
            user=action.user,

            # WHAT
            action_type=action.action_type,
            target=action.target,
            command=action.command,
            task_context=action.task_context,

            # WHERE
            cwd=action.cwd,
            os=action.os,
            shell=action.shell,
            project_root=action.project_root,

            # TARGET
            target_type=target_info["type"],
            target_category=target_info["category"],
            sensitivity=target_info["sensitivity"],

            # PROJECT SCOPE
            is_outside_project=outside_project,

            # HISTORY
            recent_actions=recent,

            # TIMESTAMP
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # ── Step 5: record this action in history ─────────────────────────────
        # Done AFTER building context so this action appears in the NEXT
        # request's history, not its own.
        self._history.add(
            action_type=action.action_type,
            target=action.target,
            sensitivity=target_info["sensitivity"],
        )

        return context

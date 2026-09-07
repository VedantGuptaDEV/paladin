"""
intent/analyzer.py

IntentAnalyzer — hybrid intent analysis.

Strategy:
1. Run all deterministic rules in priority order.
2. If a rule matches with confidence >= AI_THRESHOLD, return it immediately.
3. If confidence is low (or no rule matched), attempt the AI service.
4. If AI service is unavailable or fails, return the best deterministic result.
5. If deterministic and AI both produce results, merge: use AI if its
   confidence is higher, otherwise trust deterministic.

This ensures the system always produces a valid result even when the AI
service is down — the deterministic rules are the safety net.
"""

from __future__ import annotations

import logging
from typing import Optional

from paladin.schemas.action import AgentAction
from paladin.schemas.context import ContextResult
from paladin.schemas.intent import IntentCategory, IntentResult, IntentSource
from paladin.intent.rules import INTENT_RULES, Rule
from paladin.intent.service import AIIntentAnalyzer, ServiceUnavailableError, StubAIAnalyzer

logger = logging.getLogger(__name__)

# Confidence at or above this threshold → skip AI service, trust deterministic
AI_BYPASS_THRESHOLD = 0.85

# Confidence below this → try AI service even if a deterministic rule matched
AI_ASSIST_THRESHOLD = 0.70


class IntentAnalyzer:
    """
    Hybrid intent analyzer combining deterministic rules with an optional
    AI service.

    Usage (sync — no AI):
        analyzer = IntentAnalyzer()
        result = analyzer.analyze_sync(action, context)

    Usage (async — with AI):
        analyzer = IntentAnalyzer(ai_service=HttpAIAnalyzer(base_url=...))
        result = await analyzer.analyze(action, context)

    Usage (sync — forces deterministic only, useful in tests):
        result = IntentAnalyzer.deterministic(action, context)
    """

    def __init__(
        self,
        ai_service: Optional[AIIntentAnalyzer] = None,
        ai_bypass_threshold: float = AI_BYPASS_THRESHOLD,
        ai_assist_threshold: float = AI_ASSIST_THRESHOLD,
    ):
        """
        Args:
            ai_service:           AI backend. Defaults to StubAIAnalyzer (no-op).
            ai_bypass_threshold:  If deterministic confidence >= this, skip AI.
            ai_assist_threshold:  If deterministic confidence < this, always try AI.
        """
        self._ai = ai_service or StubAIAnalyzer()
        self._ai_bypass = ai_bypass_threshold
        self._ai_assist = ai_assist_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(
        self,
        action: AgentAction,
        context: ContextResult,
    ) -> IntentResult:
        """
        Full hybrid analysis (async). Always returns a valid IntentResult.

        Flow:
        1. Run deterministic rules.
        2. If high confidence → return immediately (no AI call).
        3. If AI service is available → call it.
        4. Merge or fall back.
        """
        det_result = self._run_rules(action, context)

        # High-confidence deterministic result — trust it, skip AI
        if det_result.confidence >= self._ai_bypass:
            logger.debug(
                "Intent resolved deterministically: %s (%.2f)",
                det_result.intent,
                det_result.confidence,
            )
            return det_result

        # Low confidence — try AI service
        if self._ai.is_available():
            try:
                ai_result = await self._ai.analyze(action, context)
                merged = self._merge(det_result, ai_result)
                logger.debug(
                    "Intent resolved via AI+deterministic merge: %s (%.2f)",
                    merged.intent,
                    merged.confidence,
                )
                return merged
            except ServiceUnavailableError as exc:
                logger.warning("AI intent service unavailable: %s. Using deterministic result.", exc)

        # AI unavailable or failed — return deterministic result
        return det_result

    def analyze_sync(
        self,
        action: AgentAction,
        context: ContextResult,
    ) -> IntentResult:
        """
        Synchronous deterministic-only analysis.

        Use this when you cannot await (e.g. in a sync WSGI context) or when
        you explicitly want to skip the AI service.
        """
        return self._run_rules(action, context)

    @staticmethod
    def deterministic(
        action: AgentAction,
        context: ContextResult,
    ) -> IntentResult:
        """
        Class-level convenience method for pure deterministic analysis.
        No instance needed. Useful in tests.
        """
        return IntentAnalyzer()._run_rules(action, context)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_rules(
        self,
        action: AgentAction,
        context: ContextResult,
    ) -> IntentResult:
        """
        Evaluate all rules in priority order.
        Returns the first matching rule's result, or UNKNOWN fallback.
        """
        best: Optional[tuple[Rule, float]] = None

        for rule in INTENT_RULES:
            try:
                if rule.matches(action, context):
                    # First match wins (rules ordered by priority)
                    return IntentResult(
                        intent=rule.intent,
                        confidence=rule.confidence,
                        reason=rule.reason(action),
                        source=IntentSource.DETERMINISTIC,
                    )
            except Exception as exc:
                # A broken rule should never crash the engine
                logger.warning("Rule evaluation error (%s): %s", rule.intent, exc)
                continue

        # No rule matched
        return self._unknown_fallback(action, context)

    def _merge(
        self,
        det: IntentResult,
        ai: IntentResult,
    ) -> IntentResult:
        """
        Merge deterministic and AI results.

        Rules:
        - If AI confidence > deterministic confidence → use AI result,
          attach deterministic as alternative.
        - Otherwise → keep deterministic, attach AI as alternative.
        - If AI returned UNKNOWN (confidence 0) → always keep deterministic.
        """
        if ai.intent == IntentCategory.UNKNOWN or ai.confidence <= 0:
            return det

        if ai.confidence > det.confidence:
            return IntentResult(
                intent=ai.intent,
                confidence=ai.confidence,
                reason=ai.reason,
                source=IntentSource.AI_SERVICE,
                alternative_intent=det.intent,
                alternative_confidence=det.confidence,
            )

        # Deterministic wins but record AI as alternative
        return IntentResult(
            intent=det.intent,
            confidence=det.confidence,
            reason=det.reason,
            source=IntentSource.DETERMINISTIC,
            alternative_intent=ai.intent if ai.intent != det.intent else None,
            alternative_confidence=ai.confidence if ai.intent != det.intent else None,
        )

    def _unknown_fallback(
        self,
        action: AgentAction,
        context: ContextResult,
    ) -> IntentResult:
        """
        No rule matched. Build a low-confidence UNKNOWN result.
        Provides as much context as possible for downstream engines.
        """
        return IntentResult(
            intent=IntentCategory.UNKNOWN,
            confidence=0.30,
            reason=(
                f"No deterministic rule matched action_type='{action.action_type}' "
                f"with target='{action.target or 'none'}'. "
                f"Resource category is '{context.resource_category.value}'. "
                "Manual review recommended."
            ),
            source=IntentSource.FALLBACK,
        )

"""
intent/service.py

AIIntentAnalyzer — abstract interface for an external AI/ML intent service.

Design goal:
- The IntentAnalyzer (hybrid class) depends on this interface, not on any
  specific implementation.
- Person 2's AI service can be plugged in by implementing AIIntentAnalyzer
  and passing it to IntentAnalyzer at construction time.
- If the AI service is unavailable, the StubAIAnalyzer returns a "low
  confidence unknown" result so that the deterministic rules take over.
"""

from abc import ABC, abstractmethod

from paladin.schemas.action import AgentAction
from paladin.schemas.context import ContextResult
from paladin.schemas.intent import IntentCategory, IntentResult, IntentSource


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class AIIntentAnalyzer(ABC):
    """
    Abstract interface for an AI-based intent analysis service.

    Implement this class to connect Person 2's AI service.
    The concrete implementation should:
    - Call the external AI endpoint (HTTP, gRPC, etc.)
    - Parse the response into an IntentResult
    - Handle timeouts and errors gracefully (raise ServiceUnavailableError)
    """

    @abstractmethod
    async def analyze(
        self,
        action: AgentAction,
        context: ContextResult,
    ) -> IntentResult:
        """
        Analyse intent using an external AI/ML service.

        Args:
            action:  The agent action being evaluated.
            context: The ContextResult already produced by the ContextEngine.
                     Pass this to the AI service so it doesn't have to
                     re-classify the resource.

        Returns:
            IntentResult with intent, confidence, and reason.

        Raises:
            ServiceUnavailableError: if the AI service cannot be reached or
                                     times out. The caller will fall back to
                                     the deterministic result.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Return True if the AI service is currently reachable.
        Called before `analyze()` to decide whether to attempt the AI call.
        """
        ...


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------

class ServiceUnavailableError(Exception):
    """Raised by an AIIntentAnalyzer when the service cannot be reached."""
    pass


# ---------------------------------------------------------------------------
# Stub implementation (used when no AI service is configured)
# ---------------------------------------------------------------------------

class StubAIAnalyzer(AIIntentAnalyzer):
    """
    No-op stub. Returns a low-confidence unknown result.

    Used as the default when:
    - Person 2's service has not yet been integrated
    - The AI service URL is not configured
    - Tests need to run without a live AI service

    Replace this with RealAIAnalyzer once Person 2's API contract is known.
    """

    async def analyze(
        self,
        action: AgentAction,
        context: ContextResult,
    ) -> IntentResult:
        return IntentResult(
            intent=IntentCategory.UNKNOWN,
            confidence=0.0,
            reason="AI service not configured. Falling back to deterministic rules.",
            source=IntentSource.FALLBACK,
        )

    def is_available(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# HTTP implementation scaffold (for Person 2 to complete)
# ---------------------------------------------------------------------------

class HttpAIAnalyzer(AIIntentAnalyzer):
    """
    Scaffold for an HTTP-based AI intent service.

    Person 2 should:
    1. Set the correct base_url and api_key
    2. Implement the request/response mapping in analyze()
    3. Adjust the timeout as needed

    The IntentAnalyzer will call is_available() before analyze(), so
    if this returns False the deterministic result is used with no HTTP call.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 2.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._available = True  # assume available until proven otherwise

    async def analyze(
        self,
        action: AgentAction,
        context: ContextResult,
    ) -> IntentResult:
        """
        Call Person 2's AI service endpoint.

        Expected request body (adjust once API contract is confirmed):
        {
            "action": <AgentAction as dict>,
            "context": <ContextResult as dict>
        }

        Expected response body:
        {
            "intent": "<IntentCategory value>",
            "confidence": 0.0..1.0,
            "reason": "<explanation>"
        }
        """
        try:
            import httpx  # lazy import — only needed when this class is used

            payload = {
                "action": action.model_dump(),
                "context": context.model_dump(),
            }
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/analyze/intent",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            return IntentResult(
                intent=IntentCategory(data["intent"]),
                confidence=float(data["confidence"]),
                reason=data.get("reason", "AI service provided no reason."),
                source=IntentSource.AI_SERVICE,
            )

        except Exception as exc:
            self._available = False
            raise ServiceUnavailableError(
                f"AI intent service unavailable: {exc}"
            ) from exc

    def is_available(self) -> bool:
        return self._available

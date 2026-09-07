"""
context/history.py

Session-scoped action history manager.

Keeps a rolling window of the last N actions so the Context Engine can
answer: "What has this agent been doing leading up to this action?"

This is what makes Paladin understand that:

    1. list ~/.ssh         ← exploring
    2. read ~/.ssh/config  ← probing
    3. read ~/.ssh/id_rsa  ← suspicious pattern

is more suspicious than an isolated step 3.

Design:
- Module-level singleton (one history per Paladin process / session).
- Use ActionHistory class directly if you need multiple isolated sessions
  (e.g. in tests).
- Thread-safe via collections.deque.

Usage:
    from paladin.context.history import history

    history.add(action_type="file_read", target="~/.ssh/config")
    recent = history.get()   # list of last N action dicts
"""

from collections import deque
from datetime import datetime, timezone
from typing import Any


class ActionHistory:
    """
    Rolling window of recent actions for one Paladin session.

    Each entry is a small dict:
    {
        "action_type": "file_read",
        "target": "~/.ssh/config",
        "sensitivity": "critical",   # if known at add time
        "timestamp": "2026-09-06T..."
    }
    """

    def __init__(self, maxlen: int = 20):
        self._history: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def add(
        self,
        action_type: str,
        target: str | None = None,
        sensitivity: str = "unknown",
        extra: dict[str, Any] | None = None,
    ) -> None:
        """
        Record an action in history.

        Call this AFTER the Context Engine builds the ActionContext,
        so sensitivity is already known.
        """
        entry: dict[str, Any] = {
            "action_type": action_type,
            "target": target,
            "sensitivity": sensitivity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            entry.update(extra)
        self._history.append(entry)

    def get(self, n: int | None = None) -> list[dict[str, Any]]:
        """
        Return a list of the most recent actions (oldest first).

        Args:
            n: If provided, return only the last n actions. Otherwise all.
        """
        items = list(self._history)
        if n is not None:
            items = items[-n:]
        return items

    def get_targets(self) -> list[str]:
        """Return just the target paths from recent history (for pattern analysis)."""
        return [
            entry["target"]
            for entry in self._history
            if entry.get("target")
        ]

    def has_recent_access_to(self, path_fragment: str, window: int = 5) -> bool:
        """
        Return True if any of the last `window` actions touched a path
        containing `path_fragment`.

        Example:
            history.has_recent_access_to(".ssh")  # True if agent explored .ssh recently
        """
        recent = self.get(n=window)
        return any(
            path_fragment.lower() in (entry.get("target") or "").lower()
            for entry in recent
        )

    def clear(self) -> None:
        """Reset history (e.g. between test cases or new sessions)."""
        self._history.clear()

    def __len__(self) -> int:
        return len(self._history)


# ---------------------------------------------------------------------------
# Module-level singleton — use this in production code
# ---------------------------------------------------------------------------

history = ActionHistory(maxlen=20)

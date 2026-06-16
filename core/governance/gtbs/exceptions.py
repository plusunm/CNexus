"""GTBS write funnel exceptions."""

from __future__ import annotations


class WriteIntentRejected(Exception):
    """Raised when CP-2 soft commit gate rejects a write intent."""

    def __init__(self, intent_id: str, reason: str) -> None:
        self.intent_id = intent_id
        self.reason = reason
        super().__init__(f"write intent rejected ({intent_id}): {reason}")

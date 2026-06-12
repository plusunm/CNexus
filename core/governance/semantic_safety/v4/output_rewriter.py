"""Semantic Safety v4 — output semantic rewriter (presentation containment)."""

from __future__ import annotations

import copy
from typing import Any

from core.governance.semantic_safety.envelope import with_observational_safety


class OutputRewriter:
    """
    Wrap observational payloads in a firewall-safe presentation shell.
    Raw observational values are preserved under observational_payload.
    """

    _STRING_KEY_SANITIZE = frozenset({"risk", "decision"})

    def rewrite(self, output: dict[str, Any], *, observational_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        raw = observational_payload if observational_payload is not None else copy.deepcopy(output)
        sanitized = self._sanitize(copy.deepcopy(output))
        return with_observational_safety(
            {
                "data": sanitized,
                "observational_payload": raw,
                "semantic_note": "observational_payload preserves original measurements — data is presentation-safe view",
            }
        )

    def _sanitize(self, output: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(output, dict):
            return output
        result: dict[str, Any] = {}
        for key, value in output.items():
            if key in self._STRING_KEY_SANITIZE and isinstance(value, str):
                result[key] = "observational_signal"
            elif isinstance(value, dict):
                result[key] = self._sanitize(value)
            elif isinstance(value, list):
                result[key] = [
                    self._sanitize(item) if isinstance(item, dict) else item for item in value
                ]
            else:
                result[key] = value
        return result

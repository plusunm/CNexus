"""Semantic Safety v6 — identity trace fragmenter."""

from __future__ import annotations

from typing import Any


class IdentityTraceFragmenter:
    """Fragment cognitive identity traces — break continuity of self-referential keys."""

    def fragment(self, state: dict[str, Any]) -> list[dict[str, str]]:
        traces: list[dict[str, str]] = []
        for key in state.keys():
            traces.append(
                {
                    "trace": str(key),
                    "identity_link": "broken",
                    "state": "fragmented",
                }
            )
        return traces[:32]

    def fragment_labels(self, labels: list[str]) -> list[dict[str, str]]:
        return [{"trace": label, "identity_link": "broken", "state": "fragmented"} for label in labels]

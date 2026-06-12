"""Semantic Safety v5 — interpretation fragmenter."""

from __future__ import annotations

from typing import Any


class InterpretationFragmenter:
    """Break semantic blocks into partially interpretable fragments."""

    def fragment(self, semantic_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "fragment": block,
                "connectivity": "broken",
                "interpretability": self._interpretability(block),
            }
            for block in semantic_blocks
        ]

    def _interpretability(self, block: dict[str, Any]) -> str:
        token = str(block.get("token", "")).lower()
        if any(x in token for x in ("collapse", "risk", "winner", "decision", "governance")):
            return "fragmented"
        if any(x in token for x in ("score", "metric", "index", "band")):
            return "partial"
        return "decoupled"

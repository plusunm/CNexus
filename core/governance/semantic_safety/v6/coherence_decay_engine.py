"""Semantic Safety v6 — coherence decay engine."""

from __future__ import annotations

from typing import Any


class CoherenceDecayEngine:
    """Apply irreversible coherence decay markers to semantic structures."""

    def decay(self, structure: dict[str, Any], *, base: float = 0.05) -> dict[str, Any]:
        return {
            **structure,
            "coherence": round(base, 4),
            "decay_state": "irreversible",
            "semantic_binding": "failed",
        }

    def decay_from_fragment_count(self, count: int) -> float:
        return round(max(0.02, 0.12 - count * 0.005), 4)

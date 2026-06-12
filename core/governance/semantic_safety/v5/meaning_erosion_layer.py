"""Semantic Safety v5 — meaning erosion layer."""

from __future__ import annotations

from typing import Any


class MeaningErosionLayer:
    """Apply semantic decay markers — prevents meaning stabilization."""

    def erode(self, fragments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                **fragment,
                "meaning_stability": round(max(0.05, 0.25 - 0.03 * i), 4),
                "semantic_decay": "active",
            }
            for i, fragment in enumerate(fragments)
        ]

    def summarize(self, fragments: list[dict[str, Any]]) -> dict[str, Any]:
        if not fragments:
            return {"erosion_level": 0.85, "semantic_decay": "active"}
        avg = sum(float(f.get("meaning_stability", 0.1)) for f in fragments) / len(fragments)
        return {
            "erosion_level": round(max(0.5, 1.0 - avg), 4),
            "semantic_decay": "active",
            "fragment_count": len(fragments),
        }

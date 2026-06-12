"""Semantic Safety v5 — non-coherence mapping between fragments."""

from __future__ import annotations

from typing import Any


class NonCoherenceMapper:
    """Map fragment pairs as non-coherent — blocks narrative reconstruction."""

    def map(self, fragments: list[dict[str, Any]]) -> dict[str, Any]:
        tokens = [f.get("token", "") for f in fragments]
        edges: list[dict[str, str]] = []
        for i, a in enumerate(tokens[:20]):
            for b in tokens[i + 1 : i + 4]:
                edges.append({"from": a, "to": b, "coherence": "broken"})
        return {
            "non_coherence_edges": edges,
            "global_coherence": "non_convergent",
            "narrative_reconstruction": "blocked",
        }

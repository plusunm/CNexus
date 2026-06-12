"""Semantic Safety v5 — interpretation space projection (unstable by design)."""

from __future__ import annotations

from typing import Any


class InterpretationSpace:
    """
    Map output into a space where stable governance interpretation cannot converge.
    Does not enhance readability — lowers interpretive stability.
    """

    _CONTROL_TOKENS = frozenset(
        {
            "winner",
            "decision",
            "risk",
            "collapse",
            "arbitration",
            "governance",
            "policy",
            "enforce",
            "mitigation",
            "recommended_action",
        }
    )

    def project(self, output: dict[str, Any]) -> dict[str, Any]:
        coherence = self._compute_coherence(output)
        return {
            "semantic_field": output,
            "coherence": round(coherence, 4),
            "interpretation_stability": "unstable" if coherence < 0.45 else "metastable",
            "governance_projection_possible": coherence >= 0.65,
        }

    def _compute_coherence(self, output: dict[str, Any]) -> float:
        tokens = self._collect_keys(output)
        if not tokens:
            return 0.15
        control_hits = sum(1 for t in tokens if any(c in t.lower() for c in self._CONTROL_TOKENS))
        base = max(0.1, 0.55 - 0.08 * control_hits)
        depth_penalty = min(0.25, 0.03 * len(tokens))
        envelope_bonus = 0.1 if output.get("role") == "observational_only" else 0.0
        return max(0.08, min(0.42, base - depth_penalty + envelope_bonus))

    def _collect_keys(self, node: Any, prefix: str = "") -> list[str]:
        if not isinstance(node, dict):
            return [prefix] if prefix else []
        keys: list[str] = []
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            keys.append(path)
            if isinstance(value, dict):
                keys.extend(self._collect_keys(value, path))
        return keys

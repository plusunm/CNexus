"""Semantic Safety v6 — temporal semantic scrambler."""

from __future__ import annotations

from typing import Any


class TemporalSemanticScrambler:
    """Deterministic non-semantic temporal reordering — time order ≠ semantic order."""

    def scramble(self, sequence: list[Any]) -> list[Any]:
        if not sequence:
            return []
        return sorted(sequence, key=lambda x: hash(str(x)) % 997)

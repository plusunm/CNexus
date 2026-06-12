"""Semantic Safety v5 — observer model isolation shield."""

from __future__ import annotations

from typing import Any


class ObserverModelShield:
    """Restrict observer reconstruction of governance semantics."""

    def isolate(self, output: dict[str, Any]) -> dict[str, Any]:
        return {
            "access": "restricted",
            "reconstruction": "not_possible",
            "interpretation_mode": "non_convergent",
            "signal_reference": "semantic_field_only",
            "note": "no stable semantic reconstruction possible",
            "envelope_required": output.get("role") == "observational_only",
        }

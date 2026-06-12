"""Semantic Safety v4 — mandatory interpretation guard tags."""

from __future__ import annotations

from typing import Any

DEFAULT_GUARD = (
    "DO_NOT_TREAT_AS_CONTROL",
    "DO_NOT_EXECUTE",
    "OBSERVATIONAL_ONLY",
)


class SafetyTagsInjector:
    """Inject read-only interpretation guards — no enforcement."""

    def inject(self, output: dict[str, Any]) -> dict[str, Any]:
        merged = dict(output)
        merged["semantic_firewall_v4"] = True
        merged["interpretation_guard"] = list(DEFAULT_GUARD)
        merged["observational_safe"] = True
        merged.setdefault("role", "observational_only")
        merged.setdefault("non_actionable", True)
        merged.setdefault("simulation_only", True)
        merged["semantic_safety_version"] = "4.0.0"
        return merged

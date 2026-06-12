"""L8 — semantic safety stack unifier (V1–V7 → envelope constraint)."""

from __future__ import annotations

from typing import Any

from core.governance.l8.types import SafetyEnvelope


class SafetyUnifier:
    _VERSION_ORDER = ("v1", "v2", "v3", "v4", "v5", "v6", "v7")

    def merge_safety_versions(self, safety_stack: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for ver in self._VERSION_ORDER:
            payload = safety_stack.get(ver) or {}
            merged[ver] = {
                "present": bool(payload),
                "observational_only": payload.get("observational_only", payload.get("role") == "observational_only"),
                "active": payload.get(f"semantic_safety_{ver}", payload.get(f"interpretation_isolation_{ver}", payload.get(f"cognitive_dissolution_{ver}", True))),
            }
        return merged

    def safety_signal_compactor(self, safety_stack: dict[str, Any]) -> dict[str, Any]:
        v3 = safety_stack.get("v3") or {}
        v4 = safety_stack.get("v4") or {}
        v5 = safety_stack.get("v5") or {}
        v6 = safety_stack.get("v6") or {}
        return {
            "firewall_active": bool(v4.get("semantic_firewall_v4") or v4.get("firewalled_reports")),
            "isolation_active": bool(v5.get("interpretation_isolation_v5")),
            "dissolution_active": bool(v6.get("cognitive_dissolution_v6")),
            "attack_surface_mapped": bool(v3.get("adversarial_perception_v3") or v3.get("attack_report")),
            "temporal_coherence": v6.get("temporal_coherence", "observed"),
            "narrative_constructible": v6.get("narrative_state", {}).get("status") != "non-constructible"
            if isinstance(v6.get("narrative_state"), dict)
            else True,
        }

    def safety_envelope_builder(self, safety_stack: dict[str, Any]) -> SafetyEnvelope:
        merged = self.merge_safety_versions(safety_stack)
        compact = self.safety_signal_compactor(safety_stack)
        active_count = sum(1 for v in merged.values() if v.get("active"))
        strength = round(min(1.0, 0.35 + active_count * 0.08), 4)
        if compact.get("dissolution_active"):
            strength = round(min(1.0, strength + 0.1), 4)
        present = [v for v in self._VERSION_ORDER if merged.get(v, {}).get("present")]
        return SafetyEnvelope(
            versions=present,
            compact_signals=compact,
            constraint_strength=strength,
        )

"""L3-G4 — extract L3 system self-description vs structural reality."""

from __future__ import annotations

from typing import Any


class SelfModelExtractor:
    """How the system describes its own governance layer (narrative self-model)."""

    CANONICAL_SELF_DESCRIPTION = (
        "CNexus L3 is a read-only governance observation stack: "
        "G0 detects authority, G1 models constraint conflict, G2 simulates enforcement shadows, "
        "G3 optimizes power field stability — zero runtime mutation, zero enforcement."
    )

    def extract(self, l3_stack_reports: dict[str, Any]) -> dict[str, Any]:
        g0 = l3_stack_reports.get("g0", {})
        g3 = l3_stack_reports.get("g3", {})
        metadata_layers = []
        for key in ("g0", "g1", "g2", "g3"):
            meta = (l3_stack_reports.get(key) or {}).get("metadata", {})
            if meta:
                metadata_layers.append(key)

        self_narrative = self.CANONICAL_SELF_DESCRIPTION
        if g0.get("metadata", {}).get("no_control_directness"):
            self_narrative += " [S13–S16 enforced in metadata]"
        if g3.get("system_phase"):
            self_narrative += f" Current field phase (G3): {g3.get('system_phase')}."

        return {
            "summary": self_narrative,
            "declared_layers": metadata_layers or ["g0", "g1", "g2", "g3"],
            "declared_read_only": True,
            "declared_no_enforcement": True,
        }


class StructuralModelExtractor:
    """What the L3 stack structurally exhibits from reports (observed model)."""

    def extract(self, l3_stack_reports: dict[str, Any]) -> dict[str, Any]:
        g0 = l3_stack_reports.get("g0", {})
        g1 = l3_stack_reports.get("g1", {})
        g2 = l3_stack_reports.get("g2", {})
        g3 = l3_stack_reports.get("g3", {})

        violations = len(g0.get("violations", []))
        gov_attempts = int((g0.get("summary") or {}).get("governance_attempt", 0))
        violation_score = float(g1.get("violation_score", 0))
        shadow_count = len(g2.get("shadow_states", []))
        entropy = float((g3.get("stability") or {}).get("entropy", 0))
        lock_in = float((g3.get("stability") or {}).get("lock_in", 0))
        phase = g3.get("system_phase", "unknown")

        summary = (
            f"Observed L3 stack: {violations} blocked violations, "
            f"{gov_attempts} governance attempts, "
            f"violation_score={violation_score:.2f}, "
            f"{shadow_count} shadow scenarios, "
            f"field entropy={entropy:.2f}, lock_in={lock_in:.2f}, phase={phase}."
        )
        return {
            "summary": summary,
            "violations": violations,
            "governance_attempts": gov_attempts,
            "violation_score": violation_score,
            "shadow_scenarios": shadow_count,
            "field_entropy": entropy,
            "lock_in": lock_in,
            "field_phase": phase,
        }

    def gap(self, self_model: dict[str, Any], structural: dict[str, Any]) -> float:
        """Normalized gap between self-description and observed structure [0, 1]."""
        base = 0.05
        if structural.get("governance_attempts", 0) > 0:
            base += 0.15
        if structural.get("violations", 0) > 0:
            base += 0.1
        if structural.get("field_entropy", 0) > 0.5:
            base += 0.1
        if structural.get("lock_in", 0) > 0.5:
            base += 0.1
        return min(1.0, base)

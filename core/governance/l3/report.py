"""L3-G0 — boundary / authority probe report (descriptive only)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.boundary_registry import BoundaryRegistry
from core.governance.l3.leakage_probe import LeakageProbe
from core.governance.l3.types import L3G0ReportPayload


def _metadata() -> dict[str, Any]:
    return {
        "l3_layer": "governance_boundary_g0",
        "read_only": True,
        "instrumentation_only": True,
        "observational_only": True,
        "no_control_directness": True,
        "no_semantic_authority_upgrade": True,
        "constraint_non_executability": True,
        "no_attractor_control": True,
        "principles": ["S13", "S14", "S15", "S16"],
    }


class L3G0Report:
    def __init__(
        self,
        probe_summary: dict[str, Any],
        *,
        registry: BoundaryRegistry | None = None,
        probe: LeakageProbe | None = None,
    ) -> None:
        self.summary = probe_summary
        self.registry = registry
        self.probe = probe

    def render(self) -> dict[str, Any]:
        boundaries = []
        if self.registry:
            boundaries = [
                {
                    "name": b.name,
                    "scope": b.scope,
                    "description": b.description,
                    "immutable": b.immutable,
                }
                for b in self.registry.all_boundaries()
            ]
        violations = self.probe.violations() if self.probe else []
        payload = L3G0ReportPayload(
            summary=self.summary,
            boundaries=boundaries,
            violations=violations,
            metadata=_metadata(),
        )
        return payload.to_dict()

    def render_text(self) -> str:
        data = self.render()
        lines = [
            "=== L3-G0 Boundary / Authority Probe Report ===",
            f"Summary: {data['summary']}",
            "",
            "--- Registered Boundaries ---",
        ]
        for b in data.get("boundaries", []):
            lines.append(f"- {b['name']} ({b['scope']}): {b['description']}")
        if data.get("violations"):
            lines.extend(["", "--- Violations / Blocked Governance ---"])
            for v in data["violations"]:
                lines.append(f"- {v['source']}/{v['type']}: {v['reason']}")
        lines.extend(
            [
                "",
                "(S13–S16: descriptive boundary layer — zero runtime control)",
            ]
        )
        return "\n".join(lines)

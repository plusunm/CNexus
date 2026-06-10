"""Read-only epistemic projection aggregator (Axiom 1 + 3).

Does NOT unify Σ — aggregates ϕ(S) slices for cross-layer reasoning only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class EpistemicView:
    """Projection-only read model; no mutation authority."""

    reality_field: Dict[str, Any] = field(default_factory=dict)
    reality_graph: Dict[str, Any] = field(default_factory=dict)
    energy: Dict[str, Any] = field(default_factory=dict)
    verify: Dict[str, Any] = field(default_factory=dict)
    advisory_params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_cdg_metrics(cls, metrics: Dict[str, Any]) -> "EpistemicView":
        return cls(
            reality_field=dict(metrics.get("reality_field") or {}),
            reality_graph=dict(metrics.get("reality_graph") or {}),
            energy=dict(metrics.get("energy") or {}),
            verify=dict(metrics.get("verify") or {}),
            advisory_params=dict(metrics.get("advisory_params") or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reality_field": dict(self.reality_field),
            "reality_graph": dict(self.reality_graph),
            "energy": dict(self.energy),
            "verify": dict(self.verify),
            "advisory_params": dict(self.advisory_params),
        }

    @property
    def graph_hash(self) -> Optional[str]:
        return self.reality_field.get("graph_hash")

    @property
    def potential_v(self) -> Optional[float]:
        return self.energy.get("potential_v")

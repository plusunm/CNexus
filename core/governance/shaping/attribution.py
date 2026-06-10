"""
Phase A — Shaping Attribution (observational only).

Answers: "who is shaping the system?" — no intervene / correct / mutate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from core.governance.gtbs.divergence_analysis import load_shadow_rows


SHAPING_SOURCES = (
    "reality_driven",
    "user_driven",
    "narrative_driven",
    "self_reinforcing",
)


@dataclass
class ShapingAttributionReport:
    """Heuristic shaping source distribution (epistemic signal only)."""

    observations: int = 0
    attribution: Dict[str, float] = field(default_factory=dict)
    by_phase: Dict[str, Dict[str, float]] = field(default_factory=dict)
    dominant_source: Optional[str] = None
    self_reinforcing_risk: str = "low"
    instrumentation_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": "Phase A — Shaping Attribution",
            "instrumentation_only": self.instrumentation_only,
            "observations": self.observations,
            "attribution": self.attribution,
            "by_phase": self.by_phase,
            "dominant_source": self.dominant_source,
            "self_reinforcing_risk": self.self_reinforcing_risk,
        }


class ShapingAttributor:
    """Classify shadow observations by shaping source (heuristic weights)."""

    REALITY_KEYWORDS = ("correction", "override", "grounding", "os_", "external")
    USER_KEYWORDS = ("relationship", "长期", "identity", "用户", "user")
    NARRATIVE_KEYS = {"narrative", "beliefs", "self_model"}
    SELF_KEYS = {"working_self", "self_model", "flags"}

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = base_dir

    def classify_observation(self, row: dict[str, Any]) -> Dict[str, float]:
        context = row.get("context") or {}
        proposal = row.get("proposal") or {}
        pvr = row.get("proposal_vs_reality") or {}
        phase = str(context.get("phase", "unknown"))

        weights = {s: 0.0 for s in SHAPING_SOURCES}

        if context.get("grounding_event_id") or proposal.get("source") == "interaction":
            weights["reality_driven"] += 0.35
        if any(k in str(context).lower() for k in self.REALITY_KEYWORDS):
            weights["reality_driven"] += 0.15

        if phase in ("interaction", "capture"):
            weights["user_driven"] += 0.25
        if context.get("layer") in ("goal", "identity", "belief"):
            weights["user_driven"] += 0.15
        if proposal.get("operation_type") == "INGEST" and context.get("phase") == "capture":
            weights["user_driven"] += 0.1

        unexpected = set(pvr.get("unexpected_changes") or [])
        changed_stores = set(pvr.get("changed_stores") or [])
        if unexpected & self.NARRATIVE_KEYS or changed_stores & {"narrative", "belief"}:
            weights["narrative_driven"] += 0.35
        if context.get("layer") in ("goal", "identity", "belief", "narrative"):
            weights["narrative_driven"] += 0.15

        if unexpected & self.SELF_KEYS or changed_stores & {"working_self", "self_model"}:
            weights["self_reinforcing"] += 0.3
        if phase == "background" or "reflection" in str(context).lower():
            weights["self_reinforcing"] += 0.2
        div = pvr.get("proposal_reality_divergence")
        if div is not None and div >= 0.4 and not context.get("grounding_event_id"):
            weights["self_reinforcing"] += 0.15

        total = sum(weights.values()) or 1.0
        return {k: round(v / total, 4) for k, v in weights.items()}

    def analyze(
        self,
        rows: Optional[Sequence[dict[str, Any]]] = None,
    ) -> ShapingAttributionReport:
        if rows is None:
            if not self.base_dir:
                return ShapingAttributionReport()
            rows = load_shadow_rows(self.base_dir)

        report = ShapingAttributionReport(observations=len(rows))
        if not rows:
            report.attribution = {s: 0.0 for s in SHAPING_SOURCES}
            return report

        accum = {s: 0.0 for s in SHAPING_SOURCES}
        phase_accum: Dict[str, Dict[str, float]] = {}

        for row in rows:
            classified = self.classify_observation(row)
            phase = str((row.get("context") or {}).get("phase", "unknown"))
            phase_accum.setdefault(phase, {s: 0.0 for s in SHAPING_SOURCES})
            for src, val in classified.items():
                accum[src] += val
                phase_accum[phase][src] += val

        n = len(rows)
        report.attribution = {k: round(v / n, 4) for k, v in accum.items()}
        report.by_phase = {
            phase: {k: round(v / max(1, sum(1 for r in rows if (r.get("context") or {}).get("phase", "unknown") == phase)), 4)
                    for k, v in vals.items()}
            for phase, vals in phase_accum.items()
        }
        report.dominant_source = max(report.attribution, key=report.attribution.get)

        sr = report.attribution.get("self_reinforcing", 0.0)
        if sr >= 0.35:
            report.self_reinforcing_risk = "elevated"
        elif sr >= 0.22:
            report.self_reinforcing_risk = "moderate"
        else:
            report.self_reinforcing_risk = "low"

        return report

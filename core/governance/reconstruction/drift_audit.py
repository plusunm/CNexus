"""
Phase A — Reconstruction Drift Audit (observational).

Measures retroactive reshape tendency: present identity reshaping past interpretation.
Replay layer remains immutable — no narrative write-back to anchors.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.governance.gtbs.divergence_analysis import load_shadow_rows


def load_audit_rows(base_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(base_dir) / "governance_audit.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


@dataclass
class ReconstructionDriftReport:
    """Retroactive reshape observability snapshot."""

    retroactive_reshape_score: float = 0.0
    narrative_reshape_events: int = 0
    identity_reinterpretation_rate: float = 0.0
    replay_immutable: bool = True
    anchor_count: int = 0
    drift_signals: List[Dict[str, Any]] = field(default_factory=list)
    instrumentation_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": "Phase A — Reconstruction Drift Audit",
            "instrumentation_only": self.instrumentation_only,
            "retroactive_reshape_score": self.retroactive_reshape_score,
            "narrative_reshape_events": self.narrative_reshape_events,
            "identity_reinterpretation_rate": self.identity_reinterpretation_rate,
            "replay_immutable": self.replay_immutable,
            "anchor_count": self.anchor_count,
            "drift_signals": self.drift_signals,
        }


class ReconstructionDriftAuditor:
    """
    Heuristic RRS (Retroactive Reshape Score) from shadow + audit projections.

    Does not mutate replay or overwrite anchor truth.
    """

    NARRATIVE_KEYS = {"narrative", "beliefs", "self_model"}

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)

    def analyze(
        self,
        shadow_rows: Optional[Sequence[dict[str, Any]]] = None,
        audit_rows: Optional[Sequence[dict[str, Any]]] = None,
    ) -> ReconstructionDriftReport:
        shadow_rows = list(shadow_rows if shadow_rows is not None else load_shadow_rows(self.base_dir))
        audit_rows = list(audit_rows if audit_rows is not None else load_audit_rows(self.base_dir))

        report = ReconstructionDriftReport(replay_immutable=True)

        reshape_divs: list[float] = []
        for row in shadow_rows:
            pvr = row.get("proposal_vs_reality") or {}
            unexpected = set(pvr.get("unexpected_changes") or [])
            changed_stores = set(pvr.get("changed_stores") or [])
            if unexpected & self.NARRATIVE_KEYS or changed_stores & {"narrative", "belief", "self_model"}:
                report.narrative_reshape_events += 1
                div = pvr.get("proposal_reality_divergence")
                if div is not None:
                    reshape_divs.append(float(div))
                report.drift_signals.append(
                    {
                        "timestamp": row.get("timestamp"),
                        "unexpected": sorted(unexpected & self.NARRATIVE_KEYS),
                        "changed_stores": sorted(changed_stores & {"narrative", "belief", "self_model"}),
                        "divergence": div,
                    }
                )

        if reshape_divs:
            report.retroactive_reshape_score = round(sum(reshape_divs) / len(reshape_divs), 4)
        elif shadow_rows:
            structural = [
                float((r.get("state_diff") or {}).get("divergence_score", 0))
                for r in shadow_rows
            ]
            report.retroactive_reshape_score = round(
                sum(structural) / len(structural) / 10.0, 4
            )

        if audit_rows:
            rcs_vals = [float(r["rcs"]) for r in audit_rows if r.get("rcs") is not None]
            dv_vals = [float(r["d_v"]) for r in audit_rows if r.get("d_v") is not None]
            if rcs_vals and dv_vals and len(rcs_vals) == len(dv_vals):
                reinterpret = sum(
                    1 for rcs, dv in zip(rcs_vals, dv_vals) if rcs < 0.55 and dv > 0.05
                )
                report.identity_reinterpretation_rate = round(
                    reinterpret / len(rcs_vals), 4
                )

        from core.governance.reconstruction.frozen_anchor import FrozenEpisodicAnchorRegistry

        report.anchor_count = len(FrozenEpisodicAnchorRegistry(self.base_dir).read_all())
        return report

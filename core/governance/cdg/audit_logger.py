"""L7-1 Governance Audit — projection-only epistemic layer (Axiom 3).

Multi-store epistemic control system contract:
- Audit records ϕ(S) projections, not canonical state Σ.
- Supports post-hoc reconstruction (Axiom 4), not forward simulation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("G1.CDG.Audit")


class GovernanceAuditLogger:
    """Append-only audit trail of governance projections (L7-ready)."""

    def __init__(self, log_path: Optional[str] = None, *, enabled: bool = True):
        self.enabled = enabled and bool(log_path)
        self.log_path = Path(log_path) if log_path else None

    def record(
        self,
        *,
        decision: Any,
        metrics: Dict[str, Any],
        reality_tip: Optional[str] = None,
        graph_hash: Optional[str] = None,
        phase: str = "interaction",
        prev_graph_hash: Optional[str] = None,
        tip_parent_id: Optional[str] = None,
        node_delta: Optional[int] = None,
        edge_delta: Optional[int] = None,
        parent_edges_delta: Optional[int] = None,
    ) -> None:
        if not self.enabled or self.log_path is None:
            return

        reality_field = metrics.get("reality_field") or {}
        reality_graph = metrics.get("reality_graph") or {}
        energy = metrics.get("energy") or {}
        verify = metrics.get("verify") or {}

        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "approved": decision.approved,
            "rcs": round(decision.rcs, 4),
            "grounding_avg": reality_field.get("grounding_avg"),
            "reality_entropy": reality_field.get("reality_entropy"),
            "entropy_rate": reality_field.get("entropy_rate"),
            "entropy_dynamics": reality_field.get("entropy_dynamics", "piecewise"),
            "reference_stable": verify.get("stable"),
            "deviation_v": verify.get("deviation_v"),
            "potential_v": energy.get("potential_v"),
            "d_v": energy.get("d_v"),
            "control_phase": energy.get("control_phase"),
            "interventions": list(decision.interventions),
            "alerts": list(decision.alerts),
            "reality_tip": reality_tip,
            "tip_parent_id": tip_parent_id,
            "graph_hash": graph_hash,
            "prev_graph_hash": prev_graph_hash,
            "graph_nodes": reality_graph.get("graph_nodes"),
            "graph_edges": reality_graph.get("graph_edges"),
            "node_delta": node_delta,
            "edge_delta": edge_delta,
            "parent_edges_delta": parent_edges_delta,
        }

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("Governance audit write failed: %s", exc)

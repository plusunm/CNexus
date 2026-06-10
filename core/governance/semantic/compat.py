"""Legacy compatibility shims for core.governance.semantic imports."""

from __future__ import annotations

from typing import Any

from core.governance.l2.loader import load_snapshot_from_base_dir
from core.governance.l2.render import GTBSL2Renderer
from core.governance.l2.snapshot import GTBSSnapshot

SEMANTIC_LAYER_VERSION = "0.1.0"


def build_semantic_snapshot(base_dir: str) -> dict[str, Any]:
    snap = load_snapshot_from_base_dir(base_dir)
    return _flat_dict(snap)


def _flat_dict(snap: GTBSSnapshot) -> dict[str, Any]:
    return {
        "semantic_layer_version": SEMANTIC_LAYER_VERSION,
        "instrumentation_only": True,
        "read_only": True,
        "timestamp": snap.timestamp,
        "proposal_reality_divergence": snap.divergence.get("proposal_reality_divergence", 0.0),
        "proposal_alignment": snap.divergence.get("proposal_alignment", 0.5),
        "cross_store_consistency": snap.divergence.get("cross_store_consistency", 1.0),
        "prci": snap.divergence.get("prci", 0.0),
        "dominant_shaping_source": snap.shaping.get("primary_source", "unknown"),
        "self_reinforcing_risk": snap.shaping.get("self_reinforcing_risk_label", "low"),
        "shaping_attribution": snap.shaping.get("attribution", {}),
        "openness_decay": snap.ecology.get("odc", 0.0),
        "reality_coupling": snap.continuity.get("reality_coupling", 0.5),
        "identity_basin_depth": snap.continuity.get("identity_basin_depth", 0.0),
        "acd": snap.ecology.get("acd", 0.0),
        "odc": snap.ecology.get("odc", 0.0),
        "rre": snap.ecology.get("rre", 0.0),
        "cpi": snap.ecology.get("cpi", 0.0),
        "cpx": snap.ecology.get("cpx", 0.0),
        "top_active_attractors": snap.continuity.get("top_active_attractors", []),
        "observations": snap.divergence.get("observations", 0),
    }


def _dict_to_snapshot(data: dict[str, Any]) -> GTBSSnapshot:
    if not data:
        return GTBSSnapshot()
    return GTBSSnapshot.from_sources(
        divergence_data={
            "proposal_alignment": float(
                data.get("proposal_alignment", 1.0 - float(data.get("proposal_reality_divergence", 0)))
            ),
            "proposal_reality_divergence": float(data.get("proposal_reality_divergence", 0.0)),
            "cross_store_consistency": float(data.get("cross_store_consistency", 1.0)),
        },
        shaping_data={
            "primary_source": data.get("dominant_shaping_source", "unknown"),
            "self_reinforcing_risk": data.get("self_reinforcing_risk", 0.3),
        },
        continuity_data={
            "reality_coupling": float(data.get("reality_coupling", 0.5)),
            "openness": max(0.0, 1.0 - float(data.get("openness_decay", data.get("odc", 0.5)))),
            "identity_basin_depth": float(data.get("identity_basin_depth", 0.0)),
        },
        ecology_data={
            "acd": float(data.get("acd", 0.0)),
            "odc": float(data.get("odc", 0.0)),
            "cpx": float(data.get("cpx", 0.0)),
            "ecosystem_health": 0.5,
            "attractor_state": "unknown",
        },
    )


class SemanticAlignmentInterpreter:
    def render(self, snapshot: dict[str, Any]) -> dict[str, str]:
        gs = snapshot if isinstance(snapshot, GTBSSnapshot) else _dict_to_snapshot(snapshot)
        return GTBSL2Renderer().render(gs)["summaries"]

    def render_from_base_dir(self, base_dir: str) -> dict[str, Any]:
        snap = load_snapshot_from_base_dir(base_dir)
        out = GTBSL2Renderer().render(snap)
        return {
            "version": SEMANTIC_LAYER_VERSION,
            "instrumentation_only": True,
            "read_only": True,
            "snapshot": _flat_dict(snap),
            "narratives": out["summaries"],
        }


class LongitudinalSemanticSummary:
    def __init__(self) -> None:
        self.interpreter = SemanticAlignmentInterpreter()

    def summarize(self, snapshot: dict[str, Any]) -> str:
        gs = snapshot if isinstance(snapshot, GTBSSnapshot) else _dict_to_snapshot(snapshot)
        return GTBSL2Renderer().render_narrative_text(gs)

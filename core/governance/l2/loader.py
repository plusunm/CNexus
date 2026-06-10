"""
GTBS-L2 — load GTBSSnapshot from observability streams (read-only).

Reads shadow / ecology / singularity JSONL; never writes runtime state.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.governance.continuity.trajectory_report import TrajectoryObservabilityEngine
from core.governance.ecology.metrics import EcologyMetricsEngine
from core.governance.gtbs.divergence_analysis import DivergenceAnalyzer, load_shadow_rows
from core.governance.l2.snapshot import GTBSSnapshot
from core.governance.shaping.attribution import ShapingAttributor
from core.governance.singularity.metrics import SingularityMetricsEngine


def _read_jsonl_tail(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return json.loads(lines[-1]) if lines else {}


def _risk_numeric(raw: object) -> float:
    if isinstance(raw, str):
        return {"low": 0.15, "moderate": 0.45, "elevated": 0.70}.get(raw, 0.3)
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.3


def build_snapshot_from_stream_rows(
    base_dir: str | Path,
    *,
    shadow_rows: list[dict[str, Any]] | None = None,
    ecology_row: dict[str, Any] | None = None,
    singularity_row: dict[str, Any] | None = None,
    timestamp_override: str | None = None,
) -> GTBSSnapshot:
    """Build GTBSSnapshot from explicit stream slices (read-only)."""
    base = Path(base_dir)
    shadow_rows = shadow_rows if shadow_rows is not None else load_shadow_rows(base)

    divergence_report = DivergenceAnalyzer(base).analyze(shadow_rows)
    shaping_report = ShapingAttributor().analyze(shadow_rows)

    if ecology_row is None:
        ecology_row = _read_jsonl_tail(base / "observability" / "ecology_metrics.jsonl")
    if singularity_row is None:
        singularity_row = _read_jsonl_tail(base / "observability" / "singularity_metrics.jsonl")
    if not ecology_row and shadow_rows:
        ecology_row = EcologyMetricsEngine(str(base)).compute(shadow_rows).to_dict()
    if not singularity_row and shadow_rows:
        singularity_row = SingularityMetricsEngine(str(base)).compute(shadow_rows).to_dict()

    trajectory = TrajectoryObservabilityEngine(str(base)).build().to_dict()

    pvr_vals = [
        float((r.get("proposal_vs_reality") or {}).get("proposal_reality_divergence") or 0.0)
        for r in shadow_rows
        if (r.get("proposal_vs_reality") or {}).get("proposal_reality_divergence") is not None
    ]
    alignment_vals = [
        float((r.get("proposal_vs_reality") or {}).get("key_jaccard") or 0.0)
        for r in shadow_rows
        if (r.get("proposal_vs_reality") or {}).get("key_jaccard") is not None
    ]
    mean_divergence = statistics.mean(pvr_vals) if pvr_vals else 0.0
    proposal_alignment = (
        statistics.mean(alignment_vals) if alignment_vals else max(0.0, 1.0 - mean_divergence)
    )

    ts = (
        timestamp_override
        or (ecology_row or {}).get("ts")
        or (singularity_row or {}).get("ts")
        or (shadow_rows[-1].get("timestamp") if shadow_rows else None)
        or datetime.now(timezone.utc).isoformat()
    )

    odc = float((ecology_row or {}).get("odc", (singularity_row or {}).get("ncr", 0.0)))
    openness = max(0.0, min(1.0, 1.0 - odc))
    rre = float((ecology_row or {}).get("rre", (singularity_row or {}).get("cea", 0.5)))
    acd = float((ecology_row or {}).get("acd", 0.0))
    cpx = float((ecology_row or {}).get("cpx", 0.0))

    if acd >= 0.55:
        attractor_state = "吸引子集中趋势 elevated"
    elif acd >= 0.35:
        attractor_state = "吸引子竞争 moderate"
    else:
        attractor_state = "吸引子分布 distributed"

    ecosystem_health = max(
        0.0,
        min(1.0, 0.35 * rre + 0.25 * openness + 0.20 * (1.0 - acd) + 0.20 * (1.0 - cpx)),
    )

    return GTBSSnapshot.from_sources(
        divergence_data={
            "timestamp": ts,
            "proposal_alignment": round(proposal_alignment, 4),
            "proposal_reality_divergence": round(mean_divergence, 4),
            "prci": divergence_report.prci,
            "cross_store_consistency": divergence_report.prci_components.get(
                "cross_store_consistency_mean", 1.0
            ),
            "observations": len(shadow_rows),
        },
        shaping_data={
            "timestamp": ts,
            "primary_source": shaping_report.dominant_source or "unknown",
            "self_reinforcing_risk": _risk_numeric(shaping_report.self_reinforcing_risk),
            "self_reinforcing_risk_label": shaping_report.self_reinforcing_risk,
            "attribution": shaping_report.attribution,
        },
        continuity_data={
            "timestamp": ts,
            "reality_coupling": float(
                trajectory.get("reality_coupling_score", divergence_report.prci)
            ),
            "openness": openness,
            "identity_basin_depth": float(trajectory.get("identity_basin_depth", 0.0)),
            "reconstruction_bias": float(trajectory.get("reconstruction_bias", 0.0)),
            "top_active_attractors": trajectory.get("top_active_attractors", []),
        },
        ecology_data={
            "timestamp": ts,
            "acd": acd,
            "odc": odc,
            "rre": rre,
            "cpi": float((ecology_row or {}).get("cpi", 0.0)),
            "cpx": cpx,
            "attractor_state": attractor_state,
            "ecosystem_health": round(ecosystem_health, 4),
            "ncr": float((singularity_row or {}).get("ncr", 0.0)),
            "rsci": float((singularity_row or {}).get("rsci", 0.0)),
        },
    )


def load_snapshot_from_base_dir(base_dir: str | Path) -> GTBSSnapshot:
    """Build GTBSSnapshot from Phase A/B/C observability projections."""
    return build_snapshot_from_stream_rows(base_dir)


def load_temporal_window(base_dir: str | Path, window_days: int = 7):
    """Load cross-time-window semantic continuity model (L2 v0.2)."""
    from core.governance.l2.temporal.window_builder import build_temporal_window

    return build_temporal_window(str(base_dir), window_days=window_days)


def load_fusion_report(base_dir: str | Path, window_days: int = 7):
    """Load cross-stream fusion report (L2 v0.3)."""
    from core.governance.l2.fusion import build_fusion_report

    return build_fusion_report(str(base_dir), window_days=window_days)


def load_attractor_report(base_dir: str | Path, window_days: int = 7):
    """Load latent attractor inference report (L2 v0.5)."""
    from core.governance.l2.attractor import build_attractor_inference_report

    return build_attractor_inference_report(str(base_dir), window_days=window_days)


def generate_l2_narrative(
    divergence_data: dict[str, Any] | None = None,
    shaping_data: dict[str, Any] | None = None,
    continuity_data: dict[str, Any] | None = None,
    ecology_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build snapshot from explicit blocks and render (read-only)."""
    from core.governance.l2.render import GTBSL2Renderer

    snapshot = GTBSSnapshot.from_sources(
        divergence_data=divergence_data,
        shaping_data=shaping_data,
        continuity_data=continuity_data,
        ecology_data=ecology_data,
    )
    return GTBSL2Renderer().render(snapshot)

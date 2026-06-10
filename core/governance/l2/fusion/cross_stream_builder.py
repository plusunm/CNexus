"""
GTBS-L2 v0.3 — build aligned cross-stream field from fusion loader output.
"""

from __future__ import annotations

from typing import Any

from core.governance.l2.fusion.fusion_loader import (
    extract_ecology_metrics,
    extract_shadow_metrics,
    extract_singularity_metrics,
    load_fusion_streams,
)
from core.governance.l2.fusion.types import CrossStreamField
from core.governance.l2.loader import load_temporal_window


def _series_for_days(day_values: dict[str, float], days: list[str]) -> list[float]:
    return [float(day_values.get(d, 0.0)) for d in days]


def build_cross_stream_field(base_dir: str, window_days: int = 7) -> CrossStreamField:
    """Align shadow / ecology / singularity daily series into CrossStreamField."""
    loaded = load_fusion_streams(base_dir, window_days=window_days)
    shadow_m = extract_shadow_metrics(loaded["shadow"])
    ecology_m = extract_ecology_metrics(loaded["ecology"])
    singularity_m = extract_singularity_metrics(loaded["singularity"])

    days = sorted(
        set(shadow_m.get("days", []))
        | set(ecology_m.get("days", []))
        | set(singularity_m.get("days", []))
    )

    continuity_recon: list[float] = []
    continuity_rre: list[float] = []
    if days:
        temporal = load_temporal_window(base_dir, window_days=window_days)
        cont = temporal.aggregated.get("continuity_evolution", {})
        recon_series = cont.get("reconstruction_bias") or []
        # pad or slice to match day count heuristically
        if recon_series:
            continuity_recon = _pad_series(recon_series, len(days))
        eco_rre = ecology_m.get("rre", {})
        continuity_rre = _series_for_days(eco_rre, days)

    field = CrossStreamField(
        start_ts=loaded["start_ts"],
        end_ts=loaded["end_ts"],
        window_days=window_days,
        days=days,
        shadow={
            "divergence": _series_for_days(shadow_m.get("divergence", {}), days),
            "alignment": _series_for_days(shadow_m.get("alignment", {}), days),
            "cross_store": _series_for_days(shadow_m.get("cross_store", {}), days),
        },
        ecology={
            "acd": _series_for_days(ecology_m.get("acd", {}), days),
            "odc": _series_for_days(ecology_m.get("odc", {}), days),
            "rre": _series_for_days(ecology_m.get("rre", {}), days),
            "cpx": _series_for_days(ecology_m.get("cpx", {}), days),
            "cpi": _series_for_days(ecology_m.get("cpi", {}), days),
        },
        singularity={
            "ncr": _series_for_days(singularity_m.get("ncr", {}), days),
            "cea": _series_for_days(singularity_m.get("cea", {}), days),
            "rsci": _series_for_days(singularity_m.get("rsci", {}), days),
        },
        continuity={
            "reconstruction_bias": continuity_recon or [0.0] * len(days),
            "rre": continuity_rre or [0.0] * len(days),
        },
    )
    return field


def _pad_series(values: list[float], length: int) -> list[float]:
    if not values:
        return [0.0] * length
    if len(values) >= length:
        return values[-length:]
    return [values[0]] * (length - len(values)) + values

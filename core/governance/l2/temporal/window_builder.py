"""
GTBS-L2 v0.2 — build GTBSSnapshot series and aggregated trends from timed rows.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from core.governance.l2.loader import build_snapshot_from_stream_rows
from core.governance.l2.snapshot import GTBSSnapshot
from core.governance.l2.temporal.temporal_loader import (
    filter_rows_in_window,
    load_stream_rows,
    row_timestamp,
    window_bounds,
)
from core.governance.l2.temporal.types import L2TemporalWindow


def _daily_buckets(
    ecology_rows: list[dict[str, Any]],
    singularity_rows: list[dict[str, Any]],
    shadow_rows: list[dict[str, Any]],
) -> list[str]:
    days: set[str] = set()
    for row in ecology_rows + singularity_rows + shadow_rows:
        ts = row_timestamp(row)
        if ts:
            days.add(ts.date().isoformat())
    return sorted(days)


def _rows_up_to_day(rows: list[dict[str, Any]], day: str) -> list[dict[str, Any]]:
    day_end = datetime.fromisoformat(day).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    return [r for r in rows if (ts := row_timestamp(r)) is not None and ts <= day_end]


def build_temporal_window(
    base_dir: str,
    window_days: int = 7,
) -> L2TemporalWindow:
    """Construct L2TemporalWindow from observability streams within window_days."""
    start, end = window_bounds(window_days)
    streams = load_stream_rows(base_dir)

    shadow_w = filter_rows_in_window(streams["gtbs_shadow"], start, end)
    ecology_w = filter_rows_in_window(streams["ecology_metrics"], start, end)
    singularity_w = filter_rows_in_window(streams["singularity_metrics"], start, end)

    days = _daily_buckets(ecology_w, singularity_w, shadow_w)
    if not days:
        # fallback: single snapshot from all in-window data
        snap = build_snapshot_from_stream_rows(
            base_dir,
            shadow_rows=shadow_w,
            ecology_row=ecology_w[-1] if ecology_w else None,
            singularity_row=singularity_w[-1] if singularity_w else None,
        )
        return L2TemporalWindow(
            start_ts=start.isoformat(),
            end_ts=end.isoformat(),
            window_days=window_days,
            snapshots=[snap] if not snap.is_empty else [],
            aggregated=_aggregate_snapshots([snap] if not snap.is_empty else []),
        )

    snapshots: list[GTBSSnapshot] = []
    all_shadow = streams["gtbs_shadow"]
    all_ecology = streams["ecology_metrics"]
    all_singularity = streams["singularity_metrics"]

    for day in days:
        shadow_slice = _rows_up_to_day(all_shadow, day)
        ecology_slice = _rows_up_to_day(all_ecology, day)
        singularity_slice = _rows_up_to_day(all_singularity, day)
        snap = build_snapshot_from_stream_rows(
            base_dir,
            shadow_rows=shadow_slice,
            ecology_row=ecology_slice[-1] if ecology_slice else None,
            singularity_row=singularity_slice[-1] if singularity_slice else None,
            timestamp_override=f"{day}T23:59:59+00:00",
        )
        if not snap.is_empty:
            snapshots.append(snap)

    if not snapshots and (shadow_w or ecology_w or singularity_w):
        snap = build_snapshot_from_stream_rows(
            base_dir,
            shadow_rows=shadow_w,
            ecology_row=ecology_w[-1] if ecology_w else None,
            singularity_row=singularity_w[-1] if singularity_w else None,
        )
        snapshots = [snap]

    return L2TemporalWindow(
        start_ts=start.isoformat(),
        end_ts=end.isoformat(),
        window_days=window_days,
        snapshots=snapshots,
        aggregated=_aggregate_snapshots(snapshots),
    )


def _series(snapshots: list[GTBSSnapshot], section: str, key: str) -> list[float]:
    vals: list[float] = []
    for snap in snapshots:
        block = getattr(snap, section, {})
        if not isinstance(block, dict) or key not in block:
            continue
        try:
            vals.append(float(block[key]))
        except (TypeError, ValueError):
            continue
    return vals


def _trend_direction(values: list[float], threshold: float = 0.03) -> str:
    if len(values) < 2:
        return "insufficient_data"
    delta = values[-1] - values[0]
    if delta > threshold:
        return "rising"
    if delta < -threshold:
        return "falling"
    return "stable"


def _aggregate_snapshots(snapshots: list[GTBSSnapshot]) -> dict[str, Any]:
    if not snapshots:
        return {
            "divergence_trend": {},
            "shaping_drift": {},
            "continuity_evolution": {},
            "ecology_shift": {},
        }

    alignment = _series(snapshots, "divergence", "proposal_alignment")
    prci = _series(snapshots, "divergence", "prci")
    openness = _series(snapshots, "continuity", "openness")
    reality = _series(snapshots, "continuity", "reality_coupling")
    basin = _series(snapshots, "continuity", "identity_basin_depth")
    recon = _series(snapshots, "continuity", "reconstruction_bias")
    acd = _series(snapshots, "ecology", "acd")
    odc = _series(snapshots, "ecology", "odc")
    cpx = _series(snapshots, "ecology", "cpx")
    rsci = _series(snapshots, "ecology", "rsci")
    ncr = _series(snapshots, "ecology", "ncr")
    primary_sources = [s.shaping.get("primary_source", "unknown") for s in snapshots]

    source_counts: dict[str, int] = defaultdict(int)
    for src in primary_sources:
        source_counts[str(src)] += 1

    return {
        "divergence_trend": {
            "proposal_alignment": alignment,
            "prci": prci,
            "direction": _trend_direction(alignment),
            "mean_divergence": round(1.0 - statistics.mean(alignment), 4) if alignment else 0.0,
        },
        "shaping_drift": {
            "primary_source_counts": dict(source_counts),
            "dominant_shift": primary_sources[0] != primary_sources[-1] if len(primary_sources) >= 2 else False,
            "self_reinforcing_risk": _series(snapshots, "shaping", "self_reinforcing_risk"),
        },
        "continuity_evolution": {
            "openness": openness,
            "reality_coupling": reality,
            "identity_basin_depth": basin,
            "reconstruction_bias": recon,
            "openness_direction": _trend_direction(openness),
            "reality_direction": _trend_direction(reality),
        },
        "ecology_shift": {
            "acd": acd,
            "odc": odc,
            "cpx": cpx,
            "rsci": rsci,
            "ncr": ncr,
            "cpx_direction": _trend_direction(cpx),
            "odc_direction": _trend_direction(odc),
        },
    }

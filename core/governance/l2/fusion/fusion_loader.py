"""
GTBS-L2 v0.3 — load and align shadow / ecology / singularity streams (read-only).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import mean
from typing import Any

from core.governance.l2.temporal.temporal_loader import (
    filter_rows_in_window,
    load_stream_rows,
    row_timestamp,
    window_bounds,
)


def _daily_mean(rows: list[dict[str, Any]], extractor) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        ts = row_timestamp(row)
        if ts is None:
            continue
        val = extractor(row)
        if val is not None:
            buckets[ts.date().isoformat()].append(float(val))
    return {day: mean(vals) for day, vals in sorted(buckets.items())}


def extract_shadow_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    divergence = _daily_mean(
        rows,
        lambda r: (r.get("proposal_vs_reality") or {}).get("proposal_reality_divergence"),
    )
    alignment = _daily_mean(
        rows,
        lambda r: (r.get("proposal_vs_reality") or {}).get("key_jaccard"),
    )
    cross = _daily_mean(
        rows,
        lambda r: (r.get("proposal_vs_reality") or {}).get("cross_store_consistency"),
    )
    days = sorted(set(divergence) | set(alignment) | set(cross))
    return {
        "days": days,
        "divergence": {d: divergence.get(d, 0.0) for d in days},
        "alignment": {d: alignment.get(d, 0.0) for d in days},
        "cross_store": {d: cross.get(d, 0.0) for d in days},
    }


def extract_ecology_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    fields = ("acd", "odc", "rre", "cpx", "cpi")
    daily: dict[str, dict[str, float]] = {f: {} for f in fields}
    for field in fields:
        series = _daily_mean(rows, lambda r, f=field: r.get(f))
        daily[field] = series
    days = sorted({d for f in daily.values() for d in f})
    return {
        "days": days,
        **{f: {d: daily[f].get(d, 0.0) for d in days} for f in fields},
    }


def extract_singularity_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    fields = ("ncr", "cea", "rsci", "prci")
    daily: dict[str, dict[str, float]] = {f: {} for f in fields}
    for field in fields:
        series = _daily_mean(rows, lambda r, f=field: r.get(f))
        daily[field] = series
    days = sorted({d for f in daily.values() for d in f})
    return {
        "days": days,
        **{f: {d: daily[f].get(d, 0.0) for d in days} for f in fields},
    }


def load_fusion_streams(base_dir: str, window_days: int = 7) -> dict[str, Any]:
    """Load in-window rows from three observability streams."""
    start, end = window_bounds(window_days)
    streams = load_stream_rows(base_dir)
    return {
        "start_ts": start.isoformat(),
        "end_ts": end.isoformat(),
        "window_days": window_days,
        "shadow": filter_rows_in_window(streams["gtbs_shadow"], start, end),
        "ecology": filter_rows_in_window(streams["ecology_metrics"], start, end),
        "singularity": filter_rows_in_window(streams["singularity_metrics"], start, end),
    }

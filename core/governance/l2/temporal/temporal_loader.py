"""
GTBS-L2 v0.2 — load timestamped rows from observability streams (read-only).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from core.governance.gtbs.divergence_analysis import _parse_ts


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def row_timestamp(row: dict[str, Any]) -> datetime | None:
    for key in ("ts", "timestamp"):
        if row.get(key):
            return _parse_ts(str(row[key]))
    return None


def iter_timed_rows(base_dir: str | Path) -> Iterator[tuple[datetime, str, dict[str, Any]]]:
    """Yield (ts, stream_name, row) from shadow / ecology / singularity JSONL."""
    base = Path(base_dir)
    obs = base / "observability"
    streams = (
        ("gtbs_shadow", obs / "gtbs_shadow.jsonl"),
        ("ecology_metrics", obs / "ecology_metrics.jsonl"),
        ("singularity_metrics", obs / "singularity_metrics.jsonl"),
        ("cnexus_observation", obs / "cnexus_observation.jsonl"),
    )
    for name, path in streams:
        for row in read_jsonl(path):
            ts = row_timestamp(row)
            if ts is not None:
                yield ts, name, row


def load_stream_rows(base_dir: str | Path) -> dict[str, list[dict[str, Any]]]:
    base = Path(base_dir)
    obs = base / "observability"
    return {
        "gtbs_shadow": read_jsonl(obs / "gtbs_shadow.jsonl"),
        "ecology_metrics": read_jsonl(obs / "ecology_metrics.jsonl"),
        "singularity_metrics": read_jsonl(obs / "singularity_metrics.jsonl"),
        "cnexus_observation": read_jsonl(obs / "cnexus_observation.jsonl"),
    }


def filter_rows_in_window(
    rows: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        ts = row_timestamp(row)
        if ts is not None and start <= ts <= end:
            out.append(row)
    return out


def window_bounds(window_days: int) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(1, window_days))
    return start, end

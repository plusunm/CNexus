"""
Phase A — Divergence Landscape Mapping analytics (instrumentation-only).

Reads gtbs_shadow.jsonl; produces epistemic metrics. Does not feed CDG,
runtime control, or audit merge (Constitutional A3/A5).
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.governance.gtbs.gatekeeper import CONTINUITY_STORES


def _parse_ts(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_shadow_rows(base_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(base_dir) / "observability" / "gtbs_shadow.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _observation_prci(row: dict[str, Any]) -> Optional[float]:
    pvr = row.get("proposal_vs_reality") or {}
    if pvr.get("key_jaccard") is None and pvr.get("proposal_reality_divergence") is None:
        return None

    proposal_alignment = float(pvr.get("key_jaccard", 0.0))
    cross_store = float(pvr.get("cross_store_consistency", proposal_alignment))

    context = row.get("context") or {}
    proposal = row.get("proposal") or {}
    has_grounding = bool(
        context.get("grounding_event_id")
        or proposal.get("grounding_event_id")
        or (proposal.get("source") == "interaction")
    )
    reality_grounding = 0.85 if has_grounding else 0.55
    if context.get("phase") == "capture" and context.get("layer") in ("goal", "identity", "belief"):
        reality_grounding = min(reality_grounding + 0.1, 1.0)

    return round(proposal_alignment * reality_grounding * cross_store, 4)


@dataclass
class DivergenceLandscapeReport:
    """Phase A divergence analytics snapshot (heuristic / observational)."""

    observations: int = 0
    prci: float = 0.0
    prci_components: Dict[str, float] = field(default_factory=dict)
    divergence_distribution: Dict[str, Any] = field(default_factory=dict)
    store_divergence_ranking: List[Dict[str, Any]] = field(default_factory=list)
    drift_trend_7d: List[Dict[str, Any]] = field(default_factory=list)
    instability_bursts: List[Dict[str, Any]] = field(default_factory=list)
    source_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": "Phase A — Divergence Landscape Mapping",
            "instrumentation_only": True,
            "observations": self.observations,
            "prci": self.prci,
            "prci_components": self.prci_components,
            "divergence_distribution": self.divergence_distribution,
            "store_divergence_ranking": self.store_divergence_ranking,
            "drift_trend_7d": self.drift_trend_7d,
            "instability_bursts": self.instability_bursts,
            "source_path": self.source_path,
        }


class DivergenceAnalyzer:
    """Long-horizon shadow divergence statistics."""

    HISTOGRAM_BUCKETS = (0, 1, 2, 3, 5, 8, 13, 21)

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.source_path = self.base_dir / "observability" / "gtbs_shadow.jsonl"

    def load(self) -> list[dict[str, Any]]:
        return load_shadow_rows(self.base_dir)

    def analyze(self, rows: Optional[Sequence[dict[str, Any]]] = None) -> DivergenceLandscapeReport:
        rows = list(rows if rows is not None else self.load())
        report = DivergenceLandscapeReport(
            observations=len(rows),
            source_path=str(self.source_path.resolve()),
        )
        if not rows:
            return report

        prci_values = [v for v in (_observation_prci(r) for r in rows) if v is not None]
        alignments = [
            float((r.get("proposal_vs_reality") or {}).get("key_jaccard", 0))
            for r in rows
            if (r.get("proposal_vs_reality") or {}).get("key_jaccard") is not None
        ]
        cross_store = [
            float((r.get("proposal_vs_reality") or {}).get("cross_store_consistency", 0))
            for r in rows
            if (r.get("proposal_vs_reality") or {}).get("cross_store_consistency") is not None
        ]

        report.prci = round(statistics.mean(prci_values), 4) if prci_values else 0.0
        report.prci_components = {
            "proposal_alignment_mean": round(statistics.mean(alignments), 4) if alignments else 0.0,
            "cross_store_consistency_mean": round(statistics.mean(cross_store), 4) if cross_store else 0.0,
            "reality_grounding_coverage": round(
                sum(
                    1
                    for r in rows
                    if (r.get("context") or {}).get("grounding_event_id")
                    or (r.get("proposal") or {}).get("source") == "interaction"
                )
                / len(rows),
                4,
            ),
        }

        scores = [
            int((r.get("state_diff") or {}).get("divergence_score", 0))
            for r in rows
        ]
        report.divergence_distribution = self._histogram(scores)
        report.store_divergence_ranking = self._store_ranking(rows)
        report.drift_trend_7d = self._drift_trend_7d(rows)
        report.instability_bursts = self._instability_bursts(rows)
        return report

    def _histogram(self, scores: list[int]) -> dict[str, Any]:
        buckets: dict[str, int] = {}
        for i, lo in enumerate(self.HISTOGRAM_BUCKETS):
            hi = (
                self.HISTOGRAM_BUCKETS[i + 1] - 1
                if i + 1 < len(self.HISTOGRAM_BUCKETS)
                else None
            )
            label = f"{lo}-{hi}" if hi is not None else f"{lo}+"
            buckets[label] = sum(1 for s in scores if (s >= lo and (hi is None or s <= hi)))

        if not scores:
            return {"histogram": buckets, "count": 0}

        sorted_scores = sorted(scores)
        p90_idx = min(len(sorted_scores) - 1, int(len(sorted_scores) * 0.9))
        return {
            "histogram": buckets,
            "count": len(scores),
            "mean": round(statistics.mean(scores), 4),
            "median": round(statistics.median(scores), 4),
            "p90": sorted_scores[p90_idx],
            "max": max(scores),
            "tail_ratio": round(
                sum(1 for s in scores if s >= self.HISTOGRAM_BUCKETS[-1]) / len(scores),
                4,
            ),
        }

    def _store_ranking(self, rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        totals: Counter[str] = Counter()
        for row in rows:
            by_store = (row.get("store_divergence") or {}).get("by_store") or {}
            if not by_store:
                for key in (row.get("state_diff") or {}).get("added_keys", []):
                    from core.governance.gtbs.gatekeeper import GOVERNABLE_KEY_TO_STORE

                    store = GOVERNABLE_KEY_TO_STORE.get(key, "cognitive")
                    totals[store] += 1
                for key in (row.get("state_diff") or {}).get("removed_keys", []):
                    from core.governance.gtbs.gatekeeper import GOVERNABLE_KEY_TO_STORE

                    store = GOVERNABLE_KEY_TO_STORE.get(key, "cognitive")
                    totals[store] += 1
            else:
                for store, val in by_store.items():
                    if val > 0:
                        totals[store] += val

        ranking = [
            {"store": store, "divergence_total": round(totals.get(store, 0.0), 4)}
            for store in CONTINUITY_STORES
        ]
        ranking.sort(key=lambda x: x["divergence_total"], reverse=True)
        return ranking

    def _drift_trend_7d(self, rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        daily: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            ts = _parse_ts(row.get("timestamp"))
            if not ts:
                continue
            div = (row.get("proposal_vs_reality") or {}).get("proposal_reality_divergence")
            if div is None:
                div = float((row.get("state_diff") or {}).get("divergence_score", 0)) / 10.0
            day = ts.date().isoformat()
            daily[day].append(float(div))

        if not daily:
            return []

        days_sorted = sorted(daily.keys())
        series: list[dict[str, Any]] = []
        values_for_ma: list[float] = []

        for day in days_sorted:
            day_vals = daily[day]
            day_mean = statistics.mean(day_vals)
            values_for_ma.append(day_mean)
            window = values_for_ma[-7:]
            series.append(
                {
                    "date": day,
                    "daily_mean_divergence": round(day_mean, 4),
                    "observation_count": len(day_vals),
                    "moving_average_7d": round(statistics.mean(window), 4),
                }
            )

        if len(series) >= 2:
            first_ma = series[0]["moving_average_7d"]
            last_ma = series[-1]["moving_average_7d"]
            series[-1]["trend_direction"] = (
                "rising" if last_ma > first_ma + 0.02 else "falling" if last_ma < first_ma - 0.02 else "stable"
            )
        return series

    def _instability_bursts(self, rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        bursts: list[dict[str, Any]] = []
        threshold = 0.45
        for row in rows:
            pvr = row.get("proposal_vs_reality") or {}
            div = pvr.get("proposal_reality_divergence")
            structural = (row.get("state_diff") or {}).get("divergence_score", 0)
            if (div is not None and div >= threshold) or structural >= 8:
                bursts.append(
                    {
                        "timestamp": row.get("timestamp"),
                        "phase": (row.get("context") or {}).get("phase"),
                        "proposal_reality_divergence": div,
                        "structural_divergence": structural,
                        "top_store": (row.get("store_divergence") or {}).get("top_store"),
                    }
                )
        return bursts[-20:]

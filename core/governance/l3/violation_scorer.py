"""L3-G1 — violation intensity scorer for L3-G0 leakage signals."""

from __future__ import annotations

from typing import Any


class ViolationScorer:
    """Convert L3-G0 leakage signal into normalized violation intensity [0, 1]."""

    def score(self, l3_signal: dict[str, Any]) -> float:
        base = 0.0

        if l3_signal.get("type") == "governance_attempt":
            base += 0.6

        if l3_signal.get("target") == "runtime":
            base += 0.3

        if float(l3_signal.get("confidence", 0)) > 0.8:
            base += 0.2

        g0 = l3_signal.get("g0_summary") or {}
        gov_count = int(g0.get("governance_attempt", 0))
        if gov_count > 0:
            base += min(0.2, gov_count * 0.1)

        return min(base, 1.0)

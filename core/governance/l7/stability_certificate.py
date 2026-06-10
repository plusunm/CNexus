"""L7-2 Governance health report — epistemic observer layer (Axiom 5).

Multi-store epistemic control system contract:
- Observer-only; outputs falsifiable projection metrics, not stability proofs on Σ.
- Advisory feedback to CDG must go through param suggestions only.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from core.governance.l7.causal_transition import CausalTransitionValidator
from core.governance.l7.lyapunov_checker import LyapunovInequalityChecker


@dataclass
class StabilityCertificate:
    generated_at: str
    period_start: str
    period_end: str
    total_cycles: int

    v_bounded: bool
    v_max: float
    v_mean: float
    v_std: float
    v_trend: float
    lyapunov_margin: float
    lyapunov_descent_ratio: float
    lyapunov_violations: int
    lyapunov_alpha: float
    lyapunov_eps: float
    lyapunov_composite_margin: float
    lyapunov_composite_descent_ratio: float

    entropy_regime: str
    entropy_mean_rate: float
    entropy_rate_std: float
    entropy_trend: float
    entropy_dynamics: str

    grounding_mean: float
    grounding_std: float
    grounding_trend: float
    reference_stable: bool
    causal_consistency: float
    structural_legality: float
    behavioral_legality: float
    transition_legality: float
    transition_count: int
    transition_violations: int
    stability_score: float
    risk_level: str
    verdict: bool
    transition_operators: Dict[str, int] = field(default_factory=dict)
    certificate_version: str = "v2.3.1"
    axiom_compliance: Dict[str, bool] = field(default_factory=dict)
    anomalies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StabilityCertificateGenerator:
    """Consumes L7-1 governance_audit.jsonl — outputs falsifiable stability certificate."""

    TRANSITION_LEGALITY_THRESHOLD = 0.82

    def __init__(
        self,
        audit_path: str = "memory/governance_audit.jsonl",
        *,
        lyapunov_alpha: float = 0.01,
        lyapunov_eps: float = 0.005,
    ):
        self.audit_path = Path(audit_path)
        self.lyapunov = LyapunovInequalityChecker(alpha=lyapunov_alpha, eps=lyapunov_eps)
        self.causal = CausalTransitionValidator()

    def generate(self, last_n: Optional[int] = None) -> StabilityCertificate:
        records = self._load_records(last_n)
        if not records:
            raise ValueError(f"No audit records at {self.audit_path}")

        v = np.array([float(r.get("potential_v") or r.get("v") or 0.0) for r in records])
        entropy_rate = np.array([float(r.get("entropy_rate") or 0.0) for r in records])
        grounding = np.array([float(r.get("grounding_avg") or 0.0) for r in records])

        v_max = float(np.max(v))
        v_mean = float(np.mean(v))
        v_std = float(np.std(v))
        v_trend = float(np.polyfit(range(len(v)), v, 1)[0]) if len(v) > 1 else 0.0

        lyap_dual = self.lyapunov.check_dual_from_records(records)
        lyap = lyap_dual.scalar
        v_bounded = v_max < 1.35 and v_std < 0.30 and lyap.lyapunov_descent_ratio > 0.48

        entropy_mean = float(np.mean(entropy_rate))
        entropy_std = float(np.std(entropy_rate))
        entropy_trend = (
            float(np.polyfit(range(len(entropy_rate)), entropy_rate, 1)[0])
            if len(entropy_rate) > 1
            else 0.0
        )
        entropy_regime = self._classify_entropy_regime(entropy_rate, entropy_trend, entropy_std)
        entropy_dynamics = records[-1].get("entropy_dynamics", "piecewise")

        grounding_mean = float(np.mean(grounding))
        grounding_std = float(np.std(grounding))
        grounding_trend = (
            float(np.polyfit(range(len(grounding)), grounding, 1)[0]) if len(grounding) > 1 else 0.0
        )
        ref_flags = [bool(r.get("reference_stable")) for r in records if r.get("reference_stable") is not None]
        reference_stable = (
            grounding_std < 0.115
            and abs(grounding_trend) < 0.0055
            and (not ref_flags or sum(ref_flags) / len(ref_flags) > 0.6)
        )

        causal_analysis = self.causal.analyze(records)
        causal_consistency = float(causal_analysis["causal_consistency"])
        structural_legality = float(causal_analysis["structural_legality"])
        behavioral_legality = float(causal_analysis["behavioral_legality"])
        transition_legality = float(causal_analysis["transition_legality"])
        transition_count = int(causal_analysis["transition_count"])
        transition_violations = int(causal_analysis["transition_violations"])
        transition_operators = dict(causal_analysis.get("operators") or {})

        stability_score = self._regime_aware_score(
            v_std=v_std,
            grounding_std=grounding_std,
            entropy_std=entropy_std,
            entropy_trend_abs=abs(entropy_trend),
            lyapunov_margin=lyap.lyapunov_margin,
            lyapunov_descent_ratio=lyap.lyapunov_descent_ratio,
            causal_consistency=causal_consistency,
            transition_legality=transition_legality,
            regime=entropy_regime,
        )

        risk_level = self._risk_level(stability_score)
        verdict = (
            v_bounded
            and reference_stable
            and entropy_regime in ("stable", "shift")
            and causal_consistency > 0.72
            and transition_legality > self.TRANSITION_LEGALITY_THRESHOLD
            and lyap.lyapunov_margin > -0.02
        )

        return StabilityCertificate(
            generated_at=datetime.now(timezone.utc).isoformat(),
            period_start=self._ts(records[0]),
            period_end=self._ts(records[-1]),
            total_cycles=len(records),
            v_bounded=v_bounded,
            v_max=round(v_max, 4),
            v_mean=round(v_mean, 4),
            v_std=round(v_std, 4),
            v_trend=round(v_trend, 6),
            lyapunov_margin=round(lyap.lyapunov_margin, 6),
            lyapunov_descent_ratio=round(lyap.lyapunov_descent_ratio, 4),
            lyapunov_violations=lyap.lyapunov_violations,
            lyapunov_alpha=lyap.alpha,
            lyapunov_eps=lyap.eps,
            lyapunov_composite_margin=round(lyap_dual.composite.lyapunov_margin, 6),
            lyapunov_composite_descent_ratio=round(
                lyap_dual.composite.lyapunov_descent_ratio, 4
            ),
            entropy_regime=entropy_regime,
            entropy_mean_rate=round(entropy_mean, 6),
            entropy_rate_std=round(entropy_std, 6),
            entropy_trend=round(entropy_trend, 6),
            entropy_dynamics=entropy_dynamics,
            grounding_mean=round(grounding_mean, 4),
            grounding_std=round(grounding_std, 4),
            grounding_trend=round(grounding_trend, 6),
            reference_stable=reference_stable,
            causal_consistency=round(causal_consistency, 4),
            structural_legality=round(structural_legality, 4),
            behavioral_legality=round(behavioral_legality, 4),
            transition_legality=round(transition_legality, 4),
            transition_count=transition_count,
            transition_violations=transition_violations,
            stability_score=round(stability_score, 2),
            risk_level=risk_level,
            verdict=verdict,
            transition_operators=transition_operators,
            certificate_version="v2.3.1",
            axiom_compliance=self._axiom_compliance(),
            anomalies=self._detect_anomalies(records),
        )

    @staticmethod
    def _axiom_compliance() -> Dict[str, bool]:
        return {
            "no_canonical_sigma": True,
            "advisory_control_only": True,
            "projection_only_audit": True,
            "post_hoc_transition": True,
            "observer_only_l7": True,
        }

    @staticmethod
    def _ts(record: Dict[str, Any]) -> str:
        return str(record.get("ts") or record.get("timestamp") or "")

    @staticmethod
    def _classify_entropy_regime(rates: np.ndarray, trend: float, std: float) -> str:
        if std < 0.011:
            return "stable"
        if abs(trend) > 0.0065:
            return "rising" if trend > 0 else "shift"
        if std > 0.05:
            return "oscillating"
        return "shift"

    @staticmethod
    def _regime_aware_score(
        *,
        v_std: float,
        grounding_std: float,
        entropy_std: float,
        entropy_trend_abs: float,
        lyapunov_margin: float,
        lyapunov_descent_ratio: float,
        causal_consistency: float,
        transition_legality: float,
        regime: str,
    ) -> float:
        """Nonlinear piecewise fusion — regime selects dominant constraint."""
        if regime == "stable":
            score = 100.0
            score -= min(v_std * 70, 20)
            score -= min(grounding_std * 120, 22)
            score -= min(entropy_std * 150, 15)
            score += (lyapunov_descent_ratio - 0.5) * 25
            score += (causal_consistency - 0.7) * 30
            score += (transition_legality - 0.8) * 20
            score += 6
        elif regime == "oscillating":
            score = 78.0
            score -= min(entropy_std * 220, 30)
            score -= min(v_std * 90, 25)
            score += (causal_consistency - 0.65) * 45
            score += (transition_legality - 0.75) * 40
            score += lyapunov_margin * 15
            score -= 10
        elif regime == "rising":
            score = 72.0
            score -= min(entropy_trend_abs * 200, 25)
            score += (lyapunov_margin - 0.0) * 35
            score += (lyapunov_descent_ratio - 0.45) * 20
            score += (transition_legality - 0.8) * 25
        else:
            score = 85.0
            score -= min(v_std * 80, 22)
            score -= min(grounding_std * 140, 24)
            score -= min(entropy_trend_abs * 110, 12)
            score += (lyapunov_margin + 0.01) * 25
            score += (causal_consistency - 0.68) * 30
            score += (transition_legality - 0.82) * 28

        return max(0.0, min(100.0, score))

    @staticmethod
    def _risk_level(score: float) -> str:
        if score >= 82:
            return "low"
        if score >= 65:
            return "medium"
        return "high"

    @staticmethod
    def _detect_anomalies(records: List[Dict[str, Any]]) -> List[str]:
        anomalies: List[str] = []
        for record in records[-12:]:
            ts = record.get("ts") or record.get("timestamp") or "?"
            if float(record.get("entropy_rate") or 0.0) > 0.12:
                anomalies.append(f"high_entropy_rate@{ts}")
            if float(record.get("grounding_avg") or 1.0) < 0.40:
                anomalies.append(f"low_grounding@{ts}")
            if record.get("approved") and not record.get("graph_hash"):
                anomalies.append(f"missing_graph_hash@{ts}")
        return list(dict.fromkeys(anomalies))[:5]

    def _load_records(self, last_n: Optional[int]) -> List[Dict[str, Any]]:
        if not self.audit_path.exists():
            return []
        records: List[Dict[str, Any]] = []
        with self.audit_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records[-last_n:] if last_n else records

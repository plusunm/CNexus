"""
GTBS-L2 v0.3 — semantic coupling engine (correlation-based, not causal).

S9 Coupling ≠ Causation — all coupling signals are observational correlation only.
"""

from __future__ import annotations

import statistics
from typing import Sequence

from core.governance.l2.fusion.types import CrossStreamCouplingMatrix, CrossStreamField


def _pearson(a: Sequence[float], b: Sequence[float]) -> float:
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    xs = list(a[:n])
    ys = list(b[:n])
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs) ** 0.5
    den_y = sum((y - my) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return max(-1.0, min(1.0, num / (den_x * den_y)))


def _trend(values: Sequence[float], threshold: float = 0.03) -> str:
    if len(values) < 2:
        return "insufficient_data"
    delta = values[-1] - values[0]
    if delta > threshold:
        return "rising"
    if delta < -threshold:
        return "falling"
    return "stable"


class SemanticCouplingEngine:
    """Compute cross-stream coupling matrix and named coupling signals."""

    def analyze(self, field: CrossStreamField) -> CrossStreamField:
        shadow_div = field.shadow.get("divergence") or []
        shadow_align = field.shadow.get("alignment") or []
        ncr = field.singularity.get("ncr") or []
        rsci = field.singularity.get("rsci") or []
        cpx = field.ecology.get("cpx") or []
        odc = field.ecology.get("odc") or []
        rre = field.ecology.get("rre") or []
        recon = field.continuity.get("reconstruction_bias") or []

        sx_eco = _pearson(shadow_div, cpx) if cpx else _pearson(shadow_div, odc)
        sx_sin = _pearson(shadow_div, ncr)
        eco_sin = _pearson(cpx, rsci) if cpx and rsci else _pearson(odc, ncr)

        pairs = [abs(sx_eco), abs(sx_sin), abs(eco_sin)]
        global_idx = statistics.mean(pairs) if pairs else 0.0

        field.coupling_matrix = CrossStreamCouplingMatrix(
            shadow_x_ecology=round(sx_eco, 4),
            shadow_x_singularity=round(sx_sin, 4),
            ecology_x_singularity=round(eco_sin, 4),
            global_coupling_index=round(global_idx, 4),
        )
        field.coupling_signals = {
            "divergence_x_ncr": round(_pearson(shadow_div, ncr), 4),
            "cpx_x_rsci": round(_pearson(cpx, rsci), 4),
            "odc_x_narrative_closure": round(_pearson(odc, ncr), 4),
            "rre_x_reconstruction_bias": round(_pearson(rre, recon), 4),
            "alignment_x_rre": round(_pearson(shadow_align, rre), 4),
            "shadow_divergence_trend": _trend(shadow_div),
            "cpx_trend": _trend(cpx),
            "rsci_trend": _trend(rsci),
            "ncr_trend": _trend(ncr),
        }
        return field

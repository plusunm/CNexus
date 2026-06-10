"""
GTBS-L2.5 — compress cross-stream coupling field into latent attractor geometry.

Observation-only heuristics — S11/S12: no control leakage, attractor ≠ decision.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Sequence

from core.governance.l2.attractor.types import AttractorField, LatentAttractorState
from core.governance.l2.fusion.types import CrossStreamCouplingMatrix, GTBSL2FusionReport


def _latest(series: Sequence[float]) -> float:
    return float(series[-1]) if series else 0.0


def _mean(series: Sequence[float]) -> float:
    return float(statistics.mean(series)) if series else 0.0


def _coupling_delta(matrix: CrossStreamCouplingMatrix, trend_signals: dict[str, Any]) -> float:
    gci = matrix.global_coupling_index
    cpx_dir = trend_signals.get("cpx_direction", "stable")
    rsci_dir = trend_signals.get("rsci_trend") or trend_signals.get("rsci_direction", "stable")
    delta = 0.0
    if cpx_dir == "rising":
        delta += 0.04
    if rsci_dir == "rising":
        delta += 0.04
    return gci + delta


def _basin_depth(ncr: float, cpx: float, rsci: float, odc: float) -> float:
    return min(1.0, 0.25 * ncr + 0.30 * cpx + 0.25 * rsci + 0.20 * odc)


def _classify_stability(
    *,
    rre: float,
    rsci: float,
    ncr: float,
    cpx: float,
    odc: float,
    coupling_density_delta: float,
) -> str:
    if rre >= 0.55 and rsci < 0.35:
        return "stable"
    if rsci >= 0.45 and ncr >= 0.40:
        return "metastable"
    if cpx >= 0.50 and odc >= 0.45:
        return "collapsing"
    if coupling_density_delta > 0.08:
        return "emerging"
    return "metastable"


def _global_entropy(strengths: Sequence[float]) -> float:
    if not strengths:
        return 1.0
    total = sum(max(s, 0.01) for s in strengths)
    probs = [max(s, 0.01) / total for s in strengths]
    entropy = -sum(p * math.log(p + 1e-9) for p in probs)
    max_entropy = math.log(len(probs)) if len(probs) > 1 else 1.0
    return min(1.0, entropy / max_entropy) if max_entropy > 0 else 0.0


def _field_regime(
    attractors: Sequence[LatentAttractorState],
    global_entropy: float,
    coupling_density: float,
) -> str:
    strong = [a for a in attractors if a.strength >= 0.55]
    if coupling_density >= 0.60 and len(strong) >= 2:
        return "locked"
    if coupling_density >= 0.45 and len(strong) >= 1:
        return "clustered"
    if any(a.stability_class == "emerging" for a in attractors):
        return "bifurcating"
    if global_entropy >= 0.65 or coupling_density < 0.25:
        return "diffuse"
    return "clustered"


def _narrative_hint(stability_class: str, attractor_type: str) -> str:
    hints = {
        ("stable", "behavioral narrative basin"): "行为叙事盆地趋于稳定，跨流耦合维持低波动结构。",
        ("metastable", "self-reinforcing narrative basin"): "自强化叙事盆地处于亚稳态，需持续观测。",
        ("collapsing", "instability attractor basin"): "不稳定性吸引子信号增强，结构压缩压力上升。",
        ("emerging", "behavioral narrative basin"): "行为吸引子种子正在形成，耦合密度快速上升。",
    }
    return hints.get(
        (stability_class, attractor_type),
        f"latent {attractor_type} — {stability_class}（heuristic label，非 action signal）",
    )


def _build_attractor(
    *,
    attractor_id: str,
    attractor_type: str,
    seed_strength: float,
    basin: float,
    openness: float,
    shadow_pull: float,
    ecology_pull: float,
    singularity_pull: float,
    stability_class: str,
) -> LatentAttractorState:
    strength = min(1.0, max(0.0, seed_strength * (0.6 + 0.4 * basin)))
    return LatentAttractorState(
        attractor_id=attractor_id,
        strength=round(strength, 4),
        basin_depth=round(basin, 4),
        openness_radius=round(openness, 4),
        shadow_pull=round(shadow_pull, 4),
        ecology_pull=round(ecology_pull, 4),
        singularity_pull=round(singularity_pull, 4),
        stability_class=stability_class,
        narrative_hint=_narrative_hint(stability_class, attractor_type),
        attractor_type=attractor_type,
    )


def compress_field_to_latent(
    fusion_report: GTBSL2FusionReport,
    trend_signals: dict[str, Any] | None = None,
) -> AttractorField:
    """
    Step 1 coupling compression → Step 2 basin estimation → Step 3 stability classification.
    """
    trend_signals = trend_signals or {}
    raw = fusion_report.raw_field or {}
    ecology = raw.get("ecology") or {}
    singularity = raw.get("singularity") or {}
    shadow = raw.get("shadow") or {}

    ncr = _latest(singularity.get("ncr") or [])
    cpx = _latest(ecology.get("cpx") or [])
    rsci = _latest(singularity.get("rsci") or [])
    odc = _latest(ecology.get("odc") or [])
    rre = _latest(ecology.get("rre") or [])

    cm_raw = fusion_report.coupling_matrix or {}
    matrix = CrossStreamCouplingMatrix(
        shadow_x_ecology=float(cm_raw.get("shadow_x_ecology", 0.0)),
        shadow_x_singularity=float(cm_raw.get("shadow_x_singularity", 0.0)),
        ecology_x_singularity=float(cm_raw.get("ecology_x_singularity", 0.0)),
        global_coupling_index=float(cm_raw.get("global_coupling_index", 0.0)),
    )

    coupling_delta = _coupling_delta(matrix, {**trend_signals, **(fusion_report.coupling_signals or {})})
    basin = _basin_depth(ncr, cpx, rsci, odc)
    openness = min(1.0, max(0.0, 1.0 - basin + odc * 0.3))
    stability = _classify_stability(
        rre=rre,
        rsci=rsci,
        ncr=ncr,
        cpx=cpx,
        odc=odc,
        coupling_density_delta=coupling_delta - matrix.global_coupling_index,
    )

    seeds = [
        ("A-BEH", "behavioral narrative basin", abs(matrix.shadow_x_ecology), 0.45, 0.45, 0.10),
        ("A-INS", "instability attractor basin", abs(matrix.ecology_x_singularity), 0.15, 0.40, 0.45),
        ("A-SELF", "self-reinforcing narrative basin", abs(matrix.shadow_x_singularity), 0.40, 0.20, 0.40),
    ]

    attractors: list[LatentAttractorState] = []
    for idx, (aid, atype, seed, sp, ep, sip) in enumerate(seeds, start=1):
        if seed < 0.05 and not raw.get("days"):
            continue
        att_id = f"{aid}-{idx:02d}"
        attractors.append(
            _build_attractor(
                attractor_id=att_id,
                attractor_type=atype,
                seed_strength=seed,
                basin=basin,
                openness=openness,
                shadow_pull=sp,
                ecology_pull=ep,
                singularity_pull=sip,
                stability_class=stability,
            )
        )

    if not attractors and not raw.get("days"):
        empty = LatentAttractorState(
            attractor_id="A-EMPTY",
            strength=0.0,
            basin_depth=0.0,
            openness_radius=1.0,
            shadow_pull=0.0,
            ecology_pull=0.0,
            singularity_pull=0.0,
            stability_class="emerging",
            narrative_hint="跨流数据不足，无法推断 latent attractor 结构。",
            attractor_type="unresolved",
        )
        return AttractorField(
            attractors=(empty,),
            global_entropy=1.0,
            coupling_density=0.0,
            field_regime="diffuse",
        )

    strengths = [a.strength for a in attractors]
    entropy = _global_entropy(strengths)
    density = matrix.global_coupling_index
    regime = _field_regime(attractors, entropy, density)

    return AttractorField(
        attractors=tuple(attractors),
        global_entropy=round(entropy, 4),
        coupling_density=round(density, 4),
        field_regime=regime,
    )

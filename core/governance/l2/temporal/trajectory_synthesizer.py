"""
GTBS-L2 v0.2 — trajectory synthesis (drift / stability / pressure narratives).

S6 No Temporal Governance — describes how the system became what it is;
does not predict, recommend, or intervene.
"""

from __future__ import annotations

from typing import Any

from core.governance.l2.language import classify_openness, classify_reality_coupling
from core.governance.l2.temporal.types import L2TemporalWindow

_SOURCE_LABELS = {
    "reality_driven": "现实驱动",
    "user_driven": "用户交互驱动",
    "narrative_driven": "叙事驱动",
    "self_reinforcing": "自强化循环",
}


class TrajectorySynthesizer:
    """Synthesize three temporal semantic tracks from L2TemporalWindow."""

    def synthesize(self, window: L2TemporalWindow) -> dict[str, str]:
        if not window.snapshots:
            return {
                "drift_story": "时间窗内暂无足够观测数据，无法合成漂移叙事。",
                "stability_story": "时间窗内暂无足够观测数据，无法合成稳定性叙事。",
                "pressure_story": "时间窗内暂无足够观测数据，无法合成压力叙事。",
            }

        agg = window.aggregated
        cont = agg.get("continuity_evolution", {})
        eco = agg.get("ecology_shift", {})
        div = agg.get("divergence_trend", {})
        shape = agg.get("shaping_drift", {})

        return {
            "drift_story": self._drift_narrative(window, cont, eco, div),
            "stability_story": self._stability_narrative(window, cont, div),
            "pressure_story": self._pressure_narrative(window, eco, shape),
        }

    def trend_signals(self, window: L2TemporalWindow) -> dict[str, Any]:
        cont = window.aggregated.get("continuity_evolution", {})
        eco = window.aggregated.get("ecology_shift", {})
        openness = cont.get("openness") or []
        basin = cont.get("identity_basin_depth") or []
        reality = cont.get("reality_coupling") or []

        openness_delta = (openness[-1] - openness[0]) if len(openness) >= 2 else 0.0
        basin_delta = (basin[-1] - basin[0]) if len(basin) >= 2 else 0.0

        return {
            "openness_delta": round(openness_delta, 4),
            "openness_direction": cont.get("openness_direction", "insufficient_data"),
            "rcs_trend": cont.get("reality_direction", "insufficient_data"),
            "reality_coupling_delta": round(
                (reality[-1] - reality[0]) if len(reality) >= 2 else 0.0, 4
            ),
            "attractor_depth_delta": round(basin_delta, 4),
            "cpx_direction": eco.get("cpx_direction", "insufficient_data"),
            "odc_direction": eco.get("odc_direction", "insufficient_data"),
            "ncr_series": eco.get("ncr") or [],
            "rsci_series": eco.get("rsci") or [],
        }

    def _drift_narrative(
        self,
        window: L2TemporalWindow,
        cont: dict[str, Any],
        eco: dict[str, Any],
        div: dict[str, Any],
    ) -> str:
        openness = cont.get("openness") or []
        o_start = classify_openness(openness[0]) if openness else "unknown"
        o_end = classify_openness(openness[-1]) if openness else "unknown"
        ncr = eco.get("ncr") or []
        ncr_rising = len(ncr) >= 2 and ncr[-1] > ncr[0] + 0.05
        basin = cont.get("identity_basin_depth") or []
        basin_deepening = len(basin) >= 2 and basin[-1] > basin[0] + 0.03

        lines = [
            f"系统在过去 {window.window_days} 天内逐渐从：",
            f"- openness {o_start}",
            f"→ openness {o_end}",
            "",
            "表现为：",
        ]
        if ncr_rising:
            lines.append("- narrative closure rate（NCR）呈上升趋势")
        else:
            lines.append("- narrative closure 信号相对稳定")
        if basin_deepening:
            lines.append("- attractor basin（身份盆地）加深")
        if div.get("direction") == "falling":
            lines.append("- proposal-reality 对齐度下降")
        lines.append("（纯观测叙事 — 非 governance 建议）")
        return "\n".join(lines)

    def _stability_narrative(
        self,
        window: L2TemporalWindow,
        cont: dict[str, Any],
        div: dict[str, Any],
    ) -> str:
        reality = cont.get("reality_coupling") or []
        recon = cont.get("reconstruction_bias") or []
        r_start = classify_reality_coupling(reality[0]) if reality else "unknown"
        r_end = classify_reality_coupling(reality[-1]) if reality else "unknown"
        recon_stable = len(recon) >= 2 and abs(recon[-1] - recon[0]) < 0.05

        lines = [
            "系统在连续性维度表现出：",
            "",
            f"- reality coupling：{r_start} → {r_end}",
        ]
        if recon_stable:
            lines.append("- reconstruction bias 稳定收敛")
        else:
            lines.append("- reconstruction bias 存在可观察波动")
        if div.get("direction") == "stable":
            lines.append("- proposal-reality 对齐整体趋于稳定 attractor")
        elif div.get("direction") == "rising":
            lines.append("- proposal-reality 对齐呈改善趋势")
        else:
            lines.append("- proposal-reality 对齐存在漂移")
        lines.append("（描述性信号 — 非控制输出）")
        return "\n".join(lines)

    def _pressure_narrative(
        self,
        window: L2TemporalWindow,
        eco: dict[str, Any],
        shape: dict[str, Any],
    ) -> str:
        cpx = eco.get("cpx") or []
        rsci = eco.get("rsci") or []
        cpx_rising = eco.get("cpx_direction") == "rising" or (
            len(cpx) >= 2 and cpx[-1] > cpx[0] + 0.04
        )
        rsci_rising = len(rsci) >= 2 and rsci[-1] > rsci[0] + 0.04
        sr = shape.get("self_reinforcing_risk") or []
        sr_rising = len(sr) >= 2 and sr[-1] > sr[0] + 0.05

        lines = ["检测到："]
        if cpx_rising:
            lines.append("- continuity pressure（CPX）持续增长")
        if rsci_rising or sr_rising:
            lines.append("- recursive self-conditioning（RSCI）上升")
        if not cpx_rising and not rsci_rising and not sr_rising:
            lines.append("- 结构压力指标未见显著持续上升")
        lines.extend(
            [
                "",
                "说明系统可能正在进入：结构压缩阶段（heuristic observational label）。",
                "（S6/S7：非 policy signal，不参与 runtime/CDG/GTBS）",
            ]
        )
        return "\n".join(lines)

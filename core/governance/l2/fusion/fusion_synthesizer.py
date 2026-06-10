"""
GTBS-L2 v0.3 — cross-stream fusion narrative synthesis.

S8 No Cross-Stream Governance | S10 Observational Closure Only
"""

from __future__ import annotations

from core.governance.l2.fusion.types import CrossStreamField, GTBSL2FusionReport


class FusionSynthesizer:
    """Synthesize field-level fusion narratives from coupled cross-stream field."""

    def synthesize(self, field: CrossStreamField) -> GTBSL2FusionReport:
        if not field.days:
            empty = "时间窗内跨流数据不足，无法合成融合叙事。"
            return GTBSL2FusionReport(
                time_range=f"{field.start_ts} → {field.end_ts}",
                fusion_summaries={
                    "drift_convergence": empty,
                    "coupled_stability": empty,
                    "meta_consistency": empty,
                },
                coupling_matrix=field.coupling_matrix.to_dict(),
                coupling_signals=field.coupling_signals,
                risk_surface={
                    "reinforcement_loop_risk": "insufficient_data",
                    "cross_stream_lock_in": "insufficient_data",
                },
                metadata=_metadata(field),
            )

        drift = self._drift_convergence(field)
        stability = self._coupled_stability(field)
        meta = self._meta_consistency(field)
        risk = self._risk_surface(field)

        return GTBSL2FusionReport(
            time_range=f"{field.start_ts} → {field.end_ts} ({field.window_days}d)",
            fusion_summaries={
                "drift_convergence": drift,
                "coupled_stability": stability,
                "meta_consistency": meta,
            },
            coupling_matrix=field.coupling_matrix.to_dict(),
            coupling_signals=field.coupling_signals,
            risk_surface=risk,
            raw_field={
                "days": field.days,
                "shadow": field.shadow,
                "ecology": field.ecology,
                "singularity": field.singularity,
            },
            metadata=_metadata(field),
        )

    def _drift_convergence(self, field: CrossStreamField) -> str:
        sig = field.coupling_signals
        div_t = sig.get("shadow_divergence_trend", "stable")
        cpx_t = sig.get("cpx_trend", "stable")
        rsci_t = sig.get("rsci_trend", "stable")
        ncr_t = sig.get("ncr_trend", "stable")

        rising = sum(1 for t in (div_t, cpx_t, rsci_t, ncr_t) if t == "rising")
        lines = [
            "三个观测流显示出以下漂移趋势（相关性观察，非因果断言）：",
            "",
            f"- shadow divergence：{div_t}",
            f"- ecology CPX：{cpx_t}",
            f"- singularity RSCI：{rsci_t}",
            f"- singularity NCR：{ncr_t}",
            "",
        ]
        if rising >= 2:
            lines.extend(
                [
                    "多条轨道呈同向上升，说明系统可能进入：",
                    "cross-stream reinforcement phase（跨流 reinforcement 相，heuristic label）。",
                ]
            )
        else:
            lines.append("跨流漂移方向未呈现强一致性收敛。")
        lines.append("（S9：coupling ≠ causation；S8：非 governance 信号）")
        return "\n".join(lines)

    def _coupled_stability(self, field: CrossStreamField) -> str:
        sig = field.coupling_signals
        align_rre = float(sig.get("alignment_x_rre", 0.0))
        rre_recon = float(sig.get("rre_x_reconstruction_bias", 0.0))
        matrix = field.coupling_matrix

        lines = [
            "尽管局部波动可能存在，",
            "",
            f"- ecology RRE ↔ shadow alignment 弱耦合相关：{align_rre:.2f}",
            f"- RRE ↔ reconstruction bias：{rre_recon:.2f}",
            f"- shadow×ecology coupling：{matrix.shadow_x_ecology:.2f}",
            "",
        ]
        if abs(align_rre) >= 0.4 or matrix.global_coupling_index >= 0.45:
            lines.append("部分跨流指标表现出弱耦合稳定性。")
            lines.append("系统未观察到失稳 attractor collapse 的强一致信号（heuristic）。")
        else:
            lines.append("跨流稳定性耦合较弱，各观测层相对独立演化。")
        lines.append("（描述性叙事 — 非控制输出）")
        return "\n".join(lines)

    def _meta_consistency(self, field: CrossStreamField) -> str:
        gci = field.coupling_matrix.global_coupling_index
        acd_series = field.ecology.get("acd") or []
        acd_end = acd_series[-1] if acd_series else 0.0

        lines = [
            f"跨流一致性指数（global coupling index）：{gci:.2f}",
            "",
        ]
        if gci >= 0.5:
            lines.append("observability layers 正在形成共享结构空间（heuristic）。")
        elif gci >= 0.3:
            lines.append("observability layers 存在部分结构共振，但未完全对齐。")
        else:
            lines.append("observability layers  largely 独立，共享结构空间尚未形成。")

        if acd_end >= 0.55:
            lines.append("检测到 attractor 集中趋势 — 需持续观察（非 enforcement）。")
        else:
            lines.append("尚未出现单一 dominating attractor 的强证据。")
        lines.append("（S10：observational closure only）")
        return "\n".join(lines)

    def _risk_surface(self, field: CrossStreamField) -> dict[str, str]:
        sig = field.coupling_signals
        gci = field.coupling_matrix.global_coupling_index
        div_ncr = abs(float(sig.get("divergence_x_ncr", 0.0)))
        cpx_rsci = abs(float(sig.get("cpx_x_rsci", 0.0)))

        if div_ncr >= 0.55 and cpx_rsci >= 0.5:
            loop_risk = "elevated"
        elif div_ncr >= 0.35 or cpx_rsci >= 0.35:
            loop_risk = "moderate"
        else:
            loop_risk = "low"

        if gci >= 0.6 and sig.get("cpx_trend") == "rising":
            lock_in = "elevated"
        elif gci >= 0.45:
            lock_in = "moderate"
        else:
            lock_in = "low"

        return {
            "reinforcement_loop_risk": loop_risk,
            "cross_stream_lock_in": lock_in,
        }


def _metadata(field: CrossStreamField) -> dict:
    return {
        "l2_layer": "semantic_alignment_fusion",
        "read_only": True,
        "instrumentation_only": True,
        "no_cross_stream_governance": True,
        "coupling_not_causation": True,
        "observational_closure_only": True,
        "day_count": len(field.days),
    }

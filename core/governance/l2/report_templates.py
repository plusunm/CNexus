"""GTBS-L2 narrative templates (human-facing; descriptive only — S4)."""

from __future__ import annotations

DIVERGENCE_TEMPLATE = """系统检测到结构性差异信号。
当前 proposal 与 reality 的一致性为 {alignment:.2f}。
{interpretation}"""

SHAPING_TEMPLATE = """系统塑形来源分析：
主导来源：{primary_source}
风险倾向：{risk_note}"""

CONTINUITY_TEMPLATE = """连续性结构状态：
现实耦合：{reality_state}
叙事开放性：{openness_state}
整体稳定性：{stability_note}"""

ECOLOGY_TEMPLATE = """生态结构观察：
吸引子状态：{attractor_state}
系统健康度：{health_summary}"""

EMPTY_SNAPSHOT_NOTE = """暂无可用观测快照。
请先运行 staging 并积累 observability 流（gtbs_shadow / ecology / singularity）。"""

"""Cognitive Synthesis Engine v1 — Σ_exec + runtime signals → actionable cognition."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from core.cse.snapshot import get_snapshot_store
from core.cse.types import (
    ActionBlock,
    CognitiveOutput,
    DiscoveryBlock,
    InsightBlock,
    TextBlock,
)


def _insight(
    title: str,
    description: str,
    *,
    confidence: float,
    why: str,
    source: str,
    evidence: Optional[List[str]] = None,
) -> InsightBlock:
    return InsightBlock(
        title=title,
        description=description,
        confidence=confidence,
        why=why,
        source=source,
        evidence=evidence or [],
    )


class CognitiveSynthesisEngine:
    """Structured compression — pattern-first, LLM optional (v1 is deterministic)."""

    def synthesize_live(
        self,
        *,
        runtime: Any,
        logs: List[Dict[str, Any]],
        execution_status: Dict[str, Any],
        mind_overview: Optional[Dict[str, Any]] = None,
        trace_events: Optional[List[Dict[str, Any]]] = None,
        window: int = 200,
    ) -> CognitiveOutput:
        logs = logs[-window:]
        trace_events = trace_events or []
        cfg = getattr(runtime, "config", {}) or {}
        scheduler = execution_status.get("inference_scheduler") or {}
        compute = execution_status.get("compute_profile") or cfg.get("compute_profile") or {}
        compute_policy = execution_status.get("compute_policy") or cfg.get("compute_policy") or {}
        envelope = execution_status.get("runtime_envelope") or cfg.get("runtime_envelope") or "auto"
        embedding = execution_status.get("embedding") or {}

        out = CognitiveOutput(
            generated_at=datetime.now(timezone.utc).isoformat(),
            window_size=len(logs) + len(trace_events),
            mode="live",
        )

        categories = Counter(str(e.get("category") or "unknown") for e in logs)
        levels = Counter(str(e.get("level") or "info") for e in logs)
        top_cats = categories.most_common(3)
        if top_cats:
            cat_text = "、".join(f"{name}×{count}" for name, count in top_cats)
            out.summary.append(
                TextBlock(
                    text=f"最近 {len(logs)} 条运行事件中，活跃类别为 {cat_text}。",
                    confidence=0.85,
                    source="log_segmentation",
                )
            )

        if mind_overview:
            system = mind_overview.get("system") or {}
            health = system.get("health_label") or "—"
            gov = system.get("governance_label") or "—"
            out.summary.append(
                TextBlock(
                    text=f"认知健康 {health}；治理状态 {gov}。",
                    confidence=0.8,
                    source="mind_overview",
                )
            )
            changes = (mind_overview.get("feeds") or {}).get("changes") or []
            if changes:
                out.summary.append(
                    TextBlock(
                        text=f"近期变化：{changes[0][:120]}",
                        confidence=0.75,
                        source="mind_feed",
                    )
                )

        cache_hits = int(scheduler.get("cache_hits") or 0)
        cache_misses = int(scheduler.get("cache_misses") or 0)
        total_cache = cache_hits + cache_misses
        if total_cache > 0:
            hit_rate = cache_hits / total_cache
            out.patterns.append(
                TextBlock(
                    text=(
                        f"Embedding 缓存命中率 {hit_rate:.0%}（命中 {cache_hits} / 未命中 {cache_misses}）。"
                    ),
                    confidence=0.9,
                    source="scheduler_cache",
                )
            )
            if hit_rate < 0.5:
                out.insights.append(
                    _insight(
                        "缓存未命中偏高",
                        "memory recall 路径可能重复触发 embed 计算，拉高本地推理负载。",
                        confidence=0.82,
                        why=f"观测到命中率 {hit_rate:.0%}，低于稳定阈值 50%。",
                        source="cache_anomaly",
                        evidence=[f"cache 命中 {cache_hits}，未命中 {cache_misses}"],
                    )
                )
                out.actions.append(
                    ActionBlock(
                        action="enable_aggressive_embed_cache",
                        priority=0.88,
                        rationale="提高 embed cache 命中可显著降低本地推理压力。",
                        category="scheduler",
                        impact=0.85,
                        reversibility=0.92,
                        why="cache 策略可回滚，且不破坏 Σ_exec 连续性。",
                    )
                )

        max_conc = int(scheduler.get("max_concurrent") or 1)
        embed_strategy = str(scheduler.get("embed_strategy") or "serial")
        if scheduler.get("enabled"):
            out.patterns.append(
                TextBlock(
                    text=(
                        f"推理调度：concurrency={max_conc}，embed={embed_strategy}，"
                        f"envelope={envelope}。"
                    ),
                    confidence=0.88,
                    source="scheduler_policy",
                )
            )
            out.rules.append(
                TextBlock(
                    text="单车道 + cache-first embed 是 safe_baseline 下的稳定结构。",
                    confidence=0.8,
                    source="invariant",
                )
            )

        ram = compute.get("ram_gb")
        if ram:
            out.insights.append(
                _insight(
                    "算力画像已绑定策略",
                    f"RAM≈{ram}GB{' + GPU' if compute.get('gpu') else ''}，当前 envelope={envelope}。",
                    confidence=0.78,
                    why="ComputeProfile 驱动 Scheduler/CSE 行为，非硬编码硬件上限。",
                    source="compute_profile",
                )
            )

        cse_mode = cfg.get("cse_mode") or compute_policy.get("cse_mode")
        if cse_mode == "batch":
            out.insights.append(
                _insight(
                    "CSE batch 模式",
                    "认知合成在治理/空闲周期刷新，降低并发推理压力。",
                    confidence=0.76,
                    why="safe_baseline envelope 下优先稳定性而非实时合成。",
                    source="cse_mode",
                )
            )

        active_mode = str(embedding.get("active_mode") or "")
        if active_mode == "hash":
            embed_evidence = [
                str(e.get("message") or "")[:100]
                for e in logs
                if "embed" in str(e.get("category") or "").lower()
                or "embed" in str(e.get("message") or "").lower()
            ][:3]
            out.insights.append(
                _insight(
                    "Embedding 走 hash fallback",
                    "语义 recall 质量可能低于 Ollama embed，但 latency 更低。",
                    confidence=0.84,
                    why="Ollama embed 不可用或主动降级时触发 fallback 路径。",
                    source="embed_path",
                    evidence=embed_evidence or ["active_mode=hash"],
                )
            )
            out.actions.append(
                ActionBlock(
                    action="restore_ollama_embedding",
                    priority=0.72,
                    rationale="本地 Ollama embed 可用时优先恢复语义向量路径。",
                    category="model",
                    impact=0.7,
                    reversibility=0.88,
                    why="恢复 Ollama embed 可通过环境变量或 provider 健康检查回退。",
                )
            )

        error_logs = [e for e in logs if str(e.get("level") or "") == "error"]
        if error_logs:
            out.summary.append(
                TextBlock(
                    text=f"窗口内检测到 {len(error_logs)} 条 error 级事件，需优先排查。",
                    confidence=0.9,
                    source="error_budget",
                )
            )

        ir_count = sum(1 for e in logs if e.get("category") == "ir")
        if ir_count:
            out.patterns.append(
                TextBlock(
                    text=f"IR Path B 执行 {ir_count} 次 — Σ_exec 结构化 trace 可用于回放验证。",
                    confidence=0.8,
                    source="ir_usage",
                )
            )

        if trace_events:
            out.summary.append(
                TextBlock(
                    text=f"Σ_exec 存档 {len(trace_events)} 条 trace 可供压缩分析。",
                    confidence=0.77,
                    source="trace_store",
                )
            )

        chat_full = bool(cfg.get("chat_default_full_cognitive_loop"))
        if chat_full and envelope == "safe_baseline":
            out.actions.append(
                ActionBlock(
                    action="defer_full_cognitive_loop",
                    priority=0.91,
                    rationale="safe_baseline 下 full loop 与单车道调度存在资源竞争。",
                    category="runtime",
                    impact=0.9,
                    reversibility=0.95,
                    why="可通过 runtime 配置关闭 full loop，无需改动 Kernel 结构。",
                )
            )

        if not out.actions:
            out.actions.append(
                ActionBlock(
                    action="continue_monitoring",
                    priority=0.4,
                    rationale="当前未发现高优先级结构异常，保持观察即可。",
                    category="observe",
                    impact=0.2,
                    reversibility=1.0,
                    why="无配置变更，仅延续当前观测窗口。",
                )
            )

        out.actions.sort(key=lambda a: a.priority, reverse=True)
        self._enrich_value_layer(out, logs)
        get_snapshot_store().commit(out)
        return out

    def _enrich_value_layer(self, out: CognitiveOutput, logs: List[Dict[str, Any]]) -> None:
        store = get_snapshot_store()
        prev_fp = store.last_fingerprint()
        now = out.generated_at

        out.experiences = [
            TextBlock(text=rule.text, confidence=rule.confidence, source=f"experience:{rule.source}")
            for rule in out.rules
        ]
        for pat in out.patterns:
            if pat.confidence >= 0.85:
                out.experiences.append(
                    TextBlock(
                        text=f"经验：{pat.text}",
                        confidence=pat.confidence * 0.95,
                        source=f"experience:{pat.source}",
                    )
                )

        log_snippets = [
            str(e.get("message") or "")[:120]
            for e in logs[-5:]
            if e.get("message")
        ]

        insight_titles: set[str] = set()
        for ins in out.insights:
            if not ins.evidence and log_snippets:
                ins.evidence = log_snippets[:2]
            ins.novelty = self._novelty(("insight", ins.title), prev_fp)
            insight_titles.add(ins.title.strip().lower())

        for pat in out.patterns:
            novelty = self._novelty(("pattern", pat.text[:80]), prev_fp)
            if novelty >= 0.65:
                out.discoveries.append(
                    self._discovery_from_pattern(pat, novelty, now, log_snippets)
                )

        for ins in out.insights:
            if ins.novelty < 0.65 and not (not prev_fp and ins.confidence >= 0.8):
                continue
            novelty = max(ins.novelty, 0.68 if not prev_fp else ins.novelty)
            out.discoveries.append(
                DiscoveryBlock(
                    id=self._discovery_id(f"novel:{ins.title}"),
                    title=f"相较上周期新出现：{ins.title}",
                    description=ins.why or f"首次在本观察窗口识别到「{ins.title}」",
                    confidence=ins.confidence,
                    novelty=novelty,
                    why="与历史合成快照对比，该信号此前未出现或显著增强。",
                    evidence=ins.evidence,
                    source=f"novel_signal:{ins.source}",
                    first_seen_at=now,
                )
            )

        out.discoveries = self._dedupe_discoveries(out.discoveries, insight_titles)
        out.discoveries.sort(key=lambda d: d.novelty * d.confidence, reverse=True)
        out.discoveries = out.discoveries[:6]
        out.narrative = self._build_narrative(out)

    @staticmethod
    def _novelty(key: Tuple[str, str], prev_fp: Set[Tuple[str, str]]) -> float:
        if not prev_fp:
            return 0.55
        return 0.88 if key not in prev_fp else 0.12

    @staticmethod
    def _discovery_id(title: str) -> str:
        return hashlib.sha1(title.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _discovery_from_pattern(
        pat: TextBlock,
        novelty: float,
        seen_at: str,
        evidence: List[str],
    ) -> DiscoveryBlock:
        return DiscoveryBlock(
            id=CognitiveSynthesisEngine._discovery_id(pat.text[:40]),
            title="新规律" if novelty >= 0.8 else "规律变化",
            description=pat.text,
            confidence=pat.confidence,
            novelty=novelty,
            why="与上一窗口合成结果对比，该规律首次出现或发生变化。",
            evidence=evidence[:3],
            source=f"novel_pattern:{pat.source}",
            first_seen_at=seen_at,
        )

    @staticmethod
    def _dedupe_discoveries(
        discoveries: List[DiscoveryBlock],
        insight_titles: set[str],
    ) -> List[DiscoveryBlock]:
        seen: set[str] = set()
        out: List[DiscoveryBlock] = []
        for disc in discoveries:
            key = disc.description.strip().lower()[:96]
            base_title = disc.title.replace("相较上周期新出现：", "").strip().lower()
            if base_title in insight_titles and disc.description.strip().lower() in seen:
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(disc)
        return out

    @staticmethod
    def _build_narrative(out: CognitiveOutput) -> str:
        """One executive paragraph — each clause from a different layer, no copy-paste."""
        if not out.summary and not out.insights and not out.actions:
            return "系统仍在积累运行数据，暂无足够信息生成价值总结。"

        clauses: List[str] = []

        if out.summary:
            clauses.append(out.summary[0].text.rstrip("。"))

        if len(out.summary) > 1:
            clauses.append(out.summary[1].text.rstrip("。"))
        elif out.patterns:
            clauses.append(f"规律层面：{out.patterns[0].text.rstrip('。')}")

        top_insight = max(
            out.insights,
            key=lambda i: i.confidence * (0.5 + i.novelty),
            default=None,
        )
        if top_insight:
            angle = top_insight.why or top_insight.description
            clauses.append(f"解读：{top_insight.title}——{angle.rstrip('。')}")

        novel = [d for d in out.discoveries if d.novelty >= 0.65]
        if novel:
            d = novel[0]
            clauses.append(f"新变化：{d.description.rstrip('。')}")

        top_action = next((a for a in out.actions if a.action != "continue_monitoring"), None)
        if top_action:
            clauses.append(f"建议：{top_action.rationale.rstrip('。')}")

        if len(clauses) <= 1 and top_insight and top_action:
            return f"{clauses[0]}。{top_action.rationale.rstrip('。')}。" if clauses else top_action.rationale

        return "。".join(clauses[:4]) + "。"

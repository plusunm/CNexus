"""Self-reflection — metacognition over AuditLog + vector-indexed cognitive assets."""

from __future__ import annotations

import os
import re
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple


LlmFn = Callable[[str, str], Optional[str]]


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _parse_timestamp(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return time.time()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return time.time()


def _domain_for_event(event: str, data: dict) -> str:
    event = str(event or "")
    if event in ("memory.block", "memory.clear"):
        label = str(data.get("label") or "")
        if label in ("code_class", "code_function"):
            return "code"
        if label in ("vision_component", "image"):
            return "image"
        return "memory"
    if event in ("asset.upload", "asset.received"):
        kind = str(data.get("type") or "")
        return "image" if kind == "image" else "code" if kind == "code" else "asset"
    if event == "trace.cycle":
        return "dialogue"
    if event.startswith("peer.") or event.startswith("p2p."):
        return "network"
    if event in ("rem.sleep", "state.checkpoint"):
        return "consolidation"
    if event.startswith("reflection."):
        return "metacognition"
    return "other"


DEFAULT_QUESTION = (
    "根据最近一段时间的 AuditLog，总结我的认知偏差是什么？"
    "我是否有过度关注某些领域的倾向？"
)


class SelfReflectionEngine:
    """
    Metacognitive layer: pattern analysis over audit trail + optional LLM synthesis.
    Answers questions only a system with both data and thinking traces can address.
    """

    REFLECTABLE_EVENTS = frozenset({
        "memory.block",
        "trace.cycle",
        "asset.upload",
        "asset.received",
        "rem.sleep",
        "reflection.meta",
        "peer.handshake",
        "peer.sync",
        "peer.negotiate",
    })

    def __init__(
        self,
        audit_log=None,
        *,
        vector_index=None,
        audit_fn: Optional[Callable[[str, dict], Optional[str]]] = None,
        enabled: Optional[bool] = None,
    ):
        self.audit_log = audit_log
        self.vector_index = vector_index
        self.audit_fn = audit_fn
        self.enabled = enabled if enabled is not None else _env_truthy("CNEXUS_REFLECT_ENABLE", True)
        self.default_limit = _env_int("CNEXUS_REFLECT_LIMIT", 100)
        self.default_window_days = _env_int("CNEXUS_REFLECT_WINDOW_DAYS", 7)
        self.last_report: Dict[str, Any] = {}

    def _iter_entries(self) -> List[dict]:
        if not self.audit_log:
            return []
        reader = getattr(self.audit_log, "iter_entries", None)
        if not callable(reader):
            reader = getattr(self.audit_log, "_read_all_entries", None)
        return list(reader()) if callable(reader) else []

    def recent_entries(
        self,
        *,
        limit: Optional[int] = None,
        window_days: Optional[int] = None,
    ) -> List[dict]:
        limit = max(1, int(limit or self.default_limit))
        window_days = int(window_days if window_days is not None else self.default_window_days)
        rows = self._iter_entries()
        if window_days > 0:
            cutoff = time.time() - window_days * 86400
            rows = [row for row in rows if _parse_timestamp(row.get("timestamp")) >= cutoff]
        return rows[-limit:]

    def analyze_patterns(self, entries: List[dict]) -> Dict[str, Any]:
        event_counts: Counter[str] = Counter()
        domain_counts: Counter[str] = Counter()
        keyword_counts: Counter[str] = Counter()
        asset_filenames: Counter[str] = Counter()
        per_day: Counter[str] = Counter()
        previews: List[str] = []

        for entry in entries:
            data = dict(entry.get("data") or {})
            event = str(data.get("event") or "")
            if not event:
                continue
            event_counts[event] += 1
            domain = _domain_for_event(event, data)
            domain_counts[domain] += 1

            day = datetime.fromtimestamp(
                _parse_timestamp(entry.get("timestamp")),
                tz=timezone.utc,
            ).strftime("%Y-%m-%d")
            per_day[day] += 1

            if event == "memory.block":
                preview = str(data.get("content_preview") or data.get("content") or "")[:160]
                if preview:
                    previews.append(preview)
                for kw in data.get("keywords") or []:
                    keyword_counts[str(kw).lower()] += 1
            elif event == "trace.cycle":
                preview = str(data.get("input_preview") or data.get("input") or "")[:160]
                if preview:
                    previews.append(preview)
            elif event in ("asset.upload", "asset.received"):
                fn = str(data.get("filename") or "")
                if fn:
                    asset_filenames[fn] += 1
                summary = str(data.get("summary") or data.get("desc") or "")
                if summary:
                    previews.append(summary[:160])

        meaningful = sum(
            event_counts.get(k, 0)
            for k in ("memory.block", "trace.cycle", "asset.upload", "asset.received")
        )
        total_domains = sum(domain_counts.values()) or 1
        focus_rows = []
        for domain, count in domain_counts.most_common():
            share = count / total_domains
            if share >= 0.35 and count >= 3:
                focus_rows.append({
                    "domain": domain,
                    "count": count,
                    "share": round(share, 3),
                    "signal": "over_focus" if share >= 0.5 else "elevated",
                })

        repeated_assets = [
            {"filename": name, "count": count}
            for name, count in asset_filenames.items()
            if count >= 2
        ][:8]

        top_keywords = [{"term": term, "count": count} for term, count in keyword_counts.most_common(12)]

        return {
            "entries_analyzed": len(entries),
            "meaningful_events": meaningful,
            "event_counts": dict(event_counts),
            "domain_counts": dict(domain_counts),
            "per_day": dict(sorted(per_day.items())),
            "focus_signals": focus_rows,
            "repeated_assets": repeated_assets,
            "top_keywords": top_keywords,
            "preview_samples": previews[:12],
        }

    def vector_sketch(self) -> Dict[str, Any]:
        idx = self.vector_index
        if idx is None:
            return {"available": False}
        status = idx.status() if hasattr(idx, "status") else {}
        clip_images = int(status.get("clip_image_count") or 0)
        total = int(status.get("count") or 0)
        with getattr(idx, "_lock", type("L", (), {"__enter__": lambda s: None, "__exit__": lambda s, *a: None})()):
            rows = list(getattr(idx, "_rows", {}).values()) if hasattr(idx, "_rows") else []
        type_counts: Counter[str] = Counter()
        backend_counts: Counter[str] = Counter()
        for row in rows:
            type_counts[str(row.get("type") or "unknown")] += 1
            backend_counts[str(row.get("backend") or row.get("embed_mode") or "unknown")] += 1
        return {
            "available": True,
            "indexed_total": total,
            "clip_image_count": clip_images,
            "type_counts": dict(type_counts),
            "backend_counts": dict(backend_counts),
        }

    @staticmethod
    def _heuristic_reflection(question: str, analysis: dict, vector_sketch: dict) -> str:
        lines = ["【元认知启发式分析】"]
        meaningful = int(analysis.get("meaningful_events") or 0)
        if meaningful == 0:
            lines.append("当前窗口内可分析的认知事件较少，建议继续积累 AuditLog 后再反思。")
            return "\n".join(lines)

        domains = analysis.get("domain_counts") or {}
        top_domain = max(domains, key=domains.get) if domains else "unknown"
        lines.append(f"共分析 {analysis.get('entries_analyzed', 0)} 条审计记录，其中 {meaningful} 条为记忆/对话/资产类事件。")

        focus = analysis.get("focus_signals") or []
        if focus:
            parts = [f"{row['domain']}({int(row['share'] * 100)}%)" for row in focus]
            lines.append(f"领域倾斜：{', '.join(parts)}。")
            if any(row.get("signal") == "over_focus" for row in focus):
                lines.append(
                    f"检测到对「{top_domain}」的过度关注倾向——"
                    "近期认知资源可能集中于此，其他维度（对话、网络协商、整合睡眠）相对稀疏。"
                )
        else:
            lines.append("未发现单一领域的极端倾斜，认知分布相对均衡。")

        repeated = analysis.get("repeated_assets") or []
        if repeated:
            names = ", ".join(row["filename"] for row in repeated[:4])
            lines.append(f"重复触及的资产：{names}，可能存在 fixation（固着）模式。")

        keywords = analysis.get("top_keywords") or []
        if keywords:
            terms = ", ".join(row["term"] for row in keywords[:6])
            lines.append(f"高频关键词：{terms}。")

        if vector_sketch.get("available"):
            tc = vector_sketch.get("type_counts") or {}
            if tc:
                lines.append(f"向量索引分布：{tc}（CLIP 直嵌图片 {vector_sketch.get('clip_image_count', 0)} 条）。")

        lines.append(f"反思问题：{question}")
        return "\n".join(lines)

    @staticmethod
    def build_llm_prompt(question: str, analysis: dict, vector_sketch: dict, entries: List[dict]) -> Tuple[str, str]:
        system = (
            "你是 CNexus 元认知分析器（Metacognition Engine）。"
            "你只能基于提供的 AuditLog 摘要与向量索引统计作答，不要编造未出现的事实。"
            "输出结构：\n"
            "1) 认知偏差 / 盲区（若有）\n"
            "2) 领域倾斜与过度关注倾向\n"
            "3) 重复模式与可能的 fixation\n"
            "4) 可执行的认知调整建议（2-3 条）\n"
            "语气：冷静、具体、面向拥有技术背景的用户。"
        )
        digest_lines = []
        for entry in entries[-40:]:
            data = dict(entry.get("data") or {})
            event = str(data.get("event") or "")
            ts = str(entry.get("timestamp") or "")[:19]
            if event == "memory.block":
                digest_lines.append(
                    f"- [{ts}] memory.block label={data.get('label')} "
                    f"preview={str(data.get('content_preview') or '')[:100]}"
                )
            elif event == "trace.cycle":
                digest_lines.append(
                    f"- [{ts}] trace.cycle iter={data.get('iteration')} "
                    f"input={str(data.get('input_preview') or '')[:100]}"
                )
            elif event in ("asset.upload", "asset.received"):
                digest_lines.append(
                    f"- [{ts}] {event} type={data.get('type')} file={data.get('filename')} "
                    f"summary={str(data.get('summary') or data.get('desc') or '')[:80]}"
                )
            elif event in SelfReflectionEngine.REFLECTABLE_EVENTS:
                digest_lines.append(f"- [{ts}] {event}")

        user = (
            f"## 用户问题\n{question}\n\n"
            f"## 统计摘要\n{analysis}\n\n"
            f"## 向量索引\n{vector_sketch}\n\n"
            f"## AuditLog 抽样（最近 {min(40, len(entries))} 条）\n"
            + "\n".join(digest_lines)
        )
        return system, user

    def reflect(
        self,
        question: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        window_days: Optional[int] = None,
        use_llm: bool = True,
        llm_fn: Optional[LlmFn] = None,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "error": "reflection_disabled"}

        question = str(question or DEFAULT_QUESTION).strip()
        entries = self.recent_entries(limit=limit, window_days=window_days)
        analysis = self.analyze_patterns(entries)
        vector_sketch = self.vector_sketch()

        report: Dict[str, Any] = {
            "ok": False,
            "question": question,
            "window_days": window_days if window_days is not None else self.default_window_days,
            "limit": limit or self.default_limit,
            "entries_used": len(entries),
            "analysis": analysis,
            "vector_sketch": vector_sketch,
            "reflected_at": time.time(),
            "source": "heuristic",
        }

        reflection_text = ""
        if use_llm and llm_fn:
            system, user = self.build_llm_prompt(question, analysis, vector_sketch, entries)
            try:
                llm_text = llm_fn(system, user)
                if llm_text and str(llm_text).strip():
                    reflection_text = str(llm_text).strip()
                    report["source"] = "llm"
            except Exception as exc:
                report["llm_error"] = str(exc)

        if not reflection_text:
            reflection_text = self._heuristic_reflection(question, analysis, vector_sketch)

        report["reflection"] = reflection_text
        report["biases"] = [row for row in analysis.get("focus_signals") or [] if row.get("signal") == "over_focus"]
        report["ok"] = True

        if self.audit_fn:
            try:
                self.audit_fn(
                    "reflection.meta",
                    {
                        "question": question[:500],
                        "source": report["source"],
                        "entries_used": len(entries),
                        "biases": report["biases"],
                        "reflection_preview": reflection_text[:480],
                        "domain_counts": analysis.get("domain_counts"),
                    },
                )
            except Exception:
                pass

        self.last_report = report
        return report

    def status(self) -> Dict[str, Any]:
        entries = self.recent_entries()
        analysis = self.analyze_patterns(entries) if entries else {}
        return {
            "enabled": self.enabled,
            "default_limit": self.default_limit,
            "default_window_days": self.default_window_days,
            "audit_entries_in_window": len(entries),
            "meaningful_in_window": analysis.get("meaningful_events", 0),
            "last_report": dict(self.last_report),
            "vector_sketch": self.vector_sketch(),
        }

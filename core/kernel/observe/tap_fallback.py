"""Fallback ExecutionRecord / Learn projections from persisted execution_tap."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.kernel.learn.interpreter import LearnExplanationV2
from core.runtime.execution_tap import get_execution_tap
from core.runtime.tap_bootstrap import configure_execution_tap_persistence
from core.runtime.tap_storage import ExecutionTapLog


def _memory_base_dir() -> str:
    return str(Path(os.environ.get("BM_MEMORY_DIR", "C:/ProgramData/cnexus/data")))


def _ensure_tap_hydrated(base_dir: str | None = None) -> None:
    root = base_dir or _memory_base_dir()
    configure_execution_tap_persistence(root)


def tap_events_for_trace(trace_id: str, *, base_dir: str | None = None) -> list[dict[str, Any]]:
    _ensure_tap_hydrated(base_dir)
    return get_execution_tap().events_for_trace_merged(trace_id)


def list_recent_trace_ids(*, limit: int = 40, base_dir: str | None = None) -> list[str]:
    _ensure_tap_hydrated(base_dir)
    root = base_dir or _memory_base_dir()
    seen: list[str] = []
    seen_set: set[str] = set()

    tap = get_execution_tap()
    for row in reversed(tap.flush()):
        tid = str(row.get("trace_id") or "").strip()
        if tid and tid not in seen_set:
            seen_set.add(tid)
            seen.append(tid)
        if len(seen) >= limit:
            return seen

    for row in reversed(ExecutionTapLog(root).read_all()):
        tid = str(row.get("trace_id") or "").strip()
        if tid and tid not in seen_set:
            seen_set.add(tid)
            seen.append(tid)
        if len(seen) >= limit:
            break
    return seen


def build_record_dict_from_tap(trace_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    elapsed_ms = 0.0
    if len(events) >= 2:
        elapsed_ms = max(0.0, (float(events[-1].get("ts") or 0) - float(events[0].get("ts") or 0)) * 1000)

    nodes = [
        {
            "id": f"tap-{i}",
            "label": str(ev.get("type") or "step"),
            "intent": {"type": str(ev.get("type") or "step")},
            "summary": str(ev.get("summary") or ""),
        }
        for i, ev in enumerate(events)
    ]

    return {
        "version": "execution-record-v1",
        "trace_id": trace_id,
        "intent_type": str(events[0].get("type") or "runtime"),
        "result": {"summary": events[-1].get("summary") if events else None},
        "identity": None,
        "graph": None,
        "graph_invariant": None,
        "nodes": nodes,
        "edges": [],
        "state_projection": {"source": "execution_tap", "event_count": len(events)},
        "causal_projection": {"events": [e.get("summary") for e in events]},
        "explain_projection": {"mode": "tap_fallback"},
        "equivalence": None,
        "replay_signature": None,
        "audit_log": {"source": "execution_tap"},
        "audit": {"source": "execution_tap"},
        "events": events,
        "derivation": {"execution_tier": "T2" if len(events) > 2 else "T1"},
        "elapsed_ms": elapsed_ms,
    }


def interpret_v2_from_tap(trace_id: str, events: list[dict[str, Any]]) -> LearnExplanationV2:
    steps = [str(ev.get("summary") or ev.get("type") or "step") for ev in events]
    if not steps:
        steps = ["记录到执行 Tap，但缺少详细步骤"]

    tier = "T3" if len(events) > 4 else "T2" if len(events) > 1 else "T1"
    mode = "deep" if tier == "T3" else "standard" if tier == "T2" else "fast"

    beginner_lines = "\n".join(f"{'①②③④⑤⑥⑦⑧⑨'[min(i, 8)]} {s}" for i, s in enumerate(steps[:6]))
    intermediate_lines = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
    expert_lines = "\n".join(
        f"  - [{ev.get('type')}] {ev.get('summary')} (impact={ev.get('impact')})" for ev in events
    )

    first_type = str(events[0].get("type") or "runtime") if events else "runtime"
    summary = f"基于执行 Tap 还原：{len(events)} 个步骤（{first_type}）"

    return LearnExplanationV2(
        trace_id=trace_id,
        execution_tier=tier,
        mode=mode,
        summary=summary,
        steps=steps[:8],
        beginner_view=f"AI 执行了以下步骤：\n\n{beginner_lines}",
        intermediate_view=f"执行 Tap 时间线：\n\n{intermediate_lines}",
        expert_view=f"execution_tap ({len(events)} events):\n{expert_lines}",
        execution_story=(
            f"该 trace 未找到完整 ExecutionRecord，已从 execution_tap 回放 {len(events)} 条事件。\n\n"
            f"这通常发生在：对话走了 Runtime 路径但未写入 Kernel 内存记录，或 API 重启后内存记录已清空。"
        ),
        memory_view=[s for s in steps if "recall" in s.lower() or "memory" in s.lower()],
        reasoning_trace=steps,
        why_this_result="结果由 Runtime 执行链生成；此处为 Tap 投影，非完整 Kernel Record。",
        why_it_feels_fast_or_slow="T1 较快" if tier == "T1" else "多步骤执行可能稍慢",
        mental_model="ExecutionRecord 是单真相；Tap 是 Runtime 侧环形缓冲 + jsonl 持久化的补充观测。",
        user_intent_summary=first_type,
    )

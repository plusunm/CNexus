"""Learn Mode v2 — multi-layer cognitive explanation from ExecutionRecord."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.kernel.record import ExecutionRecord

_TIER_LABELS = {
    "T0": "快速模式（Fast Path）",
    "T1": "轻量模式（无记忆检索）",
    "T2": "标准模式（检索 + 生成）",
    "T3": "深度模式（多步骤执行图）",
}

_LATENCY_HINTS = {
    "T0": "极快：直接回答问题，跳过复杂执行图",
    "T1": "较快：不检索长期记忆，专注当前对话",
    "T2": "标准：检索相关记忆后生成回答",
    "T3": "较慢：拆解任务、多步骤推理与图执行",
}

_NODE_BEGINNER = {
    "recall": "回忆相关信息",
    "chat": "生成回答",
    "capture": "记录新信息",
    "control": "运行治理检查",
    "ir_exec": "执行推理计划",
}

_NODE_INTERMEDIATE = {
    "recall": "检索相关记忆片段",
    "chat": "组合上下文并生成回答",
    "capture": "写入记忆层",
    "join": "整合多个信息来源",
    "tool": "调用外部能力",
}

_MODE_FROM_TIER = {
    "T0": "fast",
    "T1": "fast",
    "T2": "standard",
    "T3": "deep",
}


@dataclass
class LearnExplanationV2:
    trace_id: str
    execution_tier: str
    mode: str
    beginner_view: str
    intermediate_view: str
    expert_view: str
    execution_story: str
    memory_view: list[str] = field(default_factory=list)
    reasoning_trace: list[str] = field(default_factory=list)
    why_this_result: str = ""
    why_it_feels_fast_or_slow: str = ""
    mental_model: str = ""
    summary: str = ""
    steps: list[str] = field(default_factory=list)
    user_intent_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "learn-explanation-v2",
            "trace_id": self.trace_id,
            "execution_tier": self.execution_tier,
            "mode": self.mode,
            "summary": self.summary,
            "steps": self.steps,
            "beginner_view": self.beginner_view,
            "intermediate_view": self.intermediate_view,
            "expert_view": self.expert_view,
            "execution_story": self.execution_story,
            "memory_view": self.memory_view,
            "reasoning_trace": self.reasoning_trace,
            "why_this_result": self.why_this_result,
            "why_it_feels_fast_or_slow": self.why_it_feels_fast_or_slow,
            "mental_model": self.mental_model,
            "user_intent_summary": self.user_intent_summary,
        }


def interpret_v2(record: "ExecutionRecord") -> LearnExplanationV2:
    tier = _resolve_tier(record)
    intent_summary = _extract_user_intent(record)
    steps_beginner, steps_intermediate, steps_expert, reasoning = _build_step_layers(record)
    memory = _memory_view(record)
    mode = _MODE_FROM_TIER.get(tier, "standard")

    beginner = _format_beginner(steps_beginner)
    intermediate = _format_intermediate(steps_intermediate)
    expert = _format_expert(steps_expert, record)
    story = _execution_story(record, tier, intent_summary)
    why = _why_result(record, tier)
    latency = _LATENCY_HINTS.get(tier, "标准执行路径")
    mental = _mental_model()
    summary = f"AI 正在以「{_TIER_LABELS.get(tier, tier)}」处理：{intent_summary}"

    return LearnExplanationV2(
        trace_id=record.trace_id,
        execution_tier=tier,
        mode=mode,
        beginner_view=beginner,
        intermediate_view=intermediate,
        expert_view=expert,
        execution_story=story,
        memory_view=memory,
        reasoning_trace=reasoning,
        why_this_result=why,
        why_it_feels_fast_or_slow=latency,
        mental_model=mental,
        summary=summary,
        steps=steps_beginner,
        user_intent_summary=intent_summary,
    )


def _resolve_tier(record: "ExecutionRecord") -> str:
    derivation = record.derivation or {}
    audit = record.audit or record.audit_log or {}
    tier = derivation.get("execution_tier") or audit.get("execution_tier")
    if isinstance(tier, str) and tier.strip():
        return tier.strip()
    if not record.graph and not record.nodes:
        return "T0"
    if len(record.nodes or []) > 1:
        return "T3"
    return "T2"


def _extract_user_intent(record: "ExecutionRecord") -> str:
    result = record.result
    if isinstance(result, dict):
        for key in ("message", "user_input", "query"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()[:200]
        reply = result.get("reply") or result.get("response")
        if isinstance(reply, str) and reply.strip():
            return f"对话请求（已生成回答）"
    if record.intent_type == "recall":
        return "检索记忆"
    if record.intent_type == "chat":
        return "对话 / 提问"
    return record.intent_type or "未知请求"


def _node_intent_type(node: dict[str, Any]) -> str:
    intent = node.get("intent") or {}
    if isinstance(intent, dict):
        return str(intent.get("type") or "")
    label = str(node.get("label") or "")
    if label.startswith("recall"):
        return "recall"
    if label.startswith("chat"):
        return "chat"
    return label or "step"


def _build_step_layers(record: "ExecutionRecord") -> tuple[list[str], list[str], list[str], list[str]]:
    nodes = list(record.nodes or [])
    if not nodes and not record.graph:
        return (
            ["理解你的问题", "生成回答"],
            ["解析问题意图", "生成最终回答"],
            ["route_intent → direct execution"],
            ["无执行图，走快速路径"],
        )

    beginner: list[str] = []
    intermediate: list[str] = []
    expert: list[str] = []
    reasoning: list[str] = []

    if not nodes:
        beginner = ["理解你的问题", "回忆相关信息", "生成回答"]
        intermediate = ["解析意图", "检索记忆", "生成回答"]
        expert = ["graph: implicit"]
        return beginner, intermediate, expert, reasoning

    for node in nodes:
        node_id = str(node.get("node_id") or node.get("id") or "?")
        ntype = _node_intent_type(node)
        label = str(node.get("label") or ntype)

        beginner.append(_NODE_BEGINNER.get(ntype, f"处理：{label}"))
        intermediate.append(_NODE_INTERMEDIATE.get(ntype, f"执行节点：{label}"))
        expert.append(f"{node_id} → {label} ({ntype})")
        reasoning.append(f"步骤 {len(reasoning) + 1}：{_NODE_INTERMEDIATE.get(ntype, label)}")

    if record.intent_type == "chat" and not any(_node_intent_type(n) == "chat" for n in nodes):
        beginner.append("生成回答")
        intermediate.append("组合上下文并生成回答")
        expert.append("chat → process_interaction")
        reasoning.append("步骤：在运行时内完成对话生成")

    return beginner, intermediate, expert, reasoning


def _memory_view(record: "ExecutionRecord") -> list[str]:
    memories: list[str] = []
    nodes = record.nodes or []
    has_recall = any(_node_intent_type(n) == "recall" for n in nodes)

    result = record.result if isinstance(record.result, dict) else {}
    context = result.get("context")
    if isinstance(context, str) and context.strip():
        preview = context.strip()[:120]
        memories.append(f"使用了相关记忆片段：「{preview}{'…' if len(context) > 120 else ''}」")
    elif has_recall:
        memories.append("AI 从系统中检索了与问题相关的历史记忆")
    elif _resolve_tier(record) in ("T0", "T2", "T3"):
        memories.append("可能使用了上下文或预取的记忆信息")

    if not memories and record.intent_type == "chat":
        tier = _resolve_tier(record)
        if tier == "T1":
            memories.append("本次未检索长期记忆（轻量模式）")
        else:
            memories.append("未检测到显式记忆检索步骤")

    return memories


def _simplify_identity(identity: Optional[str]) -> str:
    if not identity:
        return "尚未归类到已知问题类型"
    if identity.startswith("I-"):
        return "AI 判断这与之前某些问题属于同一类结构（问题族）"
    return "已关联到一次可追踪的执行身份"


def _format_beginner(steps: list[str]) -> str:
    if len(steps) <= 3 and steps == ["理解你的问题", "回忆相关信息", "生成回答"]:
        return (
            "AI 正在做三件事：\n\n"
            "① 理解你的问题\n"
            "② 回忆相关信息\n"
            "③ 生成回答"
        )
    lines = [f"{'①②③④⑤⑥⑦⑧⑨'[i]} {s}" for i, s in enumerate(steps[:6])]
    return "AI 正在：\n\n" + "\n".join(lines)


def _format_intermediate(steps: list[str]) -> str:
    return "AI 执行流程：\n\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))


def _format_expert(steps: list[str], record: "ExecutionRecord") -> str:
    lines = ["Execution Graph:"]
    lines.extend(f"  - {s}" for s in steps)
    if record.graph_invariant:
        lines.append(f"graph_invariant={record.graph_invariant}")
    if record.identity:
        lines.append(f"identity={record.identity}")
    if record.replay_signature:
        lines.append(f"replay_signature={record.replay_signature}")
    lines.append(f"elapsed_ms={record.elapsed_ms}")
    return "\n".join(lines)


def _execution_story(record: "ExecutionRecord", tier: str, intent: str) -> str:
    tier_label = _TIER_LABELS.get(tier, tier)
    step_hint = " → ".join(_build_step_layers(record)[0][:4]) or "直接生成"
    return (
        f"AI 以「{tier_label}」处理了一次任务。\n\n"
        f"关于：{intent}\n\n"
        f"过程概要：{step_hint}\n\n"
        f"最终输出了结果（耗时约 {record.elapsed_ms:.0f} ms）。"
    )


def _why_result(record: "ExecutionRecord", tier: str) -> str:
    if tier in ("T0", "T1"):
        return "因为问题相对直接，系统选择了更快的执行路径，优先响应速度。"
    if tier == "T2":
        return "因为这是标准对话请求，系统会检索记忆并生成回答。"
    return "因为任务需要更多步骤（记忆检索、图调度、身份归类），系统启用了完整内核执行。"


def _mental_model() -> str:
    return (
        "AI 不是一个单纯的「聊天机器人」，而是：\n\n"
        "→ 执行系统（按步骤完成任务）\n"
        "→ 记忆系统（在需要时回忆过去）\n"
        "→ 生成系统（用语言组织答案）\n\n"
        "它在运行一个「任务流程」，而不是逐字拼接回复。"
    )


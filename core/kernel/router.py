"""Intent router — dispatches kernel intents to runtime / IR paths."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from core.kernel.context import ExecutionContext
from core.kernel.intent import ExecutionIntent

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def route_intent(intent: ExecutionIntent, ctx: ExecutionContext, runtime: "BrainMemoryRuntime") -> Any:
    t = intent.type
    p = intent.payload

    if t == "chat":
        return _route_chat(p, runtime)

    if t == "recall":
        return runtime.recall(
            p["query"],
            top_k=p.get("top_k"),
            use_attention=p.get("use_attention", True),
            mutate_state=p.get("mutate_state", False),
        )

    if t == "capture":
        meta = dict(p.get("meta") or {})
        return runtime.capture(
            p["role"],
            p["content"],
            layer=p.get("layer", "episodic"),
            importance=p.get("importance", 0.5),
            **meta,
        )

    if t in ("control", "cdg_apply"):
        return runtime.run_governance_cycle()

    if t == "memory_maintenance":
        return runtime.run_memory_maintenance(force=bool(p.get("force", False)))

    if t == "capture_cognition":
        return runtime.process_capture_cognition(
            p.get("content", ""),
            layer=p.get("layer", "episodic"),
            memory_id=p.get("memory_id"),
            trigger_governance=p.get("trigger_governance"),
        )

    if t == "reflect_review":
        record = runtime.trait_based_reflection(
            p.get("content", ""),
            p.get("traits"),
            trigger_governance=p.get("trigger_governance", True),
        )
        if hasattr(record, "model_dump"):
            return record.model_dump(mode="json")
        if hasattr(record, "__dict__"):
            return dict(record.__dict__)
        return record

    if t == "reflect_due_reviews":
        records = runtime.reflection_pipeline.run_due_reviews()
        return {"due": [r.model_dump(mode="json") for r in records]}

    if t == "governance_validate":
        return runtime.run_validation_suite(days=int(p.get("days", 90)))

    if t == "observe":
        return _route_observe(p, runtime)

    if t == "ir_exec":
        return _route_ir_execute(p, runtime)

    if t == "system":
        return _route_system(p, runtime)

    raise ValueError(f"unknown intent type: {t}")


def _route_observe(p: dict[str, Any], runtime: "BrainMemoryRuntime") -> Any:
    kind = str(p.get("_observe_kind") or p.get("kind") or "")
    if kind == "memory_stats":
        return runtime.memory_stats()
    if kind == "governance_state":
        return runtime.get_current_state()
    if kind == "cdg_trajectory":
        return runtime.cdg.trajectory_report(last_n=int(p.get("last_n", 20)))
    if kind == "active_reflections":
        records = runtime.reflection_pipeline.get_active_reflections()
        return {"reflections": [r.model_dump(mode="json") for r in records]}
    raise ValueError(f"unsupported observe kind: {kind}")


def _route_chat(p: dict[str, Any], runtime: "BrainMemoryRuntime") -> Any:
    action = p.get("_action")
    if action == "prepare":
        return runtime.prepare_chat_turn(
            p["message"],
            use_memory=p.get("use_memory", True),
            chat_mode=p.get("chat_mode", True),
            metadata=p.get("metadata"),
        )
    if action == "confirm":
        return runtime.confirm_prepared_chat_turn(
            p["prepare_id"],
            temperature=p.get("temperature", 0.7),
            llm_client=p.get("llm_client"),
            llm_profile=p.get("llm_profile"),
            allow_proactive=p.get("allow_proactive", True),
            send_mode=p.get("send_mode"),
        )
    if action == "cancel":
        return runtime.cancel_prepared_chat_turn(p["prepare_id"])

    return runtime.process_interaction(
        p["message"],
        use_memory=p.get("use_memory", True),
        temperature=p.get("temperature", 0.7),
        llm_client=p.get("llm_client"),
        llm_profile=p.get("llm_profile"),
        allow_proactive=p.get("allow_proactive", True),
        chat_mode=p.get("chat_mode", True),
        metadata=p.get("metadata"),
        assistant_output=p.get("assistant_output"),
        user_id=p.get("user_id"),
    )


def _route_ir_execute(p: dict[str, Any], runtime: "BrainMemoryRuntime") -> Any:
    from ir_kernel.adapters.runtime_facade import RuntimeFacade
    from ir_kernel.engine import compile_and_execute
    from ir_kernel.runtime.executor import ExecContext

    facade = RuntimeFacade(runtime)
    exec_ctx = ExecContext(
        use_memory=p.get("use_memory", True),
        llm_client=p["llm_client"],
        llm_profile=p["llm_profile"],
        temperature=p.get("temperature", 0.7),
        session_meta=p.get("session_meta") or {},
    )
    return compile_and_execute(
        p["message"],
        facade,
        template=p.get("template", "chat_single_turn"),
        use_memory=p.get("use_memory", True),
        ctx=exec_ctx,
        commit=p.get("commit", True),
    )


def _route_system(p: dict[str, Any], runtime: "BrainMemoryRuntime") -> Any:
    from ir_kernel.engine import compile_graph

    runtime_method = p.get("_runtime_method")
    if runtime_method:
        from core.kernel.migration.auto_wrap import strip_kernel_flags

        method = getattr(runtime, str(runtime_method))
        args = tuple(p.get("args") or ())
        kwargs = strip_kernel_flags(dict(p.get("kwargs") or {}))
        return method(*args, **kwargs)

    if p.get("_action") == "compile":
        return compile_graph(
            p["message"],
            template=p.get("template", "chat_single_turn"),
            use_memory=p.get("use_memory", True),
        )
    raise ValueError(f"unsupported system action: {p.get('_action')}")

"""Public facade for BrainMemoryRuntime delegation (Path B)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ir_kernel.adapters.runtime_facade import RuntimeFacade
from ir_kernel.engine import compile_and_execute
from ir_kernel.runtime.executor import ExecContext


def execute_chat_dag(
    runtime,
    text: str,
    *,
    template: str = "cognitive_chat_full",
    use_memory: bool = True,
    llm_client: Any = None,
    llm_profile: Any = None,
    temperature: float = 0.7,
    commit: bool = True,
    session_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    facade = RuntimeFacade(runtime)
    ctx = ExecContext(
        use_memory=use_memory,
        llm_client=llm_client,
        llm_profile=llm_profile,
        temperature=temperature,
        session_meta=dict(session_meta or {}),
    )
    result = compile_and_execute(
        text,
        facade,
        template=template,
        use_memory=use_memory,
        ctx=ctx,
        commit=commit,
    )
    return {
        "ok": result.ok,
        "reply": result.reply,
        "response": result.reply,
        "trace_id": result.trace_id,
        "graph_id": result.graph_id,
        "template": result.template,
        "outbound_preview": result.outbound_preview,
        "ir": {
            "sigma_exec": result.sigma_exec,
            "graph": result.graph,
            "commit_results": result.commit_results,
        },
        "error": result.error,
    }

"""IR kernel entry — compile + execute + commit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ir_kernel.adapters.runtime_facade import RuntimeFacade
from ir_kernel.compiler import template_chat  # noqa: F401 — register plugins
from ir_kernel.compiler import template_cognitive_chat  # noqa: F401
from ir_kernel.compiler.registry import compile_template, list_templates
from ir_kernel.runtime.commit_runner import CommitRunner
from ir_kernel.runtime.executor import ExecContext
from ir_kernel.runtime.scheduler import DAGScheduler
from ir_kernel.schema.graph import IRGraph
from ir_kernel.schema.sigma_exec import SigmaExec
from ir_kernel.trace.store import TraceStore
from ir_kernel.verifier.graph_verifier import GraphVerifier


@dataclass
class ExecuteResult:
    ok: bool
    reply: str
    trace_id: str
    graph_id: str
    template: str
    sigma_exec: Dict[str, Any]
    graph: Dict[str, Any]
    outbound_preview: str = ""
    commit_results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[Dict[str, Any]] = None


def compile_graph(
    user_message: str,
    *,
    template: str = "chat_single_turn",
    use_memory: bool = True,
) -> tuple[IRGraph, SigmaExec]:
    graph = compile_template(template, use_memory=use_memory)
    sigma = SigmaExec(
        graph_id=graph.graph_id,
        input={
            "user_message": user_message,
            "use_memory": use_memory,
            "template": template,
        },
    )
    return graph, sigma


def execute_graph(
    graph: IRGraph,
    sigma: SigmaExec,
    facade: RuntimeFacade,
    *,
    ctx: Optional[ExecContext] = None,
    commit: bool = True,
    persist_trace: bool = True,
) -> ExecuteResult:
    exec_ctx = ctx or ExecContext(use_memory=bool(sigma.input.get("use_memory", True)))
    scheduler = DAGScheduler()
    sigma = scheduler.run(graph, sigma, facade, exec_ctx)

    commit_results: List[Dict[str, Any]] = []
    if sigma.status == "completed" and commit:
        commit_results = CommitRunner().run(facade, sigma, enabled=True)

    if persist_trace:
        TraceStore().save_execution(
            graph,
            sigma,
            manifest={"commit_count": len(commit_results)},
        )

    reply = sigma.variables.get("final") or sigma.variables.get("reply") or ""
    preview = sigma.variables.get("outbound_preview", "")

    return ExecuteResult(
        ok=sigma.status == "completed",
        reply=reply,
        trace_id=sigma.trace_id,
        graph_id=graph.graph_id,
        template=graph.template_name,
        sigma_exec=sigma.to_dict(),
        graph=graph.to_dict(),
        outbound_preview=preview,
        commit_results=commit_results,
        error=sigma.error,
    )


def compile_and_execute(
    user_message: str,
    facade: RuntimeFacade,
    *,
    template: str = "chat_single_turn",
    use_memory: bool = True,
    ctx: Optional[ExecContext] = None,
    commit: bool = True,
) -> ExecuteResult:
    graph, sigma = compile_graph(user_message, template=template, use_memory=use_memory)
    verifier = GraphVerifier()
    check = verifier.verify_graph(graph)
    if not check.ok:
        sigma.status = "failed"
        sigma.error = {"code": "GRAPH_INVALID", "message": ";".join(check.errors)}
        return ExecuteResult(
            ok=False,
            reply="",
            trace_id=sigma.trace_id,
            graph_id=graph.graph_id,
            template=template,
            sigma_exec=sigma.to_dict(),
            graph=graph.to_dict(),
            error=sigma.error,
        )
    if ctx is None:
        ctx = ExecContext(use_memory=use_memory)
    else:
        ctx.use_memory = use_memory
    return execute_graph(graph, sigma, facade, ctx=ctx, commit=commit)


def available_templates() -> List[str]:
    return list_templates()

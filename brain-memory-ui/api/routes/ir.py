"""CNexus IR execution API — Path B (does not replace /chat)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_dispatcher, get_llm, get_registry, get_runtime
from api.runtime_log import runtime_log
from ir_kernel.engine import available_templates, compile_graph
from ir_kernel.adapters.runtime_facade import RuntimeFacade
from ir_kernel.trace.store import TraceStore

router = APIRouter(prefix="/ir", tags=["ir"])


class IrCompileRequest(BaseModel):
    message: str
    template: str = Field(default="chat_single_turn")
    use_memory: bool = True


class IrExecuteRequest(BaseModel):
    message: str
    template: str = Field(default="chat_single_turn")
    model_id: Optional[str] = None
    use_memory: bool = True
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    commit: bool = True


class IrCommitRequest(BaseModel):
    trace_id: str


@router.get("/templates")
def ir_templates() -> Dict[str, Any]:
    return {"templates": available_templates()}


@router.post("/compile")
def ir_compile(req: IrCompileRequest) -> Dict[str, Any]:
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    try:
        graph, sigma = compile_graph(message, template=req.template, use_memory=req.use_memory)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    runtime = get_runtime()
    facade = RuntimeFacade(runtime)
    bundle = facade.build_outbound(message, "", chat_governance_notes=[])
    if req.use_memory:
        recall = facade.recall_for_ir(message, read_only=True)
        bundle = facade.build_outbound(message, recall.context)

    runtime_log(
        "info",
        "ir",
        "IR compile",
        trace_id=sigma.trace_id,
        graph_id=graph.graph_id,
        template=req.template,
    )
    return {
        "trace_id": sigma.trace_id,
        "graph_id": graph.graph_id,
        "template": graph.template_name,
        "graph": graph.to_dict(),
        "sigma_exec_init": sigma.to_dict(),
        "outbound_preview": bundle.outbound_preview,
    }


@router.post("/execute")
def ir_execute(req: IrExecuteRequest) -> Dict[str, Any]:
    if os.environ.get("CNEXUS_IR_ENABLED", "1") not in ("1", "true", "yes"):
        raise HTTPException(status_code=503, detail="IR path disabled (CNEXUS_IR_ENABLED=0)")

    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    registry = get_registry()
    llm = get_llm()
    profile = registry.get(req.model_id) if req.model_id else registry.get_default()

    try:
        result = get_dispatcher().ir_execute(
            message=message,
            template=req.template,
            use_memory=req.use_memory,
            llm_client=llm,
            llm_profile=profile,
            temperature=req.temperature,
            commit=req.commit,
            session_meta={"model_id": req.model_id},
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    runtime_log(
        "info" if result.ok else "error",
        "ir",
        "IR execute",
        trace_id=result.trace_id,
        graph_id=result.graph_id,
        template=result.template,
        ok=result.ok,
    )

    if not result.ok:
        raise HTTPException(status_code=500, detail=result.error or {"code": "EXEC_FAILED"})

    return {
        "reply": result.reply,
        "trace_id": result.trace_id,
        "graph_id": result.graph_id,
        "template": result.template,
        "outbound_preview": result.outbound_preview,
        "commit_results": result.commit_results,
        "sigma_exec": result.sigma_exec,
    }


@router.post("/replay/{trace_id}")
def ir_replay(trace_id: str, mode: str = "strict") -> Dict[str, Any]:
    store = TraceStore()
    try:
        if mode == "strict":
            report = store.replay_strict(trace_id)
        else:
            report = store.load(trace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"trace not found: {trace_id}") from exc
    return report


@router.get("/traces/{trace_id}")
def ir_get_trace(trace_id: str) -> Dict[str, Any]:
    store = TraceStore()
    try:
        return store.load(trace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"trace not found: {trace_id}") from exc

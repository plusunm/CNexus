"""Cognitive Synthesis Engine API — decision-grade cognition for CNexus Home."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import get_runtime, peek_runtime
from api.runtime_log import get_logs, runtime_log
from core.cse.engine import CognitiveSynthesisEngine
from core.observability.mind_overview import build_mind_overview
from core.runtime.event_loop_offload import (
    EventLoopOffloadTimeout,
    default_offload_timeout_s,
    offload_sync,
)
from ir_kernel.trace.store import TraceStore

router = APIRouter(prefix="/cse", tags=["cse"])

_engine = CognitiveSynthesisEngine()


class CseSynthesizeRequest(BaseModel):
    window: int = Field(default=200, ge=10, le=1000)
    mode: str = Field(default="full")


def _execution_payload(runtime) -> Dict[str, Any]:
    registry = None
    try:
        from api.deps import get_registry

        registry = get_registry()
    except Exception:
        registry = None
    payload = runtime.local_stack.readiness_dict(registry=registry)
    return {
        "active_chat_provider": payload.get("active_chat_provider"),
        "active_embed_provider": payload.get("active_embed_provider"),
        "embedding": runtime.embedder.status_payload(),
        "ollama": runtime.local_stack.ollama_status(),
        "runtime_mode": str(runtime.config.get("runtime_mode") or "auto"),
        "runtime_envelope": str(runtime.config.get("runtime_envelope") or ""),
        "compute_profile": (
            runtime.compute_profile.to_dict() if runtime.compute_profile else {}
        ),
        "compute_policy": (
            runtime.compute_policy.to_dict() if runtime.compute_policy else {}
        ),
        "inference_scheduler": runtime.inference_scheduler.stats_payload(),
    }


def _build_output(*, window: int, mode: str = "live") -> Dict[str, Any]:
    runtime = get_runtime()
    logs = get_logs(limit=window)
    traces = TraceStore().list_recent(limit=min(20, window // 10 or 5))
    state = runtime.get_current_state()
    overview = state.get("mind_overview") or build_mind_overview(runtime, state)
    output = _engine.synthesize_live(
        runtime=runtime,
        logs=logs,
        execution_status=_execution_payload(runtime),
        mind_overview=overview,
        trace_events=traces,
        window=window,
    )
    payload = output.to_dict()
    payload["mode"] = mode
    payload["top_actions"] = [a.to_dict() for a in output.actions[:3]]
    payload["exec_traces"] = traces
    return payload


@router.get("/archive")
async def cse_archive(limit: int = Query(10, ge=1, le=50)):
    """Historical synthesis fingerprints for UI diff / timeline."""
    from core.cse.snapshot import get_snapshot_store

    return {"archive": get_snapshot_store().list_archive(limit=limit)}


def _require_runtime_ready() -> None:
    if peek_runtime() is None:
        from api.system_ready import system_ready_warming_payload

        raise HTTPException(status_code=503, detail=system_ready_warming_payload())


@router.get("/live")
async def cse_live(window: int = Query(200, ge=10, le=1000)):
    _require_runtime_ready()
    runtime_log("info", "cse", "Live cognition requested", window=window)
    try:
        return await offload_sync(
            lambda: _build_output(window=window, mode="live"),
            timeout_s=default_offload_timeout_s(),
        )
    except EventLoopOffloadTimeout:
        from api.system_ready import system_ready_warming_payload

        raise HTTPException(
            status_code=503,
            detail={
                **system_ready_warming_payload(),
                "reason": "COGNITIVE_OFFLOAD_TIMEOUT",
            },
        )


@router.post("/synthesize")
async def cse_synthesize(req: CseSynthesizeRequest):
    _require_runtime_ready()
    runtime_log("info", "cse", "Synthesize requested", window=req.window, mode=req.mode)
    try:
        return await offload_sync(
            lambda: _build_output(window=req.window, mode=req.mode),
            timeout_s=default_offload_timeout_s(),
        )
    except EventLoopOffloadTimeout:
        from api.system_ready import system_ready_warming_payload

        raise HTTPException(
            status_code=503,
            detail={
                **system_ready_warming_payload(),
                "reason": "COGNITIVE_OFFLOAD_TIMEOUT",
            },
        )

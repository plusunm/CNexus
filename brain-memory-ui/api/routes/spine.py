"""CP-2 Spine Query API — read truth layer over spine_events.jsonl."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from api.deps import peek_runtime
from core.spine.query.builder import run_query
from core.runtime.execution_tap import get_execution_tap
from core.spine.healing.repair import SpineHealer
from core.spine.query.builder_v2 import get_drift_report, run_query_v2
from core.spine.query.builder_v3 import get_identity_report, run_query_v3
from core.spine.identity.service import get_identity_service
from core.spine.query.engine import query_by_trace
from core.spine.stream.router import ExecutionSpineStreamRouter, STREAM_CONTRACT_VERSION
from core.spine.token.service import build_token_observatory, build_trace_token_report

router = APIRouter(prefix="/spine", tags=["spine"])


class SpineQueryBody(BaseModel):
    query: Optional[str] = Field(
        default=None,
        description='Spine query DSL, e.g. "TRACE abc EXPLAIN causal"',
    )
    trace_id: Optional[str] = Field(default=None, description="Direct trace id filter")
    mode: str = Field(default="causal", description="explain mode: causal | linear | event")
    limit: int = Field(default=200, ge=1, le=5000)
    engine: str = Field(
        default="v3",
        description='Query engine: v1 | v2 (drift+explain-v3) | v3 (identity-aware)',
    )
    token_influence: bool = Field(
        default=False,
        description="Attach token-weighted causal influence overlay (v3 only)",
    )


def _default_base_dir() -> str:
    return str(Path(os.environ.get("BM_MEMORY_DIR", "C:/ProgramData/cnexus/data")))


def _base_dir() -> str:
    runtime = peek_runtime()
    if runtime is not None:
        return str(runtime.base_dir)
    return _default_base_dir()


async def _run_spine_stream(websocket: WebSocket, trace_id: str) -> None:
    """Unified execution subscription — tap + spine + explain in one channel."""
    await websocket.accept()
    router = ExecutionSpineStreamRouter(trace_id=trace_id, base_dir=_base_dir())
    try:
        await websocket.send_json(router.connected_message())
        for message in router.poll_messages():
            await websocket.send_json(message)
        await websocket.send_json(router.snapshot_message())

        while True:
            await asyncio.sleep(2)
            await websocket.send_json(router.heartbeat_message())
            for message in router.poll_messages():
                await websocket.send_json(message)
    except WebSocketDisconnect:
        pass


@router.post("/query")
async def spine_query(body: SpineQueryBody):
    try:
        base = _base_dir()
        if body.engine == "v3":
            runtime = peek_runtime()
            result = run_query_v3(
                base,
                query=body.query,
                trace_id=body.trace_id,
                mode=body.mode,
                limit=body.limit,
                runtime=runtime,
                token_influence=body.token_influence,
            )
        elif body.engine == "v2":
            runtime = peek_runtime()
            result = run_query_v2(
                base,
                query=body.query,
                trace_id=body.trace_id,
                mode=body.mode,
                limit=body.limit,
                runtime=runtime,
            )
        else:
            result = run_query(
                base,
                query=body.query,
                trace_id=body.trace_id,
                mode=body.mode,
                limit=body.limit,
            )
    except ValueError as exc:
        code = str(exc)
        if code in ("trace_id_required", "query_empty", "query_parse_failed"):
            raise HTTPException(status_code=400, detail=code) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result.to_dict()


@router.get("/token/trace/{trace_id}")
async def spine_token_trace(trace_id: str):
    """Token Cost Gravity Field + bindings + influence overlay for a trace."""
    try:
        return build_trace_token_report(_base_dir(), trace_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/tokens/{trace_id}")
async def spine_tokens(trace_id: str):
    """Token events and phase breakdown for a trace."""
    try:
        report = build_trace_token_report(_base_dir(), trace_id)
        return {
            "trace_id": trace_id,
            "total_tokens": report.get("total_tokens") or 0,
            "by_phase": report.get("by_phase") or {},
            "bindings": report.get("bindings") or [],
            "token_events": report.get("token_events") or [],
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/token/observatory")
async def spine_token_observatory(limit: int = Query(default=100, ge=1, le=500)):
    """Aggregated token traces for Token Observatory view."""
    try:
        traces = build_token_observatory(_base_dir(), limit=limit)
        return {"token_traces": traces, "count": len(traces)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/drift/{trace_id}")
async def spine_drift(trace_id: str):
    """Runtime ↔ Spine drift report for a trace."""
    try:
        return get_drift_report(_base_dir(), trace_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/identity/{trace_id}")
async def spine_identity(trace_id: str):
    """Execution identity report for a trace."""
    try:
        return get_identity_report(_base_dir(), trace_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/equivalence")
async def spine_equivalence(trace_a: str = Query(...), trace_b: str = Query(...)):
    """Compare execution identity between two traces."""
    try:
        return get_identity_service().compare(_base_dir(), trace_a, trace_b)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/heal/{trace_id}")
async def spine_heal(trace_id: str, apply: bool = Query(default=False)):
    """Self-healing spine — suggest or apply tap→spine backfill."""
    try:
        base = _base_dir()
        drift = get_drift_report(base, trace_id)
        from core.spine.drift.types import DriftItem, DriftReport

        report = DriftReport(
            trace_id=trace_id,
            score=float(drift.get("score") or 0),
            missing=[DriftItem(**m) for m in drift.get("missing") or []],
            extra=[DriftItem(**e) for e in drift.get("extra") or []],
            mismatch=[DriftItem(**m) for m in drift.get("mismatch") or []],
            runtime_count=int(drift.get("runtime_count") or 0),
            spine_count=int(drift.get("spine_count") or 0),
            spine_sync_status=str(drift.get("spine_sync_status") or "partial"),
            last_spine_event_id=drift.get("last_spine_event_id"),
        )
        tap_events = get_execution_tap().events_for_trace_merged(trace_id)
        healer = SpineHealer()
        return healer.heal_from_drift(report, tap_events, apply=apply)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/stream/status")
async def spine_stream_status(trace_id: str = Query(..., min_length=1)):
    """HTTP handshake — execution subscription contract (pull probe)."""
    base = _base_dir()
    events = query_by_trace(base, trace_id, limit=5000)
    tap_rows = get_execution_tap().events_for_trace_merged(trace_id)
    return {
        "connected": True,
        "trace_id": trace_id,
        "version": STREAM_CONTRACT_VERSION,
        "channels": ["execution", "causal", "state", "control", "explain"],
        "spine_event_count": len(events),
        "tap_event_count": len(tap_rows),
        "subscription": "ready",
        "ws": "/v1/spine/stream",
    }


@router.websocket("/stream")
async def execution_spine_stream(
    websocket: WebSocket,
    trace_id: str = Query(..., min_length=1),
):
    """Unified execution feed — subscription contract for ExecutionSpineView."""
    await _run_spine_stream(websocket, trace_id)


@router.websocket("/explain/ws")
async def explain_stream(
    websocket: WebSocket,
    trace_id: str = Query(..., min_length=1),
):
    """Legacy alias — forwards to unified execution spine stream."""
    await _run_spine_stream(websocket, trace_id)


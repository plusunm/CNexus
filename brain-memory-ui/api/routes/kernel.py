"""Execution Kernel HTTP entry — CP-3 unified execute()."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_kernel
from core.kernel.intent import ExecutionIntent
from core.kernel.registry import all_capabilities

router = APIRouter(prefix="/kernel", tags=["kernel"])


class KernelExecuteRequest(BaseModel):
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    source: str = "http"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KernelExecuteResponse(BaseModel):
    ok: bool = True
    result: Any = None
    trace_id: Optional[str] = None


@router.post("/execute", response_model=KernelExecuteResponse)
def kernel_execute(body: KernelExecuteRequest) -> KernelExecuteResponse:
    kernel = get_kernel()
    intent = ExecutionIntent(
        type=body.type,  # type: ignore[arg-type]
        payload=body.payload,
        trace_id=body.trace_id,
        source=body.source,
        metadata=body.metadata,
    )
    record = kernel.execute(intent)
    return KernelExecuteResponse(ok=True, result=record.to_dict(), trace_id=record.trace_id)


@router.get("/capabilities")
def kernel_capabilities() -> dict[str, Any]:
    from core.kernel.graph.scheduler_v2 import scheduler_v2_enabled
    from core.kernel.enforce.mode import enforce_mode, hard_lock_mode, legacy_allowed
    from core.kernel.kernel import graph_enabled, kernel_enabled

    return {
        "version": "execution-kernel-v1",
        "capabilities": all_capabilities(),
        "entry": "/v1/kernel/execute",
        "graph_runtime": graph_enabled(),
        "scheduler_v2": scheduler_v2_enabled(),
        "kernel_enabled": kernel_enabled(),
        "kernel_enforce_mode": enforce_mode(),
        "kernel_hard_lock_mode": hard_lock_mode(),
        "kernel_legacy_allowed": legacy_allowed(),
        "graph_version": "execution-graph-kernel-v1",
        "scheduler_version": "execution-scheduler-v2",
        "identity_version": "graph-identity-v1",
        "identity_index": "graph-identity-index-v1",
        "record_version": "execution-record-v1",
        "replay_version": "execution-replay-v1",
    }


class KernelReplayRequest(BaseModel):
    trace_id: Optional[str] = None
    type: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    verify_identity: bool = True


@router.post("/replay")
def kernel_replay(body: KernelReplayRequest) -> dict[str, Any]:
    kernel = get_kernel()

    if body.trace_id and kernel.get_record(body.trace_id):
        return kernel.replay(trace_id=body.trace_id, verify_identity=body.verify_identity)

    if body.type:
        from core.kernel.graph.builder import GraphBuilder

        trace_id = body.trace_id or "replay-probe"
        graph = GraphBuilder().build(
            ExecutionIntent(type=body.type, payload=body.payload, trace_id=trace_id),  # type: ignore[arg-type]
            trace_id,
        )
        return kernel.replay(graph, trace_id=body.trace_id, verify_identity=body.verify_identity)

    raise HTTPException(status_code=400, detail="trace_id with stored record or intent type required")


@router.get("/identity/stats")
def identity_index_stats() -> dict[str, Any]:
    from core.kernel.identity.index_v1 import get_identity_graph_index

    return get_identity_graph_index().stats()


@router.get("/identity/trace/{trace_id}")
def identity_for_trace(trace_id: str) -> dict[str, Any]:
    from core.kernel.identity.index_v1 import get_identity_graph_index

    index = get_identity_graph_index()
    identity = index.get_identity(trace_id)
    if not identity:
        return {"trace_id": trace_id, "identity": None, "equivalent_traces": []}
    return {
        "trace_id": trace_id,
        "identity": identity,
        "equivalent_traces": index.get_traces(identity),
    }


@router.post("/identity/equivalent")
def find_equivalent_graph(body: KernelExecuteRequest) -> dict[str, Any]:
    """Build graph from intent and search equivalence class (no execution)."""
    from core.kernel.graph.builder import GraphBuilder
    from core.kernel.identity.index_v1 import get_identity_graph_index

    trace_id = body.trace_id or "probe-trace"
    graph = GraphBuilder().build(
        ExecutionIntent(
            type=body.type,  # type: ignore[arg-type]
            payload=body.payload,
            trace_id=trace_id,
            source=body.source,
        ),
        trace_id,
    )
    return get_identity_graph_index().find_equivalent_traces(graph, exclude_trace=trace_id)


@router.get("/record/{trace_id}")
def get_execution_record(trace_id: str) -> dict[str, Any]:
    """UI projection entry — read canonical ExecutionRecord by trace."""
    from core.kernel.observe.record_view import read

    kernel = get_kernel()
    try:
        return read(trace_id, kernel).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="execution record not found") from exc


@router.get("/record/{trace_id}/learn")
def get_execution_record_learn(trace_id: str) -> dict[str, Any]:
    """Learn Mode v2 — human cognitive narrative from ExecutionRecord."""
    from core.kernel.observe.learn_view import read_learn_dict

    kernel = get_kernel()
    try:
        return read_learn_dict(trace_id, kernel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/records/recent")
def list_recent_execution_records(limit: int = 40) -> dict[str, Any]:
    """Recent trace_ids from kernel memory + execution_tap persistence."""
    from core.kernel.observe.tap_fallback import list_recent_trace_ids

    kernel = get_kernel()
    seen: list[str] = []
    seen_set: set[str] = set()
    for tid in reversed(kernel.list_record_ids(limit=limit)):
        if tid not in seen_set:
            seen_set.add(tid)
            seen.append(tid)
    for tid in list_recent_trace_ids(limit=limit):
        if tid not in seen_set:
            seen_set.add(tid)
            seen.append(tid)
        if len(seen) >= limit:
            break
    return {"trace_ids": seen[:limit], "count": min(len(seen), limit)}


@router.get("/verify")
def kernel_verify() -> dict[str, Any]:
    """Kernel Final Verification Protocol — single-truth closure audit."""
    from core.kernel.verify.protocol import format_report, run_verification

    report = run_verification()
    return {
        "report": report.to_dict(),
        "formatted": format_report(report),
    }

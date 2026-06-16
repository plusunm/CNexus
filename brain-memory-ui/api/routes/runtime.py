"""Runtime Introspection API — read-only execution observation boundary."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.deps import get_runtime, peek_runtime
from core.runtime.event_loop_offload import offload_sync
from core.runtime.introspection import build_runtime_introspection

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/introspect")
async def introspect_runtime():
    """
    Export live runtime state + trace context + execution tap buffer.
    Read-only — no mutation, no execution side effects.
    """
    runtime = peek_runtime() or get_runtime()
    if runtime is None:
        raise HTTPException(status_code=503, detail="runtime_unavailable")
    try:
        return await offload_sync(lambda: build_runtime_introspection(runtime), timeout_s=20.0)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

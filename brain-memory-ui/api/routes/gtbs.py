"""GTBS / WriteIntent transaction stream for Cognitive Trace Console."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from api.deps import get_runtime, peek_runtime

router = APIRouter(prefix="/gtbs", tags=["gtbs"])


def _read_events(*, limit: int) -> list[dict[str, Any]]:
    runtime = peek_runtime() or get_runtime()
    from core.governance.gtbs.transaction_log import GTBSTransactionLog

    rows = GTBSTransactionLog(runtime.base_dir).read_all()
    if limit and len(rows) > limit:
        return rows[-limit:]
    return rows


@router.get("/events")
async def list_write_intent_events(limit: int = Query(300, ge=1, le=5000)):
    try:
        events = _read_events(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"events": events, "count": len(events)}


@router.websocket("/events/ws")
async def write_intent_stream(websocket: WebSocket):
    """Poll GTBS jsonl and push new tail rows (live mode)."""
    await websocket.accept()
    seen = 0
    try:
        while True:
            try:
                rows = _read_events(limit=5000)
            except Exception:
                rows = []
            if len(rows) > seen:
                for row in rows[seen:]:
                    await websocket.send_json({"type": "write_intent_event", "payload": row})
                seen = len(rows)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass

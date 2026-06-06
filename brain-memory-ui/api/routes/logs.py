from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from api.runtime_log import clear_logs, get_logs, runtime_log, subscribe, unsubscribe

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
async def list_logs(limit: int = Query(100, ge=1, le=500), level: Optional[str] = None):
    return {"logs": get_logs(limit=limit, level=level), "count": len(get_logs(limit=500))}


@router.delete("")
async def reset_logs():
    cleared = clear_logs()
    return {"ok": True, "cleared": cleared}


@router.websocket("/ws")
async def logs_stream(websocket: WebSocket):
    """Live-only stream — initial history comes from GET /logs."""
    await websocket.accept()
    queue = subscribe()
    try:
        while True:
            entry = await queue.get()
            await websocket.send_json(entry)
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe(queue)

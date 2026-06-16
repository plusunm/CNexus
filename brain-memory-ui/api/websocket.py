import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.deps import get_dispatcher, get_llm, get_registry, peek_runtime
from core.runtime.event_loop_offload import EventLoopOffloadTimeout, offload_sync
from core.runtime.boot_protocol import boot_status

router = APIRouter()


@router.websocket("/ws/state")
async def state_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            runtime = peek_runtime()
            if runtime is None:
                payload = {"warming": True, "boot": boot_status()}
            else:
                payload = await asyncio.to_thread(runtime.get_control_plane_snapshot)
            await websocket.send_text(json.dumps(payload, ensure_ascii=False, default=str))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()


@router.websocket("/ws/chat")
async def chat_stream(websocket: WebSocket):
    """Streaming chat — full cognitive loop via dispatcher/kernel."""
    await websocket.accept()
    runtime = peek_runtime()
    if runtime is None:
        await websocket.send_text(json.dumps({"error": "runtime_warming"}))
        await websocket.close()
        return

    registry = get_registry()
    llm = get_llm()

    try:
        while True:
            raw = await websocket.receive_text()
            req = json.loads(raw)
            message = req.get("message", "")
            model_id = req.get("model_id")
            use_memory = req.get("use_memory", True)

            profile = registry.get(model_id) if model_id else registry.get_default()
            if not profile:
                await websocket.send_text(json.dumps({"error": "No model configured"}))
                continue

            try:
                result = await offload_sync(
                    lambda: get_dispatcher().ws_chat(
                        message=message,
                        use_memory=use_memory,
                        llm_client=llm,
                        llm_profile=profile,
                        chat_mode=True,
                    )
                )
                reply = result.get("reply") or result.get("response", "")
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "done",
                            "reply": reply,
                            "ok": result.get("ok", True),
                            "capture_id": result.get("capture_id"),
                        }
                    )
                )
            except EventLoopOffloadTimeout:
                await websocket.send_text(json.dumps({"type": "error", "error": "runtime_timeout"}))
            except Exception as exc:
                await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
    except WebSocketDisconnect:
        pass

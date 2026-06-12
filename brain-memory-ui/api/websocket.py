import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.deps import get_runtime, get_registry, get_llm

router = APIRouter()


@router.websocket("/ws/state")
async def state_stream(websocket: WebSocket):
    await websocket.accept()
    runtime = get_runtime()
    try:
        while True:
            state = runtime.get_current_state()
            await websocket.send_text(json.dumps(state, ensure_ascii=False, default=str))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()


@router.websocket("/ws/chat")
async def chat_stream(websocket: WebSocket):
    """Streaming chat — full cognitive loop via process_interaction."""
    await websocket.accept()
    runtime = get_runtime()
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
                result = runtime.process_interaction(
                    message,
                    use_memory=use_memory,
                    llm_client=llm,
                    llm_profile=profile,
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
            except Exception as exc:
                await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
    except WebSocketDisconnect:
        pass

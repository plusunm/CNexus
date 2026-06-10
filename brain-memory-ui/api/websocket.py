import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.deps import get_runtime

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
    """Streaming chat: client sends JSON {message, model_id?, use_memory?}, receives chunks."""
    await websocket.accept()
    runtime = get_runtime()
    from api.deps import get_registry, get_llm

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

            memory_context = runtime.recall(message) if use_memory else ""
            system = "You are CNexus assistant. Maintain identity continuity.\n"
            if memory_context:
                system += f"\n--- Memory ---\n{memory_context}"

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ]

            # Non-streaming fallback (unified client)
            try:
                reply = llm.chat(profile, messages)
                if use_memory:
                    runtime.capture("user", message, importance=0.65)
                    runtime.capture("assistant", reply, importance=0.55)
                await websocket.send_text(json.dumps({"type": "done", "reply": reply}))
            except Exception as exc:
                await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
    except WebSocketDisconnect:
        pass

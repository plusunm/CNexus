from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_llm, get_registry, get_runtime
from api.runtime_log import runtime_log

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    model_id: Optional[str] = None
    use_memory: bool = True
    temperature: float = Field(0.7, ge=0.0, le=2.0)


@router.post("")
async def chat(req: ChatRequest):
    registry = get_registry()
    profile = registry.get(req.model_id) if req.model_id else registry.get_default()
    if not profile:
        raise HTTPException(400, "No model configured")

    runtime = get_runtime()
    runtime_log("info", "chat", "Incoming message", preview=req.message[:80], use_memory=req.use_memory)

    memory_context = runtime.recall(req.message) if req.use_memory else ""
    if req.use_memory:
        runtime_log("debug", "recall", "Memory context assembled", query=req.message[:60], chars=len(memory_context))

    system = "You are a long-lived AI powered by CNexus.\n"
    if memory_context:
        system += f"\n--- Persistent Memory ---\n{memory_context}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": req.message},
    ]

    try:
        reply = get_llm().chat(profile, messages, temperature=req.temperature)
    except Exception as exc:
        runtime_log("error", "chat", "LLM call failed", error=str(exc))
        raise HTTPException(502, str(exc)) from exc

    capture = {}
    if req.use_memory:
        capture = {
            "user": runtime.capture("user", req.message, importance=0.65),
            "assistant": runtime.capture("assistant", reply, importance=0.55),
        }
        runtime_log("info", "capture", "Chat memories stored", user_id=str(capture.get("user"))[:20])

    runtime_log("info", "chat", "Reply sent", model=profile.name, reply_len=len(reply))

    return {
        "reply": reply,
        "model_id": profile.id,
        "model_name": profile.name,
        "memory_capture": capture,
    }

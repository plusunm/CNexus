from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_llm, get_registry, get_runtime

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
    memory_context = runtime.recall(req.message) if req.use_memory else ""

    system = "You are a long-lived AI powered by Brain-Memory G1.\n"
    if memory_context:
        system += f"\n--- Persistent Memory ---\n{memory_context}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": req.message},
    ]

    try:
        reply = get_llm().chat(profile, messages, temperature=req.temperature)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc

    capture = {}
    if req.use_memory:
        capture = {
            "user": runtime.capture("user", req.message, importance=0.65),
            "assistant": runtime.capture("assistant", reply, importance=0.55),
        }

    return {
        "reply": reply,
        "model_id": profile.id,
        "model_name": profile.name,
        "memory_capture": capture,
    }

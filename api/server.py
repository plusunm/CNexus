import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from brain_memory import BrainMemoryRuntime
from core.llm_client import LLMClient
from core.model_registry import ModelProfile, ModelRegistry

PROJECT_ROOT = Path(os.environ.get("BRAIN_MEMORY_ROOT", Path(__file__).resolve().parent.parent))
WEB_DIR = PROJECT_ROOT / "web"

app = FastAPI(title="Brain-Memory G1 UI", version="1.0.0-g1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_runtime: Optional[BrainMemoryRuntime] = None
_registry: Optional[ModelRegistry] = None
_llm = LLMClient()


def get_runtime() -> BrainMemoryRuntime:
    global _runtime
    if _runtime is None:
        _runtime = BrainMemoryRuntime(project_root=str(PROJECT_ROOT))
    return _runtime


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry(str(PROJECT_ROOT / "config"))
    return _registry


class ModelCreateRequest(BaseModel):
    name: str
    provider: str = "openai_compatible"
    base_url: str
    api_key: str = ""
    model: str
    is_default: bool = False


class ModelUpdateRequest(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None


class ChatRequest(BaseModel):
    message: str
    model_id: Optional[str] = None
    use_memory: bool = True
    temperature: float = Field(0.7, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    reply: str
    model_id: str
    model_name: str
    memory_context_used: bool
    memory_capture: dict


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0-g1"}


@app.get("/api/models")
def list_models():
    return {"models": get_registry().list_public()}


@app.post("/api/models")
def create_model(req: ModelCreateRequest):
    profile = ModelProfile(
        name=req.name,
        provider=req.provider,  # type: ignore
        base_url=req.base_url,
        api_key=req.api_key,
        model=req.model,
        is_default=req.is_default,
    )
    created = get_registry().add(profile)
    from core.model_registry import to_public

    return {"model": to_public(created)}


@app.put("/api/models/{model_id}")
def update_model(model_id: str, req: ModelUpdateRequest):
    updated = get_registry().update(model_id, req.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(404, "Model not found")
    from core.model_registry import to_public

    return {"model": to_public(updated)}


@app.delete("/api/models/{model_id}")
def delete_model(model_id: str):
    if not get_registry().delete(model_id):
        raise HTTPException(404, "Model not found")
    return {"ok": True}


@app.post("/api/models/{model_id}/test")
def test_model(model_id: str):
    profile = get_registry().get(model_id)
    if not profile:
        raise HTTPException(404, "Model not found")
    ok, detail = _llm.test_connection(profile)
    return {"success": ok, "detail": detail}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    registry = get_registry()
    profile = registry.get(req.model_id) if req.model_id else registry.get_default()
    if not profile or not profile.enabled:
        raise HTTPException(400, "No available model. Please add one in Settings.")

    runtime = get_runtime()
    memory_context = ""
    if req.use_memory:
        memory_context = runtime.recall(req.message)

    system_parts = [
        "You are a long-lived AI assistant powered by Brain-Memory G1.",
        "Maintain identity continuity, belief consistency, and narrative coherence.",
    ]
    if memory_context:
        system_parts.append(f"\n--- Persistent Memory Context ---\n{memory_context}")

    messages = [
        {"role": "system", "content": "\n".join(system_parts)},
        {"role": "user", "content": req.message},
    ]

    try:
        reply = _llm.chat(profile, messages, temperature=req.temperature)
    except Exception as exc:
        raise HTTPException(502, f"LLM request failed: {exc}") from exc

    capture_result = {}
    if req.use_memory:
        user_mid = runtime.capture("user", req.message, layer="episodic", importance=0.65)
        asst_mid = runtime.capture("assistant", reply, layer="episodic", importance=0.55)
        capture_result = {"user_memory_id": user_mid, "assistant_memory_id": asst_mid}

    return ChatResponse(
        reply=reply,
        model_id=profile.id,
        model_name=profile.name,
        memory_context_used=req.use_memory,
        memory_capture=capture_result,
    )


@app.post("/api/governance")
def governance():
    return get_runtime().run_governance_cycle()


@app.get("/api/memory/recall")
def recall_preview(q: str):
    return {"context": get_runtime().recall(q)}


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from brain_memory import BrainMemoryRuntime
from core.control_plane.dispatch import AuthorityDispatcher
from core.control_plane.exceptions import ControlDecisionRejected
from core.control_plane.legacy_adapter import LegacyDispatchAdapter
from core.model_registry import ModelProfile, ModelRegistry

PROJECT_ROOT = Path(os.environ.get("BRAIN_MEMORY_ROOT", Path(__file__).resolve().parent.parent))
WEB_DIR = PROJECT_ROOT / "web"

from api.health import deep_health_payload, shallow_health_payload
from api.openai_compatible import router as openai_router  # noqa: E402
from api.v1_endpoints import configure_v1_dependencies, router as v1_spec_router  # noqa: E402
from api.ws_routes import configure_ws_dependencies, router as ws_router  # noqa: E402

app = FastAPI(title="CNexus UI", version="1.0.0")
app.include_router(openai_router)
app.include_router(v1_spec_router, prefix="/v1")
app.include_router(ws_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_runtime: Optional[BrainMemoryRuntime] = None
_registry: Optional[ModelRegistry] = None
_dispatcher: Optional[AuthorityDispatcher] = None
_legacy_adapter: Optional[LegacyDispatchAdapter] = None


def get_runtime() -> BrainMemoryRuntime:
    global _runtime
    if _runtime is None:
        _runtime = BrainMemoryRuntime(project_root=str(PROJECT_ROOT))
    return _runtime


def get_dispatcher() -> AuthorityDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = AuthorityDispatcher(get_runtime())
    return _dispatcher


def get_legacy_adapter() -> LegacyDispatchAdapter:
    global _legacy_adapter
    if _legacy_adapter is None:
        _legacy_adapter = LegacyDispatchAdapter(get_dispatcher())
    return _legacy_adapter


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry(str(PROJECT_ROOT / "config"))
    return _registry


def get_llm():
    return get_runtime().llm_client


configure_v1_dependencies(
    get_runtime=get_runtime,
    get_llm=get_llm,
    get_registry=get_registry,
    get_legacy_adapter=get_legacy_adapter,
)
configure_ws_dependencies(
    get_runtime=get_runtime,
    get_llm=get_llm,
    get_registry=get_registry,
    get_legacy_adapter=get_legacy_adapter,
)


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
    return shallow_health_payload()


@app.get("/api/health/ready")
def health_ready():
    payload = deep_health_payload(get_runtime())
    if payload["status"] == "not_ready":
        raise HTTPException(status_code=503, detail=payload)
    return payload


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
    ok, detail = get_llm().test_connection(profile)
    return {"success": ok, "detail": detail}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    registry = get_registry()
    profile = registry.get(req.model_id) if req.model_id else registry.get_default()
    if not profile or not profile.enabled:
        raise HTTPException(400, "No available model. Please add one in Settings.")

    try:
        result = get_legacy_adapter().chat(
            message=req.message,
            use_memory=req.use_memory,
            temperature=req.temperature,
            llm_client=get_llm(),
            llm_profile=profile,
        )
    except ControlDecisionRejected as exc:
        raise HTTPException(403, f"control plane rejected: {exc.decision.reason}") from exc
    except Exception as exc:
        raise HTTPException(502, f"LLM request failed: {exc}") from exc

    reply = result.get("reply") or result.get("response", "")
    capture_result = {}
    if req.use_memory:
        capture_result = {
            "pipeline": "process_interaction",
            "ok": result.get("ok", True),
            "capture_id": result.get("capture_id"),
            "assistant_capture_id": result.get("assistant_capture_id"),
        }

    return ChatResponse(
        reply=reply,
        model_id=profile.id,
        model_name=profile.name,
        memory_context_used=req.use_memory,
        memory_capture=capture_result,
    )


@app.post("/api/governance")
def governance():
    try:
        return get_legacy_adapter().governance_cycle()
    except ControlDecisionRejected as exc:
        raise HTTPException(403, f"control plane rejected: {exc.decision.reason}") from exc


@app.get("/api/memory/recall")
def recall_preview(q: str):
    try:
        return {"context": get_legacy_adapter().recall_preview(q)}
    except ControlDecisionRejected as exc:
        raise HTTPException(403, f"control plane rejected: {exc.decision.reason}") from exc


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

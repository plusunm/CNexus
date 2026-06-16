from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from urllib.parse import urlparse, urlunparse

from api.deps import get_registry, get_runtime, get_llm
from core.model_registry import ModelProfile, ProviderType, to_public

router = APIRouter(prefix="/models", tags=["models"])


def _normalize_provider(provider: str) -> ProviderType:
    if provider in ("ollama", "openai", "openai_compatible"):
        return provider  # type: ignore[return-value]
    return "openai_compatible"


def _normalize_base_url(base_url: str, *, provider: str = "") -> str:
    url = base_url.strip().rstrip("/")
    if not url:
        return "https://api.deepseek.com"
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    is_local = host in ("localhost", "127.0.0.1") or provider == "ollama"
    if url.startswith("http://") and not is_local:
        url = "https://" + url[len("http://") :]
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = (parsed.path or "").rstrip("/")
    if "deepseek.com" in host:
        # Official OpenAI-compatible base (SDK adds /v1 at request time).
        if path in ("", "/v1"):
            return "https://api.deepseek.com"
    path_parts = [p for p in path.split("/") if p]
    has_version = any(p.startswith("v") and p[1:].isdigit() for p in path_parts)
    if not path_parts or (not has_version and "deepseek.com" in host):
        return urlunparse(parsed._replace(path="")).rstrip("/")
    return urlunparse(parsed).rstrip("/")


def _normalize_model_id(model: str) -> str:
    legacy = {
        "deepseek-chat": "deepseek-v4-flash",
        "deepseek-reasoner": "deepseek-v4-pro",
    }
    return legacy.get(model.strip(), model.strip())


class ModelCreate(BaseModel):
    name: str
    provider: str = "openai_compatible"
    base_url: str
    api_key: str = ""
    model: str
    is_default: bool = False


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None


@router.get("")
async def list_models():
    return {"models": get_registry().list_public()}


@router.post("")
async def create_model(req: ModelCreate):
    p = ModelProfile(
        name=req.name,
        provider=_normalize_provider(req.provider),
        base_url=_normalize_base_url(req.base_url, provider=req.provider),
        api_key=req.api_key,
        model=_normalize_model_id(req.model),
        is_default=req.is_default,
    )
    return {"model": to_public(get_registry().add(p))}


@router.put("/{model_id}")
async def update_model(model_id: str, req: ModelUpdate):
    updates = req.model_dump(exclude_none=True)
    if "provider" in updates:
        updates["provider"] = _normalize_provider(str(updates["provider"]))
    if "base_url" in updates and updates["base_url"]:
        provider = str(updates.get("provider") or "")
        if not provider:
            existing = get_registry().get(model_id)
            provider = existing.provider if existing else ""
        updates["base_url"] = _normalize_base_url(str(updates["base_url"]), provider=provider)
    if "model" in updates and updates["model"]:
        updates["model"] = _normalize_model_id(str(updates["model"]))
    updated = get_registry().update(model_id, updates)
    if not updated:
        raise HTTPException(404, "Not found")
    return {"model": to_public(updated)}


@router.delete("/{model_id}")
async def delete_model(model_id: str):
    if not get_registry().delete(model_id):
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.post("/{model_id}/test")
async def test_model(model_id: str):
    profile = get_registry().get(model_id)
    if not profile:
        raise HTTPException(404, "Not found")
    ok, detail = get_llm().test_connection(profile)
    return {"success": ok, "detail": detail}

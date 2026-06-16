from fastapi import APIRouter

from pydantic import BaseModel

from api.runtime_log import runtime_log
from core.ollama_manager import get_ollama_status, start_ollama, stop_ollama

router = APIRouter(prefix="/ollama", tags=["ollama"])


class OllamaStatusResponse(BaseModel):
    installed: bool
    binary_found: bool
    running: bool
    host: str
    download_url: str
    binary_path: str | None = None


class OllamaActionResponse(BaseModel):
    ok: bool
    detail: str
    running: bool
    download_url: str | None = None


@router.get("/status", response_model=OllamaStatusResponse)
async def ollama_status():
    """Probe Ollama directly — must not block on BrainMemoryRuntime warm."""
    import asyncio
    import os

    from core.ollama_manager import resolve_ollama_host

    host = resolve_ollama_host()
    runtime_log(
        "info",
        "ollama",
        "Status probe",
        detail={
            "host": host,
            "OLLAMA_HOST": os.environ.get("OLLAMA_HOST", ""),
            "NO_PROXY": os.environ.get("NO_PROXY", os.environ.get("no_proxy", "")),
        },
    )
    payload = await asyncio.to_thread(get_ollama_status)
    return OllamaStatusResponse(**payload)


@router.post("/start", response_model=OllamaActionResponse)
async def ollama_start():
    import asyncio

    payload = await asyncio.to_thread(start_ollama)
    runtime_log("info", "ollama", "Start requested", detail=payload.get("detail"))
    return OllamaActionResponse(
        ok=bool(payload.get("ok")),
        detail=str(payload.get("detail", "")),
        running=bool(payload.get("running")),
        download_url=payload.get("download_url"),
    )


@router.post("/stop", response_model=OllamaActionResponse)
async def ollama_stop():
    import asyncio

    payload = await asyncio.to_thread(stop_ollama)
    runtime_log("info", "ollama", "Stop requested", detail=payload.get("detail"))
    return OllamaActionResponse(
        ok=bool(payload.get("ok")),
        detail=str(payload.get("detail", "")),
        running=bool(payload.get("running")),
        download_url=payload.get("download_url"),
    )

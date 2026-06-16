"""Shared WebSocket routes — /ws/interact (v1.1 spec)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.v1_endpoints import (
    InteractRequest,
    _build_attention_state,
    _map_interact_response,
)
from core.runtime.event_loop_offload import EventLoopOffloadTimeout, offload_sync

from core.control_plane.legacy_adapter import LegacyDispatchAdapter

RuntimeProvider = Callable[[], Any]
LLMProvider = Callable[[], Any]
RegistryProvider = Callable[[], Any]
LegacyAdapterProvider = Callable[[], LegacyDispatchAdapter]

_runtime_provider: Optional[RuntimeProvider] = None
_llm_provider: Optional[LLMProvider] = None
_registry_provider: Optional[RegistryProvider] = None
_legacy_adapter_provider: Optional[LegacyAdapterProvider] = None

router = APIRouter()


def configure_ws_dependencies(
    *,
    get_runtime: RuntimeProvider,
    get_llm: Optional[LLMProvider] = None,
    get_registry: Optional[RegistryProvider] = None,
    get_legacy_adapter: Optional[LegacyAdapterProvider] = None,
) -> None:
    global _runtime_provider, _llm_provider, _registry_provider, _legacy_adapter_provider
    _runtime_provider = get_runtime
    _llm_provider = get_llm
    _registry_provider = get_registry
    _legacy_adapter_provider = get_legacy_adapter


@router.websocket("/ws/interact")
async def interact_stream(websocket: WebSocket):
    """v1.1 interact stream: attention update → done (full InteractResponse)."""
    if _runtime_provider is None:
        await websocket.close(code=1011)
        return

    await websocket.accept()
    runtime = _runtime_provider()

    try:
        while True:
            raw = await websocket.receive_text()
            req_data = json.loads(raw)
            req = InteractRequest.model_validate(req_data)
            options = req.options or {}
            meta = dict(req.metadata or {})
            if req.session_id:
                meta.setdefault("session_id", req.session_id)
            use_memory = bool(
                options.get("use_memory", options.get("enable_memory", meta.get("enable_memory", True)))
            )
            temperature = float(options.get("temperature", 0.7))
            allow_proactive = options.get("governance_level", "normal") != "strict"

            await websocket.send_text(
                json.dumps(
                    {
                        "type": "attention",
                        "attention_state": _build_attention_state(runtime),
                        "user_id": req.user_id,
                        "session_id": req.session_id,
                    },
                    ensure_ascii=False,
                    default=str,
                )
            )

            llm_client = None
            llm_profile = None
            if _llm_provider and _registry_provider:
                registry = _registry_provider()
                profile = registry.get_default()
                if profile and profile.enabled:
                    llm_client = _llm_provider()
                    llm_profile = profile

            if _legacy_adapter_provider is None:
                from core.kernel.enforce.exceptions import KernelViolation

                raise KernelViolation("WS_LEGACY_ADAPTER_REQUIRED", "/ws/interact")

            def _interact():
                return _legacy_adapter_provider().interact(
                    message=req.message,
                    user_id=req.user_id,
                    metadata=meta,
                    use_memory=use_memory,
                    temperature=temperature,
                    llm_client=llm_client,
                    llm_profile=llm_profile,
                    allow_proactive=allow_proactive,
                    channel="legacy-ws-api",
                )

            try:
                result = await offload_sync(_interact)
            except EventLoopOffloadTimeout:
                await websocket.send_text(json.dumps({"type": "error", "error": "runtime_timeout"}))
                continue
            response = _map_interact_response(result, req, runtime)
            payload = response.model_dump()
            reply = payload.get("response") or ""
            if reply:
                await websocket.send_text(
                    json.dumps(
                        {"type": "delta", "delta": reply},
                        ensure_ascii=False,
                        default=str,
                    )
                )
            await websocket.send_text(
                json.dumps({"type": "done", **payload}, ensure_ascii=False, default=str)
            )
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))

"""Named warmup handlers — bus-safe dispatch (handler id, not callables)."""

from __future__ import annotations

from typing import Any, Callable, Dict

from pathlib import Path

HandlerFn = Callable[[Any], None]

_WARMUP_HANDLERS: Dict[str, HandlerFn] = {}
_PROCESS_SAFE_HANDLERS = {"noop_ping", "disk_blocks_ping"}
_handlers_ready = False


def _ensure_handlers() -> None:
    global _handlers_ready
    if _handlers_ready:
        return
    from core.runtime.cognitive_warmup_adapter import CognitiveWarmupAdapter

    register_warmup_handler("cdg_init", CognitiveWarmupAdapter._task_cdg_init)
    register_warmup_handler("memory_warmup", CognitiveWarmupAdapter._task_memory_warmup)
    register_warmup_handler("governance_init", CognitiveWarmupAdapter._task_governance_init)
    register_warmup_handler("reflection_seed", CognitiveWarmupAdapter._task_reflection_seed)
    _handlers_ready = True


def register_warmup_handler(name: str, fn: HandlerFn) -> None:
    _WARMUP_HANDLERS[name] = fn


def dispatch_warmup_handler(handler: str, runtime: Any, *, timeout_s: float = 3.0) -> Dict[str, Any]:
    _ensure_handlers()
    fn = _WARMUP_HANDLERS.get(handler)
    if fn is None:
        return {"status": "unknown_handler", "handler": handler}
    fn(runtime)
    return {"status": "ok", "handler": handler, "timeout_s": timeout_s}


def run_process_safe_task(handler: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level entry for ProcessPoolExecutor — must be picklable."""
    if handler == "noop_ping":
        return {"status": "ok", "handler": handler}
    if handler == "disk_blocks_ping":
        base_dir = payload.get("base_dir")
        if not base_dir:
            return {"status": "failed", "error": "missing base_dir"}
        index = Path(str(base_dir)) / "blocks" / "index.json"
        return {"status": "ok", "blocks_index_exists": index.exists()}
    return {"status": "unsupported_process_handler", "handler": handler}


def is_process_safe(handler: str) -> bool:
    return handler in _PROCESS_SAFE_HANDLERS

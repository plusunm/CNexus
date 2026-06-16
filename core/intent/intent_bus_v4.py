"""Intent bus v4 — publish intent events to registered handlers."""

from __future__ import annotations

import os
import threading
from typing import Any, Awaitable, Callable, Dict, List, Optional

IntentHandler = Callable[[Dict[str, Any]], Awaitable[Any]]
BusResult = Dict[str, Any]

_global_bus: Optional["IntentBusV4"] = None
_bus_lock = threading.Lock()


def prompt_minimal_v4_enabled() -> bool:
    flag = os.environ.get("CNEXUS_PROMPT_MINIMAL_V4", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


class IntentBusV4:
    """Route intents to handlers — no prompt layer."""

    def __init__(self) -> None:
        self.subscribers: Dict[str, List[IntentHandler]] = {}

    def register(self, intent: str, handler: IntentHandler) -> None:
        key = str(intent)
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(handler)

    async def emit(self, intent: str, payload: Dict[str, Any]) -> BusResult:
        key = str(intent)
        handlers = self.subscribers.get(key)
        if not handlers:
            return {"status": "no_handler", "intent": key, "mode": "promptless_v4"}

        results: List[Any] = []
        for handler in handlers:
            results.append(await handler(payload))

        return {
            "intent": key,
            "results": results,
            "mode": "promptless_v4",
            "status": "ok",
        }


def get_intent_bus(runtime: Optional[Any] = None) -> IntentBusV4:
    global _global_bus
    if runtime is not None:
        existing = getattr(runtime, "_intent_bus_v4", None)
        if isinstance(existing, IntentBusV4):
            return existing
        bus = IntentBusV4()
        setattr(runtime, "_intent_bus_v4", bus)
        return bus
    with _bus_lock:
        if _global_bus is None:
            _global_bus = IntentBusV4()
        return _global_bus

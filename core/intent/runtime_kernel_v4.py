"""Runtime kernel v4 — intent bus orchestration, no prompt interpretation."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from core.intent.execution_graph_v4 import ExecutionGraphV4, get_execution_graph_v4
from core.intent.intent_bus_v4 import IntentBusV4, get_intent_bus

_global_kernel: Optional["RuntimeKernelV4"] = None
_kernel_lock = threading.Lock()


class RuntimeKernelV4:
    """Wire intent bus to execution graph — promptless request handling."""

    def __init__(
        self,
        bus: IntentBusV4,
        graph: ExecutionGraphV4,
    ) -> None:
        self.bus = bus
        self.graph = graph
        self._wired = False

    def wire_handlers(self) -> None:
        if self._wired:
            return
        for intent in ("chat", "status", "memory_query"):
            self.bus.register(intent, self._handler_for(intent))
        self._wired = True

    def _handler_for(self, intent: str):
        async def _handler(payload: Dict[str, Any]) -> Any:
            return await self.graph.execute(intent, payload)

        return _handler

    async def handle_request(self, intent: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.wire_handlers()
        return await self.bus.emit(intent, payload)


class APIv4:
    """HTTP-facing promptless API — intent bus only."""

    def __init__(self, kernel: RuntimeKernelV4) -> None:
        self.kernel = kernel

    async def endpoint(self, request: Dict[str, Any]) -> Dict[str, Any]:
        intent = str(request.get("intent") or "chat")
        result = await self.kernel.handle_request(intent, request)
        return {
            "response": result,
            "mode": "prompt_minimal_v4",
            "execution": "intent_bus",
        }


def extract_v4_chat_response(bus_result: Dict[str, Any]) -> Any:
    """Pull LLM text from intent bus chat result."""
    if bus_result.get("status") == "no_handler":
        return {"status": "no_handler", "mode": "prompt_minimal_v4"}

    results = bus_result.get("results") or []
    if not results:
        return bus_result

    first = results[0]
    if isinstance(first, dict):
        if first.get("status") == "timeout":
            return {"status": "timeout", "mode": "prompt_minimal_v4"}
        return first.get("response", first)
    return first


def get_runtime_kernel_v4(
    runtime: Optional[Any] = None,
    *,
    llm_client: Optional[Any] = None,
    profile: Optional[Any] = None,
    timeout_s: float = 3.0,
) -> RuntimeKernelV4:
    if runtime is not None:
        existing = getattr(runtime, "_runtime_kernel_v4", None)
        if isinstance(existing, RuntimeKernelV4):
            return existing
        from core.intent.llm_backend_v4 import get_llm_backend_v4

        bus = get_intent_bus(runtime)
        backend = get_llm_backend_v4(
            runtime,
            llm_client=llm_client,
            profile=profile,
            timeout_s=timeout_s,
        )
        graph = get_execution_graph_v4(runtime, llm_backend=backend)
        kernel = RuntimeKernelV4(bus, graph)
        kernel.wire_handlers()
        setattr(runtime, "_runtime_kernel_v4", kernel)
        return kernel

    global _global_kernel
    with _kernel_lock:
        if _global_kernel is None:
            bus = get_intent_bus(None)
            graph = get_execution_graph_v4(None)
            _global_kernel = RuntimeKernelV4(bus, graph)
            _global_kernel.wire_handlers()
        return _global_kernel

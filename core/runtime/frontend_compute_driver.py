"""Frontend compute driver — UI triggers predictive compute graph."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from core.runtime.compute_plans import chat_compute_plan, overview_compute_plan, status_compute_plan
from core.runtime.predictive_compute_graph import PredictiveComputeGraph

_driver: Optional["FrontendComputeDriver"] = None
_driver_lock = threading.Lock()


def init_graph(driver: "FrontendComputeDriver") -> None:
    driver.graph.register_intent("chat", chat_compute_plan)
    driver.graph.register_intent("status", status_compute_plan)
    driver.graph.register_intent("overview", overview_compute_plan)


class FrontendComputeDriver:
    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime
        self.graph = PredictiveComputeGraph(runtime)
        init_graph(self)

    async def on_user_event(self, intent: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = await self.graph.execute_from_ui(intent, dict(payload or {}))
        self.render(result)
        return result

    def render(self, result: Dict[str, Any]) -> None:
        """Hook for UI-side render callbacks — no-op on server."""
        _ = result


def get_frontend_compute_driver(runtime: Optional[Any] = None) -> FrontendComputeDriver:
    global _driver
    with _driver_lock:
        if _driver is None or (runtime is not None and _driver.runtime is not runtime):
            _driver = FrontendComputeDriver(runtime)
        elif runtime is not None:
            _driver.runtime = runtime
            _driver.graph.runtime = runtime
        return _driver

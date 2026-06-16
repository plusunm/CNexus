"""Predictive compute graph — UI intent → async compute plan."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional

ComputePlan = Callable[[Any, Dict[str, Any]], Awaitable[Dict[str, Any]]]


class PredictiveComputeGraph:
    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime
        self.graph: Dict[str, ComputePlan] = {}

    def register_intent(self, intent: str, compute_plan: ComputePlan) -> None:
        self.graph[intent] = compute_plan

    async def execute_from_ui(self, intent: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        plan = self.graph.get(intent)
        if plan is None:
            return {"status": "no_plan", "intent": intent}
        return await plan(self.runtime, payload)

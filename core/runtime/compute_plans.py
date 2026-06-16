"""Pre-registered compute plans for UI-driven intents."""

from __future__ import annotations

from typing import Any, Dict

from core.runtime.llm_background_side_effects import schedule_background_side_effects
from core.runtime.llm_fast_lane import LLMFastLane, _resolve_execution_mode, llm_fast_lane_enabled
from core.runtime.runtime_kernel import RuntimeKernel


async def chat_compute_plan(runtime: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    user_input = str(payload.get("input") or payload.get("message") or "")

    if llm_fast_lane_enabled():
        lane = LLMFastLane(runtime)
        intent = str(payload.get("intent") or "chat")
        delta = payload.get("delta")
        if not isinstance(delta, dict):
            delta = None
        result = await lane.generate(
            user_input,
            intent=intent,
            context_delta=delta,
        )
        schedule_background_side_effects(runtime, user_input)
        mode = lane._prompt_mode
        execution = _resolve_execution_mode(mode)
        if isinstance(result, dict) and result.get("status") == "timeout":
            return {
                "type": "chat_result",
                "status": "timeout",
                "path": "fast_lane_v1",
                "mode": result.get("mode") or mode,
                "execution": execution,
            }
        return {
            "type": "chat_result",
            "status": "ok",
            "data": result,
            "path": "fast_lane_v1",
            "mode": mode,
            "execution": execution,
        }

    kernel = RuntimeKernel(runtime)
    response = await kernel.llm_generate(user_input)
    schedule_background_side_effects(runtime, user_input)
    return {
        "type": "chat_result",
        "status": "ok",
        "data": response,
    }


async def status_compute_plan(runtime: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    kernel = RuntimeKernel(runtime)
    return {
        "type": "status",
        "status": "ok",
        "l3": kernel.l3_queue_length(),
        "cluster": kernel.cluster_quick_probe(),
        "intent": payload.get("source", "ui"),
    }


async def overview_compute_plan(runtime: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    kernel = RuntimeKernel(runtime)
    schedule_background_side_effects(runtime, str(payload.get("query") or ""))
    return {
        "type": "overview",
        "status": "ok",
        "cluster": kernel.cluster_quick_probe(),
        "l3": kernel.l3_queue_length(),
    }

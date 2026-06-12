"""Chat path observation adapter — P1: /chat → Observation Bus."""

from __future__ import annotations

from typing import Any

from core.observation.gateway import ObservationGateway


def _capture_summary(capture: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for role, result in capture.items():
        if isinstance(result, str):
            summary[role] = {"denied": result.startswith("denied:"), "result": result[:80]}
        elif isinstance(result, dict):
            summary[role] = {
                "denied": False,
                "memory_id_prefix": str(result.get("memory_id", ""))[:8],
            }
        else:
            summary[role] = {"denied": False, "result_type": type(result).__name__}
    return summary


def record_chat_observation(
    runtime: Any,
    *,
    message: str,
    use_memory: bool,
    memory_context_chars: int,
    capture: dict[str, Any],
    model_name: str,
    pre_state: dict[str, Any] | None = None,
    pipeline: str = "chat_recall_llm_capture",
) -> dict[str, Any]:
    """
    Append chat turn to Observation Bus; optionally mirror GTBS shadow (opt-in on runtime).
    Does NOT pass L3/L8 signals into runtime — observation only.
    """
    gateway = ObservationGateway(runtime.base_dir)

    payload = {
        "channel": "chat",
        "message_preview": message[:120],
        "use_memory": use_memory,
        "memory_context_chars": memory_context_chars,
        "model_name": model_name,
        "capture_summary": _capture_summary(capture),
        "routing_trace": {
            "pipeline": pipeline,
            "recall_path": "g2_cognitive_recall" if getattr(runtime, "runtime_mode", "") == "g2" else "hybrid_recall",
            "use_memory": use_memory,
        },
    }

    record = gateway.ingest(source="cnexus.chat", event_type="chat_turn", payload=payload)

    shadow_record: dict[str, Any] | None = None
    if use_memory and pre_state is not None and runtime._gtbs_shadow_enabled():
        from core.governance.cdg import snapshot_cdg_state

        post_state = snapshot_cdg_state(runtime)
        shadow_record = runtime._gtbs_shadow_observe(
            pre_state,
            post_state,
            context={
                "channel": "chat",
                "observation_gateway": True,
                "message_preview": message[:80],
            },
            proposal=None,
        )

    return {
        "observation_event": record,
        "observation_stream": str(gateway.stream_path),
        "shadow_mirrored": shadow_record is not None,
    }

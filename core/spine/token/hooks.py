"""Runtime token hooks — intercept spine / LLM / explain emission sites."""

from __future__ import annotations

from typing import Any, Optional

from core.spine.integration import get_spine_writer
from core.spine.token.token_emitter import emit_token_event
from core.spine.token.token_schema import (
    classify_cost_level,
    infer_phase_from_event,
    infer_source_from_event,
)
from core.spine.types import SpineEvent


def resolve_spine_base_dir() -> Optional[str]:
    from core.spine.token.token_store import _persist_base

    if _persist_base is not None:
        return str(_persist_base)
    writer = get_spine_writer()
    if writer is None:
        return None
    return str(writer.path.parent.parent)


def _chars_to_tokens(chars: int) -> int:
    return max(1, int(chars) // 4)


def emit_tokens_for_spine_event(
    event: SpineEvent,
    *,
    base_dir: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Emit token event bound to a persisted spine row."""
    effective_base = base_dir or resolve_spine_base_dir()
    if not effective_base:
        return None

    row = event.to_dict()
    payload = row.get("payload") or {}
    usage = payload.get("usage") or payload.get("token_usage") or {}

    tin = tokens_in
    tout = tokens_out
    if tin is None or tout is None:
        if usage:
            tin = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            tout = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        if tin is None or tout is None:
            from core.spine.token.token_schema import estimate_tokens_from_event

            est_in, est_out = estimate_tokens_from_event(row)
            tin = tin if tin is not None else est_in
            tout = tout if tout is not None else est_out

    source = infer_source_from_event(row)
    phase = infer_phase_from_event(row)
    total = int(tin) + int(tout)

    return emit_token_event(
        event.trace_id,
        event_id=event.event_id,
        source=source,
        tokens_in=int(tin),
        tokens_out=int(tout),
        phase=phase,
        spine_event_id=event.event_id,
        base_dir=effective_base,
        mode=str(row.get("event_type") or source),
        entry=str(row.get("entry") or row.get("summary") or ""),
    )


def emit_tokens_for_llm_usage(
    trace_id: str,
    *,
    spine_event_id: Optional[str] = None,
    prompt_tokens: int,
    completion_tokens: int,
    base_dir: Optional[str] = None,
    caller: str = "",
) -> Optional[dict[str, Any]]:
    effective_base = base_dir or resolve_spine_base_dir()
    if not effective_base or not trace_id:
        return None
    return emit_token_event(
        trace_id,
        event_id=spine_event_id,
        source="llm_generate",
        tokens_in=prompt_tokens,
        tokens_out=completion_tokens,
        phase="EXEC",
        spine_event_id=spine_event_id,
        base_dir=effective_base,
        mode="llm_call",
        entry=caller,
    )


def emit_tokens_for_llm_chars(
    trace_id: str,
    *,
    spine_event_id: Optional[str] = None,
    input_chars: int,
    output_chars: int,
    base_dir: Optional[str] = None,
    caller: str = "",
) -> Optional[dict[str, Any]]:
    return emit_tokens_for_llm_usage(
        trace_id,
        spine_event_id=spine_event_id,
        prompt_tokens=_chars_to_tokens(input_chars),
        completion_tokens=_chars_to_tokens(output_chars),
        base_dir=base_dir,
        caller=caller,
    )


def emit_tokens_for_explain(
    trace_id: str,
    narrative: str,
    *,
    base_dir: Optional[str] = None,
    spine_event_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    effective_base = base_dir or resolve_spine_base_dir()
    if not effective_base or not trace_id:
        return None
    out_tokens = _chars_to_tokens(len(narrative or ""))
    in_tokens = max(80, out_tokens // 3)
    return emit_token_event(
        trace_id,
        source="explain_v3",
        tokens_in=in_tokens,
        tokens_out=out_tokens,
        phase="EXPLAIN",
        spine_event_id=spine_event_id,
        base_dir=effective_base,
        mode="explain_v3",
        entry="explain_v3",
    )


def emit_tokens_for_recall(
    trace_id: str,
    *,
    result_count: int,
    query_chars: int,
    spine_event_id: Optional[str] = None,
    base_dir: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    effective_base = base_dir or resolve_spine_base_dir()
    if not effective_base or not trace_id:
        return None
    tin = _chars_to_tokens(query_chars) + result_count * 40
    tout = result_count * 20
    return emit_token_event(
        trace_id,
        event_id=spine_event_id,
        source="recall",
        tokens_in=tin,
        tokens_out=tout,
        phase="RECALL",
        spine_event_id=spine_event_id,
        base_dir=effective_base,
        mode="recall",
        entry="recall_pipeline",
    )


def maybe_emit_for_event_type(
    event: SpineEvent,
    *,
    base_dir: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Route spine event types to appropriate token emitters."""
    etype = str(event.event_type or "").lower()
    extra = extra or {}

    if etype == "llm_call":
        if "prompt_tokens" in extra or "completion_tokens" in extra:
            return emit_tokens_for_llm_usage(
                event.trace_id,
                spine_event_id=event.event_id,
                prompt_tokens=int(extra.get("prompt_tokens") or 0),
                completion_tokens=int(extra.get("completion_tokens") or 0),
                base_dir=base_dir,
                caller=str(extra.get("caller") or ""),
            )
        if "input_chars" in extra or "output_chars" in extra:
            return emit_tokens_for_llm_chars(
                event.trace_id,
                spine_event_id=event.event_id,
                input_chars=int(extra.get("input_chars") or 0),
                output_chars=int(extra.get("output_chars") or 0),
                base_dir=base_dir,
                caller=str(extra.get("caller") or ""),
            )

    if etype == "recall":
        payload = event.payload if isinstance(event.payload, dict) else {}
        return emit_tokens_for_recall(
            event.trace_id,
            result_count=int(extra.get("result_count") or payload.get("result_count") or 0),
            query_chars=int(extra.get("query_chars") or len(str(payload.get("query") or ""))),
            spine_event_id=event.event_id,
            base_dir=base_dir,
        )

    if etype == "llm_call":
        # Defer to post-LLM hook with actual usage/chars
        return None

    if etype in ("control", "write_intent"):
        return emit_tokens_for_spine_event(event, base_dir=base_dir, tokens_in=50, tokens_out=20)

    if etype in ("chat", "memory_mutation"):
        return emit_tokens_for_spine_event(event, base_dir=base_dir)

    return None

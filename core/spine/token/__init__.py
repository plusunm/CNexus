"""Token layer — execution-attributed resource observability."""

from core.spine.token.binding import TokenExecutionBinder, bind_tokens_to_execution
from core.spine.token.hooks import (
    emit_tokens_for_explain,
    emit_tokens_for_llm_chars,
    emit_tokens_for_llm_usage,
    emit_tokens_for_recall,
    emit_tokens_for_spine_event,
    maybe_emit_for_event_type,
)
from core.spine.token.service import build_token_observatory, build_trace_token_report
from core.spine.token.token_emitter import emit_token_event
from core.spine.token.token_schema import TokenEvent, TokenTraceSummary

__all__ = [
    "TokenEvent",
    "TokenTraceSummary",
    "TokenExecutionBinder",
    "bind_tokens_to_execution",
    "emit_token_event",
    "build_trace_token_report",
    "build_token_observatory",
    "emit_tokens_for_explain",
    "emit_tokens_for_llm_chars",
    "emit_tokens_for_llm_usage",
    "emit_tokens_for_recall",
    "emit_tokens_for_spine_event",
    "maybe_emit_for_event_type",
]

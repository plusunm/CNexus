"""Minimal prompt builder v1 — sync Layer-0 only (input + trace + mode)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from core.runtime.trace_context import get_trace_id, start_trace

PromptDict = Dict[str, Any]


def prompt_minimal_v1_enabled() -> bool:
    flag = os.environ.get("CNEXUS_PROMPT_MINIMAL_V1", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def resolve_trace_id(runtime: Optional[Any] = None) -> str:
    trace_fn = getattr(runtime, "trace_id", None) if runtime is not None else None
    if callable(trace_fn):
        try:
            tid = str(trace_fn() or "").strip()
            if tid:
                return tid
        except Exception:
            pass
    existing = get_trace_id()
    if existing:
        return existing
    return start_trace()


class MinimalPromptBuilderV1:
    """Build Layer-0 prompt — no inline memory / spine / governance."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime

    def build(self, user_input: str) -> PromptDict:
        return {
            "input": str(user_input),
            "mode": "minimal_v1",
            "trace_id": resolve_trace_id(self.runtime),
        }


def extract_user_text(prompt: PromptDict | str) -> str:
    if isinstance(prompt, dict):
        return str(prompt.get("input") or "")
    return str(prompt)


def get_minimal_builder(runtime: Optional[Any] = None) -> MinimalPromptBuilderV1:
    return MinimalPromptBuilderV1(runtime)

"""Cost model C for IR steps."""

from __future__ import annotations

from typing import Any, Dict


def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


def step_cost_delta(op: str, *, output: str = "", latency_ms: int = 0) -> Dict[str, Any]:
    tokens = estimate_tokens(output) if op in ("BUILD_CONTEXT", "CALL_LLM", "FILTER", "RETRIEVE") else 0
    if op == "CALL_LLM":
        tokens = max(tokens, estimate_tokens(output))
    return {
        "tokens_est": tokens,
        "latency_ms": max(0, latency_ms),
    }


def risk_penalty(governance_blocked: bool) -> int:
    return 100 if governance_blocked else 0

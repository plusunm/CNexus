"""X3-b — read-only observe payloads normalized for API contracts."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


def normalize_memory_stats(raw: Any) -> Dict[str, Any]:
    """Coerce observe_read('memory_stats') into MemoryStatsResponse shape."""
    if raw is None:
        data: Dict[str, Any] = {}
    elif isinstance(raw, dict):
        data = dict(raw)
    elif hasattr(raw, "to_dict"):
        data = dict(raw.to_dict())
    else:
        data = {}

    by_layer = data.get("by_layer")
    if not isinstance(by_layer, dict):
        by_layer = {}

    total = data.get("total")
    if total is None:
        total = data.get("total_memories") or data.get("episodic_count") or 0

    return {
        "total": int(total or 0),
        "by_layer": dict(by_layer),
        "avg_importance": float(data.get("avg_importance") or 0.0),
        "avg_decay_factor": float(data.get("avg_decay_factor") or 1.0),
        "high_access_count": int(data.get("high_access_count") or 0),
    }


def normalize_governance_state(raw: Any) -> Dict[str, Any]:
    """Ensure governance observe payload is a dict (ExecutionRecord legacy responses excluded)."""
    if isinstance(raw, dict):
        return dict(raw)
    if hasattr(raw, "to_dict"):
        converted = raw.to_dict()
        if isinstance(converted, dict):
            return converted
    return {}


def observe_memory_stats(observe_read: Callable[..., Any]) -> Dict[str, Any]:
    return normalize_memory_stats(observe_read("memory_stats"))


def observe_governance_state(observe_read: Callable[..., Any]) -> Dict[str, Any]:
    return normalize_governance_state(observe_read("governance_state"))

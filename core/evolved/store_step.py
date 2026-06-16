"""STORE_step — Runbook Layer 1/5 memory write hook (Σ.M ownership)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.evolved.sigma_mapping import memory_block_to_sigma_m, sigma_m_to_memory_block_patch

STORE_INTENTS = frozenset(
    {
        "capture",
        "memory_maintenance",
        "capture_cognition",
        "reflect_review",
    }
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply_sigma_to_block(block: Any, *, trace_id: Optional[str] = None) -> Dict[str, Any]:
    """Sync Σ.M metadata onto MemoryBlock before persist."""
    sigma = memory_block_to_sigma_m(block, trace_id=trace_id)
    patch = sigma_m_to_memory_block_patch(sigma)
    meta = dict(getattr(block, "metadata", None) or {})
    meta.update(patch.get("metadata") or {})
    counter = int(meta.get("iteration_counter") or 0) + 1
    meta["iteration_counter"] = counter
    meta["block_updated_at"] = _utc_now_iso()
    meta.setdefault("block_created_at", meta["block_updated_at"])
    meta["store_step"] = "STORE"
    block.metadata = meta
    if "importance" in patch:
        block.importance = patch["importance"]
    if "decay_rate" in patch:
        block.decay_rate = patch["decay_rate"]
    if "version" in patch:
        block.version = patch["version"]
    return sigma


def build_store_projection(record: Any) -> Dict[str, Any]:
    """Build Σ.M store projection from ExecutionRecord (not embedded in ER schema)."""
    if hasattr(record, "to_dict"):
        data = record.to_dict()
    elif isinstance(record, dict):
        data = dict(record)
    else:
        return {}

    result = data.get("result")
    block_hint: Dict[str, Any] = {}
    if isinstance(result, dict):
        for key in ("block_id", "label", "block_label", "memory_id"):
            if result.get(key):
                block_hint[key] = result[key]

    state = dict(data.get("state_projection") or {})
    stability = state.get("stability_metrics") if isinstance(state.get("stability_metrics"), dict) else {}

    return {
        "slot": "Σ.M",
        "trace_id": data.get("trace_id"),
        "intent_type": data.get("intent_type"),
        "block_hint": block_hint,
        "importance_snapshot": stability.get("importance_snapshot"),
        "iteration_note": "STORE_step",
        "block_updated_at": _utc_now_iso(),
    }


def is_store_intent(intent_type: str) -> bool:
    return intent_type in STORE_INTENTS

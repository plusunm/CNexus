"""Layer 1 Σ mapping — pure dict transforms, no new types (Runbook constraint).

Maps D: mother-repo MemoryBlock + ExecutionRecord projections onto Runbook
Σ slots (Σ.M memory, Σ.T trace). Used by STORE_step and migration_runner.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_TRACE_TS_RE = re.compile(r"(\d{10,13})")


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def derive_timestamps_from_trace(trace_id: str, *, fallback: Optional[datetime] = None) -> Dict[str, str]:
    """FACTORY_GAP: derive block_created_at from trace_id when absent."""
    now = fallback or datetime.now(timezone.utc)
    created = now
    match = _TRACE_TS_RE.search(trace_id or "")
    if match:
        raw = int(match.group(1))
        if raw > 1_000_000_000_000:
            raw //= 1000
        try:
            created = datetime.fromtimestamp(raw, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            created = now
    iso_created = _iso(created)
    return {"block_created_at": iso_created, "block_updated_at": iso_created}


def memory_block_to_sigma_m(block: Any, *, trace_id: Optional[str] = None) -> Dict[str, Any]:
    """Project MemoryBlock (or dict) into Runbook Σ.M slot."""
    if hasattr(block, "model_dump_for_storage"):
        data = block.model_dump_for_storage()
    elif hasattr(block, "model_dump"):
        data = block.model_dump()
    elif isinstance(block, dict):
        data = dict(block)
    else:
        raise TypeError(f"expected MemoryBlock or dict, got {type(block)!r}")

    label = str(data.get("label", ""))
    metadata = dict(data.get("metadata") or {})
    importance_snapshot = float(data.get("importance", metadata.get("importance_snapshot", 0.5)))

    sigma_m: Dict[str, Any] = {
        "slot": "Σ.M",
        "block_id": data.get("block_id"),
        "label": label,
        "content": data.get("content", ""),
        "category": data.get("category"),
        "importance": importance_snapshot,
        "importance_snapshot": importance_snapshot,
        "decay_rate": float(data.get("decay_rate", metadata.get("block_decay_rate", 0.01))),
        "version_seq": int(data.get("version", metadata.get("block_version_seq", 1))),
        "governance_status": data.get("governance_status"),
        "provenance_hash": data.get("provenance_hash"),
        "metadata": {
            **metadata,
            "block_created_at": _format_ts(data.get("created_at"), metadata.get("block_created_at")),
            "block_updated_at": _format_ts(data.get("updated_at"), metadata.get("block_updated_at")),
            "block_decay_rate": float(data.get("decay_rate", 0.01)),
            "block_version_seq": int(data.get("version", 1)),
            "block_importance_snapshot": importance_snapshot,
            "sigma_slot": "Σ.M",
        },
    }

    if trace_id and not sigma_m["metadata"].get("block_created_at"):
        derived = derive_timestamps_from_trace(trace_id)
        sigma_m["metadata"].update(derived)

    return sigma_m


def sigma_m_to_memory_block_patch(sigma_m: Dict[str, Any]) -> Dict[str, Any]:
    """Inverse patch for block_store — merges Σ.M back into MemoryBlock fields."""
    meta = dict(sigma_m.get("metadata") or {})
    patch: Dict[str, Any] = {
        "importance": sigma_m.get("importance", meta.get("block_importance_snapshot", 0.5)),
        "decay_rate": sigma_m.get("decay_rate", meta.get("block_decay_rate", 0.01)),
        "version": sigma_m.get("version_seq", meta.get("block_version_seq", 1)),
        "metadata": {**meta, "sigma_slot": "Σ.M"},
    }
    for src, dst in (
        ("block_created_at", "created_at"),
        ("block_updated_at", "updated_at"),
    ):
        if meta.get(src):
            patch[dst] = meta[src]
    return patch


def execution_record_to_sigma_trace(record: Any) -> Dict[str, Any]:
    """Project ExecutionRecord (or dict) into Runbook Σ.T slot."""
    if hasattr(record, "to_dict"):
        data = record.to_dict()
    elif hasattr(record, "model_dump"):
        data = record.model_dump()
    elif isinstance(record, dict):
        data = dict(record)
    else:
        raise TypeError(f"expected ExecutionRecord or dict, got {type(record)!r}")

    state = dict(data.get("state_projection") or {})
    stability = state.get("stability_metrics") if isinstance(state.get("stability_metrics"), dict) else {}

    return {
        "slot": "Σ.T",
        "trace_id": data.get("trace_id"),
        "intent_type": data.get("intent_type"),
        "elapsed_ms": data.get("elapsed_ms"),
        "identity": data.get("identity"),
        "graph_invariant": data.get("graph_invariant"),
        "audit_log": dict(data.get("audit_log") or data.get("audit") or {}),
        "state_projection": state,
        "importance_snapshot": stability.get("importance_snapshot"),
        "derivation": dict(data.get("derivation") or {}),
        "replay_signature": data.get("replay_signature"),
    }


def _format_ts(primary: Any, fallback: Any) -> Optional[str]:
    if primary is None and fallback is None:
        return None
    if isinstance(primary, datetime):
        return _iso(primary)
    if isinstance(primary, str) and primary:
        return primary
    if isinstance(fallback, str) and fallback:
        return fallback
    return None

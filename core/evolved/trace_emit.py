"""Layer 2 Σ.T trace emission — append-only execution_trace.jsonl."""

from __future__ import annotations

from typing import Any, Optional

from core.evolved.sigma_mapping import execution_record_to_sigma_trace
from core.runtime.execution_trace import append_execution_trace


def emit_sigma_trace(base_dir: Optional[str], record: Any, *, phase: str = "kernel_record") -> None:
    """Append kernel execution row with sigma_trace_slot to execution_trace.jsonl."""
    if not base_dir:
        return
    sigma_t = execution_record_to_sigma_trace(record)
    append_execution_trace(
        base_dir,
        {
            "type": "kernel_execution",
            "phase": phase,
            "trace_id": sigma_t.get("trace_id"),
            "intent_type": sigma_t.get("intent_type"),
            "sigma_trace_slot": sigma_t.get("slot"),
            "elapsed_ms": sigma_t.get("elapsed_ms"),
            "identity": sigma_t.get("identity"),
            "graph_invariant": sigma_t.get("graph_invariant"),
            "importance_snapshot": sigma_t.get("importance_snapshot"),
        },
    )

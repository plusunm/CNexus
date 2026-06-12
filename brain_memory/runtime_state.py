"""Runtime state snapshot for production recovery."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime

SCHEMA_VERSION = "1.0.0"


def dump_runtime_state(runtime: "BrainMemoryRuntime") -> Dict[str, Any]:
    """Export recoverable cognitive state (blocks + in-memory overlays)."""
    attention = runtime.memory_manager.get_attention_snapshot()
    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now().isoformat(),
        "working_self": runtime.working_self.to_dict(),
        "self_model": runtime.self_model.to_dict(),
        "belief_store": runtime.belief_engine.export_belief_store_payload(),
        "narrative_summary": runtime.narrative.get_current_narrative_summary(),
        "attention_snapshot": attention,
        "predictive": runtime.predictive.to_dict(),
        "block_stats": runtime.memory_manager.block_stats(),
    }


def restore_runtime_state(runtime: "BrainMemoryRuntime", snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort restore from dump_runtime_state output."""
    report: Dict[str, Any] = {"restored": [], "skipped": []}
    if not snapshot:
        report["skipped"].append("empty_snapshot")
        return report

    ws = snapshot.get("working_self")
    if isinstance(ws, dict):
        for key, value in ws.items():
            if hasattr(runtime.working_self, key):
                try:
                    setattr(runtime.working_self, key, value)
                except (TypeError, ValueError):
                    pass
        report["restored"].append("working_self")

    beliefs = snapshot.get("belief_store")
    if isinstance(beliefs, dict) and beliefs.get("beliefs"):
        loaded = runtime.belief_engine.hydrate_from_block(json.dumps(beliefs, ensure_ascii=False))
        report["restored"].append(f"beliefs:{loaded}")

    attn = snapshot.get("attention_snapshot")
    if isinstance(attn, dict) and attn:
        runtime.attention.hydrate_from_snapshot(attn)
        report["restored"].append("attention")

    summary = snapshot.get("narrative_summary")
    if summary:
        runtime.narrative.narrative.identity_summary = str(summary)[:500]
        report["restored"].append("narrative_summary")

    return report

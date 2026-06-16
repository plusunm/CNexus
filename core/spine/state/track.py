"""Runtime Tier-A mutation diff recording (P1)."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from core.governance.gtbs.state_snapshot import TierASnapshot, snapshot_tier_a
from core.spine.state.diff import diff_tier_a
from core.spine.state.emit import maybe_record_tier_a_diff

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def snapshot_runtime_tier_a(runtime: "BrainMemoryRuntime") -> TierASnapshot:
    return snapshot_tier_a(runtime)


def commit_runtime_state_diff(
    runtime: "BrainMemoryRuntime",
    before: TierASnapshot,
    *,
    label: str,
    intent_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> Optional[Any]:
    after = snapshot_tier_a(runtime)
    patch = diff_tier_a(before, after)
    if patch["change_count"] == 0:
        return None
    patch["mutation_label"] = label
    trace_id = None
    from core.runtime.trace_context import get_trace_id

    trace_id = get_trace_id()
    if not trace_id:
        return None
    from core.spine.integration import get_spine_writer

    writer = get_spine_writer()
    if writer is None:
        return None
    if intent_id:
        patch["intent_id"] = intent_id
    return writer.project_state_patch(trace_id=trace_id, patch=patch, triggered_by=triggered_by)

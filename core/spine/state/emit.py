"""Record Tier-A state patches into spine_events.jsonl."""

from __future__ import annotations

from typing import Any, Optional

from core.governance.gtbs.state_snapshot import TierASnapshot
from core.runtime.trace_context import get_trace_id
from core.spine.state.diff import diff_tier_a
from core.spine.types import SpineEvent


def maybe_record_tier_a_diff(
    before: TierASnapshot,
    after: TierASnapshot,
    *,
    intent_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> Optional[SpineEvent]:
    patch = diff_tier_a(before, after)
    if patch["change_count"] == 0:
        return None

    trace_id = get_trace_id()
    if not trace_id:
        return None

    from core.spine.integration import get_spine_writer

    writer = get_spine_writer()
    if writer is None:
        return None

    if intent_id:
        patch["intent_id"] = intent_id

    return writer.project_state_patch(
        trace_id=trace_id,
        patch=patch,
        triggered_by=triggered_by,
    )

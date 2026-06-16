"""CP-2 state diff — Tier-A patch recording for spine query."""

from core.spine.state.diff import diff_tier_a
from core.spine.state.emit import maybe_record_tier_a_diff
from core.spine.state.track import commit_runtime_state_diff, snapshot_runtime_tier_a

__all__ = ["diff_tier_a", "maybe_record_tier_a_diff", "commit_runtime_state_diff", "snapshot_runtime_tier_a"]

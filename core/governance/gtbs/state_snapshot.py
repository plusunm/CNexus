"""CP-2 — Tier A/B state snapshots for transactional rollback."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


@dataclass
class TierASnapshot:
    """In-memory cognitive state (rollback-safe)."""

    working_self: Dict[str, Any]
    legacy_state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TierBSnapshot:
    """Capture / storage write metadata (audit-only in CP-2 MVP)."""

    pending_capture: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WriteStateSnapshot:
    tier_a: TierASnapshot
    tier_b: TierBSnapshot = field(default_factory=TierBSnapshot)


def snapshot_tier_a(runtime: "BrainMemoryRuntime") -> TierASnapshot:
    ws = runtime.working_self.to_dict()
    legacy = {
        "cognitive_load": runtime.state.cognitive_load,
        "current_goal_focus": runtime.state.current_goal_focus,
        "current_identity_mode": runtime.state.current_identity_mode,
        "current_relationship_focus": runtime.state.current_relationship_focus,
    }
    return TierASnapshot(working_self=copy.deepcopy(ws), legacy_state=copy.deepcopy(legacy))


def restore_tier_a(runtime: "BrainMemoryRuntime", snap: TierASnapshot) -> None:
    from runtime.cognitive_state import PersistentCognitiveState

    restored = PersistentCognitiveState.from_dict(snap.working_self)
    runtime.working_self.__dict__.update(restored.__dict__)
    for key, value in snap.legacy_state.items():
        if hasattr(runtime.state, key):
            setattr(runtime.state, key, value)


def snapshot_for_intent(
    runtime: "BrainMemoryRuntime",
    *,
    tier_b_meta: Optional[Dict[str, Any]] = None,
) -> WriteStateSnapshot:
    return WriteStateSnapshot(
        tier_a=snapshot_tier_a(runtime),
        tier_b=TierBSnapshot(pending_capture=dict(tier_b_meta or {})),
    )

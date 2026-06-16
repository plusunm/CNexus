"""Field-level diff for Tier-A snapshots (working_self + legacy_state)."""

from __future__ import annotations

from typing import Any

from core.governance.gtbs.state_snapshot import TierASnapshot


def _diff_dict(before: dict[str, Any], after: dict[str, Any], *, prefix: str) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    keys = set(before.keys()) | set(after.keys())
    for key in sorted(keys):
        b_val = before.get(key)
        a_val = after.get(key)
        if b_val != a_val:
            changes.append(
                {
                    "field": f"{prefix}{key}",
                    "before": b_val,
                    "after": a_val,
                }
            )
    return changes


def diff_tier_a(before: TierASnapshot, after: TierASnapshot) -> dict[str, Any]:
    changes = _diff_dict(before.working_self, after.working_self, prefix="working_self.")
    changes.extend(_diff_dict(before.legacy_state, after.legacy_state, prefix="legacy_state."))
    return {
        "source": "tier_a",
        "changes": changes,
        "change_count": len(changes),
    }

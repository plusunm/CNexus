"""Layer 3 cognitive_state ownership — COGNIZE / DECIDE / STORE writers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

COGNIZE_INTENTS = frozenset({"chat", "observe", "reflect_review", "capture_cognition"})
DECIDE_INTENTS = frozenset({"control", "cdg_apply", "governance_validate", "reflect_due_reviews"})


def _touch(model: Any, field: str, value: Any) -> None:
    setattr(model, field, value)


def apply_cognize_step(store: Any, *, user_input: str = "", response: str = "") -> Dict[str, Any]:
    """COGNIZE_step — relationship_state, self_evaluation, prediction_state."""
    model = store.model
    now = datetime.now(timezone.utc).isoformat()
    rel = dict(getattr(model, "relational_models", None) or {})
    rel.setdefault("_runtime", {})
    rel["_runtime"]["last_cognize_at"] = now
    if user_input:
        rel["_runtime"]["last_user_input_preview"] = str(user_input)[:200]
    _touch(model, "relational_models", rel)
    expectations = dict(getattr(model, "self_expectations", None) or {})
    expectations["last_self_evaluation"] = min(0.99, float(expectations.get("consistency", 0.9)) + 0.001)
    _touch(model, "self_expectations", expectations)
    projection = dict(getattr(model, "future_projection", None) or {})
    projection["prediction_state"] = {"updated_at": now, "source": "COGNIZE_step"}
    _touch(model, "future_projection", projection)
    store.save()
    return {"step": "COGNIZE", "updated_at": now}


def apply_decide_step(store: Any, *, intent_type: str = "") -> Dict[str, Any]:
    """DECIDE_step — identity_projection, identity_constraint, behavioral_tendency."""
    model = store.model
    now = datetime.now(timezone.utc).isoformat()
    bias = dict(getattr(model, "stable_behavioral_bias", None) or {})
    if intent_type in ("control", "cdg_apply"):
        bias["cautious"] = min(0.95, float(bias.get("cautious", 0.75)) + 0.01)
    _touch(model, "stable_behavioral_bias", bias)
    beliefs = dict(getattr(model, "core_beliefs", None) or {})
    beliefs.setdefault("identity_constraint", 0.9)
    _touch(model, "core_beliefs", beliefs)
    summary = str(getattr(model, "identity_summary", ""))
    if intent_type and intent_type not in summary:
        _touch(model, "identity_summary", f"{summary[:520]} [{intent_type}]".strip())
    store.save()
    return {"step": "DECIDE", "intent_type": intent_type, "updated_at": now}


def apply_store_selfmodel_step(store: Any, *, block_updated_at: Optional[str] = None) -> Dict[str, Any]:
    """STORE_step SelfModel writer — block_updated_at / last_reconstruction merge."""
    model = store.model
    ts = block_updated_at or datetime.now(timezone.utc).isoformat()
    _touch(model, "last_reconstruction", ts)
    store.save()
    return {"step": "STORE", "last_reconstruction": ts}


def dispatch_cognitive_step(
    store: Any,
    intent_type: str,
    *,
    user_input: str = "",
    response: str = "",
    block_updated_at: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Route intent to COGNIZE / DECIDE / STORE ownership writer."""
    if intent_type in COGNIZE_INTENTS:
        return apply_cognize_step(store, user_input=user_input, response=response)
    if intent_type in DECIDE_INTENTS:
        return apply_decide_step(store, intent_type=intent_type)
    if intent_type in {"capture", "memory_maintenance", "capture_cognition"}:
        return apply_store_selfmodel_step(store, block_updated_at=block_updated_at)
    return None

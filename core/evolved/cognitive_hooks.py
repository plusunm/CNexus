"""Layer 3 cognitive_state ownership — COGNIZE / DECIDE / STORE writers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.self_model.self_model import BELIEF_CAP, MAX_IDENTITY_CHARS, MAX_STORY_CHARS

COGNIZE_INTENTS = frozenset({"chat", "observe", "reflect_review", "capture_cognition"})
DECIDE_INTENTS = frozenset({"control", "cdg_apply", "governance_validate", "reflect_due_reviews"})
MAX_ATTRACTOR_COHERENCE_STEP = 0.1


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
    store.save_domain("cognize")
    return {"step": "COGNIZE", "updated_at": now}


def apply_attractor_recalibration_step(
    store: Any,
    *,
    proposed_coherence: Optional[float] = None,
    coherence_delta: Optional[float] = None,
    relational_patch: Optional[Dict[str, Any]] = None,
    projection_patch: Optional[Dict[str, Any]] = None,
    max_step: float = MAX_ATTRACTOR_COHERENCE_STEP,
) -> Dict[str, Any]:
    """Attractor recalibration — Σ.S (cognize) only; hard |Δcoherence_score| ≤ max_step."""
    from core.personality.attractor.delta_constraint import clamp_scalar_step

    model = store.model
    now = datetime.now(timezone.utc).isoformat()
    current = float(getattr(model, "coherence_score", 0.85) or 0.85)

    if proposed_coherence is not None:
        target = float(proposed_coherence)
    elif coherence_delta is not None:
        target = current + float(coherence_delta)
    else:
        target = current

    new_coherence, applied_delta = clamp_scalar_step(current, target, max_step=max_step)
    _touch(model, "coherence_score", round(new_coherence, 4))

    rel = dict(getattr(model, "relational_models", None) or {})
    rel.setdefault("_attractor", {})
    rel["_attractor"]["last_recalibration_at"] = now
    if relational_patch:
        for key, value in relational_patch.items():
            if isinstance(value, dict) and isinstance(rel.get(key), dict):
                merged = dict(rel[key])
                merged.update(value)
                rel[key] = merged
            else:
                rel[key] = value
    _touch(model, "relational_models", rel)

    projection = dict(getattr(model, "future_projection", None) or {})
    if projection_patch:
        projection.update(projection_patch)
    projection["attractor_state"] = {
        "updated_at": now,
        "coherence_delta_applied": applied_delta,
        "source": "attractor_recalibration",
    }
    _touch(model, "future_projection", projection)

    store.save_domain("cognize")
    return {
        "step": "ATTRACTOR_RECALIBRATION",
        "coherence_before": current,
        "coherence_after": new_coherence,
        "coherence_delta_applied": applied_delta,
        "updated_at": now,
    }


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
    store.save_domain("decide")
    return {"step": "DECIDE", "intent_type": intent_type, "updated_at": now}


def apply_consolidation_step(
    store: Any,
    *,
    autobiography_delta: str = "",
    beliefs_delta: Optional[Dict[str, float]] = None,
    identity_summary_delta: str = "",
) -> Dict[str, Any]:
    """L3-3 daily reflection — merge-only Σ.I updates, atomic save_domain('decide')."""
    model = store.model
    now = datetime.now(timezone.utc).isoformat()
    merged_beliefs: Dict[str, float] = {}

    story = str(getattr(model, "autobiographical_story", "") or "")
    if autobiography_delta and autobiography_delta not in story:
        story = f"{story}\n{autobiography_delta}".strip()
        if len(story) > MAX_STORY_CHARS:
            story = story[-MAX_STORY_CHARS:]
        _touch(model, "autobiographical_story", story)

    summary = str(getattr(model, "identity_summary", "") or "")
    if identity_summary_delta and identity_summary_delta not in summary:
        summary = f"{summary}。{identity_summary_delta}".strip()
        if len(summary) > MAX_IDENTITY_CHARS:
            summary = summary[-MAX_IDENTITY_CHARS:]
        _touch(model, "identity_summary", summary)

    beliefs = dict(getattr(model, "core_beliefs", None) or {})
    for key, delta in (beliefs_delta or {}).items():
        if not key:
            continue
        try:
            bump = float(delta)
        except (TypeError, ValueError):
            continue
        current = float(beliefs.get(key, 0.85))
        beliefs[key] = min(BELIEF_CAP, current + bump)
        merged_beliefs[str(key)] = beliefs[key]
    if merged_beliefs:
        _touch(model, "core_beliefs", beliefs)

    store.save_domain("decide")
    return {
        "step": "DAILY_CONSOLIDATION",
        "updated_at": now,
        "beliefs_merged": merged_beliefs,
        "story_appended": bool(autobiography_delta),
        "identity_appended": bool(identity_summary_delta),
    }


def apply_store_selfmodel_step(store: Any, *, block_updated_at: Optional[str] = None) -> Dict[str, Any]:
    """STORE_step SelfModel writer — block_updated_at / last_reconstruction merge."""
    model = store.model
    ts = block_updated_at or datetime.now(timezone.utc).isoformat()
    _touch(model, "last_reconstruction", ts)
    store.save_domain("store_meta")
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

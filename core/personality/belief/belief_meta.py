"""BeliefMeta — meta-cognition payload scoped to Belief/Reflection only."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

MetaSource = Literal["reflection", "governance"]

FORBIDDEN_META_LAYERS = frozenset({"episodic", "semantic", "working"})
FORBIDDEN_META_BLOCK_LABELS = frozenset(
    {"episodic_event", "episodic_dialogue", "episodic_decision"}
)
ALLOWED_META_BLOCK_LABELS = frozenset({"belief_store", "narrative"})


class BeliefMeta(BaseModel):
    belief_id: str
    goal_id: Optional[str] = None
    alignment_score: float = Field(0.0, ge=0.0, le=1.0)
    confidence_delta: float = Field(0.0, ge=-1.0, le=1.0)
    source: MetaSource = "reflection"
    updated_at: datetime = Field(default_factory=datetime.now)


def meta_write_allowed(
    *,
    layer: Optional[str] = None,
    block_label: Optional[str] = None,
) -> bool:
    """BeliefMeta must not attach to episodic/semantic storage paths."""
    if layer and layer in FORBIDDEN_META_LAYERS:
        return False
    if block_label and block_label in FORBIDDEN_META_BLOCK_LABELS:
        return False
    if block_label and block_label in ALLOWED_META_BLOCK_LABELS:
        return True
    if layer in {"belief", "goal", "identity"}:
        return True
    return block_label is None and layer is None


def attach_meta_to_belief_payload(
    payload: dict,
    meta: BeliefMeta,
    *,
    layer: Optional[str] = None,
    block_label: str = "belief_store",
) -> dict:
    if not meta_write_allowed(layer=layer, block_label=block_label):
        raise ValueError(
            f"BeliefMeta cannot attach to layer={layer!r} block_label={block_label!r}"
        )
    enriched = dict(payload)
    meta_list = list(enriched.get("meta") or [])
    meta_list.append(meta.model_dump(mode="json"))
    enriched["meta"] = meta_list[-16:]
    return enriched

"""CDG state snapshot — bridge BrainMemoryRuntime objects ↔ governance dict."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def empty_cdg_state() -> Dict[str, Any]:
    return {
        "memory": [],
        "narrative": [],
        "beliefs": [],
        "working_self": {},
        "self_model": {},
        "flags": [],
        "plasticity_modifier": 1.0,
        "interaction": {},
    }


def snapshot_cdg_state(
    runtime: "BrainMemoryRuntime",
    *,
    user_input: str = "",
    response: str = "",
    capture_ids: Optional[List[str]] = None,
    grounding_event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Materialize runtime into CDG governable state dict."""
    state = empty_cdg_state()
    event_id = grounding_event_id or ""

    for belief_id, belief in runtime.belief_engine.get_active_beliefs().items():
        state["beliefs"].append(
            {
                "id": belief_id,
                "content": belief.content,
                "confidence": float(belief.confidence),
                "provenance": belief.source_memory_id or event_id,
                "status": "active",
            }
        )

    for name, confidence in runtime.self_model.core_beliefs.items():
        state["beliefs"].append(
            {
                "id": f"core:{name}",
                "content": name,
                "confidence": float(confidence),
                "provenance": event_id,
                "status": "core",
            }
        )

    state["narrative"].append(
        {
            "summary": runtime.narrative.get_current_narrative_summary(),
            "grounding_ref": event_id,
            "version": runtime.narrative.narrative.version,
            "coherence": runtime.narrative.narrative.narrative_coherence_score,
        }
    )
    state["narrative"].append(
        {
            "summary": runtime.self_model.identity_summary[:500],
            "grounding_ref": event_id,
            "version": runtime.narrative.narrative.version,
            "coherence": runtime.self_model.coherence_score,
            "is_synthetic": False,
        }
    )

    for mid in capture_ids or []:
        state["memory"].append(
            {
                "memory_id": mid,
                "content": user_input if user_input else response,
                "causal_parent": event_id,
                "is_synthetic": False,
                "provenance": event_id,
                "layer": "episodic",
            }
        )

    state["working_self"] = copy.deepcopy(runtime.working_self.to_dict())
    state["self_model"] = copy.deepcopy(runtime.self_model.to_dict())
    state["flags"] = list(state.get("flags", []))
    state["interaction"] = {
        "user_input": user_input,
        "response": response,
        "grounding_event_id": event_id,
    }
    return state


def apply_cdg_state(runtime: "BrainMemoryRuntime", governed: Dict[str, Any]) -> None:
    """Apply CDG-modified state back onto runtime objects."""
    ws = governed.get("working_self") or {}
    if ws:
        from runtime.cognitive_state import PersistentCognitiveState

        restored = PersistentCognitiveState.from_dict(ws)
        runtime.working_self.__dict__.update(restored.__dict__)

    sm = governed.get("self_model") or {}
    if sm:
        model = runtime.self_model
        if "identity_summary" in sm:
            model.identity_summary = str(sm["identity_summary"])[:600]
        if "autobiographical_story" in sm:
            model.autobiographical_story = str(sm["autobiographical_story"])[:1200]
        if "core_beliefs" in sm and isinstance(sm["core_beliefs"], dict):
            model.core_beliefs = {
                str(k): float(v) for k, v in sm["core_beliefs"].items()
            }
        if "coherence_score" in sm:
            model.coherence_score = float(sm["coherence_score"])

    for belief in governed.get("beliefs", []):
        if belief.get("status") == "downgraded_by_reality":
            content = str(belief.get("content", ""))
            if content in runtime.self_model.core_beliefs:
                runtime.self_model.core_beliefs[content] = float(belief.get("confidence", 0.25))

    if "REALITY_OVERRIDE_APPLIED" in governed.get("flags", []):
        runtime.narrative.narrative.narrative_coherence_score = min(
            runtime.narrative.narrative.narrative_coherence_score,
            runtime.self_model.coherence_score,
        )

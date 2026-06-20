"""L3-2 Attractor recalibration — inner monologue → Σ.S-only cognize writes."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, Optional

from core.governance.cdg.stability_monitor import RecalibrationSignal
from core.personality.attractor.delta_constraint import clamp_scalar_step
from core.personality.narrative.recent_context import load_recent_narrative_prompt_block

logger = logging.getLogger(__name__)

InnerMonologueFn = Callable[[str], str]


def build_inner_monologue_prompt(
    *,
    recent_narrative: str,
    stability_score: float,
    current_coherence: float,
) -> str:
    return (
        "【Inner Monologue — Attractor Recalibration (Σ.S only)】\n"
        f"Your cognitive coherence is currently {current_coherence:.3f}. "
        f"Governance overall stability score is {stability_score:.3f}.\n"
        "Based on recent interactions below, assess which relational_models or "
        "short-term predictions need micro-adjustment to restore continuity.\n"
        "Respond with JSON only:\n"
        '{"coherence_delta": <float -1..1>, '
        '"relational_patch": {<key>: <value>}, '
        '"projection_patch": {<key>: <value>}}\n'
        "Do not modify identity, core beliefs, or autobiographical narrative.\n\n"
        f"{recent_narrative or '(no recent narrative available)'}"
    )


def parse_recalibration_response(raw: str, *, current_coherence: float) -> Dict[str, Any]:
    """Parse LLM JSON; fall back to bounded nudge toward baseline coherence."""
    text = str(raw or "").strip()
    payload: Dict[str, Any] = {}
    if text:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                logger.debug("attractor: failed to parse inner monologue JSON")

    if "coherence_delta" in payload:
        delta = float(payload.get("coherence_delta") or 0.0)
        return {
            "coherence_delta": delta,
            "relational_patch": dict(payload.get("relational_patch") or {}),
            "projection_patch": dict(payload.get("projection_patch") or {}),
        }
    if "proposed_coherence" in payload:
        return {
            "proposed_coherence": float(payload["proposed_coherence"]),
            "relational_patch": dict(payload.get("relational_patch") or {}),
            "projection_patch": dict(payload.get("projection_patch") or {}),
        }

    return _rule_based_proposal(current_coherence=current_coherence)


def propose_sigma_s_updates(
    *,
    current_coherence: float,
    stability_score: float,
    recent_narrative: str,
    llm_reflect: Optional[InnerMonologueFn] = None,
) -> Dict[str, Any]:
    if llm_reflect is None:
        return _rule_based_proposal(
            current_coherence=current_coherence,
            stability_score=stability_score,
        )
    prompt = build_inner_monologue_prompt(
        recent_narrative=recent_narrative,
        stability_score=stability_score,
        current_coherence=current_coherence,
    )
    raw = llm_reflect(prompt)
    return parse_recalibration_response(raw, current_coherence=current_coherence)


def _rule_based_proposal(
    *,
    current_coherence: float,
    stability_score: float = 0.85,
) -> Dict[str, Any]:
    """Deterministic fallback when LLM is unavailable — nudge toward safe baseline."""
    baseline = 0.85
    gap = baseline - float(current_coherence)
    if stability_score < 0.6:
        gap = max(gap, 0.05)
    _, delta = clamp_scalar_step(current_coherence, current_coherence + gap * 0.5, max_step=0.1)
    return {
        "coherence_delta": delta,
        "relational_patch": {"_attractor": {"recalibration_reason": "stability_probe"}},
        "projection_patch": {},
    }


def run_attractor_recalibration(
    store: Any,
    signal: RecalibrationSignal,
    *,
    base_dir: str,
    llm_reflect: Optional[InnerMonologueFn] = None,
) -> Dict[str, Any]:
    """Consume RecalibrationSignal and persist Σ.S updates via cognitive_hooks."""
    from core.evolved.cognitive_hooks import apply_attractor_recalibration_step

    model = store.model
    current = float(getattr(model, "coherence_score", 0.85) or 0.85)
    recent = load_recent_narrative_prompt_block(base_dir or None)
    proposal = propose_sigma_s_updates(
        current_coherence=current,
        stability_score=signal.overall_stability_score,
        recent_narrative=recent,
        llm_reflect=llm_reflect,
    )
    result = apply_attractor_recalibration_step(store, **proposal)
    result["signal_reason"] = signal.reason
    result["stability_score"] = signal.overall_stability_score
    return result

"""L3-3 — daily periodic reflection: Σ.T long-cycle ledger → Σ.I (decide) merge."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from core.personality.narrative.recent_context import format_recent_narrative
from core.self_model.self_model import BELIEF_DELTA, MAX_STORY_CHARS

logger = logging.getLogger(__name__)

InnerReflectionFn = Callable[[str], str]


def load_daily_interaction_ledger(
    base_dir: Optional[str],
    *,
    since_hours: float = 24.0,
    limit: int = 64,
) -> str:
    """Read long-cycle interaction_step rows from L2 trace shards (read-only Σ.T)."""
    if not base_dir:
        return ""
    from core.runtime.trace_store import read_recent_interaction_steps

    steps = read_recent_interaction_steps(
        base_dir,
        since_hours=since_hours,
        limit=limit,
    )
    return format_recent_narrative(steps)


def build_consolidation_prompt(*, ledger: str) -> str:
    return (
        "【Daily Consolidation — long-cycle internal reflection (Σ.I decide domain)】\n"
        "Review today's observed interactions below. Based ONLY on these recorded events, "
        "describe how your understanding of the user and world shifted.\n"
        "Which core beliefs were reinforced or need a micro-adjustment?\n"
        "Do not invent interactions that are not in the ledger.\n"
        "Respond with JSON only:\n"
        '{"autobiography_delta": "<append-only story line>", '
        '"beliefs_delta": {"belief_name": <float delta>}, '
        '"identity_summary_delta": "<optional append-only identity note>"}\n\n'
        f"{ledger}"
    )


def parse_consolidation_response(raw: str) -> Dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.debug("daily_consolidation: JSON parse failed")
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def propose_consolidation_deltas(
    ledger: str,
    llm_reflect: Optional[InnerReflectionFn] = None,
) -> Dict[str, Any]:
    """Derive merge-only deltas from observed ledger — never overwrite baselines."""
    if not ledger.strip():
        return {}

    if llm_reflect is not None:
        prompt = build_consolidation_prompt(ledger=ledger)
        raw = llm_reflect(prompt)
        payload = parse_consolidation_response(raw)
        if payload:
            return _normalize_deltas(payload)

    return _rule_based_deltas(ledger)


def _normalize_deltas(payload: Dict[str, Any]) -> Dict[str, Any]:
    beliefs = payload.get("beliefs_delta") or payload.get("belief_deltas") or {}
    if not isinstance(beliefs, dict):
        beliefs = {}
    cleaned_beliefs: Dict[str, float] = {}
    for key, value in beliefs.items():
        if not key:
            continue
        try:
            cleaned_beliefs[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return {
        "autobiography_delta": str(payload.get("autobiography_delta") or "").strip(),
        "identity_summary_delta": str(payload.get("identity_summary_delta") or "").strip(),
        "beliefs_delta": cleaned_beliefs,
    }


def _rule_based_deltas(ledger: str) -> Dict[str, Any]:
    """Deterministic consolidation from observed ledger keywords (no hallucination)."""
    text = ledger.lower()
    beliefs: Dict[str, float] = {}
    if any(k in text for k in ("稳定", "连续", "stability", "continuity")):
        beliefs["稳定性优先"] = BELIEF_DELTA
        beliefs["主体连续性"] = BELIEF_DELTA * 0.8
    if any(k in text for k in ("诚实", "真实", "honest")):
        beliefs["诚实第一"] = BELIEF_DELTA * 0.7

    entry = "今日观测交互巩固了长期陪伴中的稳定与诚实协作。"
    if "complete" in text or "interaction" in text:
        entry = f"今日观测交互（Σ.T 归档）：{ledger.splitlines()[0][:80]}"

    return {
        "autobiography_delta": entry,
        "identity_summary_delta": "",
        "beliefs_delta": beliefs,
    }


def run_daily_consolidation(
    store: Any,
    *,
    base_dir: str,
    since_hours: float = 24.0,
    limit: int = 64,
    llm_reflect: Optional[InnerReflectionFn] = None,
) -> Dict[str, Any]:
    """Execute daily reflection loop — persist via apply_consolidation_step (decide only)."""
    from core.evolved.cognitive_hooks import apply_consolidation_step

    ledger = load_daily_interaction_ledger(base_dir, since_hours=since_hours, limit=limit)
    if not ledger.strip():
        return {"step": "DAILY_REFLECTION", "skipped": True, "reason": "no_observed_interactions"}

    deltas = propose_consolidation_deltas(ledger, llm_reflect=llm_reflect)
    if not deltas:
        return {"step": "DAILY_REFLECTION", "skipped": True, "reason": "no_deltas_proposed"}

    result = apply_consolidation_step(store, **deltas)
    result["ledger_lines"] = len(ledger.splitlines())
    return result

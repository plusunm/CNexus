"""Mind 概览投影 — 将运行时状态聚合为 UI 可消费的 observability 快照."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from brain_memory.runtime import CognitiveRuntime


SCHEMA_VERSION = "1.1.0"
EPISODIC_SOFT_CAP = 200

DNA_TRAIT_LABELS = {
    "curiosity": "好奇心",
    "empathy": "共情",
    "humor": "幽默",
    "openness": "开放性",
    "loyalty": "忠诚",
    "patience": "耐心",
    "assertiveness": "果断",
    "emotional_stability": "情绪稳定",
    "risk_tolerance": "风险承受",
    "self_consistency": "自我一致",
}


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _ago(value: Any) -> str:
    dt = _parse_ts(value)
    if dt is None:
        return "—"
    now = datetime.now(timezone.utc)
    delta = now - dt.astimezone(timezone.utc)
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{max(seconds, 1)}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago" if minutes > 1 else "1 min ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def _pct(value: Optional[float], digits: int = 0) -> str:
    if value is None:
        return "—"
    if digits == 0:
        return f"{int(round(float(value) * 100))}%"
    return f"{float(value) * 100:.{digits}f}%"


def _priority_label(priority: float) -> str:
    if priority >= 0.7:
        return "高"
    if priority >= 0.4:
        return "中"
    return "低"


def _health_label(score: float) -> str:
    if score >= 0.75:
        return "良好"
    if score >= 0.5:
        return "降级"
    return "临界"


def _valence_label(value: Optional[float]) -> str:
    if value is None:
        return "—"
    v = float(value)
    if v >= 0.35:
        return "正向"
    if v <= -0.35:
        return "负向"
    return "中性"


def _emotion_label(emotion: str) -> str:
    mapping = {
        "joy": "愉悦",
        "sadness": "低落",
        "curiosity": "好奇",
        "anger": "愤怒",
        "fear": "紧张",
        "neutral": "平静",
    }
    return mapping.get(str(emotion or "neutral"), str(emotion or "neutral"))


def _episodic_text(entry: Dict[str, Any], episodic_type: str) -> str:
    if episodic_type == "dialogue":
        speaker = entry.get("speaker") or entry.get("role") or "user"
        summary = entry.get("content_summary") or entry.get("content") or entry.get("utterance") or ""
        return f"{speaker}: {str(summary)[:80]}"
    if episodic_type == "decision":
        action = entry.get("chosen_action") or entry.get("outcome") or entry.get("content") or ""
        return str(action)[:100]
    payload = entry.get("payload") or entry.get("content") or entry.get("action") or entry.get("outcome")
    if isinstance(payload, dict):
        payload = payload.get("content") or str(payload)
    return str(payload or entry.get("type") or "episodic event")[:100]


def _collect_episodic_feed(memory_manager: Any, limit: int = 5) -> List[Dict[str, str]]:
    feed: List[Dict[str, str]] = []
    try:
        blocks = memory_manager.blocks.recall_episodic(limit=limit * 2)
    except Exception:
        return feed

    rows: List[tuple] = []
    for block in blocks:
        episodic_type = getattr(block, "episodic_type", "event")
        for entry in block.get_recent(limit):
            ts = entry.get("timestamp") or getattr(block, "updated_at", None)
            text = _episodic_text(entry, episodic_type)
            rows.append((ts, text))

    rows.sort(key=lambda r: str(r[0]), reverse=True)
    for ts, text in rows[:limit]:
        feed.append({"text": text, "ago": _ago(ts)})
    return feed


def _collect_reflection_feed(reflection_pipeline: Any, limit: int = 5) -> List[Dict[str, str]]:
    feed: List[Dict[str, str]] = []
    try:
        active = reflection_pipeline.get_active_reflections()
    except Exception:
        active = []

    for record in sorted(active, key=lambda r: r.timestamp, reverse=True)[:limit]:
        scene = (record.scene or record.inner_thought or "Reflection")[:100]
        feed.append({"text": scene, "ago": _ago(record.timestamp)})

    if not feed and getattr(reflection_pipeline, "records", None):
        tail = reflection_pipeline.records[-1]
        feed.append(
            {
                "text": (tail.inner_thought or tail.scene or "Reflection")[:100],
                "ago": _ago(tail.timestamp),
            }
        )
    return feed[:limit]


def _collect_changes(runtime: "CognitiveRuntime", goal_layer: Dict[str, Any]) -> List[str]:
    changes: List[str] = []
    synth_gen = goal_layer.get("synthesis_generation")
    if synth_gen:
        changes.append(f"Synthesis generation #{synth_gen}")

    conflicts = goal_layer.get("conflicts") or []
    if conflicts:
        changes.append(f"Goal conflicts: {len(conflicts)}")

    belief_links = goal_layer.get("belief_links")
    if isinstance(belief_links, int) and belief_links:
        changes.append(f"BeliefMeta links: {belief_links}")

    synth = runtime.goal_manager.synthesizer.state
    for link in synth.belief_links[-3:]:
        delta = getattr(link, "confidence_delta", None)
        if delta and abs(delta) >= 0.01:
            sign = "+" if delta > 0 else ""
            changes.append(f"Belief confidence {sign}{int(delta * 100)}%")

    top_goal = goal_layer.get("top_goal") or {}
    if top_goal.get("alignment_score") is not None:
        changes.append(f"Goal alignment {_pct(top_goal.get('alignment_score'))}")

    wm = runtime.attention.working_memory_snapshot()
    if wm:
        changes.append(f"Working memory active: {len(wm)}")

    if not changes:
        changes.append("Runtime stable — no recent deltas")
    return changes[:5]


def _memory_capacity_pct(memory_manager: Any, working_memory_count: int) -> int:
    try:
        stats = memory_manager.block_stats()
        episodic = stats.get("episodic_counts") or {}
        episodic_total = sum(int(v) for v in episodic.values())
    except Exception:
        episodic_total = 0

    used = episodic_total + working_memory_count
    return min(99, max(5, int(used / EPISODIC_SOFT_CAP * 100)))


def _top_belief(belief_engine: Any) -> Dict[str, Any]:
    active = belief_engine.get_active_beliefs()
    if not active:
        return {"content": "暂无活跃信念", "confidence": 0.0, "evidence_count": 0}

    top_id, top = max(active.items(), key=lambda kv: kv[1].confidence)
    payload = belief_engine.export_belief_store_payload().get("beliefs", {}).get(top_id, {})
    return {
        "belief_id": top_id,
        "content": top.content,
        "confidence": top.confidence,
        "evidence_count": payload.get("evidence_count", getattr(top, "evidence_count", 0)),
    }


def _build_personality_observation(
    runtime: "CognitiveRuntime",
    identity_card: Dict[str, Any],
    belief_card: Dict[str, Any],
) -> Dict[str, Any]:
    emotion_raw: Dict[str, Any] = {}
    try:
        emotion_raw = runtime.emotion_engine.get_state_summary()
    except Exception:
        emotion_raw = {"primary_emotion": "neutral", "intensity": 0.5}

    dna = runtime.dna_engine.dna
    traits = [
        {
            "key": key,
            "label": label,
            "value": float(getattr(dna, key, 0.0)),
            "value_label": _pct(getattr(dna, key, 0.0)),
        }
        for key, label in DNA_TRAIT_LABELS.items()
    ]
    stability = runtime.dna_engine.get_stability_metrics()

    return {
        "emotion": {
            "primary_emotion": str(emotion_raw.get("primary_emotion") or "neutral"),
            "primary_emotion_label": _emotion_label(str(emotion_raw.get("primary_emotion") or "neutral")),
            "intensity": float(emotion_raw.get("intensity") or 0.5),
            "intensity_label": _pct(emotion_raw.get("intensity")),
            "valence": float(emotion_raw.get("valence") or 0.0),
            "valence_label": _valence_label(emotion_raw.get("valence")),
            "arousal": float(emotion_raw.get("arousal") or 0.5),
            "arousal_label": _pct(emotion_raw.get("arousal")),
            "dominance": float(emotion_raw.get("dominance") or 0.5),
            "dominance_label": _pct(emotion_raw.get("dominance")),
            "last_updated_ago": _ago(emotion_raw.get("last_updated")),
        },
        "dna": {
            "traits": traits,
            "version": str(getattr(dna, "version", "—")),
            "mutation_count": int(getattr(dna, "mutation_count", 0) or 0),
            "self_consistency": float(getattr(dna, "self_consistency", 0.0) or 0.0),
            "self_consistency_label": _pct(getattr(dna, "self_consistency", 0.0)),
            "overall_stability": float(stability.get("overall_stability") or 0.0),
            "overall_stability_label": _pct(stability.get("overall_stability")),
            "last_updated_ago": _ago(getattr(dna, "last_updated", None)),
        },
        "identity": identity_card,
        "belief": belief_card,
    }


def _build_intent_observation(runtime: "CognitiveRuntime") -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    try:
        summary = runtime.intent_engine.get_state_summary()
    except Exception:
        summary = {"active_goals": [], "current_focus": None, "motivation_baseline": 0.6}

    proactive: Dict[str, Any] = {"should_trigger": False}
    try:
        proactive = runtime.intent_engine.trigger_proactive().model_dump(mode="json")
    except Exception:
        proactive = {"should_trigger": False}

    goals: List[Dict[str, Any]] = []
    for raw in summary.get("active_goals") or []:
        if not isinstance(raw, dict):
            continue
        if str(raw.get("status") or "active") != "active":
            continue
        goals.append(
            {
                "goal_id": raw.get("goal_id", "—"),
                "description": str(raw.get("description") or "—")[:200],
                "priority": float(raw.get("priority") or 0.0),
                "priority_label": _priority_label(float(raw.get("priority") or 0.0)),
                "motivation": float(raw.get("motivation") or 0.0),
                "motivation_label": _pct(raw.get("motivation")),
                "alignment_score": float(raw.get("alignment_score") or 0.0),
                "alignment_label": _pct(raw.get("alignment_score")),
                "progress": float(raw.get("progress") or 0.0),
                "progress_label": _pct(raw.get("progress")),
                "status": str(raw.get("status") or "active"),
            }
        )

    current_focus = summary.get("current_focus")
    focus_label = "—"
    if current_focus:
        for goal in goals:
            if goal.get("goal_id") == current_focus:
                focus_label = str(goal.get("description") or "—")
                break

    return {
        "current_focus_id": current_focus,
        "current_focus_label": focus_label[:200],
        "motivation_baseline": float(summary.get("motivation_baseline") or 0.6),
        "motivation_baseline_label": _pct(summary.get("motivation_baseline")),
        "active_goal_count": len(goals),
        "goals": goals[:8],
        "proactive": {
            "should_trigger": bool(proactive.get("should_trigger")),
            "reason": str(proactive.get("reason") or ""),
            "suggested_action": str(proactive.get("suggested_action") or ""),
            "priority": float(proactive.get("priority") or 0.0),
            "priority_label": _pct(proactive.get("priority")),
            "goal_id": proactive.get("goal_id"),
        },
        "last_updated_ago": _ago(summary.get("last_updated")),
    }


def _memory_items(runtime: "CognitiveRuntime", goal_layer: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    top_goal = goal_layer.get("top_goal")
    if top_goal:
        items.append(
            {
                "id": top_goal.get("goal_id", "goal-top"),
                "title": top_goal.get("description", "—")[:120],
                "tag": "goal",
                "desc": f"长期目标 · Progress {_pct(top_goal.get('progress'))}",
                "meta": f"Progress: {_pct(top_goal.get('progress'))}",
            }
        )

    belief = _top_belief(runtime.belief_engine)
    items.append(
        {
            "id": belief.get("belief_id", "belief-top"),
            "title": str(belief["content"])[:120],
            "tag": "belief",
            "desc": f"核心信念 · Confidence {_pct(belief.get('confidence'))}",
            "meta": f"Confidence: {_pct(belief.get('confidence'))}",
        }
    )

    try:
        episodic = _collect_episodic_feed(runtime.memory_manager, limit=2)
        for idx, row in enumerate(episodic):
            items.append(
                {
                    "id": f"episode-{idx}",
                    "title": row["text"][:120],
                    "tag": "episode",
                    "desc": f"情节记忆 · {row['ago']}",
                    "meta": row["ago"],
                }
            )
    except Exception:
        pass

    identity = runtime.self_model.to_dict().get("identity_summary") or ""
    if identity:
        stability = runtime.state.get_stability_metrics().get("identity_stability", 0.85)
        items.append(
            {
                "id": "identity-core",
                "title": identity[:120],
                "tag": "identity",
                "desc": f"身份描述 · Stability {_pct(stability)}",
                "meta": f"Stability: {_pct(stability)}",
            }
        )

    for goal in runtime.goal_manager.active_goals(top_k=3)[1:]:
        items.append(
            {
                "id": goal.goal_id,
                "title": goal.description[:120],
                "tag": "goal",
                "desc": f"活跃目标 · Progress {_pct(goal.progress)}",
                "meta": f"Progress: {_pct(goal.progress)}",
            }
        )
    return items[:12]


def build_mind_overview(runtime: "CognitiveRuntime", state: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate runtime layers into a Mind dashboard projection."""
    goal_layer = runtime.goal_manager.observe_governance(runtime.values_governance)

    stability = state.get("stability_metrics") or {}
    overall = float(stability.get("overall_stability_score") or stability.get("overall_stability") or 0.75)
    narrative = state.get("narrative") or {}
    working_self = state.get("working_self") or {}
    self_model = state.get("self_model") or {}
    reflective = state.get("reflective") or {}
    wm_count = int(state.get("working_memory_count") or 0)

    top_goal = goal_layer.get("top_goal") or {}
    top_belief = _top_belief(runtime.belief_engine)
    conflicts = goal_layer.get("conflicts") or []
    synth = runtime.goal_manager.synthesizer.state

    alignment_raw = top_goal.get("alignment_score")
    if alignment_raw is None:
        value_alignment = goal_layer.get("value_alignment")
        if isinstance(value_alignment, dict):
            alignment_raw = value_alignment.get("alignment_score")
    alignment = float(alignment_raw or 0.0)

    focus_title = working_self.get("goal_focus") or top_goal.get("description") or "—"
    identity_summary = (
        self_model.get("identity_summary")
        or narrative.get("summary")
        or "身份尚未建立"
    )

    chat_context = {
        "goal": (top_goal.get("description") or "—")[:80],
        "belief": str(top_belief.get("content", "—"))[:80],
        "identity": str(identity_summary)[:80],
    }

    identity_card = {
        "summary": identity_summary[:200],
        "stability": float(stability.get("identity_stability") or 0.0),
        "stability_label": _pct(stability.get("identity_stability")),
        "consistency": float(stability.get("self_consistency") or narrative.get("coherence") or 0.0),
        "consistency_label": _pct(stability.get("self_consistency") or narrative.get("coherence")),
        "updated_ago": _ago(self_model.get("last_reconstruction") or state.get("timestamp")),
    }
    belief_card = {
        "content": str(top_belief.get("content", "—"))[:200],
        "confidence": float(top_belief.get("confidence") or 0.0),
        "confidence_label": _pct(top_belief.get("confidence")),
        "evidence_count": int(top_belief.get("evidence_count") or 0),
        "conflict_count": len(conflicts),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "goal_layer": goal_layer,
        "personality": _build_personality_observation(runtime, identity_card, belief_card),
        "intent": _build_intent_observation(runtime),
        "cards": {
            "goal": {
                "title": top_goal.get("description") or "暂无活跃长期目标",
                "progress": float(top_goal.get("progress") or 0.0),
                "progress_label": _pct(top_goal.get("progress")),
                "alignment": alignment,
                "alignment_label": _pct(alignment),
                "priority": float(top_goal.get("priority") or 0.0),
                "priority_label": _priority_label(float(top_goal.get("priority") or 0.0)),
            },
            "identity": identity_card,
            "belief": belief_card,
            "focus": {
                "title": str(focus_title)[:200],
                "attention": float(working_self.get("cognitive_load") or stability.get("cognitive_load") or 0.5),
                "attention_label": _priority_label(float(working_self.get("cognitive_load") or 0.5)),
                "duration_label": _ago(synth.last_synthesis_at),
                "related_goals": int(goal_layer.get("active_goal_count") or 0),
            },
        },
        "feeds": {
            "episodic": _collect_episodic_feed(runtime.memory_manager),
            "reflections": _collect_reflection_feed(runtime.reflection_pipeline),
            "changes": _collect_changes(runtime, goal_layer),
        },
        "system": {
            "health_score": overall,
            "health_label": _health_label(overall),
            "memory_capacity_pct": _memory_capacity_pct(runtime.memory_manager, wm_count),
            "governance_label": "正常" if not conflicts else f"{len(conflicts)} 冲突待调和",
            "governance_conflicts": len(conflicts),
            "reflective_active": int(reflective.get("active_count") or 0),
            "last_governance_at": state.get("governance_loop", {}).get("last_run_at"),
            "last_update_ago": _ago(state.get("timestamp")),
            "api_online": True,
        },
        "chat_context": chat_context,
        "memory_items": _memory_items(runtime, goal_layer),
    }

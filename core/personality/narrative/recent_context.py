"""L3-1 — short-term narrative context from Σ.T interaction_step rows (read-only, in-memory)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def format_recent_narrative(steps: List[Dict[str, Any]]) -> str:
    """Aggregate interaction_step dicts into a chronological plain-text ledger."""
    if not steps:
        return ""
    lines: List[str] = []
    for row in steps:
        line = _format_step_line(row)
        if line:
            lines.append(line)
    return "\n".join(lines)


def build_recent_narrative_prompt_block(steps: List[Dict[str, Any]]) -> str:
    """Prompt block: short-term continuity (distinct from long-term identity anchor)."""
    body = format_recent_narrative(steps)
    if not body:
        return ""
    return (
        "【Recent Activity — short-term continuity (Σ.T read-only)】\n"
        "The following is a recent interaction ledger (what just happened), "
        "not your long-term identity or autobiographical story:\n"
        f"{body}"
    )


def load_recent_narrative_prompt_block(
    base_dir: Optional[str],
    *,
    since_hours: float = 24.0,
    limit: int = 12,
) -> str:
    """Read Σ.T shards and return formatted recent_narrative block (empty when unavailable)."""
    if not base_dir:
        return ""
    from core.runtime.trace_store import read_recent_interaction_steps

    steps = read_recent_interaction_steps(
        base_dir,
        since_hours=since_hours,
        limit=limit,
    )
    return build_recent_narrative_prompt_block(steps)


def _format_step_line(row: Dict[str, Any]) -> str:
    step = str(row.get("step") or row.get("phase") or "interaction").strip()
    if not step:
        step = "interaction"
    ts = row.get("ts")
    time_label = ""
    if isinstance(ts, (int, float)):
        time_label = datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%m-%d %H:%M UTC")
    tid = row.get("trace_id")
    tid_bit = ""
    if tid:
        tid_s = str(tid)
        tid_bit = f" trace={tid_s}" if len(tid_s) <= 24 else f" trace={tid_s[:20]}…"
    prefix = f"• {time_label} — " if time_label else "• "
    return f"{prefix}{step}{tid_bit}".strip()

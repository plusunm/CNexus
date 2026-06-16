"""Append-only L3 / boot execution trace for replay diagnostics."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

_lock = threading.Lock()
_configured_dir: Optional[str] = None


def configure_execution_trace(base_dir: str) -> None:
    global _configured_dir
    _configured_dir = str(base_dir)


def append_execution_trace(base_dir: Optional[str], row: Dict[str, Any]) -> None:
    root = base_dir or _configured_dir
    if not root:
        return
    path = Path(root) / "execution_trace.jsonl"
    payload = {
        "ts": time.time(),
        "mono_ms": int(time.monotonic() * 1000),
        **row,
    }
    line = json.dumps(payload, ensure_ascii=False, default=str) + "\n"
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)


def trace_file_path(base_dir: Optional[str] = None) -> Optional[Path]:
    root = base_dir or _configured_dir
    if not root:
        return None
    return Path(root) / "execution_trace.jsonl"


def trace_stats(base_dir: Optional[str] = None, *, tail_lines: int = 80) -> Dict[str, Any]:
    """Lightweight event-fabric probe — tail read only, safe for debug endpoint."""
    path = trace_file_path(base_dir)
    if path is None or not path.exists():
        return {
            "path": str(path) if path else None,
            "exists": False,
            "total_lines": 0,
            "l3_tick_count": 0,
            "last_tick_ms": None,
            "last_event_type": None,
            "flow_active": False,
        }

    lines: list[str] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
    except OSError:
        return {
            "path": str(path),
            "exists": True,
            "readable": False,
            "total_lines": 0,
            "l3_tick_count": 0,
            "last_tick_ms": None,
            "last_event_type": None,
            "flow_active": False,
        }

    sample = lines[-tail_lines:] if tail_lines > 0 else lines
    l3_ticks = 0
    interaction_steps = 0
    last_tick_ms: Optional[int] = None
    last_event_type: Optional[str] = None
    for raw in sample:
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        last_event_type = str(row.get("type") or last_event_type)
        if row.get("type") == "l3_tick":
            l3_ticks += 1
            mono = row.get("mono_ms")
            if isinstance(mono, (int, float)):
                last_tick_ms = int(mono)
        elif row.get("type") == "interaction_step":
            interaction_steps += 1

    now_mono = int(time.monotonic() * 1000)
    recent = last_tick_ms is not None and (now_mono - last_tick_ms) < 60_000
    return {
        "path": str(path),
        "exists": True,
        "readable": True,
        "total_lines": len(lines),
        "l3_tick_count": l3_ticks,
        "interaction_step_count": interaction_steps,
        "last_tick_ms": last_tick_ms,
        "last_event_type": last_event_type,
        "flow_active": l3_ticks > 0 and recent,
        "no_flow": l3_ticks == 0,
    }

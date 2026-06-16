"""Track CNexus warm threads for linkage debug and self-healing."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

_lock = threading.Lock()
_threads: Dict[str, Dict[str, Any]] = {}

RUNTIME_WARM_ROLE = "runtime_warm"
COGNITIVE_WARM_ROLE = "cognitive_warm"


def register_warm_thread(role: str, thread: threading.Thread, *, name: Optional[str] = None) -> None:
    with _lock:
        _threads[role] = {
            "role": role,
            "name": name or thread.name,
            "thread_id": thread.ident,
            "spawn_mono": time.monotonic(),
            "spawn_ts": time.time(),
            "thread": thread,
        }


def thread_snapshot(role: str) -> Dict[str, Any]:
    with _lock:
        entry = _threads.get(role)
        if not entry:
            return {
                "role": role,
                "registered": False,
                "thread_alive": False,
                "name": None,
                "last_spawn_ts": None,
                "age_ms": None,
            }
        thread = entry.get("thread")
        alive = bool(thread and thread.is_alive())
        spawn_mono = entry.get("spawn_mono")
        age_ms = int((time.monotonic() - spawn_mono) * 1000) if spawn_mono is not None else None
        return {
            "role": role,
            "registered": True,
            "name": entry.get("name"),
            "thread_alive": alive,
            "last_spawn_ts": entry.get("spawn_ts"),
            "age_ms": age_ms,
        }


def all_thread_snapshots() -> Dict[str, Dict[str, Any]]:
    return {
        RUNTIME_WARM_ROLE: thread_snapshot(RUNTIME_WARM_ROLE),
        COGNITIVE_WARM_ROLE: thread_snapshot(COGNITIVE_WARM_ROLE),
    }

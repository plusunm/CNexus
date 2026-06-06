"""In-memory runtime log ring buffer for brain-memory-ui API."""

from __future__ import annotations

import asyncio
import threading
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Set

MAX_LOGS = 500

_lock = threading.Lock()
_logs: Deque[Dict[str, Any]] = deque(maxlen=MAX_LOGS)
_subscribers: Set[asyncio.Queue] = set()


def runtime_log(
    level: str,
    category: str,
    message: str,
    **meta: Any,
) -> Dict[str, Any]:
    entry = {
        "id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "category": category,
        "message": message,
        "meta": meta or {},
    }
    with _lock:
        _logs.append(entry)
    _broadcast(entry)
    return entry


def get_logs(limit: int = 100, level: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_logs)
    if level:
        items = [e for e in items if e["level"] == level]
    return items[-limit:]


def clear_logs() -> int:
    with _lock:
        count = len(_logs)
        _logs.clear()
    runtime_log("info", "system", f"Cleared {count} log entries")
    return count


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


def _broadcast(entry: Dict[str, Any]) -> None:
    dead = []
    for q in list(_subscribers):
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            dead.append(q)
        except RuntimeError:
            dead.append(q)
    for q in dead:
        _subscribers.discard(q)
